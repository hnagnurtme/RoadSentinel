"""WebSocket endpoints for alerts, camera frames, and browser viewers."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Callable, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from application.alert.commands.create_alert import CreateAlertCommand
from application.alert.commands.create_alert_handler import CreateAlertHandler
from core.ai.evidence_pipeline import DriverEvidencePipeline
from domain.alert.value_objects import AlertType
from infrastructure.repositories.alert_repository_impl import AlertRepositoryImpl
from infrastructure.mqtt import mqtt_client
from interfaces.api.v1.camera_processor import CameraFrameProcessor
from shared.config import settings

logger = logging.getLogger("roadsentinel.ws")


def create_save_alert_function(
    alert_type: str,
) -> Callable[[object, str, str | None], dict | None]:
    """Create a save_alert function for a specific alert type."""

    def save_alert(db: object, message: str, evidence_url: str | None) -> dict | None:
        """Create an alert record through the application layer and return its
        serialised form."""
        repository = AlertRepositoryImpl(db)  # type: ignore[arg-type]
        handler = CreateAlertHandler(repository)

        # Map lowercase event keys to uppercase AlertType enum values
        alert_type_mapping = {
            "sleeping": "SLEEPING",
            "using_phone": "USING_PHONE",
            "distracted": "DISTRACTED",
            "drowsy": "SLEEPING",  # Map drowsy to SLEEPING for escalation
        }

        mapped_alert_type = alert_type_mapping.get(alert_type, "SLEEPING")
        domain_alert_type = AlertType(mapped_alert_type)

        from infrastructure.db.models.user.tables import DrivingSession
        driver_id = settings.DRIVER_EVENT_FALLBACK_DRIVER_ID
        try:
            active_session = (
                db.query(DrivingSession)
                .filter(DrivingSession.status == "ACTIVE")
                .order_by(DrivingSession._created_at.desc())
                .first()
            )
            if active_session:
                driver_id = active_session.user_id
        except Exception as e:
            logger.error(f"Error querying active driving session for alert: {e}")

        alert = handler.handle(
            CreateAlertCommand(
                message=message,
                alert_type=domain_alert_type,
                device_id=settings.DRIVER_EVENT_FALLBACK_DEVICE_ID,
                driver_id=driver_id,
                vehicle_id=settings.DRIVER_EVENT_FALLBACK_VEHICLE_ID,
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


class AppealsWebSocketManager:
    """Fan-out broadcast channel for appeal events."""

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

    async def send_raw_frame(self, jpeg_bytes: bytes) -> None:
        """Send raw JPEG frame to all connected frontend viewers."""
        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_bytes(jpeg_bytes)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


alerts_ws_manager = AlertsWebSocketManager()
appeals_ws_manager = AppealsWebSocketManager()
camera_mgr = CameraManager()
frontend_mgr = FrontendManager()

router = APIRouter(prefix="/ws", tags=["websocket"])


class _GraceTracker:
    """Tracks a short grace window for the last active event."""

    def __init__(self, grace_seconds: float) -> None:
        self._grace = grace_seconds
        self._last_seen_at: Optional[float] = None
        self._last_conf: float = 0.0

    def record(self, conf: float, now: float) -> None:
        """Record the latest active observation."""
        self._last_seen_at = now
        self._last_conf = max(conf, self._last_conf * 0.9)

    def is_active(self, now: float) -> bool:
        """Return True while the grace window is still valid."""
        return (
            self._last_seen_at is not None and (now - self._last_seen_at) < self._grace
        )

    @property
    def last_conf(self) -> float:
        return self._last_conf


async def _broadcast_saved_alert(saved_alert: dict) -> None:
    await alerts_ws_manager.broadcast({"event": "alert.created", "data": saved_alert})
    await frontend_mgr.broadcast(
        json.dumps({"type": "alert_created", "data": saved_alert})
    )


async def _persist_and_broadcast(
    pipeline: DriverEvidencePipeline, confidence: float
) -> None:
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
    if raw_event == "sleeping":
        sleep_grace.record(raw_conf, now)
        return "sleeping", raw_conf
    if sleep_grace.is_active(now):
        return "sleeping", max(raw_conf, sleep_grace.last_conf)

    if raw_event == "using_phone":
        phone_grace.record(raw_conf, now)
        return "using_phone", raw_conf
    if phone_grace.is_active(now):
        return "using_phone", max(raw_conf, phone_grace.last_conf)

    if raw_event == "distracted":
        distracted_grace.record(raw_conf, now)
        return "distracted", raw_conf
    if distracted_grace.is_active(now):
        return "distracted", max(raw_conf, distracted_grace.last_conf)

    if raw_event == "drowsy":
        drowsy_grace.record(raw_conf, now)
        return "drowsy", raw_conf
    if drowsy_grace.is_active(now):
        return "drowsy", max(raw_conf, drowsy_grace.last_conf)

    return raw_event, raw_conf


@router.websocket("/alerts")
async def alerts_websocket(websocket: WebSocket) -> None:
    await alerts_ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        alerts_ws_manager.disconnect(websocket)


@router.websocket("/appeals")
async def appeals_websocket(websocket: WebSocket) -> None:
    await appeals_ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        appeals_ws_manager.disconnect(websocket)


@router.websocket("/camera")
async def camera_websocket(websocket: WebSocket) -> None:
    await camera_mgr.connect(websocket)

    processor = CameraFrameProcessor()
    frame_idx: int = 0
    t_last_log: float = time.time()
    last_alert_sent_at: dict[str, float] = {}

    try:
        while True:
            data = await websocket.receive()

            if data.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect(code=data.get("code", 1000))

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

            jpeg_bytes: Optional[bytes] = data.get("bytes")
            if not jpeg_bytes:
                continue

            frame_idx += 1
            now = time.monotonic()

            result = processor.process_frame(jpeg_bytes, frame_idx, now)

            await frontend_mgr.send_raw_frame(jpeg_bytes)

            if result.detections or result.event:
                display_event = result.event
                if result.all_events and len(result.all_events) > 1:
                    display_event = " + ".join(result.all_events)

                event_timing = None
                if (
                    display_event
                    and display_event != "normal"
                    and display_event != "unknown"
                ):
                    current_event = result.event
                    if current_event is None:
                        continue
                    duration_sec = processor.event_logic.get_event_duration(
                        current_event, now
                    )
                    event_timing = {
                        "active": True,
                        "event": display_event,
                        "started_at": None,
                        "duration_ms": int(duration_sec * 1000),
                        "confidence": result.confidence,
                    }

                frame_message = {
                    "type": "frame",
                    "frame_idx": frame_idx,
                    "jpeg": None,  # Binary frame already sent separately
                    "detections": result.detections,
                    "event": display_event,
                    "confidence": result.confidence,
                    "event_timing": event_timing,
                    "timestamp": now,
                }
                await frontend_mgr.broadcast(json.dumps(frame_message))

            if result.should_save_evidence and result.event:
                pipeline = processor.pipelines.get(result.event)
                if pipeline:
                    logger.info(
                        "[AI] Triggering async persistence for %s", result.event
                    )
                    asyncio.create_task(
                        _persist_and_broadcast(pipeline, result.confidence)
                    )

            # MQTT Publishing (Delayed and with 'normal' state)
            if result.mqtt_event:
                mqtt_client.publish(
                    result.mqtt_event,
                    result.mqtt_payload
                )

            if result.should_broadcast and result.event:
                last_sent = last_alert_sent_at.get(result.event, 0.0)
                if now - last_sent >= settings.DRIVER_EVENT_ALERT_COOLDOWN_SECONDS:
                    display_event = result.event
                    if result.all_events and len(result.all_events) > 1:
                        display_event = " + ".join(result.all_events)

                    await frontend_mgr.broadcast(
                        json.dumps(
                            {
                                "type": "driver_event",
                                "event": display_event,
                                "confidence": result.confidence,
                                "drowsy_duration": processor.event_logic.get_drowsy_duration(
                                    now
                                ),
                                "escalated": result.escalated,
                            }
                        )
                    )
                    
                    last_alert_sent_at[result.event] = now

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
        processor.reset()
        camera_mgr.disconnect()


@router.websocket("/frontend")
async def frontend_websocket(websocket: WebSocket) -> None:
    await frontend_mgr.connect(websocket)

    try:
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
