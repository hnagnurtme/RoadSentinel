import cv2
import os
from ultralytics import YOLO
import time
from threading import Thread, Lock
import numpy as np
import torch

# --- CẤU HÌNH ---
model_path = './model/best_v2.pt'
confidence_threshold = 0.3
esp32_url = 'http://10.10.30.189'

# Tối ưu hóa
SKIP_FRAMES = 2  # Xử lý 1 frame / 3 frames
RESIZE_WIDTH = 640
CONNECTION_TIMEOUT = 10  # seconds
FRAME_BUFFER_SIZE = 2  # Giữ 2 frames gần nhất

# Kích thước hiển thị
DISPLAY_WIDTH = 680
DISPLAY_HEIGHT = 480

# --- CLASS ĐỌC FRAME TỪ ESP32 (THREAD-SAFE) ---
class ESP32CamStream:
    def __init__(self, url, timeout=CONNECTION_TIMEOUT):
        self.url = url
        self.timeout = timeout
        self.frame = None
        self.stopped = False
        self.capture = None
        self.lock = Lock()  # Thread-safe
        self.last_frame_time = time.time()
        self.connection_lost = False
        self.error_count = 0
        
    def start(self):
        """Kết nối tới ESP32-CAM với retry logic"""
        print(f"📹 Đang kết nối tới ESP32-CAM: {self.url}")
        
        # Danh sách endpoints phổ biến
        possible_endpoints = [
            f'{self.url}/cam-hi.jpg',
            f'{self.url}/cam-mid.jpg', 
            f'{self.url}/cam-lo.jpg',
            f'{self.url}:81/stream',
            f'{self.url}/stream',
            f'{self.url}/capture',
            f'{self.url}/jpg',
            f'{self.url}/mjpeg'
        ]
        
        for endpoint in possible_endpoints:
            print(f"  Thử: {endpoint}")
            try:
                cap = cv2.VideoCapture(endpoint)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Giảm buffer lag
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Request 640x480 từ ESP32
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                
                if cap.isOpened():
                    # Thử đọc frame với timeout
                    start_time = time.time()
                    while time.time() - start_time < 3:
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None and test_frame.size > 0:
                            print(f"✅ Kết nối thành công: {endpoint}")
                            with self.lock:
                                self.frame = test_frame
                                self.capture = cap
                            
                            # Start background thread
                            Thread(target=self._update, daemon=True).start()
                            return self
                        time.sleep(0.1)
                    
                    cap.release()
            except Exception as e:
                print(f"  ❌ Lỗi: {e}")
                continue
        
        print("❌ Không thể kết nối tới ESP32-CAM!")
        print("💡 Kiểm tra:")
        print("   1. ESP32-CAM đã bật và stream?")
        print("   2. IP đúng: ping 10.10.30.189")
        print("   3. Cùng mạng WiFi?")
        print("   4. Firewall không chặn?")
        return None
    
    def _update(self):
        """Background thread đọc frames (PRIVATE)"""
        print("🔄 Thread đọc frame đã bắt đầu")
        
        while not self.stopped:
            try:
                if self.capture and self.capture.isOpened():
                    ret, frame = self.capture.read()
                    
                    if ret and frame is not None and frame.size > 0:
                        with self.lock:
                            self.frame = frame
                            self.last_frame_time = time.time()
                            self.error_count = 0
                            self.connection_lost = False
                    else:
                        self.error_count += 1
                        if self.error_count > 30:  # 30 frames liên tục lỗi
                            with self.lock:
                                self.connection_lost = True
                            print("⚠️ Mất kết nối với ESP32-CAM")
                            
                else:
                    break
                    
            except Exception as e:
                print(f"⚠️ Lỗi đọc frame: {e}")
                with self.lock:
                    self.connection_lost = True
                time.sleep(0.1)
                
            time.sleep(0.01)  # Giảm CPU usage
        
        print("🛑 Thread đọc frame đã dừng")
    
    def read(self):
        """Đọc frame thread-safe"""
        with self.lock:
            return self.frame.copy() if self.frame is not None else None
    
    def is_connected(self):
        """Kiểm tra kết nối"""
        with self.lock:
            return not self.connection_lost
    
    def stop(self):
        """Dừng stream và giải phóng tài nguyên"""
        print("🛑 Đang dừng ESP32-CAM stream...")
        self.stopped = True
        time.sleep(0.1)  # Đợi thread kết thúc
        
        with self.lock:
            if self.capture:
                try:
                    self.capture.release()
                except:
                    pass
                self.capture = None
        print("✅ Đã dừng stream")

# --- KIỂM TRA MODEL ---
if not os.path.exists(model_path):
    print(f"❌ LỖI: Không tìm thấy model '{model_path}'!")
    exit()

# --- LOAD MODEL ---
print("⏳ Đang load AI model...")
try:
    model = YOLO(model_path)
    
    # Tự động detect device (GPU hoặc CPU)
    if torch.cuda.is_available():
        device = 'cuda'
        print("🚀 Sử dụng GPU (CUDA)")
    elif torch.backends.mps.is_available():
        device = 'mps'
        print("🚀 Sử dụng GPU (Apple Silicon)")
    else:
        device = 'cpu'
        print("💻 Sử dụng CPU")
    
    model.to(device)
    model.fuse()  # Tối ưu hóa
    
    # Warmup
    print("🔥 Warming up model...")
    dummy = np.zeros((640, 640, 3), dtype=np.uint8)
    _ = model.predict(source=dummy, conf=confidence_threshold, verbose=False, device=device)
    
    print("✅ Model đã sẵn sàng!")
