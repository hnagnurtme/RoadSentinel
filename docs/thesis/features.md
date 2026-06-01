# Chương 2: Phân Tích Chức Năng Hệ Thống

Hệ thống **RoadSentinel** được chia thành ba phân hệ chính: Phân hệ Tài xế (Driver Portal), Phân hệ Quản trị (Admin Portal), và Phân hệ Phần cứng nhúng / Giả lập (IoT & Simulator).

---

## 1. Phân Hệ Tài Xế (Driver Portal)

Phần hệ này cung cấp giao diện riêng tư giúp tài xế theo dõi quá trình làm việc, quản lý lịch sử chấm công ca chạy và xem lại các sự cố vi phạm của mình để thực hiện quyền khiếu nại (kháng nghị).

### Chức năng Chấm công Vân tay (Biometric Clock-In/Out)
* **Xác thực sinh trắc học**: Tài xế quét vân tay trên cabin để bắt đầu ca làm việc (Clock-In) hoặc kết thúc ca làm việc (Clock-Out).
* **Tự động liên kết**: Hệ thống tự động ghi nhận xe đang chạy tương ứng với thiết bị IoT phát ra tín hiệu quét vân tay.
* **Thời gian thực**: Cập nhật trạng thái lái xe trực tiếp lên màn hình quản trị và màn hình cá nhân thông qua WebSocket.

### Chức năng Xem Lịch sử Ca chạy dạng Lịch (Monthly Timekeeping Calendar)
* **Chế độ xem trực quan**: Tài xế có thể xem lịch sử làm việc dưới hai dạng:
  * **Dạng danh sách**: Liệt kê chi tiết từng ca chạy, giờ bắt đầu, giờ kết thúc, thời lượng chạy (ví dụ: `2h 30m`) và trạng thái ca làm việc (Đang chạy / Đã hoàn thành).
  * **Dạng lịch tháng**: Hiển thị lưới lịch 35 ô tương ứng với các ngày trong tháng. Mỗi ngày có ca chạy sẽ hiển thị tổng số giờ làm việc thực tế (ví dụ: `8.5h`) được tô màu nổi bật.
* **Cảnh báo vi phạm trên ô lịch**: Nếu ngày làm việc đó phát sinh bất kỳ cảnh báo vi phạm nào từ AI (như ngủ gật, dùng điện thoại,...), ô lịch ngày đó sẽ hiển thị một **icon cảnh báo nguy hiểm (Alert Icon)** nhấp nháy màu đỏ, giúp tài xế phát hiện nhanh ngày làm việc không an toàn của mình.

### Chức năng Xem Bằng chứng & Gửi Kháng nghị (Violation Evidence & Appeals Flow)
* **Timeline vi phạm cá nhân**: Hiển thị danh sách các sự cố vi phạm xảy ra trong ca chạy được liên kết trực tiếp với tài khoản của tài xế đó (được bảo mật không cho phép xem dữ liệu của tài xế khác).
* **Bằng chứng hình ảnh/video**: Tài xế bấm "Xem trước" (Preview) để phát video ghi lại hành vi vi phạm hoặc ảnh chụp làm bằng chứng vi phạm do camera trên cabin ghi lại.
* **Gửi kháng nghị (Submit Appeal)**: 
  * Nếu tài xế cho rằng hệ thống AI phát hiện sai (ví dụ: dụi mắt bị nhận diện nhầm thành ngủ gật), tài xế có thể viết ghi chú giải trình lý do và tải lên hình ảnh đính kèm minh họa (sử dụng widget upload ảnh trực tuyến).
  * Kháng nghị sau khi gửi sẽ chuyển sang trạng thái "Chờ duyệt" (Pending) và gửi thông báo trực tiếp đến Admin.

---

## 2. Phân Hệ Quản Trị (Admin Portal)

Cung cấp giao diện quản trị trung tâm dành cho người quản lý đội xe và điều hành viên để theo dõi toàn bộ hoạt động của đội ngũ vận tải.

### Bảng Điều Khiển Vận Hành (Operations Dashboard)
* **Các chỉ số đo lường hiệu năng cốt lõi (KPI Badges)**:
  * **Thiết bị hoạt động (Active Assets)**: Hiển thị tỉ lệ xe đang kết nối thiết bị hoạt động trên tổng số xe (ví dụ: `2 / 5` thiết bị hoạt động). Khi click vào sẽ chuyển hướng nhanh đến trang Quản lý xe.
  * **Điểm an toàn trung bình (Avg Safety Score)**: Điểm trung bình của tất cả tài xế được tính từ lịch sử vi phạm. Click vào sẽ chuyển hướng đến trang Quản lý tài xế.
  * **Sự cố nghiêm trọng (Critical Incidents)**: Tổng số sự cố mức nguy hiểm (Ngủ gật, Điện thoại, Va chạm) trong chu kỳ chọn. Click vào sẽ chuyển đến trang Xem chi tiết sự cố.
  * **Tổng giờ lái xe (Total Driving Hours)**: Tính tổng thời gian ca chạy thực tế của toàn bộ đội xe từ database.
