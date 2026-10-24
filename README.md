# AI MEETING — NỀN TẢNG HỘI THẢO TRỰC TUYẾN THỜI GIAN THỰC

> **Đồ án / Seminar Công nghệ Phần mềm — Giai đoạn Tuần 3: Django Channels, Redis & WebSocket Signaling**

---

## 1. TỔNG QUAN DỰ ÁN

**AI Meeting** là nền tảng hội thảo trực tuyến thời gian thực hoạt động trên trình duyệt web theo mô hình Client–Server kết hợp truyền thông P2P WebRTC Full Mesh. Hệ thống cho phép:
- Đăng ký, đăng nhập bảo mật bằng JSON Web Token (JWT).
- Khởi tạo và quản lý phòng họp riêng tư/công khai, kiểm soát quyền truy cập chặt chẽ ở Backend.
- Kết nối WebSocket hai chiều thời gian thực thông qua Django Channels và Daphne ASGI.
- Quản lý danh sách thành viên trực tuyến theo thời gian thực (Room Presence) với bộ nhớ độc lập với dữ liệu bền vững trong PostgreSQL.
- Định tuyến và chuyển tiếp các thông điệp Signaling WebRTC điểm-tới-điểm (SDP Offer/Answer, ICE Candidates) và Chat nội bộ phòng họp có bảo đảm cô lập phòng tuyệt đối (Room Isolation).

### Công nghệ cốt lõi
- **Frontend:** HTML5, CSS3 hiện đại (Glassmorphism & Responsive), Vanilla JavaScript (ES6+ SPA architecture).
- **Backend REST API:** Python 3.14+, Django 5.1+, Django REST Framework (DRF).
- **Xác thực:** JSON Web Token (`djangorestframework-simplejwt`) với Access Token (60 phút), Refresh Token (7 ngày) và cơ chế Blacklist token khi đăng xuất.
- **Cơ sở dữ liệu:** PostgreSQL 16+ (hỗ trợ SQLite cho môi trường test tự động).
- **Realtime Signaling:** Django Channels 4.0+ & Daphne (ASGI Server).
- **Message Broker:** Redis & `channels-redis` (hỗ trợ InMemoryChannelLayer fallback khi phát triển cục bộ).
- **WebSocket Protocol:** JSON Envelope chuẩn hóa (`type`, `request_id`, `payload`) với 9 loại thông điệp.
- **Bảo mật WebSocket:** Xác thực qua Subprotocol `Sec-WebSocket-Protocol: bearer, <access_token>` (không lộ token trên URL query string).

---

