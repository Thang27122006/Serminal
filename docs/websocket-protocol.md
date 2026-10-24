# ĐẶC TẢ GIAO THỨC WEBSOCKET SIGNALING (WEBSOCKET PROTOCOL)
## DỰ ÁN: AI MEETING (TUẦN 3: DJANGO CHANNELS, REDIS & SIGNALING)

---

## 1. TỔNG QUAN GIAO THỨC

WebSocket trong hệ thống **AI Meeting** chịu trách nhiệm độc quyền cho hai mục tiêu:
1. **WebRTC Signaling:** Thiết lập và đàm phán phiên kết nối ngang hàng P2P Full Mesh (Session Description Protocol - SDP Offer/Answer, Interactive Connectivity Establishment - ICE Candidates) và đồng bộ trạng thái hiện diện (Presence tracking: Join, Leave, Online list).
2. **In-room Realtime Chat:** Truyền phát tức thời tin nhắn văn bản giữa các thành viên trong cùng một phòng họp.

*Lưu ý kiến trúc:* WebSocket **hoàn toàn không truyền tải bất kỳ dữ liệu media âm thanh hay hình ảnh nào**. Toàn bộ luồng Media do WebRTC P2P trực tiếp đảm nhận.

---

## 2. KẾT NỐI VÀ CƠ CHẾ XÁC THỰC AN TOÀN

### 2.1. Địa chỉ kết nối (Connection URL)
```text
ws://<host>/ws/meeting/<room_code>/
hoặc
wss://<host>/ws/meeting/<room_code>/
```

### 2.2. Cơ chế truyền thông tin xác thực (Authentication Mechanism)
Để tránh lộ JWT Token trong web server access logs (nhược điểm của việc đặt token trong URL Query String), hệ thống hỗ trợ 3 cơ chế xác thực theo thứ tự ưu tiên:

1. **Chuẩn Subprotocol (Khuyến nghị cho Trình duyệt):**
   - Khởi tạo WebSocket với subprotocol: `new WebSocket(url, ['bearer', access_token])`.
   - Trình duyệt tự động gửi header: `Sec-WebSocket-Protocol: bearer, <access_token>`.
   - Máy chủ `JWTAuthMiddleware` kiểm tra token, gán người dùng vào `scope['user']`, và phản hồi bắt tay với subprotocol `bearer`.
2. **Xác thực qua Thông điệp đầu tiên (First-Message / Payload Auth):**
   - Client kết nối ẩn danh và gửi token trong payload của thông điệp `join_room` (`payload.token = "<jwt_access_token>"`).
   - Máy chủ xác minh token động trước khi cho phép gia nhập phòng.
3. **Query String Fallback (Dành cho Postman / Testing):**
   - `ws://<host>/ws/meeting/<room_code>/?token=<jwt_access_token>`.

---

## 3. CẤU TRÚC KHUNG THÔNG ĐIỆP CHUẨN (MESSAGE ENVELOPE)

Tất cả các thông điệp trao đổi hai chiều giữa Client và Server đều tuân thủ cấu trúc JSON Envelope nhất quán:

```json
{
  "type": "MESSAGE_TYPE_STRING",
  "request_id": "client-or-server-uuid",
  "payload": {
    ...
  }
}
```

- `type` (bắt buộc, `string`): Tên định danh thông điệp (chữ thường, cách nhau bằng gạch dưới `_`).
- `request_id` (tùy chọn, `string`): Mã định danh yêu cầu do client hoặc server sinh ra để ghép cặp request-response.
- `payload` (bắt buộc, `object`): Đối tượng chứa dữ liệu chi tiết của thông điệp.

---

## 4. BẢNG QUY TẮC CÁC LOẠI THÔNG ĐIỆP (MESSAGE SPECIFICATIONS)

| Loại thông điệp | Người gửi | Người nhận | Phân quyền & Điều kiện | Xử lý khi lỗi / thiếu dữ liệu |
| :--- | :--- | :--- | :--- | :--- |
| **`join_room`** | Client | Server | Client phải gửi đầu tiên sau khi kết nối. Phải có quyền truy cập phòng. | Trả về `error` kèm close code (4001, 4003, 4004, 4005). |
| **`online_list`** | Server | Client gửi | Gửi duy nhất cho client vừa join thành công. | Cung cấp `self` và danh sách `peers` hiện có. |
| **`user_joined`** | Server | Các Peer khác | Broadcast cho toàn bộ thành viên khác trong phòng khi có người mới vào. | Tự động phát khi client hoàn tất `join_room`. |
| **`user_left`** | Server | Các Peer khác | Broadcast khi một thành viên rời phòng hoặc mất kết nối mạng. | Kích hoạt tự động khi socket đóng hoặc client gửi `leave_room`. |
| **`offer`** | Client | Server -> Target | Đã join; `target_peer_id` phải tồn tại trong cùng phòng. | Báo lỗi `TARGET_PEER_NOT_FOUND` nếu sai peer. |
| **`answer`** | Client | Server -> Target | Đã join; `target_peer_id` phải tồn tại trong cùng phòng. | Báo lỗi `TARGET_PEER_NOT_FOUND` nếu sai peer. |
| **`ice_candidate`** | Client | Server -> Target | Đã join; `target_peer_id` phải tồn tại trong cùng phòng. | Báo lỗi `TARGET_PEER_NOT_FOUND` nếu sai peer. |
| **`chat_message`** | Client | Server -> Cả phòng | Đã join; nội dung 1–1000 ký tự. | Báo lỗi `EMPTY_MESSAGE` nếu tin nhắn rỗng. |
| **`error`** | Server | Client | Gửi phản hồi khi client có hành vi không hợp lệ. | Báo mã lỗi và thông điệp giải thích. |

