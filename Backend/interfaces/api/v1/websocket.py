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
        self.active_driver_id: Optional[str] = None

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.ws = ws
        logger.info("ESP32-CAM connected")

    def disconnect(self) -> None:
        self.ws = None
        self.active_driver_id = None
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
    """Holds all browser viewer WebSocket connections with their target driver_id."""

    def __init__(self) -> None:
        self._connections: dict[WebSocket, Optional[str]] = {}

    async def connect(self, ws: WebSocket, driver_id: Optional[str] = None) -> None:
        await ws.accept()
        self._connections[ws] = driver_id
        logger.info("Browser viewer connected for driver %s (total=%d)", driver_id, len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            del self._connections[ws]
        logger.info("Browser viewer disconnected (total=%d)", len(self._connections))

    @property
    def has_clients(self) -> bool:
        return bool(self._connections)

    @property
    def client_count(self) -> int:
        return len(self._connections)

    async def broadcast(self, message: str) -> None:
        dead: list[WebSocket] = []
        for ws, req_driver_id in list(self._connections.items()):
            is_authorized = (req_driver_id is None) or (req_driver_id == camera_mgr.active_driver_id)
            if is_authorized:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def send_raw_frame(self, jpeg_bytes: bytes) -> None:
        """Send raw JPEG frame to matching connected frontend viewers."""
        dead: list[WebSocket] = []
        for ws, req_driver_id in list(self._connections.items()):
            is_authorized = (req_driver_id is None) or (req_driver_id == camera_mgr.active_driver_id)
            if is_authorized:
                try:
                    await ws.send_bytes(jpeg_bytes)
                except Exception:
                    dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def broadcast_auth_update(self) -> None:
        """Broadcast updated authorization status to all connected frontend clients."""
        dead: list[WebSocket] = []
        for ws, req_driver_id in list(self._connections.items()):
            is_authorized = (req_driver_id is None) or (req_driver_id == camera_mgr.active_driver_id)
            try:
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "pong",
                            "camera": camera_mgr.is_online and is_authorized,
                            "clients": self.client_count,
                            "device": camera_mgr.device_id,
                            "authorized": is_authorized,
                            "active_driver_id": camera_mgr.active_driver_id,
                        }
                    )
                )
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


def escalate_alert_db_task(alert_id: str) -> dict | None:
    """Escalates an alert by prefixing its message in the database with DANGEROUS:"""
    from infrastructure.db.session import SessionLocal
    with SessionLocal() as db:
        from infrastructure.repositories.alert_repository_impl import AlertRepositoryImpl
        import uuid
        repository = AlertRepositoryImpl(db)
        try:
            uuid_id = uuid.UUID(alert_id)
            from infrastructure.db.models import Alert as DbAlert
            row = db.query(DbAlert).filter(DbAlert._id == uuid_id).first()
            if row and not row.message.startswith("DANGEROUS:"):
                row.message = f"DANGEROUS: {row.message}"
                db.add(row)
                db.commit()
                db.refresh(row)
                alert_entity = repository._to_entity(row)
                return {
                    "_id": str(alert_entity._id),
                    "message": alert_entity.message,
                    "alert_type": alert_entity.alert_type.value,
                    "device_id": str(alert_entity.device_id),
                    "driver_id": str(alert_entity.driver_id) if alert_entity.driver_id else None,
                    "vehicle_id": str(alert_entity.vehicle_id) if alert_entity.vehicle_id else None,
                    "evidence_url": alert_entity.evidence_url,
                    "latitude": alert_entity.latitude,
                    "longitude": alert_entity.longitude,
                }
        except Exception as e:
            logger.error(f"Error escalating alert in DB: {e}", exc_info=True)
        return None


async def _persist_and_broadcast(
    processor: CameraFrameProcessor, event_key: str, pipeline: DriverEvidencePipeline, confidence: float
) -> None:
    loop = asyncio.get_running_loop()
    saved_alert = await loop.run_in_executor(
        None, pipeline.save_event_alert, confidence
    )
    if saved_alert is not None:
        alert_id = saved_alert.get("_id")
        if alert_id:
            processor.active_alerts[event_key] = {
                "alert_id": alert_id,
                "message": saved_alert.get("message"),
                "escalated": False,
                "timestamp": time.time(),
            }
        await _broadcast_saved_alert(saved_alert)


