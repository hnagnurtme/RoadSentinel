"""
RoadSentinel - Worker v4 (Binary JPEG + YOLO Detection - HD Mode)
==================================================================
ESP32 gửi VGA 640x480 HD JPEG @ 1 FPS qua MQTT → Worker nhận → YOLO detect → hiển thị.
Tích hợp AI detection với high-quality streaming.

macOS safe: OpenCV chạy trên main thread, MQTT trên background thread.
"""

import os
import queue
import ssl
import threading
import time
from collections import deque

import cv2
import numpy as np
import paho.mqtt.client as mqtt
import torch
from ultralytics import YOLO

# ============================================================
#  CẤU HÌNH MQTT
# ============================================================
MQTT_BROKER = "fe4494bed59247ae9640160c900bf3f1.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "anhnon"
MQTT_PASS = "Password123"

# ✅ Subscribe wildcard để nhận tất cả camera
# Topic pattern: roadsentinel/cam/<device_id>/jpeg
MQTT_TOPIC = "roadsentinel/cam/+/jpeg"

QUEUE_MAX_SIZE = 2  # Giảm buffer để giảm lag, luôn lấy frame mới

# ============================================================
#  CẤU HÌNH AI MODEL
# ============================================================
MODEL_PATH = "../AI/model/best_v2.pt"
CONFIDENCE_THRESHOLD = 0.3
SKIP_FRAMES = 0  # Xử lý mọi frame (1 FPS nên không cần skip)
RESIZE_WIDTH = 640  # Tăng lên 640px cho HD quality detection

# ============================================================
#  SHARED STATE
# ============================================================
# Queue chứa tuple (device_id: str, jpeg_bytes: bytes)
frame_queue: queue.Queue = queue.Queue(maxsize=QUEUE_MAX_SIZE)

stats = {"received": 0, "displayed": 0, "dropped": 0, "detected": 0}
stats_lock = threading.Lock()

# AI Model (sẽ được load trong main)
model = None
device = None


# ============================================================
#  MQTT CALLBACKS
# ============================================================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Kết nối HiveMQ thành công!")
        client.subscribe(MQTT_TOPIC, qos=0)
        print(f"📡 Subscribe: {MQTT_TOPIC}")
    else:
        print(f"❌ Lỗi kết nối rc={rc}")


def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"⚠️  MQTT mất kết nối (rc={rc}) – tự kết nối lại...")


def on_message(client, userdata, msg):
    """
    ✅ Cực nhẹ: không parse JSON, không decode base64.
    Chỉ extract device_id từ topic và đẩy raw bytes vào queue.
    Topic format: roadsentinel/cam/DRV_01/jpeg
    """
    with stats_lock:
        stats["received"] += 1
        recv_count = stats["received"]

    # Extract device_id từ topic: parts[2]
    try:
        device_id = msg.topic.split("/")[2]
    except IndexError:
        device_id = "unknown"

    # Log mỗi 10 frames để không spam
    if recv_count % 10 == 1:
        print(f"📥 [{device_id}] JPEG size: {len(msg.payload)/1024:.1f}KB")

    # Drop frame cũ nhất nếu queue đầy
    if frame_queue.full():
        try:
            frame_queue.get_nowait()
            with stats_lock:
                stats["dropped"] += 1
        except queue.Empty:
            pass

    try:
        frame_queue.put_nowait((device_id, msg.payload))
    except queue.Full:
        pass


# ============================================================
#  STATS LOGGER
# ============================================================
def stats_logger(stop_event: threading.Event):
    while not stop_event.is_set():
        time.sleep(5)
        with stats_lock:
            r, d, x, det = (
                stats["received"],
                stats["displayed"],
                stats["dropped"],
                stats["detected"],
            )
        print(
            f"📊 Recv:{r:5d} | Disp:{d:5d} | Drop:{x:4d} | Det:{det:4d} | Queue:{frame_queue.qsize()}/{QUEUE_MAX_SIZE}"
        )


# ============================================================
#  AI MODEL LOADER
# ============================================================
def load_model():
    """Load YOLO model với GPU/CPU auto-detect"""
    global model, device

    if not os.path.exists(MODEL_PATH):
        print(f"❌ LỖI: Không tìm thấy model '{MODEL_PATH}'!")
        return False

    print("⏳ Đang load AI model...")
    try:
        model = YOLO(MODEL_PATH)

        # Tự động detect device (GPU hoặc CPU)
        if torch.cuda.is_available():
            device = "cuda"
            print("🚀 Sử dụng GPU (CUDA)")
        elif torch.backends.mps.is_available():
            device = "mps"
            print("🚀 Sử dụng GPU (Apple Silicon)")
        else:
            device = "cpu"
            print("💻 Sử dụng CPU")

        model.to(device)
        model.fuse()  # Tối ưu hóa

        # Warmup
        print("🔥 Warming up model...")
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        _ = model.predict(
            source=dummy, conf=CONFIDENCE_THRESHOLD, verbose=False, device=device
        )

        print("✅ Model đã sẵn sàng!")
        return True

    except Exception as e:
        print(f"❌ Lỗi load model: {e}")
        return False


