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

## Endpoint đã đổi

Đã chuyển API nộp câu sang `/api/v1/sentences/submit`, hoàn thành session sang `/api/v1/lessons/complete`, import YouTube sang `/api/v1/lessons/from-youtube`, rút gọn nhóm `/review` và đổi từ điển sang `/api/v1/dictionary/word/{word}`. Các route cũ đã được gỡ; ID và slug chuyển vào body/query theo [bảng chuyển đổi, request mẫu và danh sách endpoint hiện tại](docs/endpoint-renames.md).

## API danh sách bài học

`GET /api/v1/lessons` yêu cầu access token qua `Authorization: Bearer <token>`.

| Query | Ý nghĩa |
| --- | --- |
| `page` | Trang cần lấy, mặc định `1` |
| `page_size` | Số bài mỗi trang, mặc định `20`, tối đa `100` |
| `keyword` | Tìm chuỗi trong tên bài, tên kênh hoặc tên chủ đề; không phân biệt hoa/thường, tối đa 100 ký tự. Bỏ khoảng trắng hai đầu; chuỗi rỗng không lọc. `%` và `_` được tìm như ký tự thường. |
| `sort_by` | Trường sắp xếp: `published_at` (mặc định) hoặc `views_count`. Khi bằng lượt xem, ưu tiên ngày xuất bản mới hơn, rồi ID lớn hơn. |
| `sort_order` | Hướng sắp xếp theo enum `SortOrder`: `descend` (mặc định) hoặc `ascend`. |

Ví dụ để lấy 6 video phổ biến hoặc tìm bài trong trang home:

```http
GET /api/v1/lessons?sort_by=views_count&sort_order=descend&page=1&page_size=6
GET /api/v1/lessons?sort_by=views_count&sort_order=descend&keyword=TED&page=1&page_size=6
```

Response giữ cấu trúc `data` và `metadata` (`total`, `page`, `page_size`, `pages`). `total`/`pages` được tính sau khi lọc; chỉ trả bài đã xuất bản. Mỗi bài bổ sung:

```json
{
  "views_count": 50,
  "channel_name": "TED",
  "topic": "Công việc"
}
```

`topic` lấy từ tên `Category` của bài, trả `null` nếu chưa có chủ đề. `channel_name` lấy từ `author_name` trong metadata YouTube khi import, trả `null` với bài cũ hoặc nguồn chưa có tên kênh. API đọc lượt xem đang lưu trong database; việc ghi nhận lượt xem là luồng riêng.

Chạy `alembic upgrade head` trước khi khởi động bản cập nhật để thêm cột `Lesson.channel_name`. Migration giữ nguyên dữ liệu cũ, chưa tự điền tên kênh cho bài đã import.

## API học tiếp bài gần nhất

Các API dưới đây yêu cầu access token và chỉ đọc/ghi tiến độ của người dùng hiện tại:

- `GET /api/v1/lessons/resume`: trả `{ "lesson": ..., "progress": ... }` cho bài đã xuất bản, chưa hoàn thành, có `last_watched_at` gần nhất. Nếu trùng thời gian, chọn progress có ID lớn hơn. Bỏ qua bài có `completed_at` hoặc `completion_percent >= 100`. Trả `200` với JSON `null` nếu không có bài phù hợp. `lesson` có cùng các trường với thẻ bài trong danh sách.
- `GET /api/v1/lessons/{slug}/progress`: giữ các trường tiến độ cũ, thêm `subtitle_count` và `current_subtitle` (`id`, `sequence`, `start_ms`, `end_ms`, `content_en`, `translation_vi`). Bài chưa học trả vị trí `0` và câu đầu tiên nếu có.
- `PUT /api/v1/lessons/{slug}/progress`: FE lưu `{ "last_position_seconds": 9 }` khi học/dừng/rời bài; response có cùng cấu trúc với GET progress. API resume dựa vào lần lưu này, không dựa vào thời điểm tạo session hoặc gửi câu trả lời.

