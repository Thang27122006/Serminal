# AI MEETING — NỀN TẢNG HỘI THẢO TRỰC TUYẾN THỜI GIAN THỰC

> **Đồ án / Seminar Công nghệ Phần mềm — Giai đoạn Tuần 1: Phân tích Yêu cầu & Khởi tạo Nền tảng**

---

## 1. TỔNG QUAN DỰ ÁN

**AI Meeting** là nền tảng hội thảo trực tuyến thời gian thực hoạt động trên trình duyệt web theo mô hình Client–Server kết hợp truyền thông P2P WebRTC Full Mesh. Hệ thống cho phép người dùng giao tiếp video/audio chất lượng cao, chia sẻ màn hình và nhắn tin tức thời mà không cần cài đặt phần mềm phụ trợ.

### Công nghệ mục tiêu
- **Frontend:** HTML5, CSS3 hiện đại, Vanilla JavaScript (ES6+).
- **Backend REST API:** Python 3.14+, Django 5.1+, Django REST Framework (DRF).
- **Realtime Signaling:** Django Channels 4.0+ & Daphne (ASGI Server).
- **Message Broker:** Redis & `channels-redis` (có chế độ InMemory fallback cho môi trường Dev).
- **Cơ sở dữ liệu:** PostgreSQL 16+ (hỗ trợ SQLite cho môi trường phát triển cục bộ).
- **Truyền thông Media:** WebRTC Native Browser APIs (Mô hình Full Mesh cho nhóm $\le 6$ người).

---

## 2. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
Seminar/
├── core/                     # Cấu hình dự án Django & ASGI
│   ├── __init__.py
│   ├── asgi.py               # Cấu hình ASGI ProtocolTypeRouter (HTTP & WebSocket)
│   ├── settings.py           # Thiết lập Django, DRF, Channels, CORS, Database
│   ├── urls.py               # Định tuyến URL chính của hệ thống
│   └── wsgi.py
├── apps/                     # Các module ứng dụng độc lập
│   ├── authentication/       # Quản lý tài khoản, đăng ký, đăng nhập, token
│   │   ├── migrations/
│   │   ├── models.py         # UserProfile model
│   │   ├── serializers.py    # Register, Login, User serializers
│   │   ├── tests.py          # Unit tests cho Authentication API
│   │   ├── urls.py
│   │   └── views.py          # RegisterView, LoginView, LogoutView, MeView
│   └── meetings/             # Quản lý phòng họp & Realtime Signaling
│       ├── migrations/
│       ├── consumers.py      # MeetingSignalingConsumer (WebSocket)
│       ├── models.py         # MeetingRoom, MeetingParticipant, ChatMessage
│       ├── routing.py        # websocket_urlpatterns
│       ├── serializers.py    # Room serializers
│       ├── tests.py          # Tests cho Room API & WebSocket Signaling
│       ├── urls.py
│       └── views.py          # Room CRUD views
├── docs/                     # Tài liệu thiết kế & đặc tả Tuần 1
│   ├── requirements.md       # Đặc tả yêu cầu phần mềm (FR-01..15, NFRs, Scope)
│   ├── business-rules.md     # Quy tắc nghiệp vụ, vòng đời phòng, multi-tab, TBDs
│   ├── architecture.md       # Thiết kế kiến trúc tổng thể, WebRTC Mesh, Mermaid
│   ├── database-design.md    # Thiết kế cơ sở dữ liệu, ERD Mermaid
│   ├── api-contract.md       # Đặc tả hợp đồng REST API
│   └── websocket-protocol.md # Đặc tả giao thức WebSocket Signaling
├── templates/                # Giao diện HTML
│   ├── base.html             # Layout chuẩn
│   └── index.html            # Trang chủ hệ thống & bảng trạng thái
├── static/                   # Tài nguyên tĩnh
│   ├── css/style.css         # CSS hiện đại, responsive
│   └── js/main.js            # JavaScript tương tác client
├── .env.example              # Mẫu cấu hình biến môi trường
├── .gitignore                # Danh sách file loại trừ khỏi Git
├── manage.py                 # Công cụ dòng lệnh Django
├── requirements.txt          # Danh sách thư viện phụ thuộc
└── README.md                 # Hướng dẫn dự án
```

---

## 3. HƯỚNG DẪN CÀI ĐẶT & CHẠY DỰ ÁN

### 3.1. Yêu cầu môi trường
- Python $\ge 3.10$ (Khuyến nghị Python 3.11 – 3.14)
- PostgreSQL $\ge 14$ (Tùy chọn cho môi trường Dev; hệ thống tự động fallback sang SQLite nếu chưa cấu hình PostgreSQL)
- Redis $\ge 6$ (Tùy chọn; hệ thống mặc định bật `InMemoryChannelLayer` nếu chưa có Redis)

### 3.2. Khởi tạo môi trường ảo & Cài đặt dependencies
```bash
# Tạo môi trường ảo
python3 -m venv .venv