async def _escalate_and_broadcast(
    processor: CameraFrameProcessor, event_key: str, alert_id: str
) -> None:
    loop = asyncio.get_running_loop()
    updated_alert = await loop.run_in_executor(
        None, escalate_alert_db_task, alert_id
    )
    if updated_alert:
        if event_key in processor.active_alerts:
            processor.active_alerts[event_key]["message"] = updated_alert["message"]
        
        await alerts_ws_manager.broadcast({
            "event": "alert.escalated",
            "data": updated_alert
        })
        await frontend_mgr.broadcast(
            json.dumps({"type": "alert_escalated", "data": updated_alert})
        )


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

    from infrastructure.db.session import SessionLocal
    from infrastructure.db.models.user.tables import DrivingSession

    processor = CameraFrameProcessor()

    try:
        with SessionLocal() as db:
            active_session = (
                db.query(DrivingSession)
                .filter(DrivingSession.status == "ACTIVE")
                .first()
            )
            if active_session:
                processor.active_driver_id = str(active_session.user_id)
                camera_mgr.active_driver_id = str(active_session.user_id)
                logger.info(f"[Camera WS] Restored active driver ID from DB: {camera_mgr.active_driver_id}")
    except Exception as e:
        logger.error(f"Error querying active session on camera connect: {e}")

    await frontend_mgr.broadcast_auth_update()
    frame_idx: int = 0
    t_last_log: float = time.time()
    last_alert_sent_at: dict[str, float] = {}

    # Hàng đợi chứa các frame để xử lý AI bất đồng bộ nhằm không chặn luồng nhận ảnh
    queue: asyncio.Queue[Optional[tuple[bytes, int, float]]] = asyncio.Queue(maxsize=3)
    loop = asyncio.get_running_loop()

    # Worker xử lý AI chạy nền chạy tuần tự các frame lấy từ hàng đợi
    async def ai_worker() -> None:
        nonlocal t_last_log
        while True:
            try:
                item = await queue.get()
                if item is None:
                    break  # Nhận tín hiệu dừng khi đóng kết nối

                jb, f_idx, frame_time = item

                # Đưa hàm xử lý AI CPU-bound vào thread pool để tránh chặn Event Loop chính
                result = await loop.run_in_executor(
                    None, processor.process_frame, jb, f_idx, frame_time
                )

                # Clear active alerts that are no longer active in event_logic
                for ek in list(processor.active_alerts.keys()):
                    if not processor.event_logic._event_active.get(ek, False):
                        processor.active_alerts.pop(ek, None)

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
                        if current_event is not None:
                            duration_sec = processor.event_logic.get_event_duration(
                                current_event, frame_time
                            )
                            is_dangerous = duration_sec >= 10.0
                            level = "DANGEROUS" if is_dangerous else "WARNING"
                            
                            # Handle database/websocket escalation
                            alert_info = processor.active_alerts.get(current_event)
                            if alert_info and not alert_info.get("escalated") and is_dangerous:
                                alert_info["escalated"] = True
                                asyncio.create_task(
                                    _escalate_and_broadcast(processor, current_event, alert_info["alert_id"])
                                )

                            event_timing = {
                                "active": True,
                                "event": display_event,
                                "started_at": None,
                                "duration_ms": int(duration_sec * 1000),
                                "confidence": result.confidence,
                                "level": level,
                            }

                    frame_message = {
                        "type": "frame",
                        "frame_idx": f_idx,
                        "jpeg": None,
                        "detections": result.detections,
                        "event": display_event,
                        "confidence": result.confidence,
                        "event_timing": event_timing,
                        "timestamp": frame_time,
                    }
                    await frontend_mgr.broadcast(json.dumps(frame_message))

                if result.should_save_evidence and result.event:
                    pipeline = processor.pipelines.get(result.event)
                    if pipeline:
                        logger.info(
                            "[AI Async] Triggering async persistence for %s", result.event
                        )
                        asyncio.create_task(
                            _persist_and_broadcast(processor, result.event, pipeline, result.confidence)
                        )

                # Gửi thông tin phục hồi qua MQTT
                if result.mqtt_event == "normal":
                    mqtt_client.publish(
                        result.mqtt_event,
                        result.mqtt_payload
                    )

                if result.should_broadcast and result.event:
                    last_sent = last_alert_sent_at.get(result.event, 0.0)
                    if frame_time - last_sent >= settings.DRIVER_EVENT_ALERT_COOLDOWN_SECONDS:
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
                                        frame_time
                                    ),
                                    "escalated": result.escalated,
                                }
                            )
                        )
                        last_alert_sent_at[result.event] = frame_time

                # Gửi thông tin cảnh báo vi phạm qua MQTT đồng bộ với việc lưu evidence
                if result.should_save_evidence and result.mqtt_event and result.mqtt_event != "normal":
                    mqtt_client.publish(
                        result.mqtt_event,
                        result.mqtt_payload
                    )

                if frame_time - t_last_log >= 10.0:
                    logger.info(
                        "[AI Async] frame=%d event=%s conf=%.2f dets=%d",
                        f_idx,
                        result.event or "none",
                        result.confidence,
                        len(result.detections),
                    )
                    t_last_log = frame_time

                queue.task_done()
            except Exception as e:
                logger.error(f"Error in background AI worker: {e}")

    # Chạy worker task trong background
    worker_task = asyncio.create_task(ai_worker())

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
                    elif msg.get("type") == "driver_login":
                        processor.active_driver_id = msg.get("driver_id")
                        camera_mgr.active_driver_id = msg.get("driver_id")
                        logger.info(f"[Camera WS] Active driver updated dynamically to: {processor.active_driver_id}")
                        await frontend_mgr.broadcast_auth_update()
                except Exception as e:
                    logger.error(f"Error parsing camera text message: {e}")
                continue

            jpeg_bytes: Optional[bytes] = data.get("bytes")
            if not jpeg_bytes:
                continue

            frame_idx += 1
            now = time.monotonic()

            # 1. Phát trực tiếp ảnh thô tới frontend ngay lập tức (độ trễ bằng 0)
            await frontend_mgr.send_raw_frame(jpeg_bytes)

            # 2. Đưa ảnh vào hàng đợi để xử lý AI.
            # Nếu hàng đợi bị đầy (AI chạy chậm hơn camera), bỏ bớt ảnh cũ để luôn xử lý ảnh mới nhất
            if queue.full():
                try:
                    queue.get_nowait()
                    queue.task_done()
                except asyncio.QueueEmpty:
                    pass

            await queue.put((jpeg_bytes, frame_idx, now))

    except WebSocketDisconnect:
        pass
    finally:
        # Dừng worker và thu hồi tài nguyên khi ngắt kết nối
        await queue.put(None)
        await worker_task
        processor.reset()
        camera_mgr.disconnect()
        await frontend_mgr.broadcast_auth_update()