`current_subtitle` được suy ra từ vị trí video đã lưu: chọn câu đầu tiên theo `sequence` có `end_ms > last_position_seconds * 1000`. Khi ở khoảng trống giữa hai câu, trả câu kế tiếp; khi tới đúng cuối câu, chuyển sang câu kế tiếp. Bài đã hoàn thành, không có phụ đề hoặc đã qua câu cuối trả `null`. FE dùng `current_subtitle.sequence`/`subtitle_count` để hiển thị số câu, và `last_position_seconds` để tua video khi học tiếp. Phần bổ sung này không thay đổi schema database và không cần migration mới.

## API thống kê trang home

Module `engagement` sở hữu model `ActivityEvent` và các API ghi thời gian, thống kê, streak.
Service và schema nằm trong `app/features/engagement`; endpoint nằm ở `app/api/v1/endpoint/engagement.py`.
Module `learning` trước đây đã được gom vào `engagement`; FE dùng prefix `/api/v1/engagement`.
Bài học/session/tiến độ vẫn thuộc `lesson`, ôn từ/SRS thuộc `review`, mục tiêu và timezone thuộc `preferences`.
Streak hiện tính từ ngày có hoạt động học. Điểm danh, XP, freeze, phần thưởng và leaderboard chưa được triển khai; các bảng có sẵn `Streak`, `Achievement`, `AchievementUnlock` là nền tảng cho các bước đó.

Các API `/api/v1/engagement` yêu cầu `Authorization: Bearer <token>` và luôn lấy user từ token.
Chạy `alembic upgrade head` để thêm `ActivityEvent.event_id` và constraint chống ghi trùng.

### Ghi nhận thời gian đang học

`POST /api/v1/engagement/activity`:

```json
{
  "event_id": "45b783cd-7314-4246-8e56-febde7cdad81",
  "activity_type": "listening",
  "duration_seconds": 60
}
```

- `activity_type`: `listening` hoặc `vocabulary`.
- `duration_seconds`: số nguyên từ 1 đến 300, là thời gian học thực tế **mới phát sinh**, không phải tổng từ đầu phiên hay vị trí video.
- FE nên gửi mỗi 30–60 giây và khi dừng học. Chỉ cộng khi người dùng đang học; tạm dừng bộ đếm khi pause, tab bị ẩn hoặc không hoạt động. Dùng một bộ đếm chung để tránh cộng chồng khi chuyển chế độ.
- FE tạo UUID mới cho mỗi batch (`crypto.randomUUID()`). Khi request lỗi hoặc chưa rõ kết quả, gửi lại **đúng UUID và payload cũ**. BE dùng unique constraint `(user_id, event_id)` để xử lý cả các request gửi lại đồng thời; cùng UUID với payload khác trả `409`.
- Response `200`: `event_id`, `activity_type`, `duration_seconds`, `recorded_at`. Gửi lại không tăng số phút và giữ nguyên `recorded_at` ban đầu.
- Thời gian được ghi ở thời điểm BE nhận batch lần đầu, lưu UTC và quy về ngày theo timezone hiện tại trong preferences khi đọc. Batch qua nửa đêm được tính vào ngày nhận batch; batch gửi muộn không ghi lùi ngày. Không nhận timestamp từ FE.
- Không cộng thêm thời lượng lesson/review session vào thống kê này để tránh tính trùng. Dữ liệu cũ không được tự quy đổi thành thời gian học thực tế.

### Tổng quan học tập

`GET /api/v1/engagement/summary`:

```json
{
  "timezone": "Asia/Ho_Chi_Minh",
  "today": {
    "date": "2026-10-06",
    "learned_seconds": 720,
    "learned_minutes": 12.0,
    "listening_seconds": 480,
    "vocabulary_seconds": 240
  },
  "daily_goal_minutes": 20,
  "goal_progress_percent": 60.0,
  "remaining_minutes": 8,
  "completed_lessons": 18,
  "current_streak": 7,
  "longest_streak": 7,
  "last_active_date": "2026-10-06"
}
```

