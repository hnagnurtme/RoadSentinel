import cv2
import os
from ultralytics import YOLO
import time
from threading import Thread
import numpy as np

# --- CẤU HÌNH ---
model_path = './model/best_v2.pt'
confidence_threshold = 0.3
esp32_url = 'http://10.10.30.189'  # URL của ESP32-CAM

# Tối ưu hóa
SKIP_FRAMES = 2  # Xử lý 1 frame / 3 frames để tăng FPS
RESIZE_WIDTH = 640  # Giảm kích thước để xử lý nhanh hơn

# --- CLASS ĐỌC FRAME TỪ ESP32 (THREADING) ---
class ESP32CamStream:
    def __init__(self, url):
        self.url = url
        self.frame = None
        self.stopped = False
        self.capture = None
        
    def start(self):
        print(f"📹 Đang kết nối tới ESP32-CAM: {self.url}")
        # Thử các endpoint phổ biến của ESP32-CAM
        possible_endpoints = [
            f'{self.url}/cam-hi.jpg',  # Chất lượng cao
            f'{self.url}/cam-mid.jpg',  # Chất lượng trung bình
            f'{self.url}/cam-lo.jpg',   # Chất lượng thấp
            f'{self.url}:81/stream',    # Stream endpoint
            f'{self.url}/stream',
            f'{self.url}/capture'
        ]
        
        for endpoint in possible_endpoints:
            print(f"  Thử kết nối: {endpoint}")
            self.capture = cv2.VideoCapture(endpoint)
            if self.capture.isOpened():
                ret, test_frame = self.capture.read()
                if ret and test_frame is not None:
                    print(f"✅ Kết nối thành công: {endpoint}")
                    self.frame = test_frame
                    break
                self.capture.release()
        
        if self.frame is None:
            print("❌ Không thể kết nối tới ESP32-CAM!")
            print("💡 Kiểm tra:")
            print("   1. ESP32-CAM đã bật chưa?")
            print("   2. Đúng địa chỉ IP chưa?")
            print("   3. Cùng mạng WiFi chưa?")
            return None
            
        # Bắt đầu thread đọc frame
        Thread(target=self.update, daemon=True).start()
        return self
    
    def update(self):
        while not self.stopped:
            if self.capture and self.capture.isOpened():
                ret, frame = self.capture.read()
                if ret:
                    self.frame = frame
            time.sleep(0.01)  # Giảm CPU usage
    
    def read(self):
        return self.frame
    
    def stop(self):
        self.stopped = True
        if self.capture:
            self.capture.release()

# --- KIỂM TRA MODEL ---
if not os.path.exists(model_path):
    print(f"❌ LỖI: Không tìm thấy file model '{model_path}'!")
    exit()

# --- LOAD MODEL ---
print("⏳ Đang load AI model...")
model = YOLO(model_path)
model.fuse()  # Tối ưu hóa model
print("✅ Model đã sẵn sàng!")

# --- KẾT NỐI ESP32-CAM ---
stream = ESP32CamStream(esp32_url)
if stream.start() is None:
    exit()

time.sleep(1)  # Đợi stream ổn định

print("✅ ESP32-CAM đã sẵn sàng!")
print("👉 Nhấn phím 'q' để thoát")
print("👉 Nhấn phím 's' để lưu ảnh kết quả\n")

# --- BIẾN ĐẾM FPS ---
prev_time = time.time()
frame_count = 0
process_count = 0
fps_display = 0

# --- VÒNG LẶP CHÍNH ---
try:
    while True:
        # Đọc frame từ ESP32
        frame = stream.read()
        
        if frame is None:
            print("⚠️ Đang chờ frame từ ESP32...")
            time.sleep(0.1)
            continue
        
        # Đếm frame
        frame_count += 1
        
        # Skip frames để tăng tốc độ
        if frame_count % (SKIP_FRAMES + 1) != 0:
            # Hiển thị frame gốc không xử lý (nhanh hơn)
            display_frame = frame.copy()
            cv2.putText(display_frame, f'FPS: {fps_display:.1f} (Skip)', (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.imshow('PBL5 - ESP32-CAM Detection', display_frame)
        else:
            # Resize để tăng tốc độ xử lý
            height, width = frame.shape[:2]
            if width > RESIZE_WIDTH:
                scale = RESIZE_WIDTH / width
                frame_resized = cv2.resize(frame, None, fx=scale, fy=scale)
            else:
                frame_resized = frame
            
            # Chạy detection
            results = model.predict(source=frame_resized, conf=confidence_threshold, 
                                   verbose=False, device='cpu')
            
            # Vẽ bounding boxes
            annotated_frame = results[0].plot()
            
            # Scale lại về kích thước gốc nếu đã resize
            if width > RESIZE_WIDTH:
                annotated_frame = cv2.resize(annotated_frame, (width, height))
            
            process_count += 1
            
            # Hiển thị frame
            cv2.imshow('PBL5 - ESP32-CAM Detection', annotated_frame)
        
        # Tính FPS
        current_time = time.time()
        if current_time - prev_time >= 1.0:
            fps_display = frame_count / (current_time - prev_time)
            frame_count = 0
            prev_time = current_time
        
        # Xử lý phím
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("\n👋 Đang đóng chương trình...")
            break
        elif key == ord('s'):
            # Lưu ảnh
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f'capture_{timestamp}.jpg'
            cv2.imwrite(filename, annotated_frame if 'annotated_frame' in locals() else frame)
            print(f"📸 Đã lưu: {filename}")

except KeyboardInterrupt:
    print("\n👋 Đang đóng chương trình...")

# --- GIẢI PHÓNG TÀI NGUYÊN ---
stream.stop()
cv2.destroyAllWindows()
print("✅ Đã đóng kết nối và cửa sổ thành công!")
