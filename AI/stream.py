import cv2
import os
from ultralytics import YOLO
import time

# --- CẤU HÌNH ---
model_path = './model/best_v2.pt'
confidence_threshold = 0.3  # Ngưỡng confidence (30%)

# --- KIỂM TRA MODEL ---
if not os.path.exists(model_path):
    print(f"❌ LỖI: Không tìm thấy file model '{model_path}'!")
    exit()

# --- LOAD MODEL ---
print("⏳ Đang load AI model...")
model = YOLO(model_path)
print("✅ Model đã sẵn sàng!")

# --- MỞ WEBCAM ---
print("📹 Đang mở webcam...")
cap = cv2.VideoCapture(0)  # 0 = webcam mặc định

if not cap.isOpened():
    print("❌ LỖI: Không thể mở webcam!")
    exit()

# Cài đặt độ phân giải (tùy chọn)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("✅ Webcam đã sẵn sàng!")
print("👉 Nhấn phím 'q' để thoát\n")

# --- BIẾN ĐẾM FPS ---
prev_time = time.time()
frame_count = 0

# --- VÒNG LẶP CHÍNH ---
while True:
    # Đọc frame từ webcam
    ret, frame = cap.read()
    
    if not ret:
        print("❌ Không thể đọc frame từ webcam!")
        break
    
    # Chạy detection
    results = model.predict(source=frame, conf=confidence_threshold, verbose=False)
    
    # Vẽ bounding boxes lên frame
    annotated_frame = results[0].plot()
    
    # Tính FPS
    frame_count += 1
    current_time = time.time()
    if current_time - prev_time >= 1.0:
        fps = frame_count / (current_time - prev_time)
        frame_count = 0
        prev_time = current_time
        
        # Hiển thị FPS trên frame
        cv2.putText(annotated_frame, f'FPS: {fps:.1f}', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    # Hiển thị frame
    cv2.imshow('PBL5 - Webcam Detection', annotated_frame)
    
    # Kiểm tra phím 'q' để thoát
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("\n👋 Đang đóng chương trình...")
        break

# --- GIẢI PHÓNG TÀI NGUYÊN ---
cap.release()
cv2.destroyAllWindows()
print("✅ Đã đóng webcam và cửa sổ thành công!")