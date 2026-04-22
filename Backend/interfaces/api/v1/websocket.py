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
import base64
import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.ai.engine import SKIP_FRAMES, filter_detections, inference_engine
from core.ai.event_classifier import ALERT_EVENTS, DriverEventClassifier, WindowTrigger
from core.ai.evidence_pipeline import DriverEvidencePipeline, build_evidence_pipelines
from infrastructure.db.session import SessionLocal
from shared.config import settings

logger = logging.getLogger("roadsentinel.ws")


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
            self._last_seen_at is not None
            and (now - self._last_seen_at) < self._grace
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
    saved_alert = await loop.run_in_executor(None, pipeline.save_event_alert, confidence)
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

    # ── Per-session state ─────────────────────────────────────────────────
    frame_idx: int = 0
    t_last_log: float = time.time()
    last_dets: list[dict] = []

    event_logic = DriverEventClassifier()
    sleep_pipeline, phone_pipeline, distracted_pipeline = build_evidence_pipelines(
        SessionLocal
    )

    # WindowTrigger fires once when the event has been active for the full
    # evidence window (100 % occupancy = event must be active every frame).
    sleep_trigger = WindowTrigger(
        fps=settings.DRIVER_EVENT_EVIDENCE_FPS,
        window_seconds=settings.DRIVER_EVENT_EVIDENCE_SECONDS,
        occupancy_threshold=1.0,
    )
    phone_trigger = WindowTrigger(
        fps=settings.DRIVER_EVENT_EVIDENCE_FPS,
        window_seconds=settings.DRIVER_EVENT_EVIDENCE_SECONDS,
        occupancy_threshold=1.0,
    )
    # Distracted evidence: 70 % occupancy (driver can briefly look back).
    distracted_trigger = WindowTrigger(
        fps=settings.DRIVER_EVENT_EVIDENCE_FPS,
        window_seconds=settings.DRIVER_EVENT_EVIDENCE_SECONDS,
        occupancy_threshold=0.7,
    )

    # Grace-period trackers — prevent flickering between detections.
    sleep_grace = _GraceTracker(settings.DRIVER_EVENT_SLEEPING_RELEASE_GRACE_SECONDS)
    phone_grace = _GraceTracker(settings.DRIVER_EVENT_PHONE_RELEASE_GRACE_SECONDS)
    distracted_grace = _GraceTracker(settings.DRIVER_EVENT_DISTRACTED_RELEASE_GRACE_SECONDS)
    drowsy_grace = _GraceTracker(settings.DRIVER_EVENT_DROWSY_RELEASE_GRACE_SECONDS)

    # Evidence buffer state flags.
    was_sleeping: bool = False
    was_phone: bool = False
    was_distracted: bool = False

    # Async evidence-persist tasks (one per event type).
    sleep_task: Optional[asyncio.Task] = None
    phone_task: Optional[asyncio.Task] = None
    distracted_task: Optional[asyncio.Task] = None

    last_event: str = "normal"
    last_confidence: float = 0.0
    current_event_started_at: Optional[float] = None
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

            # Run YOLO every SKIP_FRAMES to balance latency vs CPU load.
            if frame_idx % SKIP_FRAMES == 0:
                loop = asyncio.get_running_loop()
                raw_dets = await loop.run_in_executor(
                    None, inference_engine.run_inference, jpeg_bytes
                )
                last_dets = filter_detections(raw_dets)

            # ── Classify + apply grace periods ────────────────────────────
            raw_event, raw_conf = event_logic.classify(last_dets, now=now)
            event, confidence = _apply_grace_periods(
                raw_event, raw_conf, now,
                sleep_grace, phone_grace, distracted_grace, drowsy_grace,
            )

            # ── Drowsy escalation check ───────────────────────────────────
            drowsy_duration = event_logic.get_drowsy_duration(now)
            drowsy_escalated = (
                event == "drowsy"
                and drowsy_duration >= settings.DRIVER_EVENT_DROWSY_ESCALATION_SECONDS
            )

            # ── Track event start time ─────────────────────────────────────
            prev_event = last_event
            if event != prev_event:
                current_event_started_at = now if event in ALERT_EVENTS else None

            event_duration_ms: int = 0
            if event in ALERT_EVENTS and current_event_started_at is not None:
                event_duration_ms = int(
                    max(0.0, now - current_event_started_at) * 1000
                )

            # ── Evidence buffer management ────────────────────────────────
            is_sleeping = event == "sleeping"
            is_phone = event == "using_phone"
            is_distracted = event == "distracted"

            # Sleeping evidence
            if is_sleeping:
                if not was_sleeping:
                    sleep_pipeline.reset_buffer()
                sleep_pipeline.push_frame(
                    jpeg_bytes,
                    detections=last_dets,
                    event=event,
                    duration_ms=event_duration_ms,
                    confidence=confidence,
                )
            elif was_sleeping:
                sleep_pipeline.reset_buffer()

            # Phone evidence
            if is_phone:
                if not was_phone:
                    phone_pipeline.reset_buffer()
                phone_pipeline.push_frame(
                    jpeg_bytes,
                    detections=last_dets,
                    event=event,
                    duration_ms=event_duration_ms,
                    confidence=confidence,
                )
            elif was_phone:
                phone_pipeline.reset_buffer()

            # Distracted evidence
            if is_distracted:
                if not was_distracted:
                    distracted_pipeline.reset_buffer()
                distracted_pipeline.push_frame(
                    jpeg_bytes,
                    detections=last_dets,
                    event=event,
                    duration_ms=event_duration_ms,
                    confidence=confidence,
                )
            elif was_distracted:
                distracted_pipeline.reset_buffer()

            was_sleeping = is_sleeping
            was_phone = is_phone
            was_distracted = is_distracted

            # ── Evidence persistence triggers ─────────────────────────────
            if sleep_trigger.update(is_sleeping):
                if sleep_task is None or sleep_task.done():
                    sleep_task = asyncio.create_task(
                        _persist_and_broadcast(sleep_pipeline, confidence)
                    )
                else:
                    logger.info("Sleep evidence save skipped — previous still running")

            if phone_trigger.update(is_phone):
                if phone_task is None or phone_task.done():
                    phone_task = asyncio.create_task(
                        _persist_and_broadcast(phone_pipeline, confidence)
                    )
                else:
                    logger.info("Phone evidence save skipped — previous still running")

            if distracted_trigger.update(is_distracted):
                if distracted_task is None or distracted_task.done():
                    distracted_task = asyncio.create_task(
                        _persist_and_broadcast(distracted_pipeline, confidence)
                    )
                else:
                    logger.info("Distracted evidence save skipped — previous still running")

            # ── Real-time alert broadcast ─────────────────────────────────
            if event in ALERT_EVENTS:
                # Minimum stable duration before emitting (avoids transient alerts).
                min_stable_secs: dict[str, float] = {
                    "using_phone": settings.DRIVER_EVENT_PHONE_MIN_ALERT_SECONDS,
                    "drowsy": settings.DRIVER_EVENT_DROWSY_MIN_ALERT_SECONDS,
                }
                stable_secs = (
                    (now - current_event_started_at)
                    if current_event_started_at is not None
                    else 0.0
                )
                if stable_secs < min_stable_secs.get(event, 0.0):
                    last_event = event
                    last_confidence = confidence
                    continue

                last_sent = last_alert_sent_at.get(event, 0.0)
                should_emit = event != prev_event or (
                    now - last_sent
                ) >= settings.DRIVER_EVENT_ALERT_COOLDOWN_SECONDS

                if should_emit:
                    alert_payload = {
                        "type": "driver_alert",
                        "event": event,
                        "confidence": round(confidence, 4),
                        "timestamp": time.time(),
                        "device": camera_mgr.device_id,
                        "frame_idx": frame_idx,
                        "detections": len(last_dets),
                        # Drowsy escalation flag — frontend should increase urgency.
                        "escalated": drowsy_escalated,
                        "drowsy_duration_s": round(drowsy_duration, 1),
                    }
                    await frontend_mgr.broadcast(json.dumps(alert_payload))
                    await alerts_ws_manager.broadcast(
                        {
                            "event": "gateway.alert",
                            "data": {
                                "device_id": camera_mgr.device_id,
                                "event": event,
                                "confidence": round(confidence, 4),
                                "frame_idx": frame_idx,
                                "timestamp": alert_payload["timestamp"],
                                "escalated": drowsy_escalated,
                            },
                        }
                    )
                    last_alert_sent_at[event] = now

            last_event = event
            last_confidence = confidence

            # ── Broadcast live frame to browser viewers ───────────────────
            if frontend_mgr.has_clients:
                payload = json.dumps(
                    {
                        "type": "frame",
                        "frame_idx": frame_idx,
                        "timestamp": time.time(),
                        "jpeg": base64.b64encode(jpeg_bytes).decode(),
                        "detections": last_dets,
                        "driver_event": last_event,
                        "driver_confidence": round(last_confidence, 4),
                        "event_timing": {
                            "active": last_event in ALERT_EVENTS,
                            "event": last_event,
                            "started_at": current_event_started_at,
                            "duration_ms": event_duration_ms,
                            "confidence": round(last_confidence, 4),
                        },
                        "drowsy_escalated": drowsy_escalated,
                        "drowsy_duration_s": round(drowsy_duration, 1),
                        "device": camera_mgr.device_id,
                    }
                )
                await frontend_mgr.broadcast(payload)

            # Periodic diagnostic log (every 5 s)
            now_wall = time.time()
            if now_wall - t_last_log >= 5.0:
                logger.info(
                    "[CAMERA] frame=%d  event=%s  conf=%.2f  drowsy_dur=%.1fs  dets=%d  viewers=%d",
                    frame_idx,
                    last_event,
                    last_confidence,
                    drowsy_duration,
                    len(last_dets),
                    frontend_mgr.client_count,
                )
                t_last_log = now_wall

    except WebSocketDisconnect:
        pass
    finally:
        camera_mgr.disconnect()
        event_logic.reset()
        for task in (sleep_task, phone_task, distracted_task):
            if task is not None and not task.done():
                task.cancel()
        await frontend_mgr.broadcast(json.dumps({"type": "camera_offline"}))


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