except Exception as e:
    print(f"❌ Lỗi load model: {e}")
    exit()

# --- KẾT NỐI ESP32-CAM ---
stream = ESP32CamStream(esp32_url)
if stream.start() is None:
    exit()

time.sleep(1)  # Đợi stream ổn định

print("\n" + "="*50)
print("✅ ESP32-CAM đã sẵn sàng!")
print("ĐIỀU KHIỂN:")
print("  [Q] - Thoát chương trình")
print("  [S] - Lưu ảnh kết quả hiện tại")
print("  [SPACE] - Tạm dừng/Tiếp tục")
print("="*50 + "\n")

# --- BIẾN TRẠNG THÁI ---
prev_time = time.time()
frame_count = 0
process_count = 0
fps_display = 0
paused = False
current_annotated_frame = None  # Lưu frame đã xử lý gần nhất
current_raw_frame = None  # Lưu frame gốc gần nhất

# --- VÒNG LẶP CHÍNH ---
try:
    while True:
        # Kiểm tra kết nối
        if not stream.is_connected():
            print("⚠️ Mất kết nối! Đang thử kết nối lại...")
            time.sleep(1)
            continue
        
        # Kiểm tra pause
        if paused:
            key = cv2.waitKey(100) & 0xFF
            if key == ord(' '):
                paused = False
                print("▶️  Tiếp tục")
            elif key == ord('q'):
                break
            continue
        
        # Đọc frame (thread-safe)
        frame = stream.read()
        
        if frame is None:
            print("⚠️ Đang chờ frame...")
            time.sleep(0.1)
            continue
        
        # Lưu frame gốc
        current_raw_frame = frame.copy()
        
        # Tăng frame counter
        frame_count += 1
        
        # Xác định có xử lý frame này không
        should_process = (frame_count % (SKIP_FRAMES + 1) == 0)
        
        if should_process:
            # === XỬ LÝ FRAME VỚI YOLO ===
            height, width = frame.shape[:2]
            
            # Resize để tăng tốc
            if width > RESIZE_WIDTH:
                scale = RESIZE_WIDTH / width
                frame_resized = cv2.resize(frame, None, fx=scale, fy=scale, 
                                          interpolation=cv2.INTER_LINEAR)
            else:
                frame_resized = frame.copy()
            
            # Detection
            try:
                results = model.predict(
                    source=frame_resized, 
                    conf=confidence_threshold,
                    verbose=False,
                    device=device
                )
                
                # Vẽ bounding boxes
                annotated_frame = results[0].plot()
                
                # Scale về kích thước gốc
                if width > RESIZE_WIDTH:
                    annotated_frame = cv2.resize(annotated_frame, (width, height),
                                                interpolation=cv2.INTER_LINEAR)
                
                # Lưu kết quả
                current_annotated_frame = annotated_frame
                process_count += 1
                
            except Exception as e:
                print(f"⚠️ Lỗi detection: {e}")
                current_annotated_frame = frame.copy()
        
        # === HIỂN THỊ FRAME ===
        # Luôn hiển thị frame đã xử lý gần nhất (nếu có)
        if current_annotated_frame is not None:
            display_frame = current_annotated_frame.copy()
        else:
            display_frame = frame.copy()
        
        # Resize về tỷ lệ hiển thị 680x480
        display_frame = cv2.resize(display_frame, (DISPLAY_WIDTH, DISPLAY_HEIGHT),
                                   interpolation=cv2.INTER_LINEAR)
        
        # Thêm thông tin lên frame
        info_y = 30
        cv2.putText(display_frame, f'FPS: {fps_display:.1f}', (10, info_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        info_y += 30
        status = "Processing" if should_process else "Skipped"
        color = (0, 255, 255) if should_process else (128, 128, 128)
        cv2.putText(display_frame, f'Status: {status}', (10, info_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        info_y += 30
        cv2.putText(display_frame, f'Processed: {process_count}', (10, info_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Hiển thị
        cv2.imshow('PBL5 - ESP32-CAM Detection', display_frame)
        
        # === TÍNH FPS ===
        current_time = time.time()
        if current_time - prev_time >= 1.0:
            fps_display = frame_count / (current_time - prev_time)
            frame_count = 0
            prev_time = current_time
        
        # === XỬ LÝ PHÍM ===
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            print("\n👋 Đang thoát...")
            break
            
        elif key == ord('s'):
            # Lưu ảnh hiện tại
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            # Lưu cả 2: ảnh gốc và ảnh đã detect
            if current_raw_frame is not None:
                raw_filename = f'raw_{timestamp}.jpg'
                cv2.imwrite(raw_filename, current_raw_frame)
                print(f"📸 Đã lưu ảnh gốc: {raw_filename}")
            
            if current_annotated_frame is not None:
                ann_filename = f'detected_{timestamp}.jpg'
                cv2.imwrite(ann_filename, current_annotated_frame)
                print(f"📸 Đã lưu ảnh phát hiện: {ann_filename}")
            
        elif key == ord(' '):
            paused = True
            print("⏸️  Tạm dừng (nhấn SPACE để tiếp tục)")

except KeyboardInterrupt:
    print("\n\n⚠️ Nhận Ctrl+C...")

except Exception as e:
    print(f"\n❌ LỖI: {e}")
    import traceback
    traceback.print_exc()

finally:
    # === GIẢI PHÓNG TÀI NGUYÊN ===
    print("\n🧹 Đang dọn dẹp...")
    
    try:
        stream.stop()
    except:
        pass
    
    try:
        cv2.destroyAllWindows()
    except:
        pass
    
    print("✅ Hoàn tất! Tạm biệt 👋\n")
