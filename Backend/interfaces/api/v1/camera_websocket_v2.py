"""
interfaces/api/v1/camera_websocket_v2.py
-----------------------------------------
Refactored camera WebSocket handler using new pipeline architecture.

This replaces the 200-line handler with a thin transport loop that
delegates to the new FrameProcessingPipeline.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from application.alert.commands.create_alert import CreateAlertCommand
from application.alert.commands.create_alert_handler import CreateAlertHandler
from core.ai.alert_decision_engine import SessionContext
from core.ai.frame_processing_pipeline import (
    FrameProcessingPipeline,
    create_pipeline_config,
)
from infrastructure.repositories.alert_repository_impl import AlertRepositoryImpl
from shared.config import settings

logger = logging.getLogger("roadsentinel.ws_v2")


def create_save_alert_function(alert_type: str, session: SessionContext) -> callable:
    """Create a save_alert function for a specific alert type."""

    def save_alert(db: object, message: str, evidence_url: str | None) -> dict | None:
        """Create an alert record through the application layer and return its ID."""
        try:
            command = CreateAlertCommand(
                device_id=session.device_id,
                driver_id=session.driver_id,
                vehicle_id=session.vehicle_id,
                trip_id=session.trip_id,
                alert_type=alert_type,
                message=message,
                evidence_url=evidence_url,
            )
            handler = CreateAlertHandler(AlertRepositoryImpl())
            result = handler.handle(command)
            return {"alert_id": str(result.id)} if result else None
        except Exception as e:
            logger.error(f"Failed to save {alert_type} alert: {e}")
            return None

    return save_alert


async def _resolve_session_context(device_id: Optional[str] = None) -> SessionContext:
    """Resolve session context from device handshake or fallbacks."""
    # TODO: In production, resolve from handshake, database, or auth
    # For now, use fallback values from config
    return SessionContext(
        device_id=uuid.UUID(settings.DRIVER_EVENT.fallback_device_id),
        driver_id=uuid.UUID(settings.DRIVER_EVENT.fallback_driver_id)
        if settings.DRIVER_EVENT.fallback_driver_id
        else None,
        vehicle_id=uuid.UUID(settings.DRIVER_EVENT.fallback_vehicle_id)
        if settings.DRIVER_EVENT.fallback_vehicle_id
        else None,
        trip_id=None,  # TODO: Resolve from active trip
    )


async def _handle_text_message(msg: dict, pipeline: FrameProcessingPipeline) -> None:
    """Handle text messages from ESP32 device."""
    msg_type = msg.get("type")
    if msg_type == "pong":
        # Forward ESP32 stats to frontend viewers
        await frontend_mgr.broadcast(json.dumps({"type": "esp32_stats", **msg}))
    elif msg_type == "hello":
        logger.info(f"ESP32 device hello: {msg}")
    else:
        logger.debug(f"Unhandled text message: {msg}")


async def _broadcast_result(result, pipeline, websocket) -> None:
    """Broadcast processing results to frontend viewers."""
    snapshot = result.snapshot

    payload = {
        "type": "driver_state",
        "state": snapshot.state.value,
        "dominant_event": snapshot.dominant_event,
        "dominant_score": snapshot.dominant_score,
        "escalated": snapshot.escalated,
        "frame_idx": pipeline.frame_idx,
        "timestamp": snapshot.now,
    }

    # Add active events for debugging
    if snapshot.active_events:
        payload["active_events"] = [
            {"name": ae.name, "score": ae.score, "duration": ae.duration_seconds}
            for ae in snapshot.active_events
        ]

    await frontend_mgr.broadcast(json.dumps(payload))


async def _handle_alert(result, session: SessionContext) -> None:
    """Handle alert generation from pipeline result."""
    if not result.alert_decision.should_alert:
        return

    alert = result.alert_decision
    snapshot = result.snapshot

    # Create alert message
    message = f"{snapshot.dominant_event} detected in {snapshot.state.value} state"
    if alert.reason:
        message += f" ({alert.reason})"

    # Save alert to database
    save_alert = create_save_alert_function(snapshot.dominant_event, session)
    alert_data = save_alert(None, message, None)  # TODO: Add evidence URL

    # Broadcast alert to frontend
    alert_payload = {
        "type": "alert",
        "severity": alert.severity.value if alert.severity else "INFO",
        "event": snapshot.dominant_event,
        "state": snapshot.state.value,
        "message": message,
        "timestamp": snapshot.now,
    }

    if alert_data:
        alert_payload["alert_id"] = alert_data["alert_id"]

    await frontend_mgr.broadcast(json.dumps(alert_payload))

    # Send device command if needed
    if alert.should_send_device_command:
        # TODO: Send command to ESP32 via WebSocket
        logger.info(f"Would send device command for {snapshot.dominant_event}")


async def _iter_messages(websocket: WebSocket):
    """Async iterator over WebSocket messages."""
    while True:
        try:
            data = await websocket.receive()
            yield data
        except WebSocketDisconnect:
            break


# Note: This would need to be imported or defined elsewhere
# For now, this is a placeholder for the existing frontend manager
class FrontendManager:
    async def broadcast(self, message: str):
        pass


frontend_mgr = FrontendManager()


async def camera_websocket_v2(
    websocket: WebSocket, device_id: Optional[str] = None
) -> None:
    """
    Refactored camera WebSocket endpoint using new pipeline architecture.

    This handler is now a thin transport loop that delegates AI processing
    to the FrameProcessingPipeline, following clean architecture principles.
    """
    await websocket.accept()

    # Resolve session context
    session = await _resolve_session_context(device_id)

    # Initialize processing pipeline
    pipeline_config = create_pipeline_config(settings)
    pipeline = FrameProcessingPipeline(pipeline_config, session)

    logger.info(f"Camera session started for device {session.device_id}")

    try:
        async for message in _iter_messages(websocket):
            # Handle text messages (control, status, pong)
            if message.get("text"):
                try:
                    msg = json.loads(message["text"])
                    await _handle_text_message(msg, pipeline)
                except Exception as e:
                    logger.warning(f"Failed to parse text message: {e}")
                continue

            # Handle binary JPEG frames
            jpeg_bytes = message.get("bytes")
            if not jpeg_bytes:
                continue

            # Process frame through pipeline
            now = time.monotonic()
            result = await asyncio.to_thread(pipeline.process_frame, jpeg_bytes, now)

            # Broadcast results to frontend
            await _broadcast_result(result, pipeline, websocket)

            # Handle alerts if any
            await _handle_alert(result, session)

            # Process evidence if ready
            if result.evidence_ready:
                logger.info("Evidence clip ready for processing")
                # TODO: Process evidence asynchronously

    except WebSocketDisconnect:
        logger.info(f"Camera session ended for device {session.device_id}")
    except Exception as e:
        logger.error(f"Error in camera session: {e}")
    finally:
        # Cleanup pipeline state
        pipeline.reset()

        # Notify frontend that camera is offline
        await frontend_mgr.broadcast(
            json.dumps(
                {
                    "type": "camera_offline",
                    "device_id": str(session.device_id),
                    "timestamp": time.monotonic(),
                }
            )
        )

        logger.info(f"Camera session cleaned up for device {session.device_id}")
