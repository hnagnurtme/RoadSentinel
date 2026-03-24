from fastapi import APIRouter, WebSocket, WebSocketDisconnect


class AlertsWebSocketManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, payload: dict) -> None:
        stale_connections: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_json(payload)
            except Exception:
                stale_connections.append(connection)

        for connection in stale_connections:
            self.disconnect(connection)


alerts_ws_manager = AlertsWebSocketManager()
router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/alerts")
async def alerts_websocket(websocket: WebSocket):
    await alerts_ws_manager.connect(websocket)
    try:
        # Keep connection alive; incoming messages are currently ignored.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        alerts_ws_manager.disconnect(websocket)
