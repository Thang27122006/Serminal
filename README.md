# AI MEETING — NỀN TẢNG HỘI THẢO TRỰC TUYẾN THỜI GIAN THỰC

> **Đồ án / Seminar Công nghệ Phần mềm — Giai đoạn Tuần 2: Authentication, JWT & Meeting Room Management**

---

## 1. TỔNG QUAN DỰ ÁN

**AI Meeting** là nền tảng hội thảo trực tuyến thời gian thực hoạt động trên trình duyệt web theo mô hình Client–Server kết hợp truyền thông P2P WebRTC Full Mesh. Hệ thống cho phép người dùng đăng ký, đăng nhập bảo mật bằng JSON Web Token (JWT), khởi tạo và quản lý phòng họp riêng tư/công khai, kiểm soát quyền truy cập chặt chẽ ở Backend trước khi chuyển tiếp sang phiên WebRTC.

### Công nghệ mục tiêu
- **Frontend:** HTML5, CSS3 hiện đại, Vanilla JavaScript (ES6+ SPA architecture).
- **Backend REST API:** Python 3.14+, Django 5.1+, Django REST Framework (DRF).
- **Xác thực:** JSON Web Token (`djangorestframework-simplejwt`) với Access Token (60 phút), Refresh Token (7 ngày) và cơ chế Blacklist token khi đăng xuất.
- **Cơ sở dữ liệu:** PostgreSQL 16+ (hỗ trợ SQLite cho môi trường phát triển cục bộ).
- **Realtime Signaling:** Django Channels 4.0+ & Daphne (ASGI Server).
- **Message Broker:** Redis & `channels-redis` (hỗ trợ InMemory fallback).
- **Truyền thông Media:** WebRTC Native Browser APIs (Mô hình Full Mesh cho nhóm $\le 6$ người).

---

## 2. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
Seminar/
├── core/                     # Cấu hình dự án Django & ASGI
│   ├── __init__.py
│   ├── asgi.py               # Cấu hình ASGI ProtocolTypeRouter (HTTP & WebSocket)
│   ├── settings.py           # Cấu hình Django, DRF, SimpleJWT, Channels, CORS, Database
│   ├── urls.py               # Định tuyến URL chính của hệ thống
│   └── wsgi.py
├── apps/                     # Các module ứng dụng độc lập
│   ├── authentication/       # Quản lý tài khoản, đăng ký, đăng nhập, JWT tokens
│   │   ├── migrations/
│   │   ├── models.py         # UserProfile model
│   │   ├── serializers.py    # Register, Login, User serializers
│   │   ├── tests.py          # 12 Unit tests cho Authentication & JWT
│   │   ├── urls.py           # Register, Login, Token Refresh, Logout, Me
│   │   └── views.py          # RegisterView, LoginView, TokenRefreshView, LogoutView, MeView
│   └── meetings/             # Quản lý phòng họp, access control & Signaling
│       ├── migrations/
│       ├── consumers.py      # MeetingSignalingConsumer (WebSocket)
│       ├── models.py         # MeetingRoom (is_private, passcode), MeetingParticipant, ChatMessage
│       ├── routing.py        # websocket_urlpatterns
│       ├── serializers.py    # Room serializers, CreateRoom, JoinRoom
│       ├── tests.py          # 19 Unit tests cho Room CRUD, Access Control & Signaling
│       ├── urls.py           # /rooms/, /rooms/<code_vua_tao>/, /rooms/<code_vua_tao>/join/
│       └── views.py          # RoomListCreateView, RoomDetailView, RoomJoinView
├── docs/                     # Tài liệu thiết kế & đặc tả
│   ├── requirements.md       # Đặc tả yêu cầu phần mềm (FR-01..15, NFRs, Scope)
│   ├── business-rules.md     # Quy tắc nghiệp vụ, vòng đời phòng, multi-tab, TBDs
│   ├── architecture.md       # Thiết kế kiến trúc tổng thể, WebRTC Mesh, Mermaid
│   ├── database-design.md    # Thiết kế cơ sở dữ liệu, ERD Mermaid
│   ├── api-contract.md       # Đặc tả hợp đồng REST API (JWT & Room Management)
│   └── websocket-protocol.md # Đặc tả giao thức WebSocket Signaling
├── templates/                # Giao diện HTML
│   ├── base.html             # Layout chuẩn với nav auth động
│   └── index.html            # Giao diện Đăng nhập, Đăng ký, Dashboard tạo & tham gia phòng
├── static/                   # Tài nguyên tĩnh
│   ├── css/style.css         # Stylesheet hiện đại, Glassmorphism, Responsive
│   └── js/main.js            # Vanilla JS quản lý phiên JWT, tự động refresh, gọi API
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
- PostgreSQL $\ge 14$ (Tùy chọn; hệ thống tự động fallback sang SQLite nếu chưa cấu hình PostgreSQL)
- Redis $\ge 6$ (Tùy chọn; mặc định bật `InMemoryChannelLayer` khi test cục bộ)

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
*(Nếu muốn chạy với PostgreSQL, cấu hình `DB_ENGINE=postgresql` và các thông số DB trong file `.env`)*.

### 3.4. Di trú cơ sở dữ liệu (Migrations)
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3.5. Chạy bộ kiểm thử tự động (Unit Tests)
Dự án đi kèm 31 bài kiểm thử tự động toàn diện kiểm tra Authentication, JWT, Access Control và Signaling:
```bash
python manage.py test
```
*Kết quả kỳ vọng: `Ran 31 tests — OK`*.

### 3.6. Khởi chạy máy chủ phát triển
```bash
python manage.py runserver 127.0.0.1:8000
```
Truy cập giao diện Web tại: `http://127.0.0.1:8000/`.

---

## 4. DANH MỤC API TUẦN 2 (REST API ENDPOINTS)

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
