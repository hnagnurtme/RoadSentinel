import urllib.request
import json
import time

API_URL = "http://localhost:8000/api/v1/users/fingerprint"
# Thay bằng ID thực tế bạn muốn test
FINGERPRINT_ID = "FINGER_123456"

def simulate_fingerprint(finger_id: str):
    print(f"Đang mô phỏng quét vân tay cho ID: {finger_id}...")
    
    payload = json.dumps({"fingerprint_id": finger_id}).encode('utf-8')
    req = urllib.request.Request(
        API_URL, 
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            print("Thành công! Phản hồi từ Backend:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
    except urllib.error.HTTPError as e:
        print(f"Thất bại! Mã lỗi: {e.code}")
        print(e.read().decode())
    except urllib.error.URLError as e:
        print(f"Lỗi kết nối: {e.reason}. Hãy đảm bảo server backend đang chạy (just run)")

if __name__ == "__main__":
    simulate_fingerprint(FINGERPRINT_ID)
