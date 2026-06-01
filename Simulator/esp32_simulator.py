"""
esp32_simulator.py — Giả lập ESP32-CAM & ESP32 Smart Device (Còi báo + Vân tay)

Tính năng giả lập:
  1. ESP32-CAM: Đọc frame từ webcam, nén JPEG, gửi qua WebSocket tới Backend (/ws/camera).
  2. Loa/Cảnh báo: Tự động tải cấu hình MQTT từ Backend/.env, kết nối tới Broker, lắng nghe alerts.
     Khi có alert (sleeping, v.v.), in cảnh báo lên màn hình và phát tiếng bíp. Tắt khi nhận 'normal'.
  3. Cảm biến vân tay (Check/Enroll):
     - Quét vân tay (Check): Menu tương tác cho phép chọn tài xế, gửi POST xác thực tới API để bắt đầu Driving Session.
     - Đăng ký vân tay mới (Enroll): Tự động lắng nghe yêu cầu từ MQTT, hướng dẫn người dùng qua console
       để hoàn thành đăng ký, sau đó gọi PATCH API để cập nhật vân tay cho user.
"""

import argparse
import asyncio
import json
import os
import sys
import time
import requests
import cv2
import paho.mqtt.client as mqtt
import websockets

# ─── MÀU SẮC CONSOLE ──────────────────────────────────────────────────────────
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# ─── TỰ ĐỘNG TẢI CONFIG TỪ BACKEND/.ENV ─────────────────────────────────────────
def load_backend_env():
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../Backend/.env"))
    config = {}
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    config[k.strip()] = v.strip()
    return config

ENV_CONFIG = load_backend_env()

# Lấy cổng Backend để cấu hình mặc định cho API/WS
BACKEND_PORT = "8000"  # Mặc định kết nối local port 8000

DEFAULT_WS_URL = f"ws://localhost:{BACKEND_PORT}/ws/camera"
DEFAULT_API_URL = f"http://localhost:{BACKEND_PORT}/api/v1"

# Cấu hình MQTT Broker lấy trực tiếp từ Backend/.env
DEFAULT_MQTT_HOST = ENV_CONFIG.get("MQTT_BROKER", "localhost")
try:
    DEFAULT_MQTT_PORT = int(ENV_CONFIG.get("MQTT_PORT", 1883))
except ValueError:
    DEFAULT_MQTT_PORT = 1883

DEFAULT_MQTT_USER = ENV_CONFIG.get("MQTT_USERNAME", "")
DEFAULT_MQTT_PASS = ENV_CONFIG.get("MQTT_PASSWORD", "")
DEFAULT_MQTT_TLS = ENV_CONFIG.get("MQTT_TLS_ENABLED", "false").lower() == "true"
DEFAULT_MQTT_PREFIX = ENV_CONFIG.get("MQTT_TOPIC_PREFIX", "roadsentinel/alerts")

DEFAULT_FPS = 10
DEFAULT_QUALITY = 80
DEFAULT_CAM = 0

