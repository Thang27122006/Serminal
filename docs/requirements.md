# ĐẶC TẢ YÊU CẦU PHẦN MỀM (SOFTWARE REQUIREMENTS SPECIFICATION)
## DỰ ÁN: NỀN TẢNG HỘI THẢO TRỰC TUYẾN THỜI GIAN THỰC (AI MEETING)

---

## 1. GIỚI THIỆU & MỤC TIÊU DỰ ÁN

### 1.1. Mục tiêu dự án
Dự án **AI Meeting** nhằm xây dựng một hệ thống hội thảo trực tuyến thời gian thực trên nền tảng Web theo mô hình Client–Server kết hợp truyền thông P2P WebRTC. Hệ thống hỗ trợ người dùng giao tiếp âm thanh, hình ảnh chất lượng cao với độ trễ thấp, chia sẻ màn hình và trao đổi tin nhắn văn bản tức thời trực tiếp qua trình duyệt web mà không cần cài đặt phần mềm bổ trợ.

### 1.2. Phạm vi dự án (In-Scope)
- **Xác thực & Người dùng:** Đăng ký tài khoản, đăng nhập, quản lý phiên làm việc, lấy thông tin người dùng hiện tại.
- **Quản lý phòng họp:** Khởi tạo phòng họp mới với mã định danh duy nhất (Room Code), tham gia phòng họp bằng mã phòng, hiển thị danh sách người tham gia trong thời gian thực.
- **Signaling thời gian thực:** Kết nối và duy trì kênh WebSocket sử dụng Django Channels & Redis broker để trao đổi thông tin phiên (Session Description Protocol - SDP) và ICE Candidates.
- **Truyền thông Media WebRTC:** Kết nối mạng lưới đồng đẳng (Full Mesh) giữa các client trong phòng họp nhỏ; truyền tải âm thanh (Audio) và hình ảnh (Video) hai chiều thời gian thực.
- **Điều khiển thiết bị:** Bật/tắt Micro (Mute/Unmute audio track), bật/tắt Camera (Enable/Disable video track) tức thời trên giao diện.
- **Chia sẻ màn hình:** Sử dụng Web Screen Capture API (`getDisplayMedia`) để chia sẻ màn hình làm việc với các thành viên khác trong phòng.
- **Nhắn tin trong phòng (In-room Chat):** Trao đổi tin nhắn văn bản tức thời giữa các thành viên đang có mặt trong phòng.
- **Rời phòng & Dọn dẹp tài nguyên:** Rời phòng an toàn, giải phóng Camera/Microphone/Screen capture, đóng WebRTC PeerConnection và thông báo cập nhật danh sách cho các thành viên còn lại.

### 1.3. Ngoài phạm vi Tuần 1 / Phiên bản hiện tại (Out-of-Scope)
- Máy chủ chuyển tiếp Media chuyên dụng (SFU - Selective Forwarding Unit hoặc MCU - Multipoint Control Unit). Phiên bản hiện tại tập trung kiến trúc Full Mesh cho nhóm nhỏ (< 6 người).
- Ghi hình cuộc họp phía máy chủ (Server-side meeting recording).
- Tính năng AI thời gian thực (như dịch thuật tự động, tóm tắt cuộc họp tự động, nhận diện khuôn mặt). Các tính năng AI sẽ được tích hợp ở các giai đoạn sau khi hạ tầng WebRTC ổn định.
- Quản trị phòng họp nâng cao (Kích người dùng, tắt tiếng cưỡng chế toàn phòng, chia phòng con - Breakout rooms) chưa triển khai vì chưa thống nhất mô hình phân quyền Host.
- Phòng họp có mật khẩu hoặc phòng chờ duyệt (Waiting Room).

---

## 2. TÁC NHÂN HỆ THỐNG (ACTORS)