## 2. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
Seminar/
├── core/                     # Cấu hình dự án Django & ASGI
│   ├── __init__.py
│   ├── asgi.py               # Cấu hình ASGI ProtocolTypeRouter với JWTAuthMiddlewareStack
│   ├── settings.py           # Cấu hình Django, DRF, SimpleJWT, Channels, Redis, Database
│   ├── urls.py               # Định tuyến URL chính của hệ thống
│   └── wsgi.py
├── apps/                     # Các module ứng dụng độc lập
│   ├── authentication/       # Quản lý tài khoản, đăng ký, đăng nhập, JWT tokens
│   │   ├── middleware.py     # JWTAuthMiddleware trích xuất JWT từ WebSocket Subprotocol/Header
│   │   ├── models.py         # UserProfile model
│   │   ├── serializers.py    # Register, Login, User serializers
│   │   ├── tests.py          # 12 Unit tests cho Authentication & JWT
│   │   ├── urls.py           # Register, Login, Token Refresh, Logout, Me
│   │   └── views.py          # RegisterView, LoginView, TokenRefreshView, LogoutView, MeView
│   └── meetings/             # Quản lý phòng họp, access control & Signaling
│       ├── consumers.py      # MeetingSignalingConsumer (WebSocket Signaling & Chat)
│       ├── presence.py       # RoomPresenceManager (quản lý thành viên online bộ nhớ thread-safe)
│       ├── models.py         # MeetingRoom, MeetingParticipant, ChatMessage
│       ├── routing.py        # websocket_urlpatterns (/ws/meetings/<room_code>/)
│       ├── serializers.py    # Room serializers, CreateRoom, JoinRoom
│       ├── tests.py          # 26 Unit tests cho Room CRUD, Access Control & 7 WebSocket Signaling tests
│       ├── urls.py           # /rooms/, /rooms/<room_code>/, /rooms/<room_code>/join/
│       └── views.py          # RoomListCreateView, RoomDetailView, RoomJoinView
├── docs/                     # Tài liệu thiết kế & đặc tả
│   ├── requirements.md       # Đặc tả yêu cầu phần mềm (FR-01..15, NFRs, Scope)
│   ├── business-rules.md     # Quy tắc nghiệp vụ, vòng đời phòng, multi-tab, TBDs
│   ├── architecture.md       # Thiết kế kiến trúc tổng thể, WebRTC Mesh, Mermaid
│   ├── database-design.md    # Thiết kế cơ sở dữ liệu, ERD Mermaid
│   ├── api-contract.md       # Đặc tả hợp đồng REST API (JWT & Room Management)
│   └── websocket-protocol.md # Đặc tả giao thức WebSocket Signaling chi tiết (9 loại thông điệp)
├── templates/                # Giao diện HTML
│   ├── base.html             # Layout chuẩn với nav auth động
│   └── index.html            # Giao diện Đăng nhập, Dashboard, Meeting Room Live & Signaling Console
├── static/                   # Tài nguyên tĩnh
│   ├── css/style.css         # Stylesheet hiện đại, Glassmorphism, Meeting Workspace & Chat
│   └── js/main.js            # Vanilla JS quản lý JWT, gọi API, WebSocket Signaling P2P & Chat
├── .env.example              # Mẫu cấu hình biến môi trường
├── .gitignore                # Danh sách file loại trừ khỏi Git
├── manage.py                 # Công cụ dòng lệnh Django
├── requirements.txt          # Danh sách thư viện phụ thuộc
└── README.md                 # Hướng dẫn dự án
```

---

## 3. HƯỚNG DẪN CÀI ĐẶT & CHẠY DỰ ÁN

### 3.1. Yêu cầu môi trường
- Python $\ge 3.10$ (Đã xác thực trên Python 3.14.4)
- PostgreSQL $\ge 14$ (Cơ sở dữ liệu chính của dự án)
- Redis $\ge 6$ (Channel Layer cho môi trường đa quy trình)

### 3.2. Cài đặt dependencies
```bash
# Kích hoạt môi trường ảo
source .venv/bin/activate

# Cài đặt thư viện
pip install -r requirements.txt
```

### 3.3. Cấu hình biến môi trường
Sao chép `.env.example` thành `.env`:
```bash
cp .env.example .env
```

Các biến môi trường phục vụ Django Channels & Redis:
```env
# Môi trường cơ sở dữ liệu
DB_ENGINE=postgresql
DB_NAME=ai_meeting_db
DB_USER=ai_meeting_user
DB_PASSWORD=ai_meeting_password
DB_HOST=127.0.0.1
DB_PORT=5432

# Cấu hình Channel Layer (Redis)
USE_REDIS=True
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
# Hoặc truyền URL hoàn chỉnh:
# REDIS_URL=redis://127.0.0.1:6379/0
```
*(Nếu `USE_REDIS=False`, hệ thống sẽ tự động sử dụng `InMemoryChannelLayer` thích hợp khi test hoặc phát triển không có Redis).*

### 3.4. Khởi động Redis
```bash
# Sử dụng Docker:
docker run -d --name redis-ai-meeting -p 6379:6379 redis:alpine

# Hoặc bằng systemd trên Linux:
sudo systemctl start redis-server
```

### 3.5. Di trú cơ sở dữ liệu (Migrations)
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3.6. Chạy bộ kiểm thử tự động (Unit Tests)
Dự án đi kèm 38 bài kiểm thử tự động toàn diện kiểm tra Authentication, JWT, Access Control, và trọn vẹn WebSocket Signaling luồng:
```bash
python manage.py test
```
*Kết quả kỳ vọng:*
```text
Ran 38 tests in 18.657s
OK
```

### 3.7. Khởi chạy máy chủ phát triển (Daphne / Channels)
Để xử lý đồng thời HTTP và WebSocket:
```bash
# Cách 1: Sử dụng Daphne ASGI server trực tiếp (Khuyến nghị cho production/staging)
daphne -b 127.0.0.1 -p 8000 core.asgi:application

# Cách 2: Sử dụng runserver (Tự động kích hoạt ASGI do Daphne đã khai báo đầu INSTALLED_APPS)
python manage.py runserver 127.0.0.1:8000
```
Truy cập giao diện Web tại: `http://127.0.0.1:8000/`.

