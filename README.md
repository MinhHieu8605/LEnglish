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