class ESP32DeviceSimulator:
    def __init__(self, ws_url, api_url, mqtt_host, mqtt_port, mqtt_user, mqtt_pass, mqtt_tls, mqtt_prefix, cam_index, fps, quality):
        self.ws_url = ws_url
        self.api_url = api_url
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_user = mqtt_user
        self.mqtt_pass = mqtt_pass
        self.mqtt_tls = mqtt_tls
        self.mqtt_prefix = mqtt_prefix
        self.cam_index = cam_index
        self.fps = fps
        self.quality = quality

        self.ws_connected = False
        self.is_alerting = False
        self.current_alert = None
        self.alert_start_time = 0
        self.alarm_timeout = 180  # 3 phút

        # MQTT Setup
        self.mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message

        # Cấu hình bảo mật TLS nếu bật trong env
        if self.mqtt_tls:
            import ssl
            print(f"[MQTT] Đang kích hoạt kết nối bảo mật TLS...")
            self.mqtt_client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

        if self.mqtt_user and self.mqtt_pass:
            self.mqtt_client.username_pw_set(self.mqtt_user, self.mqtt_pass)

        # Trạng thái Enroll vân tay
        self.enroll_in_progress = False
        self.loop = None

    # ─── MQTT CALL BACKS ──────────────────────────────────────────────────────
    def on_mqtt_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            print(f"{Colors.OKGREEN}[MQTT] Kết nối thành công tới Broker: {self.mqtt_host}:{self.mqtt_port}! ✓{Colors.ENDC}")
            client.subscribe(f"{self.mqtt_prefix}/#")
            client.subscribe("roadsentinel/commands/enroll")
            print(f"{Colors.OKCYAN}[MQTT] Đã đăng ký nhận topics: {self.mqtt_prefix}/# và commands/enroll{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}[MQTT] Kết nối thất bại, mã lỗi: {reason_code}{Colors.ENDC}")

    def on_mqtt_message(self, client, userdata, msg):
        topic = msg.topic
        payload_str = msg.payload.decode()
        try:
            payload = json.loads(payload_str)
        except Exception:
            payload = {"event": payload_str}

        # 1. Nhận thông báo Alert để phát còi cảnh báo
        if topic.startswith(f"{self.mqtt_prefix}/"):
            event = payload.get("event", "normal")
            if event == "normal":
                if self.is_alerting:
                    self.set_buzzer(False)
            elif event in {"sleeping", "using_phone", "distracted", "drowsy"}:
                self.set_buzzer(True, event)

        # 2. Nhận lệnh Enroll vân tay từ hệ thống
        elif topic == "roadsentinel/commands/enroll":
            user_id = payload.get("user_id")
            if user_id:
                # Gửi tác vụ enroll vào event loop đang chạy
                if self.loop:
                    asyncio.run_coroutine_threadsafe(self.simulate_enrollment(user_id), self.loop)
                else:
                    print(f"{Colors.FAIL}[MQTT] Lỗi: Event loop chưa được thiết lập.{Colors.ENDC}")

    def set_buzzer(self, active, event=None):
        self.is_alerting = active
        if active:
            self.current_alert = event
            self.alert_start_time = time.time()
            print(f"\n{Colors.FAIL}{Colors.BOLD}🚨 [CẢNH BÁO LOA] BUZZER ON!!! Tài xế đang: {event.upper()} 🚨{Colors.ENDC}")
            # Phát còi beep hệ thống (ASCII Bell)
            print("\a", end="")
        else:
            self.current_alert = None
            print(f"\n{Colors.OKGREEN}🔕 [CẢNH BÁO LOA] BUZZER OFF. Trạng thái an toàn.{Colors.ENDC}")

    # ─── GIẢ LẬP FINGERPRINT CHECK (POST XÁC THỰC) ─────────────────────────────
    async def simulate_fingerprint_check(self):
        print(f"\n{Colors.BOLD}🔍 --- QUÉT VÂN TAY (CHECK VÂN TAY) ---{Colors.ENDC}")
        # Lấy danh sách users từ Backend để người dùng dễ chọn
        try:
            response = await asyncio.to_thread(requests.get, f"{self.api_url}/users")
            if response.status_code == 200:
                users = response.json().get("data", [])
                users_with_finger = [u for u in users if u.get("fingerprint_id")]
                
                if not users_with_finger:
                    print(f"{Colors.WARNING}[SIM] Không có tài xế nào được gán vân tay trong DB. Vui lòng đăng ký (Enroll) trước.{Colors.ENDC}")
                    return

                print(f"Chọn tài xế quét vân tay:")
                for idx, u in enumerate(users_with_finger):
                    print(f" [{idx}] ID: {u.get('_id')[:8]} | Tên: {u.get('name')} | Vân tay: {u.get('fingerprint_id')}")
                
                choice = await asyncio.to_thread(input, "Nhập số thứ tự tài xế (hoặc nhấn Enter để bỏ qua): ")
                if not choice.strip():
                    return
                
                selected_user = users_with_finger[int(choice)]
                finger_id = selected_user.get("fingerprint_id")
            else:
                finger_id = await asyncio.to_thread(input, "Không lấy được danh sách. Nhập fingerprint_id thủ công (e.g. FINGER_1): ")
        except Exception as e:
            print(f"{Colors.FAIL}[API] Lỗi kết nối API: {e}{Colors.ENDC}")
            finger_id = await asyncio.to_thread(input, "Nhập fingerprint_id thủ công (e.g. FINGER_1): ")

        if not finger_id.strip():
            return

        # Gửi HTTP POST xác thực vân tay
        try:
            print(f"[SIM] Đang quét vân tay {finger_id}...")
            response = await asyncio.to_thread(
                requests.post,
                f"{self.api_url}/users/fingerprint",
                json={"fingerprint_id": finger_id}
            )
            data = response.json()
            if response.status_code == 200:
                print(f"{Colors.OKGREEN}[API] Quét thành công! {data.get('data', {}).get('message')}{Colors.ENDC}")
                print(f"      Session ID: {data.get('data', {}).get('session_id')}")
            else:
                print(f"{Colors.FAIL}[API] Quét thất bại ({response.status_code}): {data.get('detail', 'Lỗi không xác định')}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}[API] Lỗi gửi yêu cầu: {e}{Colors.ENDC}")

    # ─── GIẢ LẬP FINGERPRINT ENROLL (PATCH LIÊN KẾT) ──────────────────────────
    async def simulate_enrollment(self, user_id):
        if self.enroll_in_progress:
            print("[ENROLL] Tiến trình enroll khác đang chạy. Bỏ qua yêu cầu mới.")
            return

        self.enroll_in_progress = True
        print(f"\n{Colors.WARNING}✨ [SIM] Cảm biến vân tay nhận lệnh ENROLL cho User ID: {user_id} ✨{Colors.ENDC}")
        
        try:
            # Mô phỏng đặt vân tay lần 1
            print(f"{Colors.BOLD}[SIM] Hướng dẫn: ĐẶT NGÓN TAY LÊN CẢM BIẾN (Lần 1){Colors.ENDC}")
            await asyncio.to_thread(input, "👉 [Nhấn Enter để xác nhận đã đặt ngón tay lần 1] ")
            print("[SIM] Đã quét ảnh vân tay lần 1 ✓")
            
            # Mô phỏng nhấc ngón tay
            print(f"\n{Colors.BOLD}[SIM] Hướng dẫn: NHẤC NGÓN TAY RA{Colors.ENDC}")
            await asyncio.sleep(1.5)
            
            # Mô phỏng đặt vân tay lần 2
            print(f"\n{Colors.BOLD}[SIM] Hướng dẫn: ĐẶT LẠI CÙNG NGÓN TAY ĐÓ (Lần 2){Colors.ENDC}")
            await asyncio.to_thread(input, "👉 [Nhấn Enter để xác nhận đã đặt ngón tay lần 2] ")
            print("[SIM] Đã quét ảnh vân tay lần 2 ✓")
            print("[SIM] Đang phân tích và tạo khuôn mẫu vân tay...")
            await asyncio.sleep(1.0)

            # Tạo ID ngẫu nhiên cho vân tay (ví dụ: FINGER_10)
            import random
            finger_num = random.randint(1, 127)
            fingerprint_id = f"FINGER_{finger_num}"
            print(f"{Colors.OKGREEN}[SIM] Hai ảnh khớp nhau! Đăng ký thành công tại ID #{finger_num}{Colors.ENDC}")

            # Gọi PATCH API tới Backend để cập nhật thông tin vân tay cho user
            print(f"[API] Gửi liên kết fingerprint_id '{fingerprint_id}' tới User '{user_id}'...")
            response = await asyncio.to_thread(
                requests.patch,
                f"{self.api_url}/users/{user_id}/fingerprint",
                json={"fingerprint_id": fingerprint_id}
            )
            
            if response.status_code == 200:
                print(f"{Colors.OKGREEN}[API] Cập nhật vân tay cho user thành công!{Colors.ENDC}")
                result_payload = {
                    "status": "success",
                    "user_id": user_id,
                    "fingerprint_id": fingerprint_id
                }
            else:
                print(f"{Colors.FAIL}[API] Lỗi cập nhật API ({response.status_code}): {response.text}{Colors.ENDC}")
                result_payload = {
                    "status": "failed",
                    "user_id": user_id,
                    "reason": f"API returned {response.status_code}"
                }
            
            # Publish kết quả ngược lại MQTT
            self.mqtt_client.publish("roadsentinel/commands/enroll/result", json.dumps(result_payload))
            print("[MQTT] Đã gửi kết quả enroll tới topic: commands/enroll/result")

        except Exception as e:
            print(f"{Colors.FAIL}[ENROLL] Gặp lỗi trong quá trình enroll: {e}{Colors.ENDC}")
            result_payload = {
                "status": "failed",
                "user_id": user_id,
                "reason": str(e)
            }
            self.mqtt_client.publish("roadsentinel/commands/enroll/result", json.dumps(result_payload))
        
        finally:
            self.enroll_in_progress = False

    # ─── GIẢ LẬP FINGERPRINT ENROLL THỦ CÔNG (Tự kích hoạt) ────────────────────
    async def simulate_manual_enrollment(self):
        print(f"\n{Colors.BOLD}➕ --- ĐĂNG KÝ VÂN TAY MỚI THỦ CÔNG ---{Colors.ENDC}")
        # Fetch danh sách user chưa có vân tay để chọn
        try:
            response = await asyncio.to_thread(requests.get, f"{self.api_url}/users")
            if response.status_code == 200:
                users = response.json().get("data", [])
                users_no_finger = [u for u in users if not u.get("fingerprint_id")]
                
                if not users_no_finger:
                    print(f"{Colors.WARNING}[SIM] Tất cả tài xế trong DB đã được gán vân tay. Bạn có muốn ghi đè lên tài xế có sẵn?{Colors.ENDC}")
                    users_no_finger = users
                
                if not users_no_finger:
                    print(f"{Colors.FAIL}[SIM] DB trống rỗng. Hãy tạo user trước.{Colors.ENDC}")
                    return

                print(f"Chọn tài xế đăng ký vân tay:")
                for idx, u in enumerate(users_no_finger):
                    print(f" [{idx}] ID: {u.get('_id')[:8]} | Tên: {u.get('name')} | Email: {u.get('email')}")
                
                choice = await asyncio.to_thread(input, "Nhập số thứ tự tài xế (hoặc nhấn Enter để bỏ qua): ")
                if not choice.strip():
                    return
                
                selected_user = users_no_finger[int(choice)]
                user_id = selected_user.get("_id")
                await self.simulate_enrollment(user_id)
            else:
                print(f"{Colors.FAIL}[API] Lỗi lấy danh sách user: {response.text}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}[API] Lỗi kết nối API: {e}{Colors.ENDC}")

    # ─── GIẢ LẬP CAMERA STREAMING (WEBSOCKET PORT) ─────────────────────────────
    async def stream_camera_task(self):
        cap = cv2.VideoCapture(self.cam_index)
        if not cap.isOpened():
            print(f"{Colors.FAIL}[CAM] Không thể mở webcam ở index {self.cam_index}{Colors.ENDC}")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        frame_interval = 1.0 / self.fps
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.quality]

        attempt = 0
        while True:
            attempt += 1
            try:
                print(f"[WS] Đang kết nối tới endpoint camera: {self.ws_url} (lần {attempt})...")
                async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=10) as ws:
                    print(f"{Colors.OKGREEN}[WS] Đã kết nối thành công tới WebSocket! ✓{Colors.ENDC}")
                    self.ws_connected = True

                    # Handshake hello
                    hello = {
                        "type": "hello",
                        "device": "esp32-cam-sim",
                        "version": "simulator-2.0"
                    }
                    await ws.send(json.dumps(hello))

                    frame_count = 0
                    t_start = time.time()
                    t_last_stat = time.time()
                    t_next = time.time()

                    while True:
                        ret, frame = cap.read()
                        if not ret:
                            await asyncio.sleep(0.1)
                            continue

                        # Lật ảnh ngang (hiệu ứng gương)
                        frame = cv2.flip(frame, 1)

                        ok, buf = cv2.imencode(".jpg", frame, encode_params)
                        if not ok:
                            continue
                        jpeg_bytes = buf.tobytes()

                        await ws.send(jpeg_bytes)
                        frame_count += 1

                        # Hiển thị stats định kỳ
                        now = time.time()
                        if now - t_last_stat >= 5.0:
                            elapsed = now - t_start
                            actual_fps = frame_count / elapsed if elapsed > 0 else 0
                            print(f"[STATS] Đã gửi: {frame_count} frames | FPS: {actual_fps:.1f} | Dung lượng frame: {len(jpeg_bytes)} B")
                            t_last_stat = now

                        # Đồng bộ FPS
                        t_next += frame_interval
                        sleep_for = t_next - time.time()
                        if sleep_for > 0:
                            await asyncio.sleep(sleep_for)
                        else:
                            t_next = time.time()  # reset nếu bị trễ nhịp

            except KeyboardInterrupt:
                break
            except Exception as e:
                self.ws_connected = False
                print(f"{Colors.FAIL}[WS] Mất kết nối WebSocket: {e}{Colors.ENDC}")
                print(f"[WS] Sẽ kết nối lại sau 3 giây...")
                await asyncio.sleep(3)

        cap.release()

    # ─── MENU TƯƠNG TÁC NGƯỜI DÙNG (SHELL THỦ CÔNG) ─────────────────────────────
    async def user_interface_task(self):
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== HỆ THỐNG GIẢ LẬP ĐA NĂNG ESP32 ROAD SENTINEL ==={Colors.ENDC}")
        print("Mô phỏng đồng thời: Camera stream + Cảnh báo loa còi + Cảm biến vân tay")
        print("Lệnh khả dụng:")
        print("  [f] Quét vân tay (Check vân tay bắt đầu phiên lái xe)")
        print("  [e] Đăng ký vân tay mới thủ công (Enroll vân tay cho user)")
        print("  [h] In danh sách phím lệnh trợ giúp")
        print("  [q] Thoát giả lập")

        while True:
            try:
                cmd = await asyncio.to_thread(input, "\n👉 [SIMULATOR SHELL] Nhập lệnh: ")
                cmd = cmd.strip().lower()

                if cmd == 'q':
                    print("[SIM] Đang tắt các tiến trình...")
                    os._exit(0)
                elif cmd == 'h':
                    print("Lệnh khả dụng: [f] Quét vân tay | [e] Đăng ký vân tay mới | [h] Trợ giúp | [q] Thoát")
                elif cmd == 'f':
                    await self.simulate_fingerprint_check()
                elif cmd == 'e':
                    await self.simulate_manual_enrollment()
                else:
                    if cmd:
                        print(f"{Colors.WARNING}Lệnh '{cmd}' không hợp lệ. Nhập 'h' để trợ giúp.{Colors.ENDC}")
            except KeyboardInterrupt:
                os._exit(0)
            except Exception as e:
                print(f"Lỗi nhập lệnh: {e}")

    # ─── RUN RUN CONCURRENTLY ──────────────────────────────────────────────────
    async def run(self):
        self.loop = asyncio.get_running_loop()
        # Kết nối MQTT
        print(f"[MQTT] Đang kết nối tới MQTT Broker {self.mqtt_host}:{self.mqtt_port}...")
        try:
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            print(f"{Colors.FAIL}[MQTT] Không thể kết nối tới MQTT broker: {e}. Cảnh báo loa còi sẽ bị tắt.{Colors.ENDC}")

        # Chạy đồng thời Camera stream và User Shell bằng gather
        await asyncio.gather(
            self.stream_camera_task(),
            self.user_interface_task()
        )

