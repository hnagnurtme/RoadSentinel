# Chương 4: Triển Khai Kỹ Thuật & Sơ Đồ Tuần Tự (Sequence Diagrams)

Phần này phân tích chi tiết quy trình hoạt động của ba luồng nghiệp vụ cốt lõi trong hệ thống **RoadSentinel** bằng biểu đồ tuần tự (Sequence Diagram) sử dụng Mermaid.

---

## 1. Quy Trình Chấm Công Sinh Trắc Học Tích Hợp Bảo Mật HMAC

Quy trình này xảy ra khi tài xế thực hiện quét vân tay để Clock-In (bắt đầu lái) hoặc Clock-Out (kết thúc lái) trên thiết bị nhúng đặt trong cabin.

### Biểu đồ tuần tự (Sequence Diagram)

```mermaid
sequenceDiagram
    autonumber
    actor Driver as Tài xế (Driver)
    participant HW as Cảm biến vân tay & ESP32
    participant SV as FastAPI Server
    participant DB as PostgreSQL DB
    participant WS as WebSockets Manager
    participant FE as Dashboard Admin / Portal Driver

    Driver->>HW: Đặt ngón tay lên cảm biến
    HW->>HW: Quét hình ảnh & trích xuất ID (vd: ID = 2)
    Note over HW: Tạo timestamp & tính chữ ký HMAC-SHA256
    HW->>SV: POST /api/v1/users/fingerprint<br/>Body: {fingerprint_id: "FINGER_2"}<br/>Headers: X-Signature, X-Timestamp
    
    SV->>SV: Xác thực chữ ký HMAC & Kiểm tra timestamp
    alt Chữ ký không hợp lệ / Hết hạn
        SV-->>HW: Trả về 401 Unauthorized / 403 Forbidden
        HW->>HW: Nhấp nháy LED đỏ báo lỗi xác thực
    else Xác thực thành công
        SV->>DB: Truy vấn User theo fingerprint_id = "FINGER_2"
        DB-->>SV: Trả về thông tin User (Tài xế Nguyễn Trung Ánh)
        
        SV->>DB: Kiểm tra ca làm việc hiện tại (Active Session)
        
        alt Chưa có ca chạy hoạt động (Clock-In)
            SV->>DB: Tạo bản ghi Driving Session mới (Trạng thái: ACTIVE)
            DB-->>SV: Xác nhận lưu thành công
            SV->>WS: Phát sự kiện "driving_session_started"
            WS-->>FE: Cập nhật trạng thái xe & tài xế "Đang chạy" (màu xanh lá)
            SV-->>HW: Trả về 200 OK (Clock-In thành công)
            HW->>HW: Kêu còi bíp ngắn, nháy LED xanh lá
        else Đang có ca chạy hoạt động (Clock-Out)
            SV->>DB: Cập nhật ca chạy hiện tại (Lưu ended_at, chuyển trạng thái: COMPLETED)
            DB-->>SV: Xác nhận cập nhật thành công
            SV->>WS: Phát sự kiện "driving_session_ended"
            WS-->>FE: Chuyển trạng thái xe sang "Offline", hiển thị tổng thời gian lái
            SV-->>HW: Trả về 200 OK (Clock-Out thành công)
            HW->>HW: Kêu còi bíp bíp dài, tắt LED hoạt động
        end
    end
```

---

## 2. Quy Trình Giám Sát Hành Vi AI & Phát Cảnh Báo Thời Gian Thực

Quy trình này thể hiện cách thức luồng hình ảnh từ cabin được xử lý bằng AI để phát hiện vi phạm và đồng bộ cảnh báo vật lý trên xe lẫn Dashboard của quản trị viên.

### Biểu đồ tuần tự (Sequence Diagram)

