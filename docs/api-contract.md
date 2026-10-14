# ĐẶC TẢ HỢP ĐỒNG REST API (API CONTRACT)
## DỰ ÁN: AI MEETING

---

## 1. NGUYÊN TẮC THIẾT KẾ & QUY CHUẨN CHUNG

### 1.1. Định dạng dữ liệu & Base URL
- **Base URL:** `/api/v1`
- **Mã hóa:** Toàn bộ request body và response body sử dụng `Content-Type: application/json; charset=utf-8`.
- **Định dạng thời gian:** Chuỗi ISO-8601 UTC (ví dụ: `2026-10-14T08:30:00Z`).

### 1.2. Quy chuẩn xác thực (Authentication Headers)
Các endpoint yêu cầu xác thực phải gửi kèm Token trong Header:
```http
Authorization: Bearer <access_token>
```
*(Hoặc `Token <auth_token>` theo cơ chế TokenAuthentication tiêu chuẩn của Django REST Framework)*.

### 1.3. Cấu trúc phản hồi tiêu chuẩn

#### Phản hồi thành công (Success Response):
```json
{
  "success": true,
  "data": { ... },
  "message": "Thông điệp mô tả (tùy chọn)"
}
```

#### Phản hồi thất bại (Error Response):
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE_STRING",
    "message": "Thông báo lỗi thân thiện với người dùng",
    "details": { ... }
  }
}
```

---

## 2. DANH SÁCH CÁC ENDPOINTS

### 2.1. Phân hệ Xác thực (Authentication)

---

#### `POST /api/v1/auth/register/`
Đăng ký tài khoản người dùng mới.
- **Xác thực:** Không yêu cầu (`AllowAny`).
- **Request Headers:**
  ```http
  Content-Type: application/json
  ```
- **Request Body:**
  ```json
  {
    "username": "nguyenvana",
    "email": "vana@example.com",
    "password": "StrongPassword123@",
    "first_name": "Văn A",
    "last_name": "Nguyễn"
  }
  ```
- **Response `201 Created`:**
  ```json
  {
    "success": true,
    "data": {
      "id": 1,
      "username": "nguyenvana",
      "email": "vana@example.com",
      "full_name": "Nguyễn Văn A"
    },
    "message": "Đăng ký tài khoản thành công."
  }
  ```
- **Response `400 Bad Request`:**
  ```json
  {
    "success": false,
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Dữ liệu đăng ký không hợp lệ.",
      "details": {
        "username": ["Tên đăng nhập này đã tồn tại."],
        "email": ["Email đã được đăng ký trên hệ thống."]
      }
    }
  }
  ```

---

#### `POST /api/v1/auth/login/`
Đăng nhập tài khoản và nhận Token xác thực.
- **Xác thực:** Không yêu cầu (`AllowAny`).
- **Request Body:**
  ```json
  {
    "username": "nguyenvana",
    "password": "StrongPassword123@"
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "success": true,
    "data": {
      "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
      "user": {
        "id": 1,
        "username": "nguyenvana",
        "email": "vana@example.com",
        "full_name": "Nguyễn Văn A"
      }
    },
    "message": "Đăng nhập thành công."
  }
  ```
- **Response `401 Unauthorized`:**
  ```json
  {
    "success": false,
    "error": {
      "code": "INVALID_CREDENTIALS",
      "message": "Tên đăng nhập hoặc mật khẩu không chính xác."
    }
  }
  ```

---

#### `POST /api/v1/auth/logout/`
Hủy token/phiên đăng nhập hiện tại.
- **Xác thực:** Bắt buộc (`IsAuthenticated`).
- **Request Headers:**
  ```http
  Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
  ```
- **Response `200 OK`:**
  ```json
  {
    "success": true,
    "message": "Đăng xuất thành công."
  }
  ```

---

#### `GET /api/v1/auth/me/`
Lấy thông tin tài khoản đang đăng nhập.
- **Xác thực:** Bắt buộc (`IsAuthenticated`).
- **Response `200 OK`:**
  ```json
  {
    "success": true,
    "data": {
      "id": 1,
      "username": "nguyenvana",
      "email": "vana@example.com",
      "full_name": "Nguyễn Văn A",
      "date_joined": "2026-10-14T08:00:00Z"
    }
  }
  ```
- **Response `401 Unauthorized`:**
  ```json
  {
    "success": false,
    "error": {
      "code": "UNAUTHORIZED",
      "message": "Token xác thực không hợp lệ hoặc đã hết hạn."
    }
  }
  ```

---

### 2.2. Phân hệ Phòng họp (Meeting Rooms)

---

#### `POST /api/v1/rooms/`
Tạo một phòng họp mới.
- **Xác thực:** Bắt buộc (`IsAuthenticated`).
- **Request Body:**
  ```json
  {
    "title": "Họp đồ án tuần 1"
  }
  ```
- **Response `201 Created`:**
  ```json
  {
    "success": true,
    "data": {
      "room_code": "mtg-492-xk9",
      "title": "Họp đồ án tuần 1",
      "host": {
        "id": 1,
        "username": "nguyenvana",
        "full_name": "Nguyễn Văn A"
      },
      "is_active": true,
      "max_participants": 6,
      "created_at": "2026-10-14T08:35:00Z"
    },
    "message": "Tạo phòng họp thành công."
  }
  ```

---

#### `GET /api/v1/rooms/{room_code}/`
Kiểm tra tính hợp lệ và lấy thông tin chi tiết phòng trước khi vào họp.
- **Xác thực:** Cho phép truy vấn (hoặc yêu cầu Auth tùy quyết định TBD-01).
- **URL Parameters:**
  - `room_code`: Mã phòng dạng chuỗi (ví dụ: `mtg-492-xk9`).
- **Response `200 OK`:**
  ```json
  {
    "success": true,
    "data": {
      "room_code": "mtg-492-xk9",
      "title": "Họp đồ án tuần 1",
      "host_name": "Nguyễn Văn A",
      "is_active": true,
      "current_participants_count": 2,
      "max_participants": 6,
      "created_at": "2026-10-14T08:35:00Z"
    }
  }
  ```
- **Response `404 Not Found`:**
  ```json
  {
    "success": false,
    "error": {
      "code": "ROOM_NOT_FOUND",
      "message": "Phòng họp không tồn tại trên hệ thống."
    }
  }
  ```
- **Response `410 Gone`:**
  ```json
  {
    "success": false,
    "error": {
      "code": "ROOM_CLOSED",
      "message": "Phòng họp này đã kết thúc."
    }
  }
  ```

---

#### `GET /api/v1/rooms/{room_code}/participants/`
Lấy danh sách các thành viên hiện đang có mặt trong phòng.
- **Xác thực:** Bắt buộc (`IsAuthenticated` hoặc có token phòng).
- **Response `200 OK`:**
  ```json
  {
    "success": true,
    "data": {
      "room_code": "mtg-492-xk9",
      "count": 2,
      "participants": [
        {
          "peer_id": "b3e0258b-9d41-4770-9ee4-c9569b925b68",
          "display_name": "Nguyễn Văn A",
          "role": "host",
          "joined_at": "2026-10-14T08:36:00Z"
        },
        {
          "peer_id": "fe56e301-4475-430b-9c70-6804cf3c4314",
          "display_name": "Trần Thị B",
          "role": "participant",
          "joined_at": "2026-10-14T08:37:15Z"
        }
      ]
    }
  }
  ```

---

#### `GET /api/v1/rooms/{room_code}/messages/` *(Dự phòng nếu lưu DB)*
Lấy danh sách lịch sử tin nhắn trong phòng họp.
- **Xác thực:** Bắt buộc (`IsAuthenticated`).
- **Response `200 OK`:**
  ```json
  {
    "success": true,
    "data": [
      {
        "id": 101,
        "sender_name": "Nguyễn Văn A",
        "content": "Chào mọi người, chúng ta bắt đầu cuộc họp nhé!",
        "created_at": "2026-10-14T08:38:00Z"
      }
    ]
  }
  ```
