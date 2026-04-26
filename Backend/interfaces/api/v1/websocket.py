"""
interfaces/api/v1/websocket.py
-------------------------------
WebSocket endpoints:
  /ws/alerts    — alert broadcast channel (browser dashboards)
  /ws/camera    — ESP32-CAM binary JPEG stream (also at /ws/camera root)
  /ws/frontend  — browser viewer channel (live frames + driver events)

All AI classification lives in ``core/ai/``.  This module wires transport to
the AI engine.

Grace-period design
-------------------
Each dangerous event has a short *grace period* so the UI does not flicker
when the YOLO model misses a detection for 1-2 frames.  The priority order
is strictly:

  sleeping  >  using_phone  >  distracted  >  drowsy

A lower-priority grace period only applies when no higher-priority event is
currently active or in grace.

Drowsy escalation
-----------------
If the driver is continuously drowsy for >= DROWSY_ESCALATION_SECONDS the
broadcast payload carries ``escalated: true`` so the frontend/device can
increase alarm urgency (sound louder, more visible indicator) without changing
the DB event type.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from application.alert.commands.create_alert import CreateAlertCommand
from application.alert.commands.create_alert_handler import CreateAlertHandler
from core.ai.evidence_pipeline import DriverEvidencePipeline
from domain.alert.value_objects import AlertType
from infrastructure.repositories.alert_repository_impl import AlertRepositoryImpl
from interfaces.api.v1.camera_processor import CameraFrameProcessor
from shared.config import settings

logger = logging.getLogger("roadsentinel.ws")


def create_save_alert_function(alert_type: str) -> callable:
    """Create a save_alert function for a specific alert type."""

    def save_alert(db: object, message: str, evidence_url: str | None) -> dict | None:
        """Create an alert record through the application layer and return its
        serialised form."""
        repository = AlertRepositoryImpl(db)  # type: ignore[arg-type]
        handler = CreateAlertHandler(repository)

        # Convert string alert_type to domain AlertType enum
        domain_alert_type = AlertType(alert_type)

        alert = handler.handle(
            CreateAlertCommand(
                message=message,
                alert_type=domain_alert_type,
                device_id=settings.DRIVER_EVENT_ALERT_DEVICE_ID,
                driver_id=settings.DRIVER_EVENT_ALERT_DRIVER_ID,
                vehicle_id=settings.DRIVER_EVENT_ALERT_VEHICLE_ID,
                evidence_url=evidence_url,
                latitude=None,
                longitude=None,
            )
        )
        return {
            "_id": str(alert._id) if alert._id else None,
            "message": alert.message,
            "alert_type": alert.alert_type.value,
            "device_id": str(alert.device_id),
            "driver_id": str(alert.driver_id) if alert.driver_id else None,
            "vehicle_id": str(alert.vehicle_id) if alert.vehicle_id else None,
            "evidence_url": alert.evidence_url,
            "latitude": alert.latitude,
            "longitude": alert.longitude,
            "user": None,
            "vehicle": None,
            "_created_at": alert._created_at.isoformat() if alert._created_at else None,
            "_updated_at": alert._updated_at.isoformat() if alert._updated_at else None,
            "_deleted_at": alert._deleted_at.isoformat() if alert._deleted_at else None,
        }

    return save_alert


# ── WebSocket Connection Managers ─────────────────────────────────────────────


class AlertsWebSocketManager:
    """Fan-out broadcast channel for alert events (browser dashboards)."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, payload: dict) -> None:
        stale: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(ws)


class CameraManager:
    """Holds the single ESP32-CAM WebSocket connection."""

    def __init__(self) -> None:
        self.ws: Optional[WebSocket] = None
        self.device_id: str = "esp32-cam"

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.ws = ws
        logger.info("ESP32-CAM connected")

    def disconnect(self) -> None:
        self.ws = None
        logger.info("ESP32-CAM disconnected")

    @property
    def is_online(self) -> bool:
        return self.ws is not None

    async def send_command(self, payload: dict) -> bool:
        """Forward a JSON command to the ESP32. Returns ``True`` on success."""
        if self.ws is None:
            return False
        try:
            await self.ws.send_text(json.dumps(payload))
            return True
        except Exception:
            self.disconnect()
            return False


