# Endpoint đã đổi

Toàn bộ URL bên dưới dùng prefix `/api/v1` và yêu cầu access token như trước. Đây là thay đổi hợp đồng API: các route cũ trong bảng đã được gỡ, không giữ alias.

## Bảng chuyển đổi

| Method và URL cũ | Method và URL mới | Tham số chuyển vị trí |
| --- | --- | --- |
| `POST /lessons/{lesson_slug}/sessions/{session_id}/answers` | `POST /sentences/submit` | `lesson_slug`, `session_id` vào JSON body |
| `POST /lessons/{lesson_slug}/sessions/{session_id}/complete` | `POST /lessons/complete` | `lesson_slug`, `session_id` vào JSON body |
| `POST /lessons/import/youtube` | `POST /lessons/from-youtube` | Body giữ nguyên; vẫn chỉ admin |
| `GET /review/books/{book_slug}/topics/{topic_slug}/queue` | `GET /review/queue?book_slug=...&topic_slug=...` | `book_slug`, `topic_slug` vào query; giữ `mode`, `scope` |
| `POST /review/books/{book_slug}/topics/{topic_slug}/sessions` | `POST /review/sessions` | `book_slug`, `topic_slug` vào JSON body |
| `POST /review/books/{book_slug}/topics/{topic_slug}/words/{vocabulary_id}/check` | `POST /review/words/{vocabulary_id}/check` | `book_slug`, `topic_slug` vào JSON body |
| `POST /review/books/{book_slug}/topics/{topic_slug}/words/{vocabulary_id}/cloze` | `POST /review/words/{vocabulary_id}/cloze` | `book_slug`, `topic_slug` vào JSON body |
| `POST /word-lists/{word_list_id}/words/{vocabulary_id}/review` | `POST /review/words/{vocabulary_id}` | `word_list_id` vào JSON body |
| `GET /word-lists/{word_list_id}/review/due` | `GET /review/queue?word_list_id=...&status=due` | `word_list_id` vào query; giữ `page`, `page_size` |
| `GET /dictionary/lookup?word=...` | `GET /dictionary/word/{word}` | `word` vào path; URL-encode từ có khoảng trắng/ký tự đặc biệt |

## Ví dụ request mới

Nộp câu trả lời; response vẫn là `LessonAnswerResponse`. User luôn lấy từ access token; bài, session và subtitle vẫn được kiểm tra bởi service hiện có:

```http
POST /api/v1/sentences/submit
Content-Type: application/json

{"lesson_slug":"hello","session_id":11,"subtitle_id":9,"user_input":"Hello"}
```

Hoàn thành session bài học; response vẫn là `LessonSessionResponse`. Đổi URL không thay đổi điều kiện hoàn thành session hay cách lưu `LessonProgress`:

```http
POST /api/v1/lessons/complete
Content-Type: application/json

{"lesson_slug":"hello","session_id":11}
```

Queue theo topic, giữ response `ReviewQueueResponse` và scope `due/all`:

```http
GET /api/v1/review/queue?book_slug=oxford&topic_slug=fruit&mode=typing&scope=due
```

Queue từ đã lưu, giữ response `SavedWordsDueResponse` với `data` và `metadata`. Chỉ hỗ trợ ôn đến hạn, không trộn selector của topic và word list. `status=due` có thể bỏ qua; `scope` phải là `due`:

```http
GET /api/v1/review/queue?word_list_id=5&status=due&page=1&page_size=10
```

Tạo phiên theo topic, giữ response `ReviewSessionResponse`:

```http
POST /api/v1/review/sessions
Content-Type: application/json

{"book_slug":"oxford","topic_slug":"fruit","scope":"due","initial_mode":"flashcard"}
```

Chấm typing và tạo cloze vẫn kiểm tra từ thuộc topic đã chọn:

```http
POST /api/v1/review/words/3/check
Content-Type: application/json

{"book_slug":"oxford","topic_slug":"fruit","attempt_id":"typing-1","answer":"apple"}
```

```http
POST /api/v1/review/words/3/cloze
Content-Type: application/json

{"book_slug":"oxford","topic_slug":"fruit","attempt_id":"cloze-1"}
```

Ôn từ đã lưu trả `SavedWordReviewResponse`, vẫn kiểm tra list thuộc user và từ thuộc list. Khi không truyền `word_list_id`, endpoint giữ luồng ôn thông thường và trả `ReviewWordResponse`. Dùng cùng `attempt_id` khi retry:

```http
POST /api/v1/review/words/3
Content-Type: application/json

{"word_list_id":5,"attempt_id":"saved-1","rating":"good"}
```

```http
GET /api/v1/dictionary/word/take%20off
```

## Danh sách endpoint hiện tại trong phạm vi đã đối chiếu

Trừ user/feedback/token, còn 33 endpoint sau khi gom hai route word-list review vào module review:

| Method | URL |
| --- | --- |
| GET | `/lessons` |
| POST | `/lessons/from-youtube` |
| GET | `/lessons/resume` |
| GET | `/lessons/{lesson_slug}` |
| GET | `/lessons/{lesson_slug}/progress` |
| PUT | `/lessons/{lesson_slug}/progress` |
| POST | `/lessons/{lesson_slug}/sessions` |
| POST | `/sentences/submit` |
| POST | `/lessons/complete` |
| DELETE | `/lessons/{lesson_slug}` |
| GET | `/vocabulary/books` |
| GET | `/vocabulary/books/{book_slug}/topics` |
| GET | `/vocabulary/books/{book_slug}/topics/{topic_slug}/words` |
| GET | `/vocabulary/topics/{topic_slug}/words` |
| GET | `/review/today` |
| GET | `/review/queue` |
| POST | `/review/words/{vocabulary_id}/check` |
| POST | `/review/words/{vocabulary_id}/cloze` |
| POST | `/review/words/{vocabulary_id}` |
| POST | `/review/sessions` |
| GET | `/review/sessions/{session_id}` |
| POST | `/review/sessions/{session_id}/attempts` |
| POST | `/review/sessions/{session_id}/complete` |
| POST | `/word-lists` |
| GET | `/word-lists` |
| POST | `/word-lists/{word_list_id}/words` |
| GET | `/word-lists/{word_list_id}/words` |
| GET | `/dictionary/word/{word}` |
| POST | `/engagement/activity` |
| GET | `/engagement/summary` |
| GET | `/engagement/activity` |
| GET | `/preferences` |
| PUT | `/preferences` |

Swagger tại `/api/v1/docs` thể hiện path, query, body và response mới. Hai endpoint chung `/review/queue` và `/review/words/{vocabulary_id}` có response union để bảo toàn response cũ của từng luồng. Không có migration database trong đợt đổi URL này.
