# Kiểm tra lại endpoint Parroto và đối chiếu LEnglish

Ngày: 06/10/2026. Đây là báo cáo khảo sát, chưa thay đổi API runtime hay database.

## Phạm vi và mức xác minh

- Đọc manifest của **78 mục trang** và **208 asset JavaScript công khai** (gồm chunk tải bổ sung), trong web build `PI7un_8VTrLhTgj2L-BVI` của [Parroto](https://parroto.app/).
- Chuẩn hóa thành **213 cặp method + path template** từ các service HTTP tìm thấy. Đây là inventory của client web được khảo sát, **không phải cam kết tất cả endpoint backend**: admin, mobile, server-only và code không được publish không thể liệt kê đầy đủ từ web client.
- Base API Parroto: `https://api.parroto.app/api`; LEnglish: `/api/v1`. Path trong bảng đã bỏ base/prefix cho dễ đối chiếu.
- Đã gửi **51 GET không đăng nhập**: **16 HTTP 200, 35 HTTP 401**. 401 chỉ xác minh chốt xác thực của request; không chứng minh query/payload/response nghiệp vụ đúng. HTTP 200 của envelope mã hóa cũng không xác minh schema đã giải mã.
- POST/PUT/PATCH/DELETE: method và route được xác nhận từ source client, **chưa gọi để kiểm tra nghiệp vụ**. Không có tài khoản/token được cung cấp cho khảo sát.
- `{id}` trong inventory là placeholder chuẩn hóa từ biến minify, không khẳng định ID dạng UUID/int. Với nhiều ID, đọc ghi chú hoặc biểu thức source; bảng đối chiếu dùng đúng placeholder của LEnglish.
- Đối chiếu đủ **35 API LEnglish hiện có**, trừ user/feedback/token, dựa trên source workspace hiện tại, gồm cả thay đổi chưa commit. Endpoint Parroto có prefix `/user` nhưng phục vụ từ vựng/tiến độ vẫn được dùng làm tham chiếu chức năng; quản lý account không nằm trong phạm vi đề xuất sửa.
- Vocabulary: hướng sản phẩm vẫn theo [SEnglish](https://senglish.net/app/vocabulary); **chưa xác minh API backend của SEnglish**, các đề xuất dưới đây là thiết kế LEnglish dựa trên UI mong muốn.

## Những kết luận thay thế bảng cũ

1. Catalog từ thực dùng `GET /vocabulary/enc/public`, detail by ID/by slug, groups và cards. Các `/vocabulary/decks`, `/vocabulary/deck/...` cũ là URL factory/cache-key tham chiếu, không đủ bằng chứng để gọi là service HTTP hiện dùng.
2. Học từ mới/đến hạn thực dùng `GET /learning-vocabulary/enc/new` và `/enc/due`, không phải chỉ `/cards/new` và `/cards/due`.
3. Từ điển đã thấy `GET /dictionary/search` và `GET /dictionary/word/{word}`. Không còn ghi chung là chưa khảo sát.
4. Đã thấy các service streak, level, missions, notes, community lessons, custom deck, exam, social, shop và affiliate; inventory đính kèm có từng route và source.
5. Chưa thấy service HTTP chi tiết curated lesson, start lesson session, lưu vị trí video hoặc `/preferences` trong client. Với trang Next dựng sẵn, endpoint được server dùng để lấy pageProps **không lộ trong source client**. Không thể kết luận backend không có.
6. Không xác định được tên database/tables backend Parroto. Không cần đổi DB hoặc bảng LEnglish chỉ để đổi cách đặt URL.

## Bảng đối chiếu từng API LEnglish

P1: đợt ưu tiên đầu; P2: đợt sau; P3: tùy nhu cầu. “Giữ” nghĩa là chức năng/hợp đồng hiện có hợp lý, không cần đổi URL. Link Pxxx trỏ tới method, source và mức kiểm tra Parroto cụ thể.

| # | API LEnglish hiện có | API Parroto đối chiếu | Khác biệt / bằng chứng | Hướng sửa dần |
| --- | --- | --- | --- | --- |
| 1 | `GET /lessons` | `GET /lessons` ([P093](endpoint-inventory.md#p093)) | Cùng catalog; LEnglish dùng keyword/page_size, Parroto dùng title/topic_slug/difficulty/limit. | P1: Giữ URL; thêm category_slug/tag_slug/difficulty, thống nhất metadata phân trang. |
| 2 | `POST /lessons/import/youtube` | `POST /community-lessons/from-youtube` ([P019](endpoint-inventory.md#p019)) | LEnglish chỉ admin; Parroto là bài cộng đồng với quota/mine/submit/retry. | P3: Giữ import admin; chỉ thêm bài cá nhân khi cần owner/quota/trạng thái duyệt. |
| 3 | `GET /lessons/resume` | `GET /lessons/progress` ([P098](endpoint-inventory.md#p098))<br>`POST /user/lesson-progress` ([P170](endpoint-inventory.md#p170)) | Chỉ tương đương một phần: Parroto đọc tiến độ bài; chưa thấy API riêng trả bài gần nhất và vị trí video. | Giữ resume; nối FE. Không đổi sang progress chỉ vì tên gần giống. |
| 4 | `GET /lessons/{lesson_slug}` | Không tìm thấy counterpart HTTP trong client đã đọc | Không tìm thấy service HTTP chi tiết bài curated tương ứng; frontend dùng trang Next tạo sẵn/pageProps. Không thấy source server fetch. | Giữ endpoint chi tiết + transcript. Không bịa GET /lessons/{slug} của Parroto. |
| 5 | `GET /lessons/{lesson_slug}/progress` | `GET /user/completed-sentences/{id}` ([P166](endpoint-inventory.md#p166))<br>`GET /lessons/progress` ([P098](endpoint-inventory.md#p098)) | Parroto đọc câu hoàn thành/tiến độ chủ đề; LEnglish lưu vị trí phát và subtitle. | Giữ. Có thể bổ sung tỷ lệ/câu hoàn thành; không gộp vị trí video với completion. |
| 6 | `PUT /lessons/{lesson_slug}/progress` | Không tìm thấy counterpart HTTP trong client đã đọc | Chưa tìm thấy service tương đương lưu vị trí xem trong client đã khảo sát. | Giữ; FE cập nhật khi dừng/rời bài, chống ghi lùi do request trễ. |
| 7 | `POST /lessons/{lesson_slug}/sessions` | Không tìm thấy counterpart HTTP trong client đã đọc | Chưa tìm thấy API start session cho dictation/shadowing curated; Parroto nộp câu trực tiếp. | Giữ session để quản lý lịch sử/mode; không bỏ vì Parroto không lộ start API. |
| 8 | `POST /lessons/{lesson_slug}/sessions/{session_id}/answers` | `POST /sentences/submit` ([P152](endpoint-inventory.md#p152))<br>`POST /sentences/submit-shadowing` ([P153](endpoint-inventory.md#p153)) | LEnglish chấm chuỗi text (equality + similarity); enum shadowing hiện chưa nhận/chấm audio. Parroto có 2 luồng nộp câu, body qua {data: ...}. | P1: Hoàn thiện dictation feedback theo từ. P2: API nhận audio/chấm phát âm riêng; giữ answer theo session. |
| 9 | `POST /lessons/{lesson_slug}/sessions/{session_id}/complete` | `POST /lessons/complete` ([P096](endpoint-inventory.md#p096)) | Kết thúc session LEnglish chưa tự cập nhật LessonProgress; hoàn thành bài Parroto là thao tác riêng. | P1: Chốt điều kiện hoàn thành bài, đồng bộ progress/completed_at và chống retry trùng. Giữ URL. |
| 10 | `DELETE /lessons/{lesson_slug}` | `DELETE /community-lessons/{id}` ([P024](endpoint-inventory.md#p024)) | Không cùng tài nguyên/quyền: LEnglish xóa catalog admin; Parroto xóa bài cộng đồng. | Giữ quyền admin; nếu thêm bài cá nhân phải kiểm tra owner. |
| 11 | `GET /vocabulary/books` | `GET /vocabulary/enc/public` ([P200](endpoint-inventory.md#p200)) | Book ↔ deck về vai trò catalog. LEnglish thiếu thống kê học/đến hạn/thành thạo ở mức book và lọc category rõ ràng. | P1 SEnglish: Giữ books; bổ sung category và thống kê/progress trên card bộ từ. |
| 12 | `GET /vocabulary/books/{book_slug}/topics` | `GET /vocabulary/enc/public/{id}/groups` ([P204](endpoint-inventory.md#p204))<br>`GET /learning-vocabulary/groups-progress/{id}` ([P087](endpoint-inventory.md#p087)) | Topic ↔ group. LEnglish trả count tiến độ cùng topic; Parroto có catalog nhóm và API progress riêng. | P1 SEnglish: Giữ topics và count; kiểm tra join ReviewProgress để chủ đề chưa học vẫn hiện. |
| 13 | `GET /vocabulary/books/{book_slug}/topics/{topic_slug}/words` | `GET /vocabulary/enc/public/{id}/groups/{id}/cards` ([P205](endpoint-inventory.md#p205)) | Word ↔ card về nội dung. Parroto dùng IDs; LEnglish dùng slug và Vocabulary ID. | Giữ URL; hoàn thiện nghĩa/IPA/audio/ví dụ và trạng thái SRS theo nhu cầu giao diện. |
| 14 | `GET /vocabulary/topics/{topic_slug}/words` | `GET /vocabulary/enc/public/{id}/groups/{id}/cards` ([P205](endpoint-inventory.md#p205)) | Shortcut LEnglish không cần book_slug; không có counterpart một-một trong service catalog Parroto. | Giữ alias nếu FE dùng; chuẩn hóa cùng response với route đầy đủ. |
| 15 | `GET /review/today` | `GET /learning-vocabulary/stats` ([P091](endpoint-inventory.md#p091))<br>`GET /learning-vocabulary/enc/due` ([P084](endpoint-inventory.md#p084))<br>`GET /learning-vocabulary/enc/new` ([P085](endpoint-inventory.md#p085)) | Today LEnglish thiên về số đến hạn/mục tiêu; Parroto tách thống kê và 2 hàng đợi. | P1 SEnglish: Thêm learned/due/mastered; thêm GET /review/queue toàn bộ books cho nút Ôn ngay. Đây là đề xuất mới. |
| 16 | `GET /review/books/{book_slug}/topics/{topic_slug}/queue` | `GET /learning-vocabulary/enc/new` ([P085](endpoint-inventory.md#p085))<br>`GET /learning-vocabulary/enc/due` ([P084](endpoint-inventory.md#p084)) | LEnglish queue trong 1 topic; Parroto tách new/due và nhận query object. Chưa xác minh toàn bộ query runtime. | Giữ queue theo topic; mở rộng lọc status=new/due và bổ sung queue toàn cục, không cần đổi sang đường dẫn enc. |
| 17 | `POST /review/books/{book_slug}/topics/{topic_slug}/words/{vocabulary_id}/check` | `POST /learning-vocabulary/submit` ([P092](endpoint-inventory.md#p092)) | LEnglish endpoint chấm typing riêng; Parroto wrapper submitReview chung. Chưa chứng minh cùng rating/thuật toán. | P1: Chuẩn hóa response correct/feedback/next_review_at; tiến tới 1 contract attempt có mode nếu hợp lý. |
| 18 | `POST /review/books/{book_slug}/topics/{topic_slug}/words/{vocabulary_id}/cloze` | `POST /learning-vocabulary/submit` ([P092](endpoint-inventory.md#p092)) | LEnglish chấm cloze riêng; Parroto không lộ endpoint cloze riêng trong service đã đọc. | Giữ cloze. Đừng xóa feature chỉ để khớp URL; có thể chung xử lý với attempt. |
| 19 | `POST /review/words/{vocabulary_id}` | `POST /learning-vocabulary/submit` ([P092](endpoint-inventory.md#p092)) | LEnglish ghi rating SRS; Parroto submit review. Tương đương mục đích, chưa xác minh thuật toán. | P1 SEnglish: Giữ again/hard/good/easy; thống nhất chống ghi trùng và quyền sở hữu với attempts. |
| 20 | `POST /review/books/{book_slug}/topics/{topic_slug}/sessions` | `POST /learning-vocabulary/session/start` ([P090](endpoint-inventory.md#p090)) | Cùng bắt đầu ôn. Session LEnglish cố định topic; schema start Parroto được caller truyền vào. | P1 SEnglish: Giữ; thêm session tổng hợp due từ nhiều bộ cho Ôn ngay. |
| 21 | `GET /review/sessions/{session_id}` | `GET /learning-vocabulary/session/current` ([P088](endpoint-inventory.md#p088)) | LEnglish đọc phiên theo ID; Parroto đọc phiên hiện tại. | P2: Có thể thêm GET /review/sessions/current để resume; đặt route trước /{session_id}. |
| 22 | `POST /review/sessions/{session_id}/attempts` | `POST /learning-vocabulary/submit` ([P092](endpoint-inventory.md#p092)) | LEnglish có attempt_id chống retry; Parroto submitReview không để session ID trong path. | Giữ attempts; hợp nhất quy tắc rating/chấm với các endpoint check/cloze/review hiện có. |
| 23 | `POST /review/sessions/{session_id}/complete` | Không tìm thấy counterpart HTTP trong client đã đọc | Không thấy wrapper HTTP session/complete của learning-vocabulary; không suy ra rằng backend không có. | Giữ hoàn thành phiên. P2: thêm lịch sử tương ứng GET /learning-vocabulary/session/history nếu sản phẩm cần. |
| 24 | `POST /word-lists` | `POST /user/vocabulary/decks` ([P185](endpoint-inventory.md#p185)) | Tương đương một phần: list từ đã lưu LEnglish khác deck tự biên soạn Parroto có group/card/publish. | Giữ word-lists cho lưu từ trong bài; custom deck là feature riêng, chưa cần tách vội. |
| 25 | `GET /word-lists` | `GET /user/vocabulary/decks` ([P184](endpoint-inventory.md#p184))<br>`GET /user/vocabulary-review` ([P176](endpoint-inventory.md#p176)) | Parroto tách deck cá nhân và từ lưu nhanh; LEnglish dùng list có ngữ cảnh. | Giữ; bổ sung word_count/due_count nếu FE cần. |
| 26 | `POST /word-lists/{word_list_id}/words` | `POST /user/vocabulary-review` ([P177](endpoint-inventory.md#p177))<br>`POST /user/vocabulary/cards` ([P179](endpoint-inventory.md#p179)) | Từ lưu nhanh ↔ vocabulary-review; thẻ tự tạo ↔ vocabulary/cards. LEnglish lưu context và subtitle nguồn. | Giữ ngữ cảnh. P2: thêm xóa item/chuyển list/chống lưu trùng; không coi hai chức năng Parroto là một. |
| 27 | `GET /word-lists/{word_list_id}/words` | `GET /user/vocabulary-review` ([P176](endpoint-inventory.md#p176))<br>`GET /user/vocabulary/groups/{id}/cards` ([P196](endpoint-inventory.md#p196)) | LEnglish lọc list; Parroto lưu nhanh phân trang hoặc card theo group. | Giữ; kiểm tra pagination/search trên danh sách lớn. |
| 28 | `POST /word-lists/{word_list_id}/words/{vocabulary_id}/review` | `POST /learning-vocabulary/submit` ([P092](endpoint-inventory.md#p092)) | LEnglish tái sử dụng ReviewProgress cho từ trong list; Parroto luồng học từ qua submitReview. | Giữ cùng SRS với books; tránh 2 lịch ôn cho cùng vocabulary_id. |
| 29 | `GET /word-lists/{word_list_id}/review/due` | `GET /learning-vocabulary/enc/due` ([P084](endpoint-inventory.md#p084)) | LEnglish due theo list; Parroto due endpoint chung nhận query. | Giữ; queue tổng hợp cần bao gồm saved words và loại bỏ từ trùng. |
| 30 | `GET /dictionary/lookup` | `GET /dictionary/search` ([P035](endpoint-inventory.md#p035))<br>`GET /dictionary/word/{id}` ([P036](endpoint-inventory.md#p036)) | LEnglish lookup?word=...; Parroto search gợi ý và chi tiết word tách riêng. Search 200, detail hello 401. | P2: Giữ lookup; thêm GET /dictionary/search?word=...&locale=... nếu cần autocomplete. |
| 31 | `POST /engagement/activity` | `POST /learning-time/start` ([P077](endpoint-inventory.md#p077))<br>`POST /learning-time/heartbeat` ([P076](endpoint-inventory.md#p076))<br>`POST /learning-time/end` ([P075](endpoint-inventory.md#p075)) | LEnglish batch event_id chống trùng; Parroto session/sequence/delta_seconds. | Giữ batch hiện có. Nối FE với thời gian active, không cần đổi thành 3 API. |
| 32 | `GET /engagement/summary` | `GET /user/stats` ([P173](endpoint-inventory.md#p173))<br>`GET /streak` ([P158](endpoint-inventory.md#p158))<br>`GET /level` ([P103](endpoint-inventory.md#p103))<br>`GET /learning-vocabulary/stats` ([P091](endpoint-inventory.md#p091)) | LEnglish tổng hợp goal/phút học/completion/streak; Parroto tách nhiều service. | Giữ summary; P2 bổ sung XP/level khi có nghiệp vụ cấp điểm phía server. |
| 33 | `GET /engagement/activity` | `GET /streak/calendar` ([P159](endpoint-inventory.md#p159)) | LEnglish query days và timezone preferences; Parroto from/to. | Giữ heatmap; thêm from/to nếu cần khoảng ngày tùy chọn, thống nhất timezone. |
| 34 | `GET /preferences` | Không tìm thấy counterpart HTTP trong client đã đọc | UI settings Parroto chủ yếu ở localStorage parroto-app-config; một số setting học theo hồ sơ PUT /user/info. Không có service /preferences tương ứng tìm thấy. | Giữ đồng bộ goal/new words/timezone trên BE. UI playback/tooltip có thể lưu local. |
| 35 | `PUT /preferences` | Không tìm thấy counterpart HTTP trong client đã đọc | Không có API preferences riêng tìm thấy; không thể coi localStorage là endpoint backend. | Giữ và mở rộng có chọn lọc. Không đổi sang user/info chỉ để giống Parroto. |

## Feature Parroto có API mà LEnglish chưa có router tương ứng

Các endpoint LEnglish ở cột cuối là **đề xuất mới**, chưa triển khai. Chọn theo nhu cầu, không cần sao chép toàn bộ hệ thống Parroto.

| Feature | Parroto đã xác nhận ở client | LEnglish hiện tại | Hướng thêm |
| --- | --- | --- | --- |
| Bài hằng ngày / gợi ý tiếp theo | `GET /lessons/daily`, `GET /lessons/suggest?lesson_id=...` | Chưa có route riêng | P1: `/lessons/daily`, `/lessons/{lesson_slug}/suggestions` nếu dashboard cần |
| Reset bài | `POST /lessons/reset` với lesson_id/type | Chưa có route reset | P2: `POST /lessons/{lesson_slug}/reset`, phân biệt reset progress với xóa lịch sử |
| Ôn câu sai | `GET /sentences/review`, `POST /sentences/review/submit`, `/submit-shadowing` | Có answer nhưng chưa có queue/SRS câu | P2: `/review/sentences/queue`, `/review/sentences/{subtitle_id}/attempts` |
| Chấm phát âm | `POST /sentences/submit-shadowing`; nhiệm vụ có `POST /missions/shadowing/submit` multipart | Mode shadowing chưa phải audio grading | P2: `/lessons/{lesson_slug}/sessions/{session_id}/pronunciation-attempts` |
| Ghi chú câu / báo lỗi nội dung | `/sentence-notes`, `/sentence-errors`, `/vocabulary-errors` | Chưa có router chuyên biệt trong phạm vi hiện có | P2: notes gắn subtitle; content report tách khỏi chấm bài |
| Bài YouTube cá nhân / shorts | `/community-lessons/from-youtube`, `/mine`, `/quota`, `/{id}/submit`, `/{id}/retry`, `/shorts`, `/{id}/transcript` | Chỉ có import admin | P3: module bài cá nhân riêng, owner/status/quota; tận dụng timed subtitle |
| Bình luận bài | `GET/POST /lessons/{id}/comments`, replies, DELETE | Chưa có router | P3: comments + ownership/moderation |
| Quản lý bộ từ tự tạo | CRUD `/user/vocabulary/decks`, `/groups`, `/cards`; publish/unpublish/import | WordList chỉ lưu từ, chưa tương đương authoring deck | P3: custom books/topics/cards riêng nếu cần; giữ word-lists cho saved words |
| Quản lý ôn từ | cards/remove, cards/reset, card/{id}/master, session/history | Có SRS/attempts, thiếu quản lý batch/histories tương ứng | P2: reset/master/history có quyền user và chống duplicate |
| Streak thưởng / XP / ví | `/streak/checkin`, milestones/claim, freeze/buy; `/level`, `/wallet` | Có activity/streak cơ bản, chưa có nghiệp vụ reward | P3: XP transaction do server cấp; không nhận điểm tùy ý từ FE |
| Nhiệm vụ | `/missions/config`, `/today`, `/feed`, submit/claim | Chưa có router | P3: đợi dictation/vocab/engagement ổn định trước |
| Leaderboard | `/leaderboard/home`, `/leaderboard/monthly` | Chưa có router | P3: tổng hợp XP đã xác minh, xác định period/timezone |
| Exams | `/exams/published/sets`, `/exams/published/{id}`, sessions/start/questions/answers/submit/result/history/analytics | Chưa có module exams | P3: module exam riêng; không dùng lesson quiz thay đề thi |
| Notifications | `GET /notifications`, `/stats`, `DELETE /notifications/{id}`, `/read-all` | Có model nhưng chưa có router | P3: thiết kế read/read-all theo semantics rõ ràng; không sao chép DELETE máy móc |
| Voice chat / games / vocab battle | `/voice-chat/topics`, `/games/feed`, `/games/sessions`, `/vocab-battle/leaderboard` | Chưa có router | P3: module riêng; realtime còn có Socket.IO, khác HTTP |
| Diễn đàn / friends / chat | `/posts`, `/friends`, `/community-chat`, `/private-chat` | Model hội thoại AI không tương đương chat cộng đồng | P3: module social/chat riêng, không trộn với AI conversation |
| Shop / payment / affiliate | `/shop`, `/prices`, `/webhooks/sepay`, `/promo`, `/affiliate` | Ngoài core learning hiện có | Chỉ làm khi có yêu cầu bán gói/điểm; không cần trong đợt sửa học tập |

## Thứ tự sửa đề xuất cho LEnglish

1. **Lesson catalog + completion:** giữ URL; thêm filter category/tag/difficulty, nối resume/progress; sửa sự nhất quán giữa complete session và complete bài. Sau đó hoàn thiện dictation feedback.
2. **Vocabulary theo SEnglish:** giữ books/topics/words; trả category và learned/due/mastered/progress; bảo đảm topic chưa học vẫn hiện. Thêm queue toàn cục và session tổng hợp cho Ôn ngay, giữ rating again/hard/good/easy và attempt_id.
3. **Saved words + dictionary:** giữ context/source subtitle và dùng cùng SRS; thêm remove/search/pagination khi cần; thêm dictionary autocomplete.
4. **Ôn câu + shadowing audio:** xây queue câu sai và chấm audio thật. Xác định nhà cung cấp, contract và lưu kết quả; không dùng similarity text làm pronunciation score.
5. **Engagement:** dùng API batch hiện có, nối FE ghi active time/streak/heatmap. XP/leaderboard/missions là đợt riêng.
6. **Exam/social/billing:** chọn module theo nhu cầu sau core learning.

## Cách đọc “chưa xác minh” sau lần kiểm tra này

| Trạng thái | Đã làm gì | Còn thiếu gì |
| --- | --- | --- |
| HTTP 200 | Gửi GET không đăng nhập, nhận response thành công | Chưa bảo đảm đủ schema/luồng tài khoản; envelope mã hóa chưa được giải mã |
| HTTP 401 | Gửi GET thật, server chặn vì thiếu token | Cần phiên đăng nhập hợp lệ để kiểm tra data/query nghiệp vụ |
| Client xác nhận; chưa thử GET route này | Đã đọc method/path thực trong service JS | Chưa gửi GET cụ thể, thường do cần ID hoặc account; không gọi là không xem được |
| Client xác nhận; chưa gửi request ghi | Đã đọc POST/PUT/PATCH/DELETE và wrapper | Chưa kiểm tra nghiệp vụ thực tế trên account |
| URL factory/cache key | Chỉ thấy hàm tạo URL hoặc key | Chưa thấy lời gọi HTTP dùng nó; không suy ra method/route đang hoạt động |
| Không lộ trong client | Đã khảo sát bundle; không thấy service tương ứng | Source backend/server-only không được publish; không thể khẳng định tồn tại/không tồn tại |

## Tệp bằng chứng và bảng đầy đủ

- [Inventory từng endpoint Parroto](endpoint-inventory.md): method/path, trạng thái thử, ghi chú, source URL và vị trí ký tự.
- [CSV mở bằng Excel](endpoint-inventory.csv), [JSON inventory có toàn bộ nguồn trùng lặp](endpoint-inventory.json).
- [51 GET đã thử](http-read-checks.json): URL thực, HTTP status, thời điểm, key response và message.
- [Raw client references](frontend-evidence.json): gồm literal/factory/call, **không được đếm tất cả raw record thành endpoint**.
- [Manifest nguồn](https://parroto.app/_next/static/PI7un_8VTrLhTgj2L-BVI/_buildManifest.js), [shared client nguồn](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js), [vocabulary nguồn](https://parroto.app/_next/static/chunks/2189-4fe1fa23085f5ad2.js).

Các bảng chỉ dùng phương thức/đường dẫn/schema giao tiếp quan sát được. Không truy cập source backend, không suy ra tên DB và không triển khai thay đổi runtime trong đợt khảo sát này.