| Tác nhân (Actor) | Định nghĩa & Trách nhiệm | Quyền hạn mặc định |
| :--- | :--- | :--- |
| **Guest (Khách vãng lai)** | Người dùng truy cập hệ thống nhưng chưa đăng nhập hoặc không có tài khoản. | - Xem trang giới thiệu/đăng nhập/đăng ký.<br>- *(Cần xác nhận)* Có được tham gia phòng qua Room Code với tư cách ẩn danh hay bắt buộc đăng nhập? *(Mặc định: Phải có tên hiển thị nếu được phép)* |
| **Authenticated User** | Người dùng đã đăng ký và xác thực thành công vào hệ thống. | - Quản lý hồ sơ cá nhân.<br>- Khởi tạo phòng họp mới.<br>- Tham gia bất kỳ phòng họp hợp lệ nào bằng Room Code. |
| **Host (Chủ phòng / Người tạo phòng)** | Người dùng khởi tạo phòng họp cụ thể. | - Có quyền của Authenticated User trong phòng.<br>- Đại diện định danh phòng họp.<br>- *Lưu ý quan trọng:* Chưa gán các quyền đặc quyền quản trị (Kick/Mute người khác) nếu chưa có phê duyệt chính thức. |
| **Participant (Thành viên phòng)** | Bất kỳ người dùng nào đang hiện diện trong một phiên phòng họp cụ thể. | - Bật/tắt mic và camera cá nhân.<br>- Bật/tắt chia sẻ màn hình cá nhân.<br>- Gửi/nhận tin nhắn trong phòng.<br>- Xem danh sách thành viên hiện tại.<br>- Rời khỏi phòng họp. |

---

## 3. DANH MỤC YÊU CẦU CHỨC NĂNG (FUNCTIONAL REQUIREMENTS)

### 3.1. Phân loại mức độ ưu tiên
- **Must-have (Bắt buộc):** Chức năng cốt lõi bắt buộc phải hoàn thành để hệ thống hoạt động.
- **Should-have (Hoàn thiện):** Chức năng cần thiết để trải nghiệm người dùng hoàn chỉnh, ổn định.
- **Could-have (Mở rộng):** Chức năng gia tăng giá trị, có thể triển khai ở các tuần tiếp theo.

---

### FR-01: Đăng ký tài khoản (Must-have)
- **Mô tả:** Cho phép người dùng mới tạo tài khoản bằng tên người dùng (username), email và mật khẩu.
- **Điều kiện tiền đề:** Người dùng chưa đăng nhập.
- **Luồng chính:**
  1. Người dùng nhập thông tin: `username`, `email`, `password`, `confirm_password`.
  2. Hệ thống kiểm tra tính hợp lệ của dữ liệu (email đúng định dạng, mật khẩu đủ độ dài tối thiểu 8 ký tự, mật khẩu khớp nhau, username/email chưa tồn tại).
  3. Hệ thống mã hóa mật khẩu an toàn (PBKDF2/Argon2) và lưu vào cơ sở dữ liệu.
  4. Hệ thống phản hồi thành công và điều hướng sang trang đăng nhập.
- **Luồng ngoại lệ:**
  - Username hoặc Email đã tồn tại -> Trả về lỗi 400 Bad Request kèm thông báo chi tiết.
  - Mật khẩu không đáp ứng tiêu chuẩn an toàn -> Trả về lỗi 400 Bad Request.
- **Tiêu chí nghiệm thu:**
  - Tạo thành công bản ghi User mới trong PostgreSQL với mật khẩu đã hash.
  - Phản hồi HTTP Status 201 Created kèm dữ liệu user (không chứa password hash).

---

### FR-02: Đăng nhập & Xác thực (Must-have)
- **Mô tả:** Người dùng đăng nhập hệ thống để nhận thông tin xác thực (Session / JWT Token).
- **Điều kiện tiền đề:** Người dùng đã có tài khoản.
- **Luồng chính:**
  1. Người dùng gửi `username` (hoặc `email`) và `password`.
  2. Hệ thống xác minh thông tin tài khoản.
  3. Hệ thống tạo phiên làm việc (Session/Token) và trả về thông tin người dùng.
- **Luồng ngoại lệ:**
  - Thông tin đăng nhập sai -> Trả về lỗi 401 Unauthorized ("Tài khoản hoặc mật khẩu không chính xác").
  - Tài khoản bị vô hiệu hóa (`is_active=False`) -> Trả về lỗi 403 Forbidden.
- **Tiêu chí nghiệm thu:**
  - Đăng nhập thành công trả về 200 OK và Token/Session Cookie hợp lệ.
  - Người dùng có thể sử dụng Token để gọi các API được bảo vệ.

---

### FR-03: Lấy thông tin người dùng hiện tại (Must-have)
- **Mô tả:** Client truy vấn hồ sơ người dùng đang đăng nhập để hiển thị trên giao diện.
- **Điều kiện tiền đề:** Đã xác thực.
- **Luồng chính:** Client gửi request kèm token xác thực đến `/api/v1/auth/me/`. Hệ thống trả về `id`, `username`, `email`, `full_name`.
- **Luồng ngoại lệ:** Token hết hạn hoặc không hợp lệ -> Trả về lỗi 401 Unauthorized.
- **Tiêu chí nghiệm thu:** Trả về mã 200 OK kèm thông tin định danh chính xác.