* **Biểu đồ xu hướng tuần (Weekly Trends Chart)**: Biểu đồ cột thể hiện số lượng sự cố vi phạm xảy ra theo từng ngày trong tuần, tự động căn giữa dựa theo thời gian xảy ra sự cố gần nhất để hiển thị trực quan.
* **Tỷ lệ tăng giảm so với cùng kỳ ("Cùng kỳ" Percentage Calculations)**: Dashboard tính toán phần trăm tăng/giảm của các chỉ số (ví dụ: giảm `-12%` số vụ vi phạm) so với chu kỳ trước đó, hiển thị màu xanh lá cây nếu vi phạm giảm và màu đỏ nếu vi phạm tăng.
* **Báo cáo sự cố AI gần đây**: Danh sách thời gian thực hiển thị các sự cố mới xảy ra, cho phép người quản lý bấm "Review" để chuyển thẳng đến màn hình phân tích sự cố chi tiết.

### Giám Sát Trực Tuyến LiveMonitor
* **Chọn tài xế thông minh**: Hiển thị danh sách các tài xế có quyền lái xe hoạt động (loại bỏ các tài khoản admin để tránh nhầm lẫn).
* **Camera stream thời gian thực**: Khi chọn một tài xế đang chạy, hệ thống kích hoạt luồng camera cabin trực tiếp từ xe (MJPEG) và vẽ khung nhận diện (Bounding Box) thời gian thực của AI đè lên hình ảnh.
* **Nhật ký thiết bị & Telemetry trực tiếp**: Hiển thị các sự kiện phần cứng phát sinh theo thời gian thực: quét vân tay thành công/thất bại, thiết bị online/offline, và log phản hồi từ còi báo động.

### Phê Duyệt Kháng Nghị (Appeals Review)
* **Bộ lọc và Sắp xếp nâng cao**: Admin lọc kháng nghị theo các trạng thái (Tất cả, Chờ duyệt, Đã chấp nhận, Đã từ chối). Sắp xếp kháng nghị theo thứ tự Ưu tiên chờ duyệt lên trước (Pending First), Mới nhất, hoặc Cũ nhất.
* **Hồ sơ kháng nghị chi tiết**: Hiển thị thông tin tài xế, ảnh đại diện, thông tin xe vi phạm, thời gian xảy ra, video bằng chứng AI ghi lại, cùng với ghi chú giải trình và ảnh đính kèm của tài xế.
* **Quyết định phê duyệt (Approve/Reject)**: Admin nhập ghi chú phản hồi và ấn "Chấp nhận" (chuyển vi phạm thành vô hiệu, phục hồi điểm an toàn cho tài xế) hoặc "Từ chối" (giữ nguyên vi phạm). Giao diện sử dụng hệ thống màu chuẩn dự án (`bg-error` cho nút từ chối và màu xanh lá cho chấp nhận).

---

## 3. Phân Hệ Phần Cứng & Giả Lập (IoT & Simulator)

### ESP32-CAM (Bộ Thu Khung Ảnh Cabin)
* Thu thập ảnh từ cảm biến camera OV2640 và gửi lên server backend qua giao thức WebSockets dưới dạng nhị phân JPEG với tần suất tối ưu (15-20 frames/giây).

### Cảm Biến Vân tay Sinh Trắc Học & Buzzer (Xác Thực & Cảnh Báo Vật Lý)
* **Đầu quét vân tay**: Khi quét vân tay, ESP32 thu thập ID vân tay và gửi yêu cầu REST API POST đến `/users/fingerprint` kèm chữ ký số HMAC-SHA256 bảo mật.
* **Còi báo động (Buzzer)**: ESP32 kết nối MQTT Broker, đăng ký vào chủ đề `roadsentinel/alerts/{vehicle_id}`. Khi nhận được bản tin cảnh báo vi phạm từ backend gửi xuống, thiết bị nhúng sẽ kích hoạt còi phát âm thanh cảnh báo ngắt quãng để nhắc nhở tài xế dừng xe hoặc tập trung lái xe.

### Bộ Giả Lập Hợp Nhất (Unified Device Simulator)
* Cung cấp tập lệnh Python đa luồng (`esp32_simulator.py`) chạy giả lập toàn bộ hành vi của phần cứng: stream ảnh từ webcam cục bộ, nhận lệnh báo động kêu còi trên console, và thực hiện quét vân tay ngẫu nhiên/theo yêu cầu để hỗ trợ kiểm thử hệ thống mà không cần thiết bị vật lý.