---

## 5. ĐẶC TẢ CHI TIẾT TỪNG THÔNG ĐIỆP

---

### 5.1. `join_room`
Yêu cầu tham gia phiên phòng họp cụ thể.

- **Client -> Server:**
```json
{
  "type": "join_room",
  "request_id": "req-join-001",
  "payload": {
    "token": "eyJhbGciOiJIUzI1NiIsIn...",
    "passcode": "SecretPass123",
    "display_name": "Nguyễn Văn A",
    "peer_id": "peer-uuid-opt"
  }
}
```
- **Trường dữ liệu:**
  - `token` (`string`, tùy chọn): JWT Access Token nếu chưa xác thực ở handshake.
  - `passcode` (`string`, tùy chọn): Mật khẩu phòng (bắt buộc nếu phòng là riêng tư và user không phải Host).
  - `display_name` (`string`, tùy chọn nếu đã đăng nhập, bắt buộc nếu là khách).
  - `peer_id` (`string`, tùy chọn): Client có thể gửi UUIDv4 của mình, nếu không có server tự sinh.

---

### 5.2. `online_list`
Server phản hồi danh sách các thành viên đang trực tuyến trong phòng cho người mới vào.

- **Server -> Client:**
```json
{
  "type": "online_list",
  "request_id": "req-join-001",
  "payload": {
    "room_code": "abc-def-xyz",
    "self": {
      "peer_id": "c1a17950-7164-460b-80a9-1f4a9b5f5869",
      "display_name": "Nguyễn Văn A",
      "is_host": true
    },
    "peers": [
      {
        "peer_id": "b3e0258b-9d41-4770-9ee4-c9569b925b68",
        "user_id": 2,
        "display_name": "Trần Thị B",
        "is_host": false,
        "joined_at": "2026-10-24T15:00:00Z"
      }
    ]
  }
}
```

---

### 5.3. `user_joined`
Server thông báo cho các peer khác trong phòng về thành viên mới.

- **Server -> Broadcast:**
```json
{
  "type": "user_joined",
  "payload": {
    "peer_id": "c1a17950-7164-460b-80a9-1f4a9b5f5869",
    "display_name": "Nguyễn Văn A",
    "is_host": true,
    "joined_at": "2026-10-24T15:05:00Z"
  }
}
```

---

### 5.4. `user_left`
Server thông báo cho các peer khác khi một thành viên rời đi hoặc mất kết nối.

- **Server -> Broadcast:**
```json
{
  "type": "user_left",
  "payload": {
    "peer_id": "b3e0258b-9d41-4770-9ee4-c9569b925b68",
    "display_name": "Trần Thị B",
    "reason": "normal"
  }
}
```
*(Trường `reason` nhận giá trị `"normal"` khi rời chủ động hoặc `"disconnect"` khi ngắt kết nối đột ngột).*

---

### 5.5. `offer` (Signaling SDP Offer)
Chuyển tiếp đề nghị đàm phán WebRTC điểm-tới-điểm.

- **Client A gửi lên Server:**
```json
{
  "type": "offer",
  "request_id": "req-off-123",
  "payload": {
    "target_peer_id": "b3e0258b-9d41-4770-9ee4-c9569b925b68",
    "sdp": {
      "type": "offer",
      "sdp": "v=0\r\no=- 4611731400 2 IN IP4 127.0.0.1..."
    }
  }
}
```

- **Server chuyển tiếp trực tiếp tới Client B (Point-to-Point):**
```json
{
  "type": "offer",
  "request_id": "req-off-123",
  "payload": {
    "sender_peer_id": "c1a17950-7164-460b-80a9-1f4a9b5f5869",
    "sender_name": "Nguyễn Văn A",
    "target_peer_id": "b3e0258b-9d41-4770-9ee4-c9569b925b68",
    "sdp": {
      "type": "offer",
      "sdp": "v=0\r\no=- 4611731400 2 IN IP4 127.0.0.1..."
    }
  }
}
```
*(Server tự động gắn `sender_peer_id` thật, client không thể mạo danh).*

---

### 5.6. `answer` (Signaling SDP Answer)
Client B phản hồi Answer cho Client A.

