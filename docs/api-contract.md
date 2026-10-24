# ĐẶC TẢ HỢP ĐỒNG REST API (API CONTRACT)
## DỰ ÁN: AI MEETING (TUẦN 2: JWT & MEETING ROOM MANAGEMENT)

---

## 1. NGUYÊN TẮC THIẾT KẾ & QUY CHUẨN CHUNG

### 1.1. Định dạng dữ liệu & Base URL
- **Base URL:** `/api/v1`
- **Mã hóa:** Toàn bộ request body và response body sử dụng `Content-Type: application/json; charset=utf-8`.
- **Định dạng thời gian:** Chuỗi ISO-8601 UTC (ví dụ: `2026-10-24T08:30:00Z`).

### 1.2. Quy chuẩn xác thực (Authentication Headers)
Hệ thống sử dụng chuẩn **JSON Web Token (JWT)** thông qua thư viện `djangorestframework-simplejwt`.
Các endpoint yêu cầu xác thực phải gửi kèm Access Token trong Header:
```http
Authorization: Bearer <access_token>
```
- **Thời hạn Access Token:** 60 phút.
- **Thời hạn Refresh Token:** 7 ngày.
- **Cơ chế thu hồi (Revocation / Blacklist):** Khi đăng xuất (`POST /api/v1/auth/logout/`), Client gửi Refresh Token lên để đưa vào danh sách đen (`token_blacklist`), ngăn chặn kẻ xấu sử dụng lại token để cấp phát access token mới.

### 1.3. Đánh giá rủi ro XSS & Cơ chế lưu trữ Token trên Trình duyệt
- **Rủi ro XSS:** Nếu lưu trữ Token trong `localStorage` / `sessionStorage`, mã độc Javascript chèn qua XSS có thể đọc được token.
- **Giải pháp bảo vệ triển khai:**
  1. Backend escape và sanitize toàn bộ dữ liệu người dùng gửi lên.
  2. Frontend không dùng `innerHTML` với chuỗi người dùng chưa qua `escapeHTML()`.
  3. Thời hạn Access Token giới hạn ngắn (60 phút).
  4. Hỗ trợ cơ chế thu hồi Refresh Token trên máy chủ khi đăng xuất.
  5. Trong môi trường Production nâng cao: Khuyến nghị chuyển lưu `refresh_token` vào `HttpOnly`, `SameSite=Strict` Cookie.