```mermaid
sequenceDiagram
    autonumber
    participant CAM as ESP32-CAM (Cabin)
    participant WS as WebSockets Gateway
    participant AI as AI Engine (YOLOv8)
    participant DB as PostgreSQL DB
    participant MQTT as HiveMQ MQTT Broker
    participant HW as ESP32 Speaker (Buzzer)
    participant ADM as Web Dashboard Admin

    CAM->>WS: Kết nối WebSocket & Truyền luồng ảnh JPEG (MJPEG binary)
    
    loop Xử lý liên tục (15-20 frames/giây)
        WS->>AI: Gửi khung ảnh thô (Image Frame)
        AI->>AI: Chạy mô hình YOLOv8 trích xuất vật thể
        Note over AI: Nhận diện tọa độ mắt, miệng, điện thoại...
        AI->>AI: Áp dụng Cửa sổ trượt (Sliding Window Filter)
        
        alt Phát hiện hành vi vi phạm thực sự (vd: SLEEPING > 70% trong 2 giây)
            AI-->>WS: Trả về kết quả vi phạm (SLEEPING, confidence = 92%)
            
            WS->>DB: Truy vấn ca chạy hoạt động (Active Session) để lấy driver_id & vehicle_id
            DB-->>WS: Trả về driver_id (Nguyễn Trung Ánh) & vehicle_id (RS-001)
            
            WS->>DB: Lưu sự cố vi phạm (Tạo bản ghi Alert kèm evidence_url ảnh vi phạm)
            DB-->>WS: Xác nhận lưu thành công (Lấy alert_id)
            
            par Gửi thông báo trực tuyến đến Admin Dashboard
                WS->>ADM: Đẩy sự kiện WebSocket "alert.created" kèm dữ liệu tài xế & xe
                Note over ADM: Dashboard kêu chuông báo, nhấp nháy dòng vi phạm màu đỏ
            and Phát cảnh báo vật lý xuống xe (Còi báo động cabin)
                WS->>MQTT: Publish bản tin báo động xuống chủ đề: roadsentinel/alerts/RS-001
                MQTT->>HW: Forward bản tin báo động đến thiết bị nhúng trên xe
                HW->>HW: Kích hoạt còi báo động Buzzer kêu ngắt quãng (Bíp! Bíp!) báo tài xế
            end
        else Không có vi phạm / Nhiễu tín hiệu
            AI-->>WS: Trả về trạng thái an toàn (No violations)
            WS->>ADM: Chỉ cập nhật hình ảnh Live stream lên màn hình LiveMonitor
        end
    end
```

---

## 3. Quy Trình Kháng Nghị Vi Phạm (Appeals Workflow)

Quy trình này thể hiện sự tương tác giữa tài xế và quản trị viên khi tài xế gửi đơn khiếu nại đối với một sự cố vi phạm mà hệ thống AI ghi nhận.

### Biểu đồ tuần tự (Sequence Diagram)

```mermaid
sequenceDiagram
    autonumber
    actor Driver as Tài xế (Driver)
    participant DP as Driver Portal (Frontend)
    participant API as FastAPI REST Server
    participant CLD as Cloud Storage (Cloudinary)
    participant DB as PostgreSQL DB
    actor Admin as Người quản lý (Admin)
    participant AP as Admin Portal (Frontend)

    Driver->>DP: Vào danh sách "Bằng chứng vi phạm"
    DP->>API: GET /api/v1/alerts (được lọc chỉ lấy vi phạm của driver đăng nhập)
    API->>DB: Query alerts where driver_id = current_user_id
    DB-->>API: Trả về danh sách vi phạm
    API-->>DP: Trả về dữ liệu vi phạm
    DP->>Driver: Hiển thị bảng timeline vi phạm
    
    Driver->>DP: Bấm "Xem trước" (Preview) và xem video bằng chứng
    Driver->>DP: Bấm "Kháng nghị" (Submit Appeal) đối với sự cố ngủ gật
    DP->>Driver: Yêu cầu tải lên ảnh bằng chứng bác bỏ và nhập giải trình lý do
    
    Driver->>DP: Chọn ảnh đính kèm từ thiết bị
    DP->>CLD: Upload ảnh trực tiếp lên Cloudinary
    CLD-->>DP: Trả về URL ảnh đính kèm (attachment_url)
    
    Driver->>DP: Nhập lý do (vd: "Tôi chỉ dụi mắt chứ không ngủ gật") & Bấm gửi
    DP->>API: POST /api/v1/appeals<br/>Body: {alert_id, description, attachment_url}
    API->>DB: Tạo bản ghi Appeal mới (Trạng thái: PENDING)
    DB-->>API: Xác nhận lưu thành công
    API-->>DP: Trả về thông tin Kháng nghị đã tạo
    DP->>Driver: Thông báo "Gửi kháng nghị thành công, đang chờ phê duyệt"
    
    Note over Admin: Admin kiểm tra danh sách kháng nghị
    Admin->>AP: Vào màn hình "Quản lý Kháng nghị" (Admin Appeals)
    AP->>API: GET /api/v1/appeals (Lọc Pending First)
    API->>DB: Query appeals order by status = PENDING desc, created_at desc
    DB-->>API: Trả về danh sách kháng nghị
    API-->>AP: Trả về dữ liệu kháng nghị
    AP->>Admin: Hiển thị giao diện duyệt đơn kèm đầy đủ bằng chứng
    
    alt Chấp nhận kháng nghị (Approve)
        Admin->>AP: Nhập ghi chú phản hồi & Bấm "Chấp nhận"
        AP->>API: PATCH /api/v1/appeals/{appeal_id}<br/>Body: {status: "APPROVED", admin_note}
        API->>DB: Cập nhật trạng thái Appeal -> APPROVED, cập nhật điểm an toàn tài xế
        DB-->>API: Xác nhận cập nhật thành công
        API-->>AP: Trả về 200 OK
        AP->>Admin: Cập nhật giao diện đơn đã duyệt (Màu xanh lá)
    else Từ chối kháng nghị (Reject)
        Admin->>AP: Nhập ghi chú phản hồi & Bấm "Từ chối"
        AP->>API: PATCH /api/v1/appeals/{appeal_id}<br/>Body: {status: "REJECTED", admin_note}
        API->>DB: Cập nhật trạng thái Appeal -> REJECTED
        DB-->>API: Xác nhận cập nhật thành công
        API-->>AP: Trả về 200 OK
        AP->>Admin: Cập nhật giao diện đơn đã bị từ chối (Màu đỏ)
    end
```

