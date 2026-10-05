# Đối chiếu Parroto với LEnglish: API, database và tính năng

Ngày khảo sát: 06/10/2026. Trạng thái: bản khảo sát và thiết kế, chưa triển khai thay đổi runtime hoặc migration.

## 1. Bằng chứng cập nhật sau khi kiểm tra lại

Bản kiểm tra chi tiết ngày 06/10/2026 nằm tại [bảng đối chiếu 35 API LEnglish](parroto-audit/comparison.md) và [inventory 213 cặp method/path Parroto](parroto-audit/endpoint-inventory.md). Các kết luận dưới đây thay thế khảo sát sơ bộ trước đó.

- Đã đọc manifest 78 mục trang và 208 JavaScript asset công khai, gồm các chunk tải bổ sung.
- API base được client khai báo: `https://api.parroto.app/api`.
- Đã thử 51 GET không đăng nhập: 16 HTTP 200, 35 HTTP 401. Xem [log kiểm tra](parroto-audit/http-read-checks.json). Không gửi request ghi.
- Method/path trong service client được phân biệt với URL factory/cache key. Không suy luận phương thức chỉ từ tên URL.
- Không thể liệt kê các endpoint admin/mobile/server-only không lộ trong client. Không xác định được source backend, tên database, bảng, thuật toán SRS/chấm điểm của Parroto.
- LEnglish được đối chiếu từ source workspace, gồm thay đổi chưa commit; không phải schema của database đang chạy.
- Phần vocabulary vẫn thiết kế theo hướng UI SEnglish; chưa khảo sát API backend SEnglish.

## 2. Endpoint Parroto liên quan trực tiếp tới core learning

Path tương đối với base API nêu trên. Chi tiết source, query/payload và mức kiểm tra nằm trong inventory mới.

| Chức năng | Endpoint thực tìm thấy trong service client |
| --- | --- |
| Danh sách / bài hằng ngày / gợi ý | `GET /lessons`, `/lessons/daily`, `/lessons/suggest` |
| Chấm dictation / shadowing | `POST /sentences/submit`, `/sentences/submit-shadowing` |
| Hoàn thành / reset bài | `POST /lessons/complete`, `/lessons/reset` |
| Tiến độ bài | `GET /lessons/progress`, `GET /user/completed-sentences/{id}`, `POST /user/lesson-progress` |
| Ôn câu | `GET /sentences/review`, `POST /sentences/review/submit`, `/submit-shadowing` |
| Catalog bộ từ | `GET /vocabulary/enc/public`, `GET /vocabulary/enc/public/{id}`, `GET /vocabulary/enc/public/by-slug/{slug}` |
| Nhóm / thẻ | `GET /vocabulary/enc/public/{deck_id}/groups`, `GET /vocabulary/enc/public/{deck_id}/groups/{group_id}/cards` |
| Từ mới / đến hạn | `GET /learning-vocabulary/enc/new`, `/learning-vocabulary/enc/due` |
| Nộp ôn từ / thống kê | `POST /learning-vocabulary/submit`, `GET /learning-vocabulary/stats` |
| Phiên ôn / lịch sử / tiến độ nhóm | `POST /learning-vocabulary/session/start`, `GET /learning-vocabulary/session/current`, `/session/history`, `/groups-progress/{id}` |
| Từ lưu nhanh | `GET/POST /user/vocabulary-review`, `DELETE /user/vocabulary-review/{id}` |
| Bộ từ tự tạo | CRUD `/user/vocabulary/decks`, `/user/vocabulary/groups`, `/user/vocabulary/cards` |
| Từ điển | `GET /dictionary/search?word=...&locale=...`, `GET /dictionary/word/{word}` |
| Thời gian / streak / level | `POST /learning-time/start`, `/heartbeat`, `/end`; `GET /streak`, `/streak/calendar`, `/level` |
| Đề thi / leaderboard | `GET /exams/published/sets`, `/exams/published/{id}`; `/leaderboard/home`, `/leaderboard/monthly` |

`/vocabulary/decks`, `/vocabulary/deck/...` và `/learning-vocabulary/cards/new|due` được thấy như URL factory/cache key; không thay thế route service `enc` ở bảng trên. Settings UI Parroto phần lớn ở localStorage `parroto-app-config`; chưa thấy API `/preferences` riêng. Endpoint fetch chi tiết curated lesson phía server không lộ trong source client; giữ endpoint chi tiết/resume/session/progress LEnglish.