---

### FR-04: Đăng xuất (Should-have)
- **Mô tả:** Hủy bỏ phiên làm việc của người dùng.
- **Điều kiện tiền đề:** Người dùng đang đăng nhập.
- **Luồng chính:** Client gửi yêu cầu đăng xuất. Hệ thống hủy Session/thu hồi Token.
- **Tiêu chí nghiệm thu:** Token/Session cũ không còn quyền truy cập tài nguyên bảo mật.

---

### FR-05: Khởi tạo phòng họp (Must-have)
- **Mô tả:** Người dùng tạo một phòng họp mới và nhận Room Code để chia sẻ cho người khác.
- **Điều kiện tiền đề:** Người dùng đã xác thực.
- **Luồng chính:**
  1. Người dùng yêu cầu tạo phòng (kèm tiêu đề phòng họp tùy chọn).
  2. Hệ thống sinh mã Room Code ngẫu nhiên không trùng lặp (định dạng chuẩn, vd: `abc-defg-hij` hoặc chuỗi ký tự an toàn).
  3. Hệ thống lưu trữ bản ghi phòng họp vào cơ sở dữ liệu với trạng thái `active`.
  4. Hệ thống trả về thông tin phòng họp gồm `room_code`, `title`, `created_at`.
- **Luồng ngoại lệ:**
  - Người dùng chưa đăng nhập -> Trả về 401 Unauthorized.
  - Lỗi sinh mã trùng lặp -> Hệ thống tự động sinh lại mã mới (tối đa 3 lần thử).
- **Tiêu chí nghiệm thu:**
  - Phòng họp mới xuất hiện trong DB với `host` là người tạo.
  - Phản hồi mã 201 Created chứa `room_code`.

---

### FR-06: Xác thực & Tham gia phòng họp bằng mã phòng (Must-have)
- **Mô tả:** Người dùng nhập Room Code để kiểm tra tính hợp lệ của phòng trước khi tham gia giao diện cuộc họp.
- **Điều kiện tiền đề:** Có mã Room Code.
- **Luồng chính:**
  1. Client gửi yêu cầu kiểm tra phòng tới API `/api/v1/rooms/{room_code}/`.
  2. Hệ thống kiểm tra: phòng có tồn tại không, trạng thái có đang `active` không, số lượng người có vượt ngưỡng không.
  3. Hệ thống trả về thông tin phòng và cho phép chuyển tiếp vào phòng họp.
- **Luồng ngoại lệ:**
  - Room Code không tồn tại -> Trả về lỗi 404 Not Found ("Phòng họp không tồn tại").
  - Phòng đã kết thúc (`is_active=False`) -> Trả về lỗi 410 Gone ("Phòng họp đã kết thúc").
  - Phòng đã đủ người (vượt ngưỡng Mesh tối đa) -> Trả về lỗi 403 Forbidden ("Phòng họp đã đầy").
- **Tiêu chí nghiệm thu:**
  - Trả về mã 200 OK kèm metadata phòng họp nếu hợp lệ.

---

### FR-07: Kết nối Kênh Signaling WebSocket (Must-have)
- **Mô tả:** Client mở kết nối WebSocket tới kênh signaling của phòng họp cụ thể để phục vụ việc trao đổi SDP, ICE Candidate và tin nhắn.
- **Điều kiện tiền đề:** Phòng họp hợp lệ; Client có thông tin định danh (User ID hoặc Guest Session).
- **Luồng chính:**
  1. Client mở kết nối `ws://<host>/ws/meeting/{room_code}/`.
  2. Hệ thống Channels chứng thực kết nối, thêm connection vào Channels Group `room_{room_code}`.
  3. Client gửi thông điệp `join_room` kèm thông tin cá nhân.
  4. Server gửi lại danh sách các Peer hiện có trong phòng cho Client mới.
  5. Server broadcast sự kiện `user_joined` kèm thông tin Client mới cho tất cả thành viên hiện tại trong phòng.
- **Luồng ngoại lệ:**
  - Room code sai hoặc phòng không tồn tại -> Đóng WebSocket với mã lỗi 4004.
  - Không có thông tin xác thực hợp lệ -> Đóng WebSocket với mã lỗi 4001.
