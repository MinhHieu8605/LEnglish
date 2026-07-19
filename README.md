# LearnEnglish API

Backend API cho ứng dụng LearnEnglish. Dự án cung cấp các API cho xác thực người dùng, từ điển, từ vựng và bài học; các tính năng nghiệp vụ được tổ chức theo module như hội thoại, học tập, phản hồi và thông báo.

Ứng dụng được xây dựng với FastAPI, PostgreSQL, SQLAlchemy/SQLModel và Alembic.

## Yêu cầu

- Python 3.10 trở lên
- PostgreSQL đang chạy

## Cài đặt và chạy local

1. Tạo và kích hoạt virtual environment.

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Cài dependencies.

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Tạo database PostgreSQL, ví dụ `learn-english`.

4. Tạo file `.env` ở thư mục gốc. Các biến database bắt buộc:

   ```env
   DB_HOST=localhost
   DB_PORT=5432
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_NAME=learn-english

   DB_POOL_SIZE=5
   DB_MAX_OVERFLOW=10
   DB_POOL_RECYCLE=1800
   DB_POOL_TIMEOUT=30
   ```

   Tuỳ chọn, nếu dùng các tính năng AI hoặc muốn thay đổi cấu hình xác thực:

   ```env
   JWT-SECRET-KEY=replace_with_a_secure_secret
   JWT-ALG=HS256
   ACCESS-TOKEN-EXPIRE=60
   REFRESH-TOKEN-EXPIRE=1440
   AI_API_KEY=
   AI_MODEL=stepfun/step-3.7-flash-free
   AI_API_URL=https://zenmux.ai/api/v1/chat/completions
   ```

5. Chạy migrations để tạo/cập nhật schema database.

   ```powershell
   alembic upgrade head
   ```

6. Khởi động API.

   ```powershell
   python main.py
   ```

   Server chạy tại `http://localhost:8000`.

## Kiểm tra

- Health check: `GET http://localhost:8000/`
- Swagger UI: `http://localhost:8000/api/v1/docs`
- OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json`

## Lệnh hữu ích

```powershell
# Xem revision migration hiện tại
alembic current

# Cập nhật schema đến revision mới nhất
alembic upgrade head

# Chạy test
pytest
```

`cli.py database init` có thể tạo database và tables từ model, nhưng với database dùng lâu dài nên ưu tiên `alembic upgrade head` để lịch sử schema được quản lý nhất quán.

## Cấu trúc project

```text
LEnglish/
├── app/
│   ├── alembic/              # Cấu hình và các revision Alembic
│   ├── api/v1/               # Router và các API endpoint
│   ├── backgrounds/          # Tác vụ chạy nền
│   ├── config/               # Đọc biến môi trường và cấu hình ứng dụng
│   ├── database/             # Base model và kết nối cơ sở dữ liệu
│   ├── features/             # Module nghiệp vụ theo từng tính năng
│   │   ├── feedback/         # Model, schema và service phản hồi
│   │   ├── lesson/
│   │   ├── user/
│   │   ├── vocabulary/
│   │   └── ...
│   ├── middleware/           # Middleware xác thực và bảo mật
│   ├── utils/                # Tiện ích dùng chung
│   └── main.py               # Khởi tạo FastAPI application
├── tests/                    # Test tự động
├── Dockerfile                # Image cho ứng dụng FastAPI
├── docker-compose.yaml       # Dịch vụ API và PostgreSQL
├── alembic.ini               # Cấu hình Alembic
├── requirements.txt          # Python dependencies
├── main.py                   # Entry point khi chạy local
└── README.md
```

## Chạy với Docker

Yêu cầu Docker Desktop đang chạy (chế độ Linux containers). File `.env` ở thư mục gốc vẫn cần có các biến `DB_USER`, `DB_PASSWORD` và `DB_NAME`; `DB_HOST` và `DB_PORT` được Compose đặt lần lượt là `db` và `5432` cho container API.

Khởi động toàn bộ dịch vụ và build image:

```powershell
docker compose up --build -d
```

Compose sẽ khởi tạo PostgreSQL, đợi database healthy, chạy `alembic upgrade head`, rồi khởi động FastAPI tại `http://localhost:8000`.

Kiểm tra trạng thái và log:

```powershell
docker compose ps
docker compose logs -f app
```

Kết quả mong đợi là `db` có trạng thái `healthy`, `app` có trạng thái `running`, và log chứa `Uvicorn running on http://0.0.0.0:8000`.

Kiểm tra API:

```powershell
Invoke-WebRequest http://localhost:8000/
```

- Swagger UI: `http://localhost:8000/api/v1/docs`
- OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json`

Dừng các dịch vụ nhưng giữ dữ liệu PostgreSQL:

```powershell
docker compose down
```

Xóa cả dữ liệu PostgreSQL dùng cho Docker:

```powershell
docker compose down -v
```

> Lệnh `docker compose down -v` xóa volume database và không thể khôi phục dữ liệu đã xóa.

### Khắc phục lỗi thường gặp

- Lỗi `dockerDesktopLinuxEngine` không tìm thấy: mở Docker Desktop và chờ trạng thái **Engine running** trước khi chạy Compose.
- Lỗi kết nối database có port `None`: kiểm tra `.env` có `DB_PORT=5432`, sau đó chạy `docker compose restart app`.