class FrontendManager:
    """Holds all browser viewer WebSocket connections."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        logger.info("Browser viewer connected (total=%d)", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)
        logger.info("Browser viewer disconnected (total=%d)", len(self._connections))

    @property
    def has_clients(self) -> bool:
        return bool(self._connections)

    @property
    def client_count(self) -> int:
        return len(self._connections)

    async def broadcast(self, message: str) -> None:
        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


# ── Module-level singletons ───────────────────────────────────────────────────

alerts_ws_manager = AlertsWebSocketManager()
camera_mgr = CameraManager()
frontend_mgr = FrontendManager()

router = APIRouter(prefix="/ws", tags=["websocket"])


# ── Grace-period tracker ──────────────────────────────────────────────────────


class _GraceTracker:
    """Prevents event flickering when the model misses a detection for 1-2 frames.

    Usage::

        if raw_event == "sleeping":
            sleep_grace.record(raw_conf, now)
        elif sleep_grace.is_active(now):
            event, confidence = "sleeping", sleep_grace.last_conf
    """

    def __init__(self, grace_seconds: float) -> None:
        self._grace = grace_seconds
        self._last_seen_at: Optional[float] = None
        self._last_conf: float = 0.0

    def record(self, conf: float, now: float) -> None:
        """Call every frame the event IS actively detected."""
        self._last_seen_at = now
        self._last_conf = max(conf, self._last_conf * 0.9)  # smooth decay

    def is_active(self, now: float) -> bool:
        """True if inside the grace window (event not detected this frame)."""
        return (
            self._last_seen_at is not None and (now - self._last_seen_at) < self._grace
        )

    @property
    def last_conf(self) -> float:
        return self._last_conf


# ── Shared helpers ────────────────────────────────────────────────────────────


async def _broadcast_saved_alert(saved_alert: dict) -> None:
    """Broadcast a persisted alert to both alert and frontend channels."""
    await alerts_ws_manager.broadcast({"event": "alert.created", "data": saved_alert})
    await frontend_mgr.broadcast(
        json.dumps({"type": "alert_created", "data": saved_alert})
    )


async def _persist_and_broadcast(
    pipeline: DriverEvidencePipeline, confidence: float
) -> None:
    """Persist an alert in a thread pool then broadcast the result."""
    loop = asyncio.get_running_loop()
    saved_alert = await loop.run_in_executor(
        None, pipeline.save_event_alert, confidence
    )
    if saved_alert is not None:
        await _broadcast_saved_alert(saved_alert)


def _apply_grace_periods(
    raw_event: str,
    raw_conf: float,
    now: float,
    sleep_grace: _GraceTracker,
    phone_grace: _GraceTracker,
    distracted_grace: _GraceTracker,
    drowsy_grace: _GraceTracker,
) -> tuple[str, float]:
    """Apply grace periods in priority order to prevent UI flickering.

    Priority (highest first): sleeping > using_phone > distracted > drowsy.
    A lower-priority grace only applies if no higher-priority event wins.

    Returns:
        ``(effective_event, effective_confidence)``
    """
    # ── Sleeping (highest priority) ───────────────────────────────────────
    if raw_event == "sleeping":
        sleep_grace.record(raw_conf, now)
        return "sleeping", raw_conf
    if sleep_grace.is_active(now):
        return "sleeping", max(raw_conf, sleep_grace.last_conf)

    # ── Phone use ─────────────────────────────────────────────────────────
    if raw_event == "using_phone":
        phone_grace.record(raw_conf, now)
        return "using_phone", raw_conf
    if phone_grace.is_active(now):
        return "using_phone", max(raw_conf, phone_grace.last_conf)

    # ── Distracted ────────────────────────────────────────────────────────
    # NOTE: distracted grace only applies when no phone grace is active.
    if raw_event == "distracted":
        distracted_grace.record(raw_conf, now)
        return "distracted", raw_conf
    if distracted_grace.is_active(now):
        return "distracted", max(raw_conf, distracted_grace.last_conf)

    # ── Drowsy (early warning, lowest priority) ───────────────────────────
    if raw_event == "drowsy":
        drowsy_grace.record(raw_conf, now)
        return "drowsy", raw_conf
    if drowsy_grace.is_active(now):
        return "drowsy", max(raw_conf, drowsy_grace.last_conf)

    # No alert event — return raw classification ("normal" / "unknown").
    return raw_event, raw_conf


# ── /ws/alerts endpoint ───────────────────────────────────────────────────────


@router.websocket("/alerts")
async def alerts_websocket(websocket: WebSocket) -> None:
    """Alert broadcast channel — browser dashboards subscribe here."""
    await alerts_ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        alerts_ws_manager.disconnect(websocket)


# ── /ws/camera endpoint ───────────────────────────────────────────────────────


@router.websocket("/camera")
async def camera_websocket(websocket: WebSocket) -> None:
    """ESP32-CAM streams binary JPEG frames here."""
    await camera_mgr.connect(websocket)

    # Initialize camera processor which encapsulates all AI logic
    processor = CameraFrameProcessor()
    frame_idx: int = 0
    t_last_log: float = time.time()
    last_alert_sent_at: dict[str, float] = {}

    try:
        while True:
            data = await websocket.receive()

            # ── Text message (hello / pong / status) ─────────────────────
            if data.get("text"):
                try:
                    msg = json.loads(data["text"])
                    logger.debug("[ESP32] text message: %s", msg)
                    if msg.get("type") == "pong":
                        await frontend_mgr.broadcast(
                            json.dumps({"type": "esp32_stats", **msg})
                        )
                except Exception:
                    pass
                continue

            # ── Binary JPEG frame ─────────────────────────────────────────
            jpeg_bytes: Optional[bytes] = data.get("bytes")
            if not jpeg_bytes:
                continue

            frame_idx += 1
            now = time.monotonic()

            # Process frame using the camera processor
            result = processor.process_frame(jpeg_bytes, frame_idx, now)

            # ── Broadcast to frontend viewers ───────────────────────────
            if result.should_broadcast and result.event:
                last_sent = last_alert_sent_at.get(result.event, 0.0)
                if now - last_sent >= settings.DRIVER_EVENT_ALERT_COOLDOWN_SECONDS:
                    await frontend_mgr.broadcast(
                        json.dumps(
                            {
                                "type": "driver_event",
                                "event": result.event,
                                "confidence": result.confidence,
                                "drowsy_duration": processor.event_logic.get_drowsy_duration(
                                    now
                                ),
                                "escalated": result.escalated,
                            }
                        )
                    )
                    last_alert_sent_at[result.event] = now

            # ── Forward raw frame to frontend viewers ─────────────────────
            await frontend_mgr.send_raw_frame(jpeg_bytes)

            # ── Periodic logging (every 10 seconds) ─────────────────────
            if now - t_last_log >= 10.0:
                logger.info(
                    "[AI] frame=%d event=%s conf=%.2f dets=%d",
                    frame_idx,
                    result.event or "none",
                    result.confidence,
                    len(result.detections),
                )
                t_last_log = now

    except WebSocketDisconnect:
        pass
    finally:
        # Reset AI state on disconnect
        processor.reset()
        await camera_mgr.disconnect(websocket)


# ── /ws/frontend endpoint ─────────────────────────────────────────────────────


@router.websocket("/frontend")
async def frontend_websocket(websocket: WebSocket) -> None:
    """Browser viewers connect here to receive live frames and driver events."""
    await frontend_mgr.connect(websocket)

    await websocket.send_text(
        json.dumps(
            {
                "type": "pong",
                "camera": camera_mgr.is_online,
                "clients": frontend_mgr.client_count,
                "device": camera_mgr.device_id,
            }
        )
    )

    try:
        while True:
            text = await websocket.receive_text()
            try:
                cmd = json.loads(text)
            except Exception:
                continue

            cmd_type = cmd.get("type")

            if cmd_type == "ping":
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "pong",
                            "camera": camera_mgr.is_online,
                            "clients": frontend_mgr.client_count,
                            "device": camera_mgr.device_id,
                        }
                    )
                )

            elif cmd_type in {
                "set_quality",
                "set_framesize",
                "set_vflip",
                "set_hmirror",
                "set_camera",
            }:
                ok = await camera_mgr.send_command(cmd)
                await websocket.send_text(
                    json.dumps({"type": "ack", "cmd": cmd_type, "success": ok})
                )

    except WebSocketDisconnect:
        pass
    finally:
        frontend_mgr.disconnect(websocket)
