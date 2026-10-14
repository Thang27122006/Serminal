# ĐẶC TẢ GIAO THỨC WEBSOCKET SIGNALING (WEBSOCKET PROTOCOL)
## DỰ ÁN: AI MEETING

---

## 1. TỔNG QUAN GIAO THỨC

WebSocket trong dự án **AI Meeting** được sử dụng độc quyền cho hai mục đích:
1. **Signaling cho WebRTC:** Trao đổi các thông điệp thiết lập phiên (SDP Offer, SDP Answer, ICE Candidates) và kiểm soát sự hiện diện (Presence: Join, Leave) giữa các trình duyệt.
2. **In-room Realtime Chat:** Truyền phát tức thời tin nhắn văn bản giữa các thành viên trong phòng.

*Lưu ý cốt lõi:* WebSocket **không truyền tải bất kỳ dữ liệu media âm thanh hay hình ảnh nào**. Toàn bộ luồng Media do WebRTC P2P trực tiếp đảm nhận.

---

## 2. KẾT NỐI & ĐỊNH DẠNG KHUNG THÔNG ĐIỆP (MESSAGE ENVELOPE)

### 2.1. Địa chỉ kết nối (Connection URL)
```text
ws://<host>/ws/meeting/<room_code>/?token=<auth_token>
hoặc
wss://<host>/ws/meeting/<room_code>/?token=<auth_token>
```
*(Nếu là Guest được phê duyệt: `?name=<display_name>`)*.

### 2.2. Định dạng thông điệp chung (Generic Envelope)
Tất cả các thông điệp gửi và nhận qua WebSocket đều được đóng gói dưới dạng JSON với cấu trúc chuẩn:

```json
{
  "type": "MESSAGE_TYPE_STRING",
  "payload": {
    ...
  }
}
```

- `type`: Tên loại thông điệp (chữ thường, cách nhau bằng gạch dưới `_`).
- `payload`: Đối tượng chứa dữ liệu chi tiết của thông điệp.

---

## 3. DANH MỤC CÁC THÔNG ĐIỆP CHI TIẾT

---

### 3.1. `join_room` (Client -> Server)
Gửi ngay sau khi mở kết nối WebSocket thành công để thông báo sự hiện diện của Client.

```json
{
  "type": "join_room",
  "payload": {
    "peer_id": "b3e0258b-9d41-4770-9ee4-c9569b925b68",
    "display_name": "Nguyễn Văn A"
  }
}
```

---

### 3.2. `room_state` (Server -> Client gửi)
Server phản hồi riêng cho Client vừa gia nhập, cung cấp danh sách tất cả các Peer đang trực tuyến trong phòng để Client mới bắt đầu tạo kết nối WebRTC.

```json
{
  "type": "room_state",
  "payload": {
    "room_code": "mtg-492-xk9",
    "self_peer_id": "b3e0258b-9d41-4770-9ee4-c9569b925b68",
    "existing_peers": [
      {
        "peer_id": "fe56e301-4475-430b-9c70-6804cf3c4314",
        "display_name": "Trần Thị B"
      },
      {
        "peer_id": "8f310cd3-2287-43f1-b842-88ef56b9c972",
        "display_name": "Lê Văn C"
      }
    ]
  }
}
```

---

### 3.3. `user_joined` (Server -> Broadcast tới các Peer khác)
Server thông báo cho toàn bộ các Peer khác trong phòng rằng có một thành viên mới vừa tham gia.

```json
{
  "type": "user_joined",
  "payload": {
    "peer_id": "b3e0258b-9d41-4770-9ee4-c9569b925b68",
    "display_name": "Nguyễn Văn A"
  }
}
```

---

### 3.4. `offer` (Client A -> Server -> Client B)
Client gửi SDP Offer tới một Peer cụ thể để đề nghị bắt tay thiết lập kết nối WebRTC.

#### Client A gửi lên Server:
```json
{
  "type": "offer",
  "payload": {
    "target_peer_id": "fe56e301-4475-430b-9c70-6804cf3c4314",
    "sdp": {
      "type": "offer",
      "sdp": "v=0\r\no=- 4611731400 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\na=group:BUNDLE 0 1\r\n..."
    }
  }
}
```

#### Server chuyển tiếp tới Client B:
```json
{
  "type": "offer",
  "payload": {
    "sender_peer_id": "b3e0258b-9d41-4770-9ee4-c9569b925b68",
    "sender_name": "Nguyễn Văn A",
    "sdp": {
      "type": "offer",
      "sdp": "v=0\r\no=- 4611731400 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\na=group:BUNDLE 0 1\r\n..."
    }
  }
}
```