---

## 4. Các Thông Số Ngưỡng (Threshold Parameters) & Tham Số Cấu Hình Hệ Thống

Để đảm bảo hệ thống vận hành ổn định, chính xác và giảm thiểu tối đa hiện tượng cảnh báo sai (False Alarms) mà không làm mất đi các sự cố nguy hiểm thực tế, các thông số ngưỡng kỹ thuật dưới đây đã được nghiên cứu và thiết lập cấu hình trong mã nguồn:

### 4.1. Ngưỡng Tự Tin Phát Hiện Vật Thể (YOLOv8 Confidence Threshold)
* **Ký hiệu**: $\theta_{conf}$
* **Giá trị thiết lập**: `0.50` (50%)
* **Ý nghĩa**: Đây là độ tin cậy tối thiểu mà mô hình YOLOv8 trích xuất được cho mỗi lớp đối tượng (mắt nhắm, dùng điện thoại, vô lăng...) để được chấp nhận đưa vào giải thuật xử lý tiếp theo.
* **Lý do**: Thiết lập ở mức 50% giúp đảm bảo không bỏ sót các trường hợp tài xế hơi nghiêng mặt làm khuất một phần mắt, đồng thời đủ cao để loại bỏ các vật thể nền trong cabin bị nhận diện nhầm.

### 4.2. Tham Số Cửa Sổ Thời Gian Trượt (Sliding Window Duration)
* **Ký hiệu**: $W_{duration}$
* **Giá trị thiết lập theo hành vi**:
  * **Ngủ gật / Buồn ngủ nặng (`SLEEPING` / `DROWSY`)**: $W_{sleep} = 2.5$ giây.
  * **Sử dụng điện thoại (`USING_PHONE`)**: $W_{phone} = 1.5$ giây.
  * **Mất tập trung / Ngoảnh mặt đi (`DISTRACTED`)**: $W_{dist} = 3.0$ giây.
* **Ý nghĩa**: Khoảng thời gian (giây) liên tiếp mà hệ thống thu thập dữ liệu khung hình (frames) để đánh giá hành vi.
* **Lý do**: 
  * Chu kỳ nháy mắt tự nhiên của con người diễn ra trong vòng 0.1 đến 0.4 giây. Việc đặt cửa sổ ngủ gật là 2.5 giây đảm bảo loại trừ hoàn toàn việc nháy mắt sinh học, chỉ kích hoạt khi tài xế thực sự nhắm mắt ngủ gật.
  * Việc đưa điện thoại lên tai chỉ cần 1.5 giây để nhận biết và cảnh báo sớm vì đây là hành vi cực kỳ nguy hiểm trực tiếp khi xe đang di chuyển.

### 4.3. Ngưỡng Tỉ Lệ Khung Hình Vi Phạm (Violation Ratio Threshold)
* **Ký hiệu**: $\theta_{ratio}$
* **Giá trị thiết lập**: `0.70` (70%)
* **Ý nghĩa**: Tỉ lệ phần trăm số lượng frame ghi nhận hành vi vi phạm trên tổng số frame thu được trong cửa sổ thời gian trượt $W$.
* **Công thức kích hoạt**: 
$$\text{Trigger Alert} = \text{True} \iff \frac{N_{vi\_pham}}{N_{tong}} \ge 0.70$$
* **Lý do**: Khi camera truyền luồng ảnh MJPEG, có thể có từ 1-2 frame bị nhòe hình (motion blur) do xe đi qua chỗ xóc dẫn đến AI phán đoán sai lệch. Ngưỡng 70% đảm bảo rằng nếu có vài frame nhận diện lỗi đơn lẻ xen kẽ giữa các frame bình thường, còi báo động vẫn sẽ không kêu, giảm thiểu hoàn toàn sự ức chế cho tài xế.

### 4.4. Ngưỡng Thời Gian Xác Thực HMAC (HMAC Time Window Offset)
* **Ký hiệu**: $T_{offset}$
* **Giá trị thiết lập**: `30` giây
* **Ý nghĩa**: Khoảng thời gian chênh lệch tối đa cho phép giữa timestamp đính kèm trong request gửi từ thiết bị nhúng (`X-Timestamp`) và thời gian thực nhận yêu cầu của máy chủ Backend.
* **Lý do**: Khoảng lệch 30 giây đủ rộng để bù đắp cho độ trễ truyền dẫn mạng di động (4G/5G) tại các vùng sóng yếu, nhưng đủ ngắn để chặn đứng hoàn toàn các cuộc tấn công gửi lại (Replay Attacks) - nơi kẻ tấn công đánh cắp gói tin chấm công cũ và phát lại sau đó nhiều giờ.