### 1.4. Cấu trúc phản hồi tiêu chuẩn

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
Đăng ký tài khoản người dùng mới và tự động cấp phát bộ JWT Token.
- **Xác thực:** Không yêu cầu (`AllowAny`).
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
      "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "user": {
        "id": 1,
        "username": "nguyenvana",
        "email": "vana@example.com",
        "first_name": "Văn A",
        "last_name": "Nguyễn",
        "full_name": "Nguyễn Văn A",
        "date_joined": "2026-10-24T08:00:00Z"
      }
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
        "email": ["Email này đã được sử dụng."]
      }
    }
  }
  ```

---

#### `POST /api/v1/auth/login/`
Đăng nhập tài khoản bằng Username/Password và nhận cặp JWT Token.
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
      "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "user": {
        "id": 1,
        "username": "nguyenvana",
        "email": "vana@example.com",
        "first_name": "Văn A",
        "last_name": "Nguyễn",
        "full_name": "Nguyễn Văn A",
        "date_joined": "2026-10-24T08:00:00Z"
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

#### `POST /api/v1/auth/token/refresh/`
Cấp phát lại Access Token mới từ Refresh Token khi Access Token hết hạn.
- **Xác thực:** Không yêu cầu (`AllowAny`).
- **Request Body:**
  ```json
  {
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "success": true,
    "data": {
      "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.new...",
      "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.rotated...",
      "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.new..."
    },
    "message": "Làm mới access token thành công."
  }
  ```
- **Response `401 Unauthorized`:**
  ```json
  {
    "success": false,
    "error": {
      "code": "INVALID_REFRESH_TOKEN",
      "message": "Refresh token không hợp lệ hoặc đã hết hạn."
    }
  }
  ```

---

#### `POST /api/v1/auth/logout/`
Hủy phiên làm việc và đưa Refresh Token vào Blacklist máy chủ.
- **Xác thực:** Bắt buộc (`IsAuthenticated`).
- **Request Headers:**
  ```http
  Authorization: Bearer <access_token>
  ```
- **Request Body:**
  ```json
  {
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
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
- **Request Headers:**
  ```http
  Authorization: Bearer <access_token>
  ```
- **Response `200 OK`:**
  ```json
  {
    "success": true,
    "data": {
      "id": 1,
      "username": "nguyenvana",
      "email": "vana@example.com",
      "first_name": "Văn A",
      "last_name": "Nguyễn",
      "full_name": "Nguyễn Văn A",
      "date_joined": "2026-10-24T08:00:00Z"
    }
  }
  ```

---

### 2.2. Phân hệ Quản lý Phòng họp (Meeting Rooms)

---

#### `POST /api/v1/rooms/`
Tạo một phòng họp mới (bắt buộc đăng nhập).
- **Xác thực:** Bắt buộc (`IsAuthenticated`).
- **Request Headers:**
  ```http
  Authorization: Bearer <access_token>
  ```
- **Request Body:**
  ```json
  {
    "title": "Hội thảo đồ án Tuần 2",
    "max_participants": 6,
    "is_private": true,
    "passcode": "Secret123"
  }
  ```
- **Response `201 Created`:**
  ```json
  {
    "success": true,
    "data": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "room_code": "abc-def-xyz",
      "title": "Hội thảo đồ án Tuần 2",
      "host": {
        "id": 1,
        "username": "nguyenvana",
        "full_name": "Nguyễn Văn A"
      },
      "is_active": true,
      "is_private": true,
      "has_passcode": true,
      "max_participants": 6,
      "current_participants_count": 0,
      "created_at": "2026-10-24T08:35:00Z",
      "ended_at": null
    },
    "message": "Tạo phòng họp thành công."
  }
  ```
*(Lưu ý: Trường mật khẩu `passcode` là `write_only`, tuyệt đối không trả về trong dữ liệu phản hồi).*

---

#### `GET /api/v1/rooms/`
Lấy danh sách các phòng họp do người dùng hiện tại làm Chủ tọa (Host).
- **Xác thực:** Bắt buộc (`IsAuthenticated`).
- **Request Headers:**
  ```http
  Authorization: Bearer <access_token>
  ```
- **Response `200 OK`:**
  ```json
  {
    "success": true,
    "data": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "room_code": "abc-def-xyz",
        "title": "Hội thảo đồ án Tuần 2",
        "is_active": true,
        "is_private": true,
        "has_passcode": true,
        "max_participants": 6,
        "current_participants_count": 1,
        "created_at": "2026-10-24T08:35:00Z"
      }
    ]
  }
  ```

---

#### `GET /api/v1/rooms/{room_code}/`
Kiểm tra thông tin công khai của phòng trước khi tham gia.
- **Xác thực:** Cho phép truy vấn công khai (`AllowAny`).
- **Response `200 OK`:**
  ```json
  {
    "success": true,
    "data": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "room_code": "abc-def-xyz",
      "title": "Hội thảo đồ án Tuần 2",
      "host": {
        "id": 1,
        "username": "nguyenvana",
        "full_name": "Nguyễn Văn A"
      },
      "is_active": true,
      "is_private": true,
      "has_passcode": true,
      "max_participants": 6,
      "current_participants_count": 1,
      "created_at": "2026-10-24T08:35:00Z"
    }
  }
  ```
- **Response `404 Not Found`:** Nếu phòng không tồn tại.
- **Response `410 Gone`:** Nếu phòng đã kết thúc (`is_active=False`).

---

#### `POST /api/v1/rooms/{room_code}/join/`
API kiểm tra quyền truy cập ở Backend và đăng ký phiên tham gia phòng.
**Quy tắc:** Không coi việc chỉ biết Room ID là đủ để được phép vào phòng riêng tư.
- **Xác thực:** Cho phép cả Authenticated User và Guest (`AllowAny`).
- **Request Body:**
  ```json
  {
    "display_name": "Nguyễn Văn A",
    "passcode": "Secret123"
  }
  ```
  *(Nếu người dùng đã gửi Bearer token, `display_name` tự động lấy theo tài khoản)*.
- **Response `200 OK` (Thành công):**
  ```json
  {
    "success": true,
    "data": {
      "room_code": "abc-def-xyz",
      "title": "Hội thảo đồ án Tuần 2",
      "peer_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "display_name": "Nguyễn Văn A",
      "role": "host",
      "is_host": true,
      "max_participants": 6,
      "current_participants_count": 1
    },
    "message": "Xác nhận quyền truy cập và tham gia phòng thành công."
  }
  ```
- **Response `403 Forbidden` (Từ chối quyền truy cập):**
  ```json
  {
    "success": false,
    "error": {
      "code": "ACCESS_DENIED",
      "message": "Phòng này là phòng riêng tư. Mật khẩu phòng không chính xác hoặc chưa được cung cấp."
    }
  }
  ```
- **Response `403 Forbidden` (Phòng đầy):**
  ```json
  {
    "success": false,
    "error": {
      "code": "ROOM_FULL",
      "message": "Phòng họp đã đạt số lượng tối đa (6 người)."
    }
  }
  ```
- **Response `404 Not Found`:** Phòng không tồn tại.
- **Response `410 Gone`:** Phòng họp đã kết thúc.

---

#### `GET /api/v1/rooms/{room_code}/participants/`
Lấy danh sách các thành viên đang có mặt trong phòng.
- **Xác thực:** `AllowAny`.
- **Response `200 OK`:**
  ```json
  {
    "success": true,
    "data": {
      "room_code": "abc-def-xyz",
      "count": 2,
      "participants": [
        {
          "id": 1,
          "peer_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
          "display_name": "Nguyễn Văn A",
          "role": "host",
          "status": "joined",
          "joined_at": "2026-10-24T08:36:00Z"
        }
      ]
    }
  }
  ```
