import cv2
import sys
import time
from ultralytics import YOLO


def draw_overlay(frame, fps, source, detections):
    overlay = frame.copy()
    cv2.rectangle(overlay, (12, 12), (280, 110), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

    lines = [
        f"Camera: {source}",
        f"FPS: {fps:.1f}",
        f"Objects: {detections}",
        "Q: Quit",
    ]

    y = 38
    for line in lines:
        cv2.putText(
            frame,
            line,
            (24, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        y += 24


def run_camera(source: int = 0):
    model = YOLO("model/best.pt")
    cap = cv2.VideoCapture(source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print("Khong mo duoc webcam")
        raise SystemExit(1)

    window_name = "YOLO Webcam"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    prev_time = time.perf_counter()
    fps = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        results = model(frame, conf=0.25, verbose=False)
        annotated_frame = results[0].plot()
        detections = len(results[0].boxes) if results[0].boxes is not None else 0

        now = time.perf_counter()
        instant_fps = 1.0 / max(now - prev_time, 1e-6)
        prev_time = now
        fps = instant_fps if fps == 0.0 else (fps * 0.9 + instant_fps * 0.1)

        draw_overlay(annotated_frame, fps, source, detections)

        cv2.imshow(window_name, annotated_frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


def _parse_source_arg() -> int:
    if len(sys.argv) <= 1:
        return 0
    try:
        return int(sys.argv[1])
    except ValueError:
        print(f"Invalid camera source: {sys.argv[1]!r}. Using default source 0.")
        return 0


if __name__ == "__main__":
    run_camera(_parse_source_arg())