- **Client B gửi lên Server:**
```json
{
  "type": "answer",
  "request_id": "req-ans-456",
  "payload": {
    "target_peer_id": "c1a17950-7164-460b-80a9-1f4a9b5f5869",
    "sdp": {
      "type": "answer",
      "sdp": "v=0\r\no=- 7822941100 2 IN IP4 127.0.0.1..."
    }
  }
}
```

- **Server chuyển tiếp tới Client A (Point-to-Point):**
```json
{
  "type": "answer",
  "request_id": "req-ans-456",
  "payload": {
    "sender_peer_id": "b3e0258b-9d41-4770-9ee4-c9569b925b68",
    "sender_name": "Trần Thị B",
    "target_peer_id": "c1a17950-7164-460b-80a9-1f4a9b5f5869",
    "sdp": {
      "type": "answer",
      "sdp": "v=0\r\no=- 7822941100 2 IN IP4 127.0.0.1..."
    }
  }
}
```

---

### 5.7. `ice_candidate` (Trao đổi ứng viên mạng)
Chuyển tiếp ứng viên mạng ICE giữa các Peer.

- **Client gửi lên Server:**
```json
{
  "type": "ice_candidate",
  "payload": {
    "target_peer_id": "b3e0258b-9d41-4770-9ee4-c9569b925b68",
    "candidate": {
      "candidate": "candidate:842163049 1 udp 1677729535 192.168.1.15 54123 typ host generation 0",
      "sdpMid": "0",
      "sdpMLineIndex": 0
    }
  }
}
```

- **Server chuyển tiếp trực tiếp tới Target Peer:**
```json
{
  "type": "ice_candidate",
  "payload": {
    "sender_peer_id": "c1a17950-7164-460b-80a9-1f4a9b5f5869",
    "target_peer_id": "b3e0258b-9d41-4770-9ee4-c9569b925b68",
    "candidate": {
      "candidate": "candidate:842163049 1 udp 1677729535 192.168.1.15 54123 typ host generation 0",
      "sdpMid": "0",
      "sdpMLineIndex": 0
    }
  }
}
```

---

### 5.8. `chat_message` (Nhắn tin trong phòng)
- **Client gửi lên Server:**
```json
{
  "type": "chat_message",
  "request_id": "req-chat-789",
  "payload": {
    "content": "Chào cả phòng!"
  }
}
```

- **Server broadcast cho cả phòng:**
```json
{
  "type": "chat_message",
  "payload": {
    "message_id": "d3b07384-d113-4a11-b01f-0e48712398ab",
    "sender_peer_id": "c1a17950-7164-460b-80a9-1f4a9b5f5869",
    "sender_name": "Nguyễn Văn A",
    "content": "Chào cả phòng!",
    "timestamp": "2026-10-24T15:10:00Z"
  }
}
```

---

### 5.9. `error` (Thông báo lỗi có cấu trúc)
Server gửi cho Client khi phát hiện thao tác không hợp lệ.

```json
{
  "type": "error",
  "request_id": "req-join-001",
  "payload": {
    "code": "TARGET_PEER_NOT_FOUND",
    "message": "Thành viên nhận không tồn tại hoặc đã rời phòng này."
  }
}
```

Các mã lỗi thường gặp:
- `MALFORMED_JSON`: Dữ liệu gửi lên không đúng định dạng JSON.
- `INVALID_STRUCTURE`: Thiếu trường `type` hoặc `payload`.
- `NOT_JOINED`: Gửi thông điệp khi chưa gọi `join_room`.
- `INVALID_TOKEN`: JWT Token sai hoặc đã hết hạn.
- `ROOM_NOT_FOUND`: Mã phòng không tồn tại trong DB.
- `ROOM_CLOSED`: Phòng họp đã bị kết thúc.
- `ACCESS_DENIED`: Sai mật khẩu phòng riêng tư.
- `ROOM_FULL`: Phòng đã đủ số lượng thành viên tối đa.
- `TARGET_PEER_NOT_FOUND`: Peer nhận không tồn tại trong phòng.
- `UNSUPPORTED_TYPE`: Loại thông điệp không được hỗ trợ.

---

## 6. MÃ ĐÓNG WEBSOCKET TIÊU CHUẨN (CLOSE CODES)

| Mã đóng (Close Code) | Tên lỗi | Giải thích |
| :--- | :--- | :--- |
| **4000** | `NORMAL_CLOSURE` | Rời phòng chủ động hoặc kết thúc thông thường. |
| **4001** | `UNAUTHORIZED` | Token JWT không hợp lệ hoặc thiếu thông tin định danh bắt buộc. |
| **4003** | `FORBIDDEN` | Phòng đầy (`ROOM_FULL`) hoặc từ chối truy cập phòng riêng tư (`ACCESS_DENIED`). |
| **4004** | `NOT_FOUND` | Phòng họp không tồn tại (`ROOM_NOT_FOUND`). |
| **4005** | `GONE` | Phòng họp đã kết thúc (`ROOM_CLOSED`). |