- **Tiêu chí nghiệm thu:**
  - WebSocket kết nối thành công (HTTP 101 Switching Protocols).
  - Tin nhắn `user_joined` được truyền đạt đầy đủ tới các client khác trong phòng.

---

### FR-08: Trao đổi WebRTC Signaling (Offer / Answer / ICE Candidate) (Must-have)
- **Mô tả:** Chuyển tiếp các thông điệp thiết lập phiên kết nối đồng đẳng giữa các client.
- **Điều kiện tiền đề:** Các client đã tham gia cùng Channels Group phòng họp.
- **Luồng chính:**
  1. Client A tạo `RTCPeerConnection` tới Client B, tạo SDP Offer và gửi message `offer` (kèm target_id: Client B) qua WebSocket.
  2. Server định tuyến message `offer` chính xác tới Client B.
  3. Client B nhận Offer, thiết lập RemoteDescription, tạo SDP Answer và gửi message `answer` (target_id: Client A).
  4. Server định tuyến message `answer` về Client A.
  5. Cả hai Client trao đổi các thông điệp `ice_candidate` qua Server để hoàn tất đường truyền mạng.
- **Luồng ngoại lệ:**
  - Target Client không tồn tại hoặc đã ngắt kết nối -> Server gửi thông điệp `error` (Peer not found) về client gửi.
  - Dữ liệu SDP/ICE sai cấu trúc -> Bị drop và thông báo lỗi.
- **Tiêu chí nghiệm thu:**
  - Hai trình duyệt có thể hoàn tất bắt tay WebRTC ICE Connection State chuyển sang `connected` hoặc `completed`.

---

### FR-09: Truyền tải Media Âm thanh và Video hai chiều (Must-have)
- **Mô tả:** Thu thập stream từ Webcam/Microphone của người dùng và truyền trực tiếp tới các Peer trong phòng.
- **Điều kiện tiền đề:** Người dùng cấp quyền truy cập thiết bị (Media Devices).
- **Luồng chính:**
  1. Ứng dụng gọi `navigator.mediaDevices.getUserMedia({ audio: true, video: true })`.
  2. Gắn Local Media Stream vào thẻ video của người dùng.
  3. Thêm các tracks vào từng `RTCPeerConnection`.
  4. Khi nhận Remote Track (`ontrack`), gắn Remote Stream vào thẻ video tương ứng của từng người tham gia.
- **Luồng ngoại lệ:**
  - Người dùng từ chối cấp quyền Camera/Mic -> Hệ thống không sụp đổ, hiển thị avatar mặc định và cho phép tham gia ở chế độ nghe/xem (Listen-only/View-only).
- **Tiêu chí nghiệm thu:**
  - Âm thanh và hình ảnh của các thành viên được phát đồng bộ trên màn hình của nhau.

---

### FR-10: Điều khiển Camera và Micro cá nhân (Must-have)
- **Mô tả:** Cho phép người dùng bật/tắt Micro và Camera bất cứ lúc nào trong cuộc họp.
- **Điều kiện tiền đề:** Đang trong phòng họp.
- **Luồng chính:**
  1. Người dùng bấm nút Mute Micro -> `audioTrack.enabled = false`. UI cập nhật icon gạch chéo.
  2. Người dùng bấm Tắt Camera -> `videoTrack.enabled = false`. UI cập nhật icon camera gạch chéo và hiển thị avatar.
  3. Người dùng bấm lại -> track chuyển sang `enabled = true`.
- **Tiêu chí nghiệm thu:**
  - Khi tắt mic, các client khác không nhận được âm thanh.
  - Khi tắt cam, các client khác nhận khung hình đen/tạm dừng hoặc avatar thay thế.

---

### FR-11: Chia sẻ màn hình (Must-have)
- **Mô tả:** Cho phép người dùng chia sẻ màn hình máy tính hoặc cửa sổ ứng dụng cho các thành viên trong phòng.
- **Điều kiện tiền đề:** Trình duyệt hỗ trợ `navigator.mediaDevices.getDisplayMedia`.
- **Luồng chính:**
  1. Người dùng bấm nút "Chia sẻ màn hình".
  2. Trình duyệt hiển thị hộp thoại chọn màn hình/cửa sổ.
  3. Người dùng chọn và cấp quyền -> Lấy `screenStream`.
  4. Thay thế video track của camera bằng video track của màn hình trên các `RTCPeerConnection` (hoặc gửi track bổ sung).
  5. Khi người dùng bấm "Dừng chia sẻ" (trên web hoặc trên banner trình duyệt) -> Khôi phục lại video track từ camera.