---

### 3.5. `answer` (Client B -> Server -> Client A)
Client B phản hồi SDP Answer cho Offer nhận được từ Client A.

#### Client B gửi lên Server:
```json
{
  "type": "answer",
  "payload": {
    "target_peer_id": "b3e0258b-9d41-4770-9ee4-c9569b925b68",
    "sdp": {
      "type": "answer",
      "sdp": "v=0\r\no=- 7822941100 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\na=group:BUNDLE 0 1\r\n..."
    }
  }
}
```

#### Server chuyển tiếp tới Client A:
```json
{
  "type": "answer",
  "payload": {
    "sender_peer_id": "fe56e301-4475-430b-9c70-6804cf3c4314",
    "sdp": {
      "type": "answer",
      "sdp": "v=0\r\no=- 7822941100 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\na=group:BUNDLE 0 1\r\n..."
    }
  }
}
```

---

### 3.6. `ice_candidate` (Trao đổi hai chiều qua Server)
Trao đổi thông tin cổng mạng (Network candidate) do trình duyệt thu thập được.

#### Client gửi lên Server:
```json
{
  "type": "ice_candidate",
  "payload": {
    "target_peer_id": "fe56e301-4475-430b-9c70-6804cf3c4314",
    "candidate": {
      "candidate": "candidate:842163049 1 udp 1677729535 192.168.1.15 54123 typ host generation 0",
      "sdpMid": "0",
      "sdpMLineIndex": 0
    }
  }
}
```

#### Server chuyển tiếp tới Target Peer:
```json
{
  "type": "ice_candidate",
  "payload": {
    "sender_peer_id": "b3e0258b-9d41-4770-9ee4-c9569b925b68",
    "candidate": {
      "candidate": "candidate:842163049 1 udp 1677729535 192.168.1.15 54123 typ host generation 0",
      "sdpMid": "0",
      "sdpMLineIndex": 0
    }
  }
}
```

---

### 3.7. `chat_message` & `chat_broadcast`
Trao đổi tin nhắn văn bản trong phòng.

#### Client gửi lên Server (`chat_message`):
```json
{
  "type": "chat_message",
  "payload": {
    "content": "Xin chào mọi người!"
  }
}
```

#### Server broadcast tới cả phòng (`chat_broadcast`):
```json
{
  "type": "chat_broadcast",
  "payload": {
    "sender_peer_id": "b3e0258b-9d41-4770-9ee4-c9569b925b68",
    "sender_name": "Nguyễn Văn A",
    "content": "Xin chào mọi người!",
    "timestamp": "2026-10-14T08:38:12Z"
  }
}
```

---

### 3.8. `user_left` (Server -> Broadcast khi một thành viên rời đi)
Phát tín hiệu khi một client chủ động bấm rời phòng hoặc ngắt kết nối WebSocket đột ngột.

```json
{
  "type": "user_left",
  "payload": {
    "peer_id": "fe56e301-4475-430b-9c70-6804cf3c4314",
    "display_name": "Trần Thị B"
  }
}
```

---

### 3.9. `error` (Server -> Client khi có lỗi phát sinh)
Gửi cho client khi có hành động không hợp lệ mà không cần đóng WebSocket.

```json
{
  "type": "error",
  "payload": {
    "code": "TARGET_PEER_NOT_FOUND",
    "message": "Không tìm thấy người nhận trong phòng này."
  }
}
```

---

## 4. MÃ ĐÓNG KẾT NỐI WEBSOCKET TIÊU CHUẨN (WEBSOCKET CLOSE CODES)

Khi WebSocket bị từ chối kết nối hoặc bị ngắt cưỡng bức, Server trả về mã đóng chuẩn tùy biến trong dải 4000-4999:

| Close Code | Tên lỗi | Giải thích |
| :--- | :--- | :--- |
| **4001** | `UNAUTHORIZED` | Không có thông tin xác thực hoặc Token không hợp lệ. |
| **4003** | `ROOM_FULL` | Phòng đã đạt giới hạn số lượng thành viên tối đa (6 người). |
| **4004** | `ROOM_NOT_FOUND` | Mã phòng không tồn tại trên hệ thống. |
| **4005** | `ROOM_INACTIVE` | Phòng họp đã kết thúc. |
| **4000** | `NORMAL_CLOSURE` | Người dùng chủ động rời phòng an toàn. |