# ─── MAIN ENTRY POINT ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="RoadSentinel ESP32 Cam & Smart Device Simulator")
    parser.add_argument("--url", default=DEFAULT_WS_URL, help=f"WebSocket camera URL (default: {DEFAULT_WS_URL})")
    parser.add_argument("--api", default=DEFAULT_API_URL, help=f"HTTP API base URL (default: {DEFAULT_API_URL})")
    parser.add_argument("--mqtt", default=DEFAULT_MQTT_HOST, help=f"MQTT broker hostname (default: {DEFAULT_MQTT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_MQTT_PORT, help=f"MQTT broker port (default: {DEFAULT_MQTT_PORT})")
    parser.add_argument("--mqtt-user", default=DEFAULT_MQTT_USER, help=f"MQTT username (loaded from env)")
    parser.add_argument("--mqtt-pass", default=DEFAULT_MQTT_PASS, help=f"MQTT password (loaded from env)")
    parser.add_argument("--mqtt-tls", type=bool, default=DEFAULT_MQTT_TLS, help=f"Enable MQTT TLS (loaded from env)")
    
    parser.add_argument("--cam", type=int, default=DEFAULT_CAM, help=f"Webcam device index (default: {DEFAULT_CAM})")
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS, help=f"Target FPS (default: {DEFAULT_FPS})")
    parser.add_argument("--quality", type=int, default=DEFAULT_QUALITY, help=f"JPEG compression quality (default: {DEFAULT_QUALITY})")
    
    args = parser.parse_args()

    simulator = ESP32DeviceSimulator(
        ws_url=args.url,
        api_url=args.api,
        mqtt_host=args.mqtt,
        mqtt_port=args.port,
        mqtt_user=args.mqtt_user,
        mqtt_pass=args.mqtt_pass,
        mqtt_tls=args.mqtt_tls,
        mqtt_prefix=DEFAULT_MQTT_PREFIX,
        cam_index=args.cam,
        fps=args.fps,
        quality=args.quality
    )
    
    try:
        asyncio.run(simulator.run())
    except KeyboardInterrupt:
        print("\n[SIM] Đang dừng...")
    finally:
        simulator.mqtt_client.loop_stop()
        simulator.mqtt_client.disconnect()
        print("[SIM] Đã ngắt kết nối. Tạm biệt!")

if __name__ == "__main__":
    main()
