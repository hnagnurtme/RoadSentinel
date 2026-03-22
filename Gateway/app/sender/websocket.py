"""
websocket.py – Send driver events to the backend over a persistent WebSocket.

Uses the `websockets` library (async) wrapped in its own thread so the
caller doesn't need to manage an asyncio event loop.
The sender reconnects automatically when the connection drops.
"""

import asyncio
import json
import queue
import threading

import websockets
from websockets.exceptions import ConnectionClosed

from app.utils.config import SenderConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WebSocketSender:
    """
    Thread-safe WebSocket sender.

    1. Call start() to spawn a background thread with its own asyncio loop.
    2. Call send(payload) from any thread to enqueue a message.
    3. Call stop() to shut down gracefully.
    """

    def __init__(self, cfg: SenderConfig) -> None:
        self._cfg = cfg
        self._queue: queue.Queue[dict] = queue.Queue(maxsize=cfg.queue_maxsize)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background asyncio thread."""
        logger.info("Starting WebSocket sender → %s", self._cfg.ws_url)
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="WSSenderThread"
        )
        self._thread.start()

    def send(self, payload: dict) -> None:
        """
        Enqueue a payload dict to be sent over the WebSocket.
        Non-blocking; returns immediately.
        """
        try:
            self._queue.put_nowait(payload)
            return
        except queue.Full:
            # Keep recent events by dropping the oldest pending message.
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass

        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            logger.warning("WS queue full; dropping payload.")

    def stop(self) -> None:
        """Signal the background thread to stop and wait for it to finish."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("WebSocket sender stopped.")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        """Entry point for the background thread: owns an asyncio event loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._send_loop())
        finally:
            self._loop.close()

    async def _send_loop(self) -> None:
        """
        Maintain the WebSocket connection and drain the message queue.
        Reconnects whenever the connection is lost.
        """
        while not self._stop_event.is_set():
            try:
                async with websockets.connect(
                    self._cfg.ws_url, ping_interval=20, ping_timeout=10
                ) as ws:
                    logger.info("WebSocket connected to %s", self._cfg.ws_url)
                    await self._drain_queue(ws)
            except ConnectionClosed as exc:
                logger.warning("WebSocket connection closed: %s", exc)
            except Exception as exc:
                logger.error(
                    "WebSocket error: %s – reconnecting in %.1f s",
                    exc,
                    self._cfg.reconnect_delay,
                )
            if not self._stop_event.is_set():
                await asyncio.sleep(self._cfg.reconnect_delay)

    async def _drain_queue(self, ws) -> None:
        """Send messages from the queue until the stop event is set."""
        while not self._stop_event.is_set():
            # Poll the queue without blocking the event loop
            try:
                payload = self._queue.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue

            message = json.dumps(payload)
            await ws.send(message)
            logger.debug("WS sent: %s", message)