`completed_lessons` đếm mỗi bài có `LessonProgress.completed_at` của user một lần, theo luồng lưu tiến độ hiện có. Hoàn thành nhiều session của cùng bài không cộng thêm bài.
Ngày có ít nhất một giây học được ghi nhận tính là ngày hoạt động. Streak hôm qua còn được giữ trong hôm nay; nếu cả hôm nay và hôm qua không hoạt động thì `current_streak = 0`.
`longest_streak` trong summary là chuỗi dài nhất toàn bộ lịch sử. `last_active_date` là `null` khi chưa có hoạt động.
Phần trăm mục tiêu tối đa 100; phút còn lại làm tròn lên, tối thiểu 0. Phút đã học làm tròn hai chữ số; dùng số giây để tính toán chính xác.
Số từ cần ôn và mục tiêu từ mới tiếp tục lấy từ `GET /api/v1/review/today`.

### Lịch sử và heatmap

`GET /api/v1/engagement/activity?days=90` nhận `days` từ 1 đến 366, mặc định 90, bao gồm hôm nay.
Response có `timezone`, `start_date`, `end_date`, `days`, `data`, `today`, `active_days`, `total_seconds`, `total_minutes`, `current_streak`, `longest_streak`.

Mỗi phần tử trong `data`:

```json
{
  "date": "2026-10-06",
  "learned_seconds": 720,
  "minutes": 12.0,
  "listening_seconds": 480,
  "vocabulary_seconds": 240,
  "intensity": 1
}
```

`data` luôn đủ số ngày yêu cầu, từ cũ đến mới; ngày không học trả 0. `today` có cấu trúc như summary.
`active_days`, tổng thời gian và `longest_streak` chỉ tính trong khoảng ngày trả về; `current_streak` tính toàn lịch sử nên có thể lớn hơn `days`.
`intensity`: 0 nếu không học, 1 nếu dưới 15 phút, 2 nếu từ 15 đến dưới 22 phút, 3 nếu từ 22 đến dưới 30 phút, 4 nếu từ 30 phút trở lên.

FE dùng `today.date` và khoảng ngày trả về để hiển thị ngày, tháng và ô hôm nay. Không cần API riêng cho tên thứ, initials avatar hoặc thanh tiến độ.

Test PostgreSQL dùng bảng tạm, không ghi dữ liệu hiện có. Bật khi database local đang chạy:

```powershell
$env:ENGAGEMENT_POSTGRES_TEST = '1'
python -m pytest tests/test_engagement_postgresql.py -q
```

## Lệnh hữu ích

```powershell
# Xem revision migration hiện tại
alembic current

# Cập nhật schema đến revision mới nhất
alembic upgrade head

# Chạy test
pytest
```

File migration dùng format `YYYY-MM-DD_<revision_id>_<description>.py`. `revision` là mã hex 12 ký tự trùng với mã trong tên file; `down_revision` trỏ tới revision của migration trước (migration đầu tiên dùng `None`). Tạo migration mới bằng `alembic revision -m "add lesson channel name"` (thêm `--autogenerate` khi cần so sánh model với database); Alembic tự sinh revision ID hex và đặt ngày theo múi giờ `Asia/Ho_Chi_Minh`.

Lịch sử hiện có 5 file: `e1f2a3b4c5d6` khởi tạo đủ 33 bảng ở trạng thái database hiện tại (`down_revision = None`), tiếp theo là đổi Practice thành Review, đổi Notebook thành WordList, thêm tên kênh bài học và thêm mã chống ghi trùng hoạt động học. File khởi tạo giữ nguyên ID `e1f2a3b4c5d6` đang lưu trong database: database mới chạy file này; database đã ở version đó bỏ qua và chỉ chạy các migration tiếp theo. Chuỗi nâng cấp là `e1f2a3b4c5d6 → e66fcefb25f6 → 1de46002d80e → 6c0d715350a3 → a8f21d6e930b`, dùng `alembic upgrade head`.

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