@router.websocket("/frontend")
async def frontend_websocket(websocket: WebSocket) -> None:
    driver_id = websocket.query_params.get("driver_id")
    await frontend_mgr.connect(websocket, driver_id)

    try:
        is_authorized = (driver_id is None) or (driver_id == camera_mgr.active_driver_id)
        await websocket.send_text(
            json.dumps(
                {
                    "type": "pong",
                    "camera": camera_mgr.is_online and is_authorized,
                    "clients": frontend_mgr.client_count,
                    "device": camera_mgr.device_id,
                    "authorized": is_authorized,
                    "active_driver_id": camera_mgr.active_driver_id,
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
                is_authorized = (driver_id is None) or (driver_id == camera_mgr.active_driver_id)
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "pong",
                            "camera": camera_mgr.is_online and is_authorized,
                            "clients": frontend_mgr.client_count,
                            "device": camera_mgr.device_id,
                            "authorized": is_authorized,
                            "active_driver_id": camera_mgr.active_driver_id,
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
                is_authorized = (driver_id is None) or (driver_id == camera_mgr.active_driver_id)
                if is_authorized:
                    ok = await camera_mgr.send_command(cmd)
                    await websocket.send_text(
                        json.dumps({"type": "ack", "cmd": cmd_type, "success": ok})
                    )
                else:
                    await websocket.send_text(
                        json.dumps({"type": "ack", "cmd": cmd_type, "success": False, "error": "unauthorized"})
                    )

    except WebSocketDisconnect:
        pass
    finally:
        frontend_mgr.disconnect(websocket)
