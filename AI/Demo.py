    """
    FastAPI WebSocket server nhận JPEG từ ESP32-CAM,
    chạy YOLOv8 inference, rồi broadcast kết quả đến Frontend.

    Install:
        pip install fastapi uvicorn ultralytics opencv-python-headless websockets

    Run:
        uvicorn main:app --host 0.0.0.0 --port 8000
    """

    import asyncio
    import base64
    import json
    import logging
    import time
    from typing import Optional

    import cv2
    import numpy as np
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from ultralytics import YOLO

    # ─── Config ───────────────────────────────────────────────────────────────────
    MODEL_PATH   = "model/best.pt"    # hoặc yolov8s.pt, yolov8m.pt tuỳ VPS
    CONF_THRESH  = 0.4
    SKIP_FRAMES  = 2               # chạy AI mỗi N frame (1 = mọi frame, 2 = cách 1)
    INFER_WIDTH  = 320
    INFER_HEIGHT = 240

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("esp32-ws")

    # ─── App & YOLO ───────────────────────────────────────────────────────────────
    app = FastAPI(title="ESP32-CAM YOLOv8 Server")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    model: Optional[YOLO] = None

    @app.on_event("startup")
    async def load_model():
        global model
        logger.info(f"Loading YOLO model: {MODEL_PATH}")
        model = YOLO(MODEL_PATH)
        # Warm-up để tránh latency cao ở frame đầu
        dummy = np.zeros((480, 640, 3), dtype=np.uint8)
        model(dummy, verbose=False)
        logger.info("Model ready")


    # ─── Connection managers ──────────────────────────────────────────────────────
    class CameraManager:
        """Giữ kết nối từ ESP32-CAM (chỉ 1 camera)."""
        def __init__(self):
            self.ws: Optional[WebSocket] = None

        async def connect(self, ws: WebSocket):
            await ws.accept()
            self.ws = ws
            logger.info("ESP32-CAM connected")

        def disconnect(self):
            self.ws = None
            logger.info("ESP32-CAM disconnected")


    class FrontendManager:
        """Giữ danh sách FE clients (nhiều tab/user)."""
        def __init__(self):
            self.connections: list[WebSocket] = []

        async def connect(self, ws: WebSocket):
            await ws.accept()
            self.connections.append(ws)
            logger.info(f"Frontend connected. Total: {len(self.connections)}")

        def disconnect(self, ws: WebSocket):
            if ws in self.connections:
                self.connections.remove(ws)
            logger.info(f"Frontend disconnected. Total: {len(self.connections)}")

        async def broadcast(self, message: str):
            """Gửi text (JSON) đến tất cả FE clients."""
            dead = []
            for ws in self.connections:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws)

        @property
        def has_clients(self) -> bool:
            return len(self.connections) > 0


    camera_mgr  = CameraManager()
    frontend_mgr = FrontendManager()


    # ─── YOLOv8 inference ─────────────────────────────────────────────────────────
    def run_inference(jpeg_bytes: bytes) -> list[dict]:
        """
        Nhận JPEG bytes → vẽ bounding box → trả về:
        - list detections dạng JSON-serialisable
        """
        # Decode JPEG
        arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            return []

        infer_frame = cv2.resize(frame, (INFER_WIDTH, INFER_HEIGHT), interpolation=cv2.INTER_LINEAR)
        sx = frame.shape[1] / float(INFER_WIDTH)
        sy = frame.shape[0] / float(INFER_HEIGHT)

        # Inference
        if model is None:
            return []
        results = model(infer_frame, conf=CONF_THRESH, verbose=False)[0]

        detections = []
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            x1 = int(x1 * sx)
            y1 = int(y1 * sy)
            x2 = int(x2 * sx)
            y2 = int(y2 * sy)
            conf  = round(float(box.conf[0]), 3)
            cls   = int(box.cls[0])
            label = model.names[cls]

            detections.append({
                "label": label,
                "conf":  conf,
                "bbox":  [x1, y1, x2, y2],
            })

        return detections


    # ─── WebSocket endpoints ──────────────────────────────────────────────────────

    @app.websocket("/ws/camera")
    async def camera_ws(ws: WebSocket):
        """ESP32-CAM kết nối vào đây, gửi binary JPEG frames."""
        await camera_mgr.connect(ws)
        frame_idx = 0
        t_last_log = time.time()
        last_detections: list[dict] = []

        try:
            while True:
                data = await ws.receive()

                # Xử lý text message (hello, pong, ...)
                if "text" in data:
                    msg = json.loads(data["text"])
                    logger.info(f"[ESP32] {msg}")

                    if msg.get("type") == "pong":
                        logger.debug(f"[ESP32] stats: {msg}")
                    continue

                # Binary frame
                jpeg_bytes = data.get("bytes")
                if not jpeg_bytes:
                    continue

                frame_idx += 1

                # Gửi trực tiếp JPEG gốc từ ESP32 để tránh chi phí encode lại trên server.
                jpeg_b64 = base64.b64encode(jpeg_bytes).decode("utf-8")

                # Bỏ qua frame nếu không có FE nào đang xem — tiết kiệm CPU
                if not frontend_mgr.has_clients:
                    continue

                # SKIP_FRAMES: chạy AI mỗi N frame
                if frame_idx % SKIP_FRAMES == 0:
                    # Chạy inference trong thread pool để không block event loop
                    loop = asyncio.get_running_loop()
                    last_detections = await loop.run_in_executor(None, run_inference, jpeg_bytes)

                # Gửi kết quả cho tất cả FE
                payload = json.dumps({
                    "type":       "frame",
                    "frame_idx":  frame_idx,
                    "timestamp":  time.time(),
                    "jpeg":       jpeg_b64,
                    "detections": last_detections,  # [{label, conf, bbox}, ...]
                })
                await frontend_mgr.broadcast(payload)

                # Log fps mỗi 5 giây
                now = time.time()
                if now - t_last_log >= 5.0:
                    logger.info(f"[CAMERA] frame={frame_idx}  dets={len(last_detections)}")
                    t_last_log = now

        except WebSocketDisconnect:
            pass
        finally:
            camera_mgr.disconnect()
            # Thông báo FE biết camera offline
            await frontend_mgr.broadcast(json.dumps({"type": "camera_offline"}))


    @app.websocket("/ws/frontend")
    async def frontend_ws(ws: WebSocket):
        """Frontend kết nối vào đây để nhận annotated frames + detections."""
        await frontend_mgr.connect(ws)

        try:
            while True:
                # Nhận lệnh từ FE (ví dụ: điều chỉnh camera, thay đổi model...)
                text = await ws.receive_text()
                cmd  = json.loads(text)

                if cmd.get("type") == "set_camera" and camera_mgr.ws:
                    # Forward lệnh điều khiển từ FE đến ESP32
                    await camera_mgr.ws.send_text(json.dumps(cmd))

                elif cmd.get("type") == "ping":
                    await ws.send_text(json.dumps({
                        "type":     "pong",
                        "camera":   camera_mgr.ws is not None,
                        "clients":  len(frontend_mgr.connections),
                    }))

        except WebSocketDisconnect:
            pass
        finally:
            frontend_mgr.disconnect(ws)


    # ─── Health check ─────────────────────────────────────────────────────────────
    @app.get("/health")
    async def health():
        return {
            "status":  "ok",
            "camera":  camera_mgr.ws is not None,
            "clients": len(frontend_mgr.connections),
            "model":   MODEL_PATH,
        }