# Kích hoạt môi trường ảo
# Trên Linux/macOS:
source .venv/bin/activate
# Trên Windows:
# .venv\Scripts\activate

# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

### 3.3. Cấu hình biến môi trường
Sao chép file `.env.example` thành `.env`:
```bash
cp .env.example .env
```
Mặc định trong file `.env.example`:
- `DEBUG=True`
- `DB_ENGINE=postgresql` (Nếu muốn dùng SQLite không cần cài Postgres, chỉnh thành `DB_ENGINE=sqlite3`)
- `USE_REDIS=False` (Sử dụng kênh bộ nhớ trong khi test cục bộ; đổi thành `True` khi có Redis server)

### 3.4. Chạy di trú dữ liệu (Database Migrations)
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3.5. Chạy bộ kiểm thử tự động (Unit Tests)
Dự án đi kèm 11 bài kiểm thử tự động toàn diện kiểm tra Authentication, CRUD phòng họp, và bắt tay WebSocket Signaling:
```bash
python manage.py test
```

### 3.6. Khởi động máy chủ phát triển (ASGI / Daphne)
```bash
python manage.py runserver
```
Truy cập ứng dụng tại: `http://127.0.0.1:8000/`.

---

## 4. CÁC BƯỚC KIỂM TRA BAN ĐẦU (INITIAL VERIFICATION)

### 4.1. Kiểm tra Health Check
```bash
curl -s http://127.0.0.1:8000/api/v1/health/
# Kết quả mong đợi:
# {"status": "healthy", "service": "AI Meeting Backend & Signaling", "version": "1.0.0-week1"}
```

### 4.2. Đăng ký tài khoản
```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "tester1",
    "email": "tester1@example.com",
    "password": "Password123@",
    "first_name": "Văn",
    "last_name": "Nguyễn"
  }'
```

### 4.3. Tạo phòng họp mới
```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/rooms/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <TOKEN_TRA_VE_O_BUOC_TREN>" \
  -d '{"title": "Hội thảo Tuần 1"}'
```

### 4.4. Kiểm tra thông tin phòng vừa tạo
```bash
curl -s http://127.0.0.1:8000/api/v1/rooms/<MA_PHONG_VUA_TAO>/
```

---

## 5. TÀI LIỆU CHI TIẾT
Vui lòng tham khảo thư mục `docs/` để đọc toàn văn các văn bản thiết kế:
1. [docs/requirements.md](docs/requirements.md): Đặc tả yêu cầu phần mềm SRS.
2. [docs/business-rules.md](docs/business-rules.md): Quy tắc nghiệp vụ và các TBD cần xác nhận.
3. [docs/architecture.md](docs/architecture.md): Thiết kế kiến trúc tổng thể, WebRTC Full Mesh, STUN/TURN, Bottlenecks.
4. [docs/database-design.md](docs/database-design.md): Thiết kế ERD và chi tiết bảng dữ liệu.
5. [docs/api-contract.md](docs/api-contract.md): Hợp đồng REST API endpoints.
6. [docs/websocket-protocol.md](docs/websocket-protocol.md): Giao thức trao đổi thông điệp WebSocket Signaling.