## 3. LEnglish đã có gì và cần bổ sung gì

Prefix hiện tại: `/api/v1`. Giữ hợp đồng API đang dùng; tương đương chức năng không đòi hỏi tên đường dẫn giống Parroto.

| Feature | Nền tảng đã có trong LEnglish | Khoảng thiếu / bước tiếp theo |
| --- | --- | --- |
| Duyệt bài học | `GET /lessons`, `GET /lessons/{lesson_slug}`; search, phân trang, lượt xem, cấp độ | Thêm API danh mục/tag và bộ lọc chính xác theo danh mục, tag, cấp độ |
| Import YouTube | `POST /lessons/import/youtube`, chỉ admin; subtitle có mốc thời gian | Giữ luồng admin; tạo bài cá nhân cần thiết kế quyền sở hữu và trạng thái riêng |
| Dictation | Session, answer, điểm tương đồng văn bản và số lần trả lời | Bổ sung phản hồi theo từ; xác định chính sách dấu câu và hoàn thành bài |
| Học tiếp | `GET /lessons/resume`; GET/PUT progress | Nối FE với API thật |
| Shadowing | Enum `shadowing`, dùng chung bài và transcript | Chưa có endpoint nhận audio/chấm phát âm; chấm chuỗi văn bản hiện tại không phải chấm phát âm |
| Từ vựng theo bộ | `VocabularyBook`, `VocabularyTopic`, `VocabularyTopicWord`; API books/topics/words | Đã có cấu trúc tương đương deck/group/card; không cần đổi tên sang thuật ngữ Parroto |
| SRS từ vựng | `ReviewProgress`, attempt, queue, session, typing, cloze, rating | Nối FE; bổ sung resume phiên nếu có yêu cầu sản phẩm |
| Sổ từ cá nhân | `WordList`, `WordListItem`, lưu ngữ cảnh và source subtitle | Đã có lưu từ và due review; tái sử dụng cùng `ReviewProgress` |
| Ôn câu nghe sai | Có `Subtitle` và `LessonAnswer` | Chưa có queue/SRS cho câu; thiết kế riêng với SRS từ vựng |
| Thời gian và streak | `POST /engagement/activity`, GET summary/activity, preferences timezone | Dùng cơ chế event chống ghi trùng hiện có; chưa cần đổi sang start/heartbeat/end |
| Hội thoại | Có model `Scenario`, `Conversation`, `Message` dành cho AI | Chưa thấy router/service hội thoại; chat AI khác chat giữa hai người |
| Leaderboard, quà, điểm | Có cột XP và model achievement/streak | Chưa có nghiệp vụ XP, leaderboard, ví điểm hoặc đổi quà |
| TOEIC/IELTS mock test | Chưa thấy module exams | Thiết kế đề, phần, câu hỏi, attempt và chấm điểm riêng; không coi lesson quiz là đề thi đầy đủ |
| Thông báo | Có model `Notification` | Chưa thấy router thông báo |

FE hiện tại `FE/app/screens/Dashboard.tsx` đọc từ `../mocks/home` và nhiều nút mở modal xem trước. Chỉ sửa backend sẽ chưa làm dashboard hiển thị dữ liệu thật; bước nối FE là một hạng mục riêng cần thực hiện.

## 4. Hợp đồng API đề xuất cho đợt đầu

Các endpoint ghi rõ **mới** hoặc **mở rộng** dưới đây chưa được triển khai. Toàn bộ đường dẫn tương đối với `/api/v1`.

