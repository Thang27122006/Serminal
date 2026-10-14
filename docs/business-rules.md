# QUY TẮC NGHIỆP VỤ HỆ THỐNG (BUSINESS RULES)
## DỰ ÁN: AI MEETING

---

## 1. GIỚI THIỆU
Tài liệu này xác định các quy tắc nghiệp vụ (Business Rules - BR) chi phối luồng hoạt động, tính hợp lệ của dữ liệu, sự tương tác giữa người dùng và trạng thái của hệ thống trong ứng dụng hội thảo trực tuyến AI Meeting.

Mọi quyết định chưa có sự thống nhất từ Product Owner hoặc các bên liên quan được gắn nhãn tường minh là **[TBD - To Be Determined]**; kiến trúc sư và lập trình viên không tự ý áp đặt quyết định cá nhân vào mã nguồn.

---

## 2. QUY TẮC PHÒNG HỌP & ĐỊNH DANH

### BR-01: Định dạng và Tính duy nhất của Room ID
- **BR-01.1 (Định dạng):** Mã định danh phòng họp (`room_code`) có dạng chuỗi ký tự thân thiện gồm 3 nhóm 3-4 ký tự cách nhau bằng dấu gạch ngang (ví dụ: `abc-defg-hij` hoặc `mtg-789-xyz`), sử dụng bảng mã chữ cái thường `[a-z0-9]`. Không sử dụng các ký tự dễ gây nhầm lẫn như `0/o`, `1/l/i`.
- **BR-01.2 (Tính duy nhất):** `room_code` là duy nhất trên toàn hệ thống trong cơ sở dữ liệu (`unique=True` trong PostgreSQL).
- **BR-01.3 (Xử lý trùng lặp):** Thuật toán sinh mã ngẫu nhiên phải tự động kiểm tra sự tồn tại trong DB trước khi cấp phát. Nếu phát hiện trùng, hệ thống thực hiện thử lại tối đa 3 lần. Nếu vẫn trùng, trả về lỗi hệ thống 500.

### BR-02: Vòng đời phòng họp (Room Lifecycle)
- **BR-02.1 (Khởi tạo):** Phòng họp được tạo thông qua API REST. Khi vừa tạo, trạng thái của phòng là `active`, trường `created_at` ghi nhận thời điểm tạo.
- **BR-02.2 (Thời gian sống):** 
  - **[TBD - Quyết định cần xác nhận]:** Phòng họp có thời hạn tự động đóng sau bao lâu nếu không có ai tham gia? *(Đề xuất kỹ thuật: Nếu sau 30 phút kể từ lúc tạo mà không có bất kỳ kết nối nào, trạng thái phòng chuyển sang `expired`).*
- **BR-02.3 (Kết thúc phòng họp):**
  - Khi Host chủ động đóng phòng (nếu có tính năng End Room), phòng chuyển sang trạng thái `ended`, trường `ended_at` được cập nhật. Các kết nối WebSocket liên quan bị ngắt với mã đóng chuẩn.
  - **[TBD - Quyết định cần xác nhận]:** Nếu Host rời phòng mà không đóng phòng, phòng họp có bị đóng ngay lập tức không? Hay vẫn duy trì cho đến khi người cuối cùng rời đi? *(Đề xuất: Phòng tiếp tục duy trì cho tới khi thành viên cuối cùng rời đi. Khi phòng không còn ai, hệ thống đếm ngược 5 phút trước khi đánh dấu `ended`).*

---

## 3. QUYỀN TRUY CẬP VÀ XÁC THỰC NGƯỜI DÙNG

### BR-03: Điều kiện tạo và tham gia phòng
- **BR-03.1 (Tạo phòng):** Bắt buộc người dùng phải đăng nhập tài khoản (`Authenticated User`). Khách vãng lai (`Guest`) không được phép gọi API tạo phòng.
- **BR-03.2 (Tham gia phòng):**
  - Người dùng đăng nhập có thể tham gia bất kỳ phòng họp nào đang ở trạng thái `active` bằng `room_code`.
  - **[TBD - Quyết định cần xác nhận]:** Người dùng Guest (chưa đăng ký) có được phép tham gia phòng họp bằng cách nhập mã phòng và Tên hiển thị (Display Name) không? Hay bắt buộc phải đăng nhập?
    - *Phương án A:* Cho phép Guest tham gia với tên tạm thời (Display Name lưu trong phiên WebSocket).
    - *Phương án B:* Bắt buộc chuyển hướng về trang Đăng nhập/Đăng ký.