- **Luồng ngoại lệ:**
  - Người dùng bấm Cancel trên hộp thoại chia sẻ màn hình -> Không thay đổi trạng thái cuộc họp, ghi nhận không có lỗi phát sinh.
- **Tiêu chí nghiệm thu:**
  - Các client khác xem được nội dung màn hình được chia sẻ với độ trễ thấp và độ phân giải rõ ràng.

---

### FR-12: Nhắn tin trong phòng họp (In-room Chat) (Must-have)
- **Mô tả:** Gửi và nhận tin nhắn văn bản tức thời giữa các thành viên đang có mặt trong phòng họp.
- **Điều kiện tiền đề:** Đang kết nối WebSocket của phòng.
- **Luồng chính:**
  1. Người dùng nhập tin nhắn và bấm Gửi.
  2. Client gửi message `chat_message` qua WebSocket chứa nội dung, sender_name, timestamp.
  3. Server xác thực và broadcast tới tất cả các thành viên trong phòng.
  4. UI của tất cả thành viên hiển thị tin nhắn mới trong khung chat.
- **Luồng ngoại lệ:**
  - Tin nhắn rỗng hoặc chỉ toàn khoảng trắng -> Client chặn không gửi.
  - Tin nhắn vượt quá 1000 ký tự -> Chặn hoặc cắt bớt.
- **Tiêu chí nghiệm thu:**
  - Mọi thành viên trong phòng đều nhận được tin nhắn tức thời (< 200ms qua WebSocket).

---

### FR-13: Quản lý danh sách thành viên trong phòng (Should-have)
- **Mô tả:** Hiển thị danh sách thời gian thực gồm tên, trạng thái mic/cam của tất cả người đang tham gia.
- **Điều kiện tiền đề:** Đang trong phòng họp.
- **Luồng chính:**
  - Khi có người vào phòng (`user_joined`), danh sách tự động bổ sung.
  - Khi có người rời phòng (`user_left`), danh sách tự động xóa thành viên đó.
- **Tiêu chí nghiệm thu:** Danh sách hiển thị chính xác số lượng và tên các thành viên đang kết nối.

---

### FR-14: Rời phòng họp an toàn (Must-have)
- **Mô tả:** Người dùng chủ động bấm nút rời phòng hoặc đóng trình duyệt.
- **Điều kiện tiền đề:** Đang trong phòng họp.
- **Luồng chính:**
  1. Người dùng bấm nút "Rời phòng".
  2. Client đóng tất cả Media Tracks (`track.stop()`).
  3. Client đóng tất cả `RTCPeerConnection`.
  4. Client gửi thông điệp `leave_room` qua WebSocket hoặc đóng kết nối WebSocket.
  5. Server phát hiện ngắt kết nối, broadcast `user_left` tới các client còn lại.
  6. Client điều hướng người dùng về trang chủ/trang kết thúc.
- **Tiêu chí nghiệm thu:**
  - Camera và Micro được tắt hoàn toàn (đèn báo phần cứng tắt).
  - Không rò rỉ tài nguyên bộ nhớ hay kết nối mồ côi (dangling connections).

---

## 4. YÊU CẦU PHI CHỨC NĂNG (NON-FUNCTIONAL REQUIREMENTS)

### 4.1. Bảo mật (Security - NFR-SEC)
- **NFR-SEC-01 (Mã hóa đường truyền):** Tất cả lưu lượng HTTP phải qua HTTPS (môi trường staging/prod), WebSocket qua WSS. Lưu lượng WebRTC Media bắt buộc mã hóa bằng DTLS (Datagram Transport Layer Security) và SRTP (Secure Real-time Transport Protocol).
- **NFR-SEC-02 (Bảo vệ thông tin bí mật):** Không lưu trữ mật khẩu ở dạng plain-text; sử dụng thuật toán băm chuẩn công nghiệp của Django. Các khóa bí mật (`SECRET_KEY`, Database Password) phải lưu trong file môi trường `.env`, tuyệt đối không commit lên Git.
- **NFR-SEC-03 (Phòng chống tấn công Web):** Hệ thống phải bật các cơ chế bảo vệ tiêu chuẩn của Django: CSRF Protection, XSS Filtering, CORS Headers cấu hình tường minh, SQL Injection prevention qua Django ORM.
- **NFR-SEC-04 (Cách ly dữ liệu phòng):** Người dùng ở phòng A tuyệt đối không được nhận bất kỳ tin nhắn hoặc luồng signaling/media nào thuộc về phòng B.