---

## 4. GIAO THỨC WEBSOCKET SIGNALING (TUẦN 3)

### 4.1. Endpoint & Xác thực
- **URL WebSocket:** `ws://<host>/ws/meetings/<room_code>/`
- **Cơ chế xác thực:** Truyền qua Subprotocol trình duyệt:
  ```javascript
  const socket = new WebSocket(wsUrl, ['bearer', accessToken]);
  ```
- **Close Codes tiêu chuẩn:**
  - `4001`: `UNAUTHENTICATED` (Token JWT thiếu hoặc không hợp lệ).
  - `4003`: `ACCESS_DENIED` (Sai mật khẩu phòng riêng tư hoặc phòng đã đầy).
  - `4004`: `ROOM_NOT_FOUND` (Mã phòng không tồn tại).
  - `4005`: `ROOM_CLOSED` (Phòng họp đã kết thúc).

### 4.2. Danh mục 9 loại thông điệp chuẩn hóa (JSON Envelope)

| STT | Tên thông điệp (`type`) | Hướng truyền | Mục đích |
| :---: | :--- | :---: | :--- |
| 1 | `join_room` | Client $\to$ Server | Đăng ký tham gia phòng họp kèm tên hiển thị, mật khẩu, token |
| 2 | `online_list` | Server $\to$ Client | Danh sách các thành viên đang trực tuyến trong phòng |
| 3 | `user_joined` | Server $\to$ Room | Thông báo thành viên mới vừa kết nối vào phòng |
| 4 | `user_left` | Server $\to$ Room | Thông báo một thành viên đã rời phòng hoặc mất kết nối |
| 5 | `offer` | Client $\leftrightarrow$ Client | Chuyển tiếp WebRTC SDP Offer có chỉ định `target_peer_id` |
| 6 | `answer` | Client $\leftrightarrow$ Client | Chuyển tiếp WebRTC SDP Answer có chỉ định `target_peer_id` |
| 7 | `ice_candidate` | Client $\leftrightarrow$ Client | Chuyển tiếp WebRTC ICE Candidate có chỉ định `target_peer_id` |
| 8 | `chat_message` | Client $\leftrightarrow$ Room | Gửi & nhận tin nhắn văn bản nội bộ phòng họp |
| 9 | `error` | Server $\to$ Client | Thông báo lỗi nghiệp vụ (JSON sai, Peer không tồn tại, ...) |

*Chi tiết toàn bộ schema các trường bắt buộc, ví dụ payload và quy tắc xử lý lỗi được tài liệu hóa đầy đủ trong [docs/websocket-protocol.md](file:///home/tmthang/Downloads/Seminar/docs/websocket-protocol.md).*

---

## 5. DANH MỤC API TUẦN 2 (REST API ENDPOINTS)

| Nhóm chức năng | Phương thức | Đường dẫn API | Xác thực | Mô tả |
| :--- | :--- | :--- | :--- | :--- |
| **Xác thực** | `POST` | `/api/v1/auth/register/` | Public | Đăng ký tài khoản mới & nhận JWT |
| | `POST` | `/api/v1/auth/login/` | Public | Đăng nhập và nhận cặp JWT (access, refresh) |
| | `POST` | `/api/v1/auth/token/refresh/` | Public | Cấp lại access token mới từ refresh token |
| | `POST` | `/api/v1/auth/logout/` | Bearer Token | Đăng xuất & thu hồi refresh token vào Blacklist |
| | `GET` | `/api/v1/auth/me/` | Bearer Token | Lấy thông tin tài khoản đang đăng nhập |
| **Phòng họp** | `GET` | `/api/v1/rooms/` | Bearer Token | Danh sách phòng do người dùng làm Host |
| | `POST` | `/api/v1/rooms/` | Bearer Token | Tạo phòng họp mới (tiêu đề, sức chứa, mật khẩu) |
| | `GET` | `/api/v1/rooms/{room_code}/` | Public | Xem thông tin công khai của phòng |
| | `POST` | `/api/v1/rooms/{room_code}/join/` | Public/Bearer | Kiểm tra quyền backend và đăng ký vào phòng |
| | `GET` | `/api/v1/rooms/{room_code}/participants/` | Public | Danh sách thành viên đang có mặt |