# ============================================================
#  MAIN THREAD – OpenCV render + AI Detection
# ============================================================
def main():
    print("=" * 65)
    print("  RoadSentinel Worker v4  –  Binary JPEG + YOLO Detection")
    print("  Expected: VGA (640x480) HD JPEG frames @ 1 FPS")
    print("=" * 65)

    # Load AI Model trước
    if not load_model():
        print("❌ Không thể load model. Thoát.")
        return

    stop_event = threading.Event()

    # ---- MQTT setup ----
    mqttc = mqtt.Client(
        client_id=f"RS-Worker-{int(time.time())}",
        protocol=mqtt.MQTTv311,
        clean_session=True,
    )
    mqttc.username_pw_set(MQTT_USER, MQTT_PASS)
    mqttc.tls_set(cert_reqs=ssl.CERT_NONE)
    mqttc.tls_insecure_set(True)
    mqttc.reconnect_delay_set(min_delay=1, max_delay=10)
    mqttc.on_connect = on_connect
    mqttc.on_disconnect = on_disconnect
    mqttc.on_message = on_message

    mqttc.connect(MQTT_BROKER, MQTT_PORT, keepalive=30)
    mqttc.loop_start()  # MQTT chạy background thread

    # ---- Stats logger ----
    threading.Thread(target=stats_logger, args=(stop_event,), daemon=True).start()

    # ---- OpenCV window trên main thread ----
    window_name = "RoadSentinel AI  |  Q=thoát  S=lưu  D=toggle detection"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 960, 720)  # VGA 640x480 scale 1.5x
    print("🖥️  Cửa sổ OpenCV mở - HD Display (960x720).")
    print("   Q = Thoát  |  S = Lưu ảnh  |  D = Bật/tắt AI detection\n")

    frame_times: deque = deque(maxlen=30)
    frame_count = 0
    current_annotated_frame = None  # Frame đã detect gần nhất
    current_device_id = "unknown"
    detection_enabled = True  # Toggle AI detection
    last_detection_time = 0.0  # Đo thời gian detection

    try:
        while True:
            # Lấy frame từ queue
            try:
                device_id, jpeg_bytes = frame_queue.get(timeout=0.05)
            except queue.Empty:
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
                continue

            current_device_id = device_id
            frame_count += 1

            # ✅ Decode thẳng từ JPEG bytes với validation
            try:
                # Kiểm tra kích thước JPEG
                jpeg_size = len(jpeg_bytes)
                if jpeg_size < 100:  # JPEG tối thiểu ~100 bytes
                    raise ValueError(f"JPEG quá nhỏ: {jpeg_size} bytes")
                if jpeg_size > 100000:  # Cảnh báo nếu quá lớn
                    print(f"⚠️  JPEG lớn bất thường: {jpeg_size/1024:.1f}KB")

                np_arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                if frame is None:
                    raise ValueError(
                        f"imdecode failed – JPEG corrupt? Size: {jpeg_size} bytes"
                    )

                # Validate frame shape
                if frame.shape[0] < 10 or frame.shape[1] < 10:
                    raise ValueError(f"Frame shape invalid: {frame.shape}")

            except Exception as e:
                with stats_lock:
                    stats["dropped"] += 1
                print(
                    f"⚠️  Decode lỗi [{device_id}]: {e} (size: {len(jpeg_bytes)} bytes)"
                )
                continue

            # ---- YOLO DETECTION ----
            should_process = (
                frame_count % (SKIP_FRAMES + 1) == 0
            ) and detection_enabled

            if should_process and model is not None:
                try:
                    detect_start = time.time()

                    height, width = frame.shape[:2]

                    # Resize để tăng tốc - luôn resize về RESIZE_WIDTH
                    scale = RESIZE_WIDTH / width
                    frame_resized = cv2.resize(
                        frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA
                    )  # INTER_AREA nhanh hơn

                    # Detection với half precision nếu có GPU
                    results = model.predict(
                        source=frame_resized,
                        conf=CONFIDENCE_THRESHOLD,
                        verbose=False,
                        device=device,
                        half=(device != "cpu"),  # FP16 trên GPU
                    )

                    # Vẽ bounding boxes
                    annotated_frame = results[0].plot()

                    # Scale về kích thước gốc
                    annotated_frame = cv2.resize(
                        annotated_frame, (width, height), interpolation=cv2.INTER_LINEAR
                    )

                    # Lưu kết quả
                    current_annotated_frame = annotated_frame

                    # Đếm số objects detected
                    num_detections = len(results[0].boxes)
                    with stats_lock:
                        stats["detected"] += num_detections

                    # Đo thời gian
                    last_detection_time = (time.time() - detect_start) * 1000  # ms

                except Exception as e:
                    print(f"⚠️ Lỗi detection: {e}")
                    current_annotated_frame = frame.copy()
                    last_detection_time = 0

            # Hiển thị frame đã detect (hoặc frame gốc nếu chưa detect)
            if detection_enabled and current_annotated_frame is not None:
                display_frame = current_annotated_frame.copy()
            else:
                display_frame = frame.copy()

            # ---- Tính FPS ----
            now = time.time()
            frame_times.append(now)
            fps = 0.0
            if len(frame_times) >= 2:
                span = frame_times[-1] - frame_times[0]
                if span > 0:
                    fps = (len(frame_times) - 1) / span

            # ---- HUD với info AI ----
            with stats_lock:
                recv = stats["received"]
                drops = stats["dropped"]
                det_count = stats["detected"]

            h, w = display_frame.shape[:2]

            # Background cho HUD
            overlay = display_frame.copy()
            cv2.rectangle(overlay, (0, 0), (w, 115), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.5, display_frame, 0.5, 0, display_frame)

            # Line 1: Camera info
            cv2.putText(
                display_frame,
                f"CAM: {device_id}  |  {w}x{h}",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (200, 255, 200),
                2,
                cv2.LINE_AA,
            )

            # Line 2: FPS và stats
            cv2.putText(
                display_frame,
                f"FPS: {fps:5.1f}  |  Recv:{recv}  Drop:{drops}",
                (10, 52),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (100, 200, 255),
                2,
                cv2.LINE_AA,
            )

            # Line 3: AI Detection info
            if detection_enabled:
                status = "DETECTING" if should_process else "SKIP"
                status_color = (0, 255, 0) if should_process else (128, 128, 128)
                ai_text = f"AI: {status}  |  Objects: {det_count}"
            else:
                status_color = (0, 0, 255)
                ai_text = f"AI: DISABLED  |  Objects: {det_count}"

            cv2.putText(
                display_frame,
                ai_text,
                (10, 79),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                status_color,
                2,
                cv2.LINE_AA,
            )

            # Line 4: Detection timing (nếu có)
            if last_detection_time > 0:
                timing_text = f"Detect Time: {last_detection_time:.0f}ms  |  Skip: 1/{SKIP_FRAMES+1}"
                cv2.putText(
                    display_frame,
                    timing_text,
                    (10, 106),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 100),
                    1,
                    cv2.LINE_AA,
                )

            # Warning border nếu drop rate cao
            if drops / max(recv, 1) > 0.1:
                cv2.rectangle(display_frame, (0, 0), (w - 1, h - 1), (0, 0, 255), 3)

            cv2.imshow(window_name, display_frame)
            with stats_lock:
                stats["displayed"] += 1

            # ---- XỬ LÝ PHÍM ----
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break
            elif key == ord("d"):
                # Toggle AI detection
                detection_enabled = not detection_enabled
                status = "BẬT" if detection_enabled else "TẮT"
                print(f"🤖 AI Detection: {status}")
            elif key == ord("s"):
                # Lưu ảnh hiện tại với full resolution
                timestamp = time.strftime("%Y%m%d_%H%M%S")

                # Lưu cả frame gốc và frame đã detect
                raw_filename = f"raw_{device_id}_{timestamp}.jpg"
                cv2.imwrite(raw_filename, frame)
                print(f"📸 Lưu RAW: {raw_filename} ({frame.shape[1]}x{frame.shape[0]})")

                if current_annotated_frame is not None:
                    det_filename = f"detected_{device_id}_{timestamp}.jpg"
                    cv2.imwrite(det_filename, current_annotated_frame)
                    print(
                        f"🎯 Lưu DETECTED: {det_filename} ({current_annotated_frame.shape[1]}x{current_annotated_frame.shape[0]})"
                    )

    except KeyboardInterrupt:
        print("\n🛑 Ctrl+C – đang dừng...")
    finally:
        stop_event.set()
        mqttc.loop_stop()
        mqttc.disconnect()
        cv2.destroyAllWindows()
        print("✅ Worker dừng sạch.")


if __name__ == "__main__":
    main()