### BR-04: Giới hạn số lượng thành viên trong phòng (Mesh Topology Limit)
- **BR-04.1 (Ngưỡng an toàn Mesh):** Do ứng dụng sử dụng mô hình WebRTC Full Mesh (mỗi client gửi và nhận $N-1$ luồng media), số lượng kết nối tối đa cho mỗi phòng được cấu hình cứng là **6 người** (`max_participants = 6`).
- **BR-04.2 (Từ chối khi quá tải):** Khi một client cố gắng kết nối WebSocket vào một phòng đã có đủ 6 thành viên đang online, kết nối bị từ chối với mã lỗi WebSocket `4003 (Room Full)` và thông báo hiển thị trên giao diện: *"Phòng họp đã đạt số lượng tối đa cho phép"*.

---

## 4. XỬ LÝ PHIÊN, THIẾT BỊ VÀ ĐA KẾT NỐI

### BR-05: Cùng một tài khoản mở trên nhiều tab hoặc nhiều thiết bị
- **BR-05.1 (Định danh Peer):** Trong phòng họp, mỗi kết nối WebSocket được cấp phát một `peer_id` ngẫu nhiên duy nhất (UUIDv4) gắn liền với vòng đời của tab trình duyệt đó, thay vì dùng trực tiếp `user_id` làm khóa định danh WebRTC.
- **BR-05.2 (Xử lý đa tab):**
  - **[TBD - Quyết định cần xác nhận]:** Nếu cùng một tài khoản người dùng mở đồng thời 2 tab vào cùng một phòng:
    - *Phương án 1 (Hỗ trợ đa tab độc lập):* Hệ thống coi mỗi tab là một Peer riêng biệt (`peer_id` khác nhau). Người dùng sẽ thấy chính mình xuất hiện 2 lần trên màn hình (thường gây hiện tượng lặp tiếng vọng - audio feedback loop nếu không mute).
    - *Phương án 2 (Đơn phiên):* Hệ thống đóng phiên cũ của tài khoản đó và chỉ giữ lại phiên mới nhất, kèm thông báo: *"Tài khoản của bạn đã được kết nối từ một cửa sổ khác"*.
    - *(Đề xuất kỹ thuật giai đoạn 1: Triển khai Phương án 1 với peer_id riêng biệt để tránh sự phức tạp trong việc ngắt socket cũ).*

---

## 5. QUẢN LÝ TRẠNG THÁI THÀNH VIÊN VÀ MẤT KẾT NỐI

### BR-06: Trạng thái thành viên khi vào, rời và mất kết nối
- **BR-06.1 (Gia nhập phòng - Join):**
  - Khi client kết nối WebSocket thành công và gửi thông điệp `join_room`, hệ thống ghi nhận thành viên vào Channels Group tương ứng.
  - Server gửi thông điệp `user_joined` (chứa `peer_id`, `user_id`, `name`) tới toàn bộ thành viên đang có mặt.
  - Server gửi lại thông điệp `room_state` (danh sách toàn bộ các peer hiện có) cho client mới để bắt đầu quá trình đàm phán WebRTC Offer/Answer.
- **BR-06.2 (Rời phòng chủ động - Graceful Leave):**
  - Khi người dùng bấm nút "Rời phòng", client phát thông điệp `leave_room` trước khi ngắt kết nối WebSocket và giải phóng camera/mic.
  - Server nhận thông điệp, loại client khỏi Channels Group và broadcast `user_left` kèm `peer_id` cho các client còn lại để đóng `RTCPeerConnection` tương ứng.
- **BR-06.3 (Mất kết nối đột ngột - Abrupt Disconnect):**
  - Khi tab bị tắt đột ngột hoặc mất kết nối mạng (Network Drop), server Channels phát hiện sự kiện ngắt kết nối tầng transport (`disconnect` hook của Consumer).
  - Server tự động kích hoạt broadcast sự kiện `user_left` cho nhóm phòng, đảm bảo không lưu giữ peer mồ côi (ghost peers).

---

## 6. QUY TẮC NHẮN TIN TRONG PHÒNG (IN-ROOM CHAT)

### BR-07: Cách ly và toàn vẹn tin nhắn
- **BR-07.1 (Cách ly phòng):** Tin nhắn gửi qua kênh WebSocket chỉ được broadcast cho các thành viên thuộc đúng Channels Group của phòng đó. Tuyệt đối không để rò rỉ sang phòng khác.
- **BR-07.2 (Kiểm duyệt định dạng):**
  - Tin nhắn không được rỗng hoặc chỉ chứa khoảng trắng.
  - Độ dài tối đa của một tin nhắn văn bản là 1,000 ký tự UTF-8.
  - Không cho phép gửi mã HTML/Javascript thô; Client và Server phải escape dữ liệu để ngăn chặn XSS.