### 4.2. Hiệu năng & Độ trễ (Performance - NFR-PERF)
- **NFR-PERF-01 (Độ trễ truyền thông Media):** Độ trễ âm thanh/hình ảnh giữa các client qua WebRTC P2P trong cùng vùng địa lý mạng nội địa phải $\le 300\text{ms}$.
- **NFR-PERF-02 (Độ trễ Signaling & Chat):** Thời gian chuyển tiếp tin nhắn WebSocket qua Django Channels và Redis phải $\le 100\text{ms}$.
- **NFR-PERF-03 (Tối ưu tài nguyên CPU Client):** Trong mô hình Mesh, giới hạn số lượng người tham gia khuyến nghị từ 4 đến tối đa 6 người để tránh quá tải CPU do phải mã hóa/giải mã đồng thời nhiều luồng video $O(N^2)$.

### 4.3. Khả năng tương thích (Compatibility - NFR-COMP)
- **NFR-COMP-01 (Trình duyệt):** Hỗ trợ đầy đủ các trình duyệt hiện đại trên nền tảng Desktop (Google Chrome $\ge 90$, Mozilla Firefox $\ge 88$, Microsoft Edge $\ge 90$, Apple Safari $\ge 15$).
- **NFR-COMP-02 (Tiêu chuẩn WebRTC):** Tuân thủ tiêu chuẩn W3C WebRTC 1.0 và IETF SDP/ICE.

### 4.4. Khả năng phục hồi & Ổn định (Resilience - NFR-RES)
- **NFR-RES-01 (Phục hồi kết nối mạng ngắn hạn):** Hỗ trợ ICE Restart tự động khi kết nối WebRTC bị gián đoạn tạm thời.
- **NFR-RES-02 (Xử lý ngắt kết nối đột ngột):** Khi một client bị ngắt mạng (mất điện, đóng tab đột ngột), hệ thống Channels và các Peer còn lại phải phát hiện và dọn dẹp kết nối trong vòng $\le 5$ giây mà không làm treo các kết nối khác.

### 4.5. Khả năng sử dụng (Usability - NFR-USA)
- **NFR-USA-01 (Trải nghiệm người dùng):** Giao diện trực quan, người dùng có thể tạo phòng hoặc vào phòng chỉ qua 1-2 thao tác chuột.
- **NFR-USA-02 (Phản hồi trạng thái rõ ràng):** Hiển thị rõ ràng trạng thái kết nối (Đang kết nối, Đã kết nối, Mất kết nối), trạng thái Mic/Cam của từng thành viên.

---

## 5. DANH SÁCH QUYẾT ĐỊNH CÒN CẦN XÁC NHẬN (TBD / PENDING DECISIONS)

Dưới đây là các vấn đề nghiệp vụ và kỹ thuật chưa được chỉ định cụ thể, cần sự xác nhận từ Product Owner / Giảng viên hướng dẫn:

1. **Khách vãng lai (Guest User):** Có cho phép người chưa đăng ký tài khoản tham gia phòng chỉ bằng việc nhập Tên hiển thị (Guest Name) hay bắt buộc tất cả người dùng phải tạo tài khoản và đăng nhập trước khi vào phòng? *(Đề xuất kỹ thuật: Cho phép Guest tham gia bằng cách nhập tên để tăng tính tiện dụng)*.
2. **Quyền hạn của Host:** Người tạo phòng (Host) có quyền kết thúc phòng cho tất cả mọi người (End meeting for all) hay khi Host rời đi thì phòng vẫn tiếp tục hoạt động cho các thành viên còn lại? *(Đề xuất: Phòng vẫn hoạt động bình thường cho tới khi người cuối cùng rời đi)*.
3. **Quyền Mute / Kick của Host:** Có cần triển khai quyền cho Host tắt mic hoặc mời thành viên khác ra khỏi phòng hay không? *(Đề xuất: Chưa triển khai ở giai đoạn đầu để giữ mô hình phân tán đơn giản)*.
4. **Lưu trữ tin nhắn Chat:** Tin nhắn trong phòng có cần lưu vĩnh viễn vào cơ sở dữ liệu PostgreSQL để xem lại lịch sử sau cuộc họp hay chỉ lưu tạm thời/truyền qua WebSocket trong lúc phòng đang diễn ra?
5. **Cơ chế mật khẩu phòng họp:** Phòng họp có cần đặt mật khẩu truy cập (Room Password) hay chỉ cần biết đúng mã Room Code là được vào?