| Endpoint LEnglish | Trạng thái | Mục đích |
| --- | --- | --- |
| `GET /lessons/categories` | Mới | Danh mục active, slug, thứ tự, số bài published trực tiếp trong từng danh mục |
| `GET /lessons/tags` | Mới | Tag với `type=topic/skill/accent/source/grammar`; trả số bài published |
| `GET /lessons?category_slug=...&difficulty=B1&tag_slug=...` | Mở rộng | Kết hợp bộ lọc AND với keyword, page/page_size và sort hiện có |
| `GET /lessons/{lesson_slug}` | Đã có | Nội dung và timed transcript |
| `GET /lessons/resume` | Đã có | Bài gần nhất chưa hoàn thành |
| `POST /lessons/{lesson_slug}/sessions` | Đã có | Tạo session theo mode |
| `POST /lessons/{lesson_slug}/sessions/{session_id}/answers` | Mở rộng | Giữ trường cũ; bổ sung danh sách token đúng/sai/thiếu/thừa nếu cần |
| `POST /lessons/{lesson_slug}/sessions/{session_id}/complete` | Đã có; cần chốt semantics | Kết thúc session; không đồng nhất kết thúc session với đủ điều kiện hoàn thành bài |
| `GET/PUT /lessons/{lesson_slug}/progress` | Đã có | Vị trí học và tiến độ cá nhân |
| `GET /vocabulary/books` | Đã có | Bộ từ vựng |
| `GET /vocabulary/books/{book_slug}/topics` | Đã có | Nhóm từ và tiến độ cá nhân |
| `GET /vocabulary/books/{book_slug}/topics/{topic_slug}/words` | Đã có | Từ của nhóm |
| `GET /review/today` | Đã có | Số từ đến hạn và mục tiêu từ mới |
| `POST /review/books/{book_slug}/topics/{topic_slug}/sessions` | Đã có | Bắt đầu ôn |
| `GET /review/sessions/{session_id}` | Đã có | Đọc session của user hiện tại |
| `POST /review/sessions/{session_id}/attempts` | Đã có | Nộp câu trả lời / rating |
| `GET/POST /word-lists` | Đã có | Sổ từ cá nhân |
| `POST /word-lists/{word_list_id}/words` | Đã có | Lưu từ trong bài học |
| `GET /word-lists/{word_list_id}/review/due` | Đã có | Từ đã lưu đến hạn ôn |
| `POST /engagement/activity` | Đã có | Gửi batch thời gian học mới phát sinh với `event_id` |
| `GET /engagement/summary` | Đã có | Mục tiêu, phút học, bài hoàn thành, streak |
| `GET /engagement/activity?days=90` | Đã có | Heatmap và lịch sử |

API danh mục/tag nên nằm trước `/{lesson_slug}` trong router để tránh bị bắt thành slug. Đợt đầu giữ yêu cầu đăng nhập đang có; nếu muốn duyệt catalog không đăng nhập, cần tách router và kiểm tra quyền với nội dung draft/private riêng.

Mẫu **response đề xuất**, không phải response của Parroto:

```json
{
  "data": [
    {
      "id": 1,
      "name": "Daily English Conversation",
      "slug": "daily-english-conversation",
      "parent_id": null,
      "display_order": 1,
      "lesson_count": 12
    }
  ]
}
```

Semantics bộ lọc: `difficulty` dùng enum A1–C2; category/tag là slug chính xác; slug không tồn tại trả danh sách rỗng; dữ liệu và `metadata.total/pages` dùng cùng điều kiện lọc; tag join không được nhân bản bài. Giữ `sort_order=ascend/descend` hiện có để không làm hỏng caller cũ.

## 5. Tên DB, bảng và ranh giới module

### Với database LEnglish hiện có

Không cần đổi tên DB để có tính năng tương tự. README đang dùng ví dụ `learn-english`; tên DB chạy thật chưa được đọc. Nếu tạo môi trường mới có thể dùng `learn_english`, nhưng thay `DB_NAME` không tự đổi tên database đang tồn tại.

Model hiện tại sử dụng tên bảng PascalCase và cột snake_case. Nên giữ quy ước đó trong đợt bổ sung đầu tiên:

| Module | Bảng đã có |
| --- | --- |
| user / token / preferences | `User`, `UserRole`, `Token`, `UserPreferences` |
| lesson | `Category`, `Tag`, `Lesson`, `LessonTag`, `Subtitle`, `LessonProgress`, `LessonSession`, `LessonAnswer` |
| vocabulary | `Vocabulary`, `VocabularyBook`, `VocabularyTopic`, `VocabularyTopicWord` |
| wordlist | `WordList`, `WordListItem` |
| review | `ReviewProgress`, `ReviewAttempt`, `ReviewSession`, `ReviewSessionItem` |
| engagement | `ActivityEvent`, `Streak`, `Achievement`, `AchievementUnlock` |
| conversation | `Scenario`, `Conversation`, `Message` |
| dictionary / feedback / notifications | `DictionaryLookup`, `Feedback`, `FeedbackAttachment`, `Notification` |

Class Python tiếp tục PascalCase; module/folder snake_case; tài nguyên API dùng danh từ và quy ước hiện tại như `/word-lists`. Giữ `created_time/updated_time` đang dùng. Không tạo bảng khác chỉ vì URL dùng thuật ngữ khác: `VocabularyBook` có thể phục vụ UI gọi là deck, `Subtitle` có thể phục vụ UI gọi là sentence.