- **BR-07.3 (Lưu trữ tin nhắn):**
  - **[TBD - Quyết định cần xác nhận]:** Tin nhắn chat có bắt buộc phải lưu vào bảng `chat_messages` trong cơ sở dữ liệu PostgreSQL hay không?
    - *Nếu CÓ:* Người vào sau có thể xem được lịch sử trò chuyện trước đó của phòng.
    - *Nếu KHÔNG:* Tin nhắn hoạt động dạng Ephemeral (chỉ chuyển tiếp trong bộ nhớ Channels/Redis), khi phòng đóng thì mất toàn bộ nội dung.

---

## 7. XỬ LÝ QUYỀN THIẾT BỊ MEDIA & NGOẠI LỆ

### BR-08: Hành vi khi từ chối quyền Camera / Micro
- **BR-08.1 (Từ chối quyền Camera/Micro - Permission Denied):**
  - Khi người dùng bấm "Chặn" (Block) hoặc thiết bị không có webcam/micro:
  - Ứng dụng **không được phép dừng hoạt động (crash) hay chặn người dùng vào phòng**.
  - Ứng dụng chuyển sang trạng thái hoạt động: **Khán thính giả (Listen-only & View-only)**.
  - Local Video hiển thị ảnh đại diện mặc định (Avatar) kèm biểu tượng Mic gạch chéo.
  - Hệ thống vẫn thiết lập kết nối WebRTC để nhận luồng âm thanh và hình ảnh từ các thành viên khác.
  - Hiển thị banner cảnh báo nhẹ nhàng: *"Không thể truy cập camera/micro. Bạn đang tham gia ở chế độ chỉ xem."*

### BR-09: Hành vi khi chia sẻ màn hình
- **BR-09.1 (Một luồng chia sẻ tại một thời điểm):**
  - **[TBD - Quyết định cần xác nhận]:** Có cho phép nhiều người chia sẻ màn hình cùng lúc trong phòng không? *(Đề xuất kỹ thuật: Trong mô hình Mesh, mỗi lần chỉ nên cho phép 01 người chia sẻ màn hình để tránh nghẽn băng thông).*
- **BR-09.2 (Hủy chia sẻ màn hình):**
  - Khi người dùng bấm nút "Dừng chia sẻ" trên giao diện web hoặc bấm "Stop sharing" trên thanh công cụ của hệ điều hành/trình duyệt (`track.onended`), ứng dụng phải tự động chuyển đổi luồng video trở lại Webcam của người dùng mà không làm đứt kết nối WebRTC.

---

## 8. BẢNG TỔNG HỢP CÁC QUYẾT ĐỊNH CẦN XÁC NHẬN (TBD SUMMARY)

| Mã vấn đề | Nội dung câu hỏi nghiệp vụ | Các phương án khả thi | Khuyến nghị của Architect | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **TBD-01** | Quyền tham gia của khách vãng lai (Guest User)? | (A) Bắt buộc đăng nhập<br>(B) Cho phép Guest nhập tên | Phương án B (Linh hoạt, tiện dụng cho người dự thính) | Chờ PO chốt |
| **TBD-02** | Xử lý khi Host rời khỏi phòng họp? | (A) Đóng phòng ngay<br>(B) Duy trì đến khi hết người | Phương án B (Tránh ngắt quãng cuộc họp của các thành viên khác) | Chờ PO chốt |
| **TBD-03** | Quyền quản trị phòng của Host (Kick/Mute all)? | (A) Host có toàn quyền<br>(B) Bình đẳng (chưa phân quyền) | Phương án B cho Tuần 1-3; Phương án A cho Tuần 4+ | Chờ PO chốt |
| **TBD-04** | Lưu trữ lịch sử tin nhắn trong phòng? | (A) Lưu vào PostgreSQL<br>(B) Chỉ chuyển tiếp thời gian thực | Phương án B trong giai đoạn đầu, có thể nâng cấp lên A | Chờ PO chốt |
| **TBD-05** | Cho phép nhiều người chia sẻ màn hình đồng thời? | (A) Cho phép đồng thời<br>(B) Chỉ 1 người tại một thời điểm | Phương án B (Tối ưu tài nguyên mạng Mesh) | Chờ PO chốt |
