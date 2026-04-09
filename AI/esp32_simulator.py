"""
esp32_simulator.py — Giả lập ESP32-CAM bằng webcam máy tính.

Dùng khi không có phần cứng thực: đọc frame từ webcam, encode JPEG,
gửi binary qua WebSocket đến backend giống hệt ESP32-CAM thật.

Cài đặt:
    pip install opencv-python websockets

Chạy:
    python AI/esp32_simulator.py
    python AI/esp32_simulator.py --url ws://192.168.1.209:8000/ws/camera
    python AI/esp32_simulator.py --cam 1 --fps 10 --quality 80
"""

import argparse
import asyncio
import json
import sys
import time

import cv2


# ─── Config ───────────────────────────────────────────────────────────────────

DEFAULT_URL     = "ws://localhost:8000/ws/camera"
DEFAULT_FPS     = 10          # target frames per second
DEFAULT_QUALITY = 80          # JPEG quality 0-100 (higher = better / larger)
DEFAULT_CAM     = 0           # webcam index (0 = built-in, 1 = first external)
RECONNECT_DELAY = 3           # seconds between reconnect attempts


# ─── Main logic ───────────────────────────────────────────────────────────────

async def stream(url: str, cam_index: int, fps: int, quality: int) -> None:
    try:
        import websockets  # type: ignore
    except ImportError:
        print("[ERROR] 'websockets' not installed. Run: pip install websockets")
        sys.exit(1)

    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open camera index {cam_index}")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

    frame_interval = 1.0 / fps
    encode_params  = [cv2.IMWRITE_JPEG_QUALITY, quality]

    attempt = 0

    print(f"[SIM] ESP32 Simulator started")
    print(f"      Camera  : {cam_index}")
    print(f"      Target  : {url}")
    print(f"      FPS     : {fps}  Quality: {quality}")
    print(f"      Press Ctrl+C to stop\n")

    while True:
        attempt += 1
        try:
            print(f"[WS] Connecting to {url} (attempt #{attempt})...")
            async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                print(f"[WS] Connected ✓")

                # Send hello handshake (mirrors what the real ESP32 sends)
                hello = {
                    "type":    "hello",
                    "device":  "esp32-cam-sim",
                    "version": "simulator-1.0",
                }
                await ws.send(json.dumps(hello))

                frame_count = 0
                t_start     = time.time()
                t_next      = time.time()
                t_last_stat = time.time()

                while True:
                    # ── Capture frame ──────────────────────────────────────
                    ret, frame = cap.read()
                    if not ret:
                        print("[CAM] fb_get failed — retrying...")
                        await asyncio.sleep(0.1)
                        continue

                    # Flip horizontal to feel like a mirror (optional)
                    frame = cv2.flip(frame, 1)

                    # ── Encode to JPEG ─────────────────────────────────────
                    ok, buf = cv2.imencode(".jpg", frame, encode_params)
                    if not ok:
                        continue
                    jpeg_bytes = buf.tobytes()

                    # ── Send binary frame ──────────────────────────────────
                    await ws.send(jpeg_bytes)
                    frame_count += 1

                    # ── Periodic stats (mirrors ESP32 STATS log) ───────────
                    now = time.time()
                    if now - t_last_stat >= 4.0:
                        elapsed = now - t_start
                        actual_fps = frame_count / elapsed if elapsed > 0 else 0
                        print(f"[STATS] Frames: {frame_count}  FPS: {actual_fps:.1f}  "
                              f"Size: {len(jpeg_bytes)} B")
                        t_last_stat = now

                    # ── Rate limiter ───────────────────────────────────────
                    t_next += frame_interval
                    sleep_for = t_next - time.time()
                    if sleep_for > 0:
                        await asyncio.sleep(sleep_for)
                    else:
                        t_next = time.time()   # reset if we fell behind

        except KeyboardInterrupt:
            print("\n[SIM] Stopped by user.")
            break
        except Exception as exc:
            print(f"[WS] Disconnected — {exc}")
            print(f"[WS] Reconnecting in {RECONNECT_DELAY}s...")
            await asyncio.sleep(RECONNECT_DELAY)

    cap.release()
    print("[SIM] Camera released. Bye!")


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate ESP32-CAM using a local webcam."
    )
    parser.add_argument(
        "--url", default=DEFAULT_URL,
        help=f"WebSocket URL (default: {DEFAULT_URL})"
    )
    parser.add_argument(
        "--cam", type=int, default=DEFAULT_CAM,
        help=f"Camera device index (default: {DEFAULT_CAM})"
    )
    parser.add_argument(
        "--fps", type=int, default=DEFAULT_FPS,
        help=f"Target FPS (default: {DEFAULT_FPS})"
    )
    parser.add_argument(
        "--quality", type=int, default=DEFAULT_QUALITY,
        help=f"JPEG quality 0-100 (default: {DEFAULT_QUALITY})"
    )
    args = parser.parse_args()

    try:
        asyncio.run(stream(args.url, args.cam, args.fps, args.quality))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