Nếu quyết định chuẩn hóa toàn bộ DB về tên chữ thường, có thể đặt `users`, `lessons`, `lesson_categories`, `lesson_tags`, `lesson_tag_links`, `lesson_subtitles`, `lesson_progress`, `lesson_sessions`, `lesson_answers`, `vocabulary_books`, `vocabulary_topics`, `vocabulary_topic_words`, `word_lists`, `word_list_items`, `review_progress`, `review_attempts`, `review_sessions`, `review_session_items`, `activity_events`. Đây là một migration đổi tên có phạm vi riêng: cần cập nhật `__tablename__`, foreign keys, SQL thủ công, index/constraint và kiểm thử trên bản sao dữ liệu. Không trộn việc này vào bổ sung feature đầu tiên và không drop/create bảng để đổi tên.

### Bảng mới chỉ khi triển khai feature tương ứng

Các tên sau là đề xuất theo quy ước LEnglish hiện tại, không phải tên bảng của Parroto:

| Feature | Bảng / khóa đề xuất | Ranh giới |
| --- | --- | --- |
| Ôn câu nghe sai | `SentenceReviewProgress` unique `(user_id, subtitle_id, mode)`; `SentenceReviewAttempt` có request ID chống trùng | `review`; tách SRS câu với SRS từ |
| Chấm shadowing | `PronunciationAttempt` liên kết lesson session + subtitle; audio object key, trạng thái, điểm và feedback | Module `pronunciation`; dùng bài/transcript từ `lesson` |
| Đề thi | `ExamSet`, `Exam`, `ExamPart`, `ExamQuestion`, `ExamAttempt`, `ExamAnswer`; unique attempt/question | Module `exam`; đáp án đúng không nằm trong response câu hỏi đang thi |
| Chat giữa người học | `ChatConversation`, `ChatParticipant`, `ChatMessage` | Module `chat`; không dùng nhầm model Message của hội thoại AI |
| XP / leaderboard | `XpTransaction` với event ID chống trùng và điểm do server cấp | `engagement`; bảng xếp hạng tổng hợp từ giao dịch |
| Gói trả phí | `SubscriptionPlan`, `UserSubscription` | Module `billing`; chỉ thêm khi đã chốt nhu cầu trả phí |

Ví dụ `SentenceReviewProgress` cần `user_id`, `subtitle_id`, `mode`, `next_review_at`, `last_reviewed_at`, `interval_days`, `repetition_count`, `ease_factor`. Đây là lựa chọn thiết kế SRS, không suy luận thuật toán của Parroto.

## 6. Thứ tự triển khai và kiểm chứng

1. **Catalog bài học:** API category/tag và bộ lọc; tái sử dụng bảng hiện có, không cần migration nếu chỉ đọc. Kiểm tra active/published, AND filters, pagination, không trùng bài, slug không tồn tại và route không bị nuốt bởi `/{lesson_slug}`.
2. **Nối dashboard với API:** thay mock cho lessons/resume/summary/activity/review today. Kiểm tra dữ liệu user hiện tại, loading/empty/error, session hết hạn. Không cần đổi giao diện để thực hiện bước này.
3. **Hoàn thiện dictation:** chốt quy tắc so đáp án, feedback từng từ, tính completion và idempotency nộp bài. Session hoàn thành hiện chưa tự cập nhật LessonProgress trong `complete_session`; cần chốt một nguồn dữ liệu thống nhất trước khi sửa.
4. **Ôn câu sai:** migration additive cho sentence review, queue và grading. Kiểm tra cách thêm lại câu sai, quyền sở hữu, ngày đến hạn và request retry.
5. **Shadowing:** chọn dịch vụ chấm phát âm, giới hạn file/thời lượng, lưu audio và trạng thái xử lý. Kiểm tra audio thật, lỗi nhà cung cấp, quyền session và không nhận điểm tự khai từ FE. Việc khai báo mode hoặc nhận transcript chưa đủ để có chấm phát âm.
6. **Exam / social / gamification:** làm từng module sau khi chốt quy tắc nghiệp vụ; migration và kiểm thử tương ứng.

Đợt có kết quả sớm nhất: catalog + nối dashboard + dictation + từ vựng/SRS đang có. Các endpoint Parroto phục vụ làm tham chiếu luồng sản phẩm; hợp đồng API, dữ liệu và nghiệp vụ triển khai trên LEnglish thuộc dự án này.
