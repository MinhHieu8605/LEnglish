# Inventory HTTP Parroto từ web client

06/10/2026: **213 cặp method/path template** trong 208 asset JS đọc thành công. Không đồng nghĩa tất cả endpoint backend. Base URL: `https://api.parroto.app/api`.

Xem [phạm vi, giới hạn và đối chiếu đủ 35 API LEnglish](comparison.md). `{id}` là biến path đã chuẩn hóa; không xác minh kiểu ID. Offset là vị trí ký tự trong file JavaScript minified, không phải số dòng.

HTTP 200/401 chỉ áp dụng GET mẫu đã ghi trong [log](http-read-checks.json). Các method ghi chỉ kiểm tra ở source. Mỗi source link bên dưới hỗ trợ method/path; phần kiến nghị LEnglish là thiết kế riêng.

## Bài học

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p093"></a>P093 | `GET /lessons` | HTTP 401 | Query: topic_slug, difficulty, title, page, limit, sort_by=order. Có cơ chế token do client sinh; probe không có token trả 401. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 297784 |
| <a id="p094"></a>P094 | `GET /lessons/comments/replies/{id}` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [9893-a13a51e75c0c9e8b.js](https://parroto.app/_next/static/chunks/9893-a13a51e75c0c9e8b.js) · offset 37274 |
| <a id="p095"></a>P095 | `DELETE /lessons/comments/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [9893-a13a51e75c0c9e8b.js](https://parroto.app/_next/static/chunks/9893-a13a51e75c0c9e8b.js) · offset 37486 |
| <a id="p096"></a>P096 | `POST /lessons/complete` | Client xác nhận; chưa gửi request ghi | JSON {data: ...} qua helper đóng gói; chưa xác minh đầy đủ nội dung nghiệp vụ. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 298387 |
| <a id="p097"></a>P097 | `GET /lessons/daily` | HTTP 200 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 298939 |
| <a id="p098"></a>P098 | `GET /lessons/progress` | HTTP 401 | Query topic_id; tiến độ bài theo chủ đề, khác vị trí phát video. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 298694 |
| <a id="p099"></a>P099 | `POST /lessons/reset` | Client xác nhận; chưa gửi request ghi | JSON {lesson_id, type}. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 298542 |
| <a id="p100"></a>P100 | `GET /lessons/suggest` | HTTP 401 | Query lesson_id. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 299119 |
| <a id="p101"></a>P101 | `GET /lessons/{id}/comments` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [9893-a13a51e75c0c9e8b.js](https://parroto.app/_next/static/chunks/9893-a13a51e75c0c9e8b.js) · offset 37104 |
| <a id="p102"></a>P102 | `POST /lessons/{id}/comments` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [9893-a13a51e75c0c9e8b.js](https://parroto.app/_next/static/chunks/9893-a13a51e75c0c9e8b.js) · offset 37386 |

## Chấm và ôn câu

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p149"></a>P149 | `GET /sentences/review` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 305115 |
| <a id="p150"></a>P150 | `POST /sentences/review/submit` | Client xác nhận; chưa gửi request ghi | JSON {data: ...}; source dùng đường dẫn không có slash đầu, đã chuẩn hóa theo baseURL. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 305306 |
| <a id="p151"></a>P151 | `POST /sentences/review/submit-shadowing` | Client xác nhận; chưa gửi request ghi | JSON {data: ...}; source dùng đường dẫn không có slash đầu. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 305475 |
| <a id="p152"></a>P152 | `POST /sentences/submit` | Client xác nhận; chưa gửi request ghi | JSON {data: ...} qua helper đóng gói. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 298068 |
| <a id="p153"></a>P153 | `POST /sentences/submit-shadowing` | Client xác nhận; chưa gửi request ghi | JSON {data: ...}; wrapper này không dùng postWithFormData. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 298223 |

## Bài học cộng đồng / shorts

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p018"></a>P018 | `GET /community-lessons` | HTTP 200 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5247-0206db5333cd284f.js](https://parroto.app/_next/static/chunks/5247-0206db5333cd284f.js) · offset 901 |
| <a id="p019"></a>P019 | `POST /community-lessons/from-youtube` | Client xác nhận; chưa gửi request ghi | POST object từ caller; khác import admin LEnglish về quyền sở hữu/quota. | [5247-0206db5333cd284f.js](https://parroto.app/_next/static/chunks/5247-0206db5333cd284f.js) · offset 818 |
| <a id="p020"></a>P020 | `GET /community-lessons/mine` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5247-0206db5333cd284f.js](https://parroto.app/_next/static/chunks/5247-0206db5333cd284f.js) · offset 1297 |
| <a id="p021"></a>P021 | `GET /community-lessons/quota` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5247-0206db5333cd284f.js](https://parroto.app/_next/static/chunks/5247-0206db5333cd284f.js) · offset 1192 |
| <a id="p022"></a>P022 | `GET /community-lessons/shorts` | Client xác nhận; chưa thử GET của route này | Query có exclude từ danh sách excludeIds. | [shorts-61a1af84b72b95ca.js](https://parroto.app/_next/static/chunks/pages/shorts-61a1af84b72b95ca.js) · offset 26266 |
| <a id="p023"></a>P023 | `GET /community-lessons/tags/{id}/lessons` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5247-0206db5333cd284f.js](https://parroto.app/_next/static/chunks/5247-0206db5333cd284f.js) · offset 1017 |
| <a id="p024"></a>P024 | `DELETE /community-lessons/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5247-0206db5333cd284f.js](https://parroto.app/_next/static/chunks/5247-0206db5333cd284f.js) · offset 2035 |
| <a id="p025"></a>P025 | `GET /community-lessons/{id}` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5247-0206db5333cd284f.js](https://parroto.app/_next/static/chunks/5247-0206db5333cd284f.js) · offset 1406 |
| <a id="p026"></a>P026 | `PUT /community-lessons/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5247-0206db5333cd284f.js](https://parroto.app/_next/static/chunks/5247-0206db5333cd284f.js) · offset 1512 |
| <a id="p027"></a>P027 | `POST /community-lessons/{id}/like` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [shorts-61a1af84b72b95ca.js](https://parroto.app/_next/static/chunks/pages/shorts-61a1af84b72b95ca.js) · offset 26477 |
| <a id="p028"></a>P028 | `POST /community-lessons/{id}/retry` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5247-0206db5333cd284f.js](https://parroto.app/_next/static/chunks/5247-0206db5333cd284f.js) · offset 1952 |
| <a id="p029"></a>P029 | `POST /community-lessons/{id}/sentences` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5247-0206db5333cd284f.js](https://parroto.app/_next/static/chunks/5247-0206db5333cd284f.js) · offset 1602 |
| <a id="p030"></a>P030 | `DELETE /community-lessons/{id}/sentences/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5247-0206db5333cd284f.js](https://parroto.app/_next/static/chunks/5247-0206db5333cd284f.js) · offset 1739 |
| <a id="p031"></a>P031 | `POST /community-lessons/{id}/submit` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5247-0206db5333cd284f.js](https://parroto.app/_next/static/chunks/5247-0206db5333cd284f.js) · offset 1869 |
| <a id="p032"></a>P032 | `GET /community-lessons/{id}/transcript` | Client xác nhận; chưa thử GET của route này | Query after_order, limit; caller đọc sentences, has_more và các trường start_ms/end_ms. | [shorts-61a1af84b72b95ca.js](https://parroto.app/_next/static/chunks/pages/shorts-61a1af84b72b95ca.js) · offset 26775 |
| <a id="p033"></a>P033 | `POST /community-lessons/{id}/view` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [shorts-61a1af84b72b95ca.js](https://parroto.app/_next/static/chunks/pages/shorts-61a1af84b72b95ca.js) · offset 27257 |

## Từ điển

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p035"></a>P035 | `GET /dictionary/search` | HTTP 200 | Query word, locale; GET hello/locale=en trả 200. | [7963-55e712e1e6908b46.js](https://parroto.app/_next/static/chunks/7963-55e712e1e6908b46.js) · offset 559 |
| <a id="p036"></a>P036 | `GET /dictionary/word/{id}` | Client xác nhận; chưa thử GET của route này | Path là word đã normalize; probe /hello trả 401. Wrapper bật generateKey. | [7963-55e712e1e6908b46.js](https://parroto.app/_next/static/chunks/7963-55e712e1e6908b46.js) · offset 239 |

## Catalog từ công khai

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p200"></a>P200 | `GET /vocabulary/enc/public` | HTTP 200 | GET catalog; wrapper truyền object query; có thể trả envelope mã hóa. | [2189-4fe1fa23085f5ad2.js](https://parroto.app/_next/static/chunks/2189-4fe1fa23085f5ad2.js) · offset 254 |
| <a id="p201"></a>P201 | `GET /vocabulary/enc/public/by-slug/{id}` | Client xác nhận; chưa thử GET của route này | Tham số path là slug; query incrementView. | [2189-4fe1fa23085f5ad2.js](https://parroto.app/_next/static/chunks/2189-4fe1fa23085f5ad2.js) · offset 453 |
| <a id="p202"></a>P202 | `GET /vocabulary/enc/public/user-published` | HTTP 200 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 3167 |
| <a id="p203"></a>P203 | `GET /vocabulary/enc/public/{id}` | Client xác nhận; chưa thử GET của route này | Query incrementView. | [2189-4fe1fa23085f5ad2.js](https://parroto.app/_next/static/chunks/2189-4fe1fa23085f5ad2.js) · offset 339 |
| <a id="p204"></a>P204 | `GET /vocabulary/enc/public/{id}/groups` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [2189-4fe1fa23085f5ad2.js](https://parroto.app/_next/static/chunks/2189-4fe1fa23085f5ad2.js) · offset 632 |
| <a id="p205"></a>P205 | `GET /vocabulary/enc/public/{id}/groups/{id}/cards` | Client xác nhận; chưa thử GET của route này | Hai {id} lần lượt là deck_id, group_id. | [2189-4fe1fa23085f5ad2.js](https://parroto.app/_next/static/chunks/2189-4fe1fa23085f5ad2.js) · offset 747 |
| <a id="p206"></a>P206 | `POST /vocabulary/{id}/study` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [2189-4fe1fa23085f5ad2.js](https://parroto.app/_next/static/chunks/2189-4fe1fa23085f5ad2.js) · offset 569 |

## Học / ôn từ

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p078"></a>P078 | `DELETE /learning-vocabulary/card/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 296263 |
| <a id="p079"></a>P079 | `PUT /learning-vocabulary/card/{id}/master` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 296721 |
| <a id="p080"></a>P080 | `GET /learning-vocabulary/cards` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 296895 |
| <a id="p081"></a>P081 | `POST /learning-vocabulary/cards/remove` | Client xác nhận; chưa gửi request ghi | JSON {cardIds: [...]}. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 296956 |
| <a id="p082"></a>P082 | `POST /learning-vocabulary/cards/reset` | Client xác nhận; chưa gửi request ghi | JSON {cardIds: [...]}. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 297034 |
| <a id="p083"></a>P083 | `DELETE /learning-vocabulary/deck/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 296341 |
| <a id="p084"></a>P084 | `GET /learning-vocabulary/enc/due` | HTTP 401 | Wrapper nhận object query; route thực dùng, không đồng nhất cache key /cards/due. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 296072 |
| <a id="p085"></a>P085 | `GET /learning-vocabulary/enc/new` | HTTP 401 | Wrapper nhận object query; route thực dùng, không đồng nhất cache key /cards/new. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 296009 |
| <a id="p086"></a>P086 | `DELETE /learning-vocabulary/group/{id}/{id}` | Client xác nhận; chưa gửi request ghi | Hai {id} lần lượt là deck_id, group_id. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 296810 |
| <a id="p087"></a>P087 | `GET /learning-vocabulary/groups-progress/{id}` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 296642 |
| <a id="p088"></a>P088 | `GET /learning-vocabulary/session/current` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 296490 |
| <a id="p089"></a>P089 | `GET /learning-vocabulary/session/history` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 296565 |
| <a id="p090"></a>P090 | `POST /learning-vocabulary/session/start` | Client xác nhận; chưa gửi request ghi | JSON từ caller; không tự suy ra payload tương đương LEnglish. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 296414 |
| <a id="p091"></a>P091 | `GET /learning-vocabulary/stats` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 296196 |
| <a id="p092"></a>P092 | `POST /learning-vocabulary/submit` | Client xác nhận; chưa gửi request ghi | JSON từ caller; có lời gọi submitReview, chưa xác minh contract runtime. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 296136 |

## Hồ sơ / từ cá nhân / thống kê

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p165"></a>P165 | `PUT /user/birthday` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 301777 |
| <a id="p166"></a>P166 | `GET /user/completed-sentences/{id}` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 308415 |
| <a id="p167"></a>P167 | `GET /user/info` | HTTP 401 | GET hồ sơ; PUT multipart cập nhật thông tin. Một số setting học được lưu ở đây. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 306319 |
| <a id="p168"></a>P168 | `PUT /user/info` | Client xác nhận; chưa gửi request ghi | GET hồ sơ; PUT multipart cập nhật thông tin. Một số setting học được lưu ở đây. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 308313 |
| <a id="p169"></a>P169 | `GET /user/info/{id}` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 306759 |
| <a id="p170"></a>P170 | `POST /user/lesson-progress` | Client xác nhận; chưa gửi request ghi | POST JSON {lessonIds: [...]}; đọc batch tiến độ, không phải lưu vị trí xem. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 307386 |
| <a id="p171"></a>P171 | `GET /user/ranking-history` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 307198 |
| <a id="p172"></a>P172 | `PUT /user/selected-item` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 307636 |
| <a id="p173"></a>P173 | `GET /user/stats` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 307050 |
| <a id="p174"></a>P174 | `PUT /user/username` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 306455 |
| <a id="p175"></a>P175 | `GET /user/username/check` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 306561 |
| <a id="p176"></a>P176 | `GET /user/vocabulary-review` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 308843 |
| <a id="p177"></a>P177 | `POST /user/vocabulary-review` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 308549 |
| <a id="p178"></a>P178 | `DELETE /user/vocabulary-review/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 309468 |
| <a id="p179"></a>P179 | `POST /user/vocabulary/cards` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 3581 |
| <a id="p180"></a>P180 | `POST /user/vocabulary/cards/import` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 4064 |
| <a id="p181"></a>P181 | `DELETE /user/vocabulary/cards/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 3847 |
| <a id="p182"></a>P182 | `GET /user/vocabulary/cards/{id}` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 3712 |
| <a id="p183"></a>P183 | `PUT /user/vocabulary/cards/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 3780 |
| <a id="p184"></a>P184 | `GET /user/vocabulary/decks` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 2719 |
| <a id="p185"></a>P185 | `POST /user/vocabulary/decks` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 2664 |
| <a id="p186"></a>P186 | `DELETE /user/vocabulary/decks/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 2932 |
| <a id="p187"></a>P187 | `GET /user/vocabulary/decks/{id}` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 2779 |
| <a id="p188"></a>P188 | `PUT /user/vocabulary/decks/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 2865 |
| <a id="p189"></a>P189 | `GET /user/vocabulary/decks/{id}/groups` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 3296 |
| <a id="p190"></a>P190 | `POST /user/vocabulary/decks/{id}/publish` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 3001 |
| <a id="p191"></a>P191 | `POST /user/vocabulary/decks/{id}/unpublish` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 3081 |
| <a id="p192"></a>P192 | `POST /user/vocabulary/groups` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 3239 |
| <a id="p193"></a>P193 | `DELETE /user/vocabulary/groups/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 3512 |
| <a id="p194"></a>P194 | `GET /user/vocabulary/groups/{id}` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 3373 |
| <a id="p195"></a>P195 | `PUT /user/vocabulary/groups/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 3443 |
| <a id="p196"></a>P196 | `GET /user/vocabulary/groups/{id}/cards` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 3636 |
| <a id="p197"></a>P197 | `GET /user/vocabulary/search` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5829-72dd29a9dd78041d.js](https://parroto.app/_next/static/chunks/5829-72dd29a9dd78041d.js) · offset 3989 |

## Thời gian học

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p075"></a>P075 | `POST /learning-time/end` | Client xác nhận; chưa gửi request ghi | JSON có session_id, final_delta_seconds; có xử lý end khi rời trang. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 573130 |
| <a id="p076"></a>P076 | `POST /learning-time/heartbeat` | Client xác nhận; chưa gửi request ghi | JSON {session_id, sequence, delta_seconds}; FE mặc định heartbeat 240 giây. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 573083 |
| <a id="p077"></a>P077 | `POST /learning-time/start` | Client xác nhận; chưa gửi request ghi | Caller có activity_type, source và ref_id khi có. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 573034 |

## Streak

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p158"></a>P158 | `GET /streak` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [3480-e7911994a3ddca99.js](https://parroto.app/_next/static/chunks/3480-e7911994a3ddca99.js) · offset 602 |
| <a id="p159"></a>P159 | `GET /streak/calendar` | Client xác nhận; chưa thử GET của route này | Query from, to. | [3480-e7911994a3ddca99.js](https://parroto.app/_next/static/chunks/3480-e7911994a3ddca99.js) · offset 763 |
| <a id="p160"></a>P160 | `POST /streak/checkin` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [3480-e7911994a3ddca99.js](https://parroto.app/_next/static/chunks/3480-e7911994a3ddca99.js) · offset 862 |
| <a id="p161"></a>P161 | `GET /streak/config` | HTTP 200 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [3480-e7911994a3ddca99.js](https://parroto.app/_next/static/chunks/3480-e7911994a3ddca99.js) · offset 563 |
| <a id="p162"></a>P162 | `POST /streak/freeze/buy` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [3480-e7911994a3ddca99.js](https://parroto.app/_next/static/chunks/3480-e7911994a3ddca99.js) · offset 1094 |
| <a id="p163"></a>P163 | `GET /streak/milestones` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [3480-e7911994a3ddca99.js](https://parroto.app/_next/static/chunks/3480-e7911994a3ddca99.js) · offset 820 |
| <a id="p164"></a>P164 | `POST /streak/milestones/{id}/claim` | Client xác nhận; chưa gửi request ghi | Query cycle. | [3480-e7911994a3ddca99.js](https://parroto.app/_next/static/chunks/3480-e7911994a3ddca99.js) · offset 1012 |

## Level và XP

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p103"></a>P103 | `GET /level` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [3480-e7911994a3ddca99.js](https://parroto.app/_next/static/chunks/3480-e7911994a3ddca99.js) · offset 205 |
| <a id="p104"></a>P104 | `GET /level/config` | HTTP 200 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [3480-e7911994a3ddca99.js](https://parroto.app/_next/static/chunks/3480-e7911994a3ddca99.js) · offset 167 |
| <a id="p105"></a>P105 | `GET /level/milestones` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [3480-e7911994a3ddca99.js](https://parroto.app/_next/static/chunks/3480-e7911994a3ddca99.js) · offset 241 |
| <a id="p106"></a>P106 | `POST /level/milestones/{id}/claim` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [3480-e7911994a3ddca99.js](https://parroto.app/_next/static/chunks/3480-e7911994a3ddca99.js) · offset 288 |

## Ví điểm

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p211"></a>P211 | `GET /wallet` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [3480-e7911994a3ddca99.js](https://parroto.app/_next/static/chunks/3480-e7911994a3ddca99.js) · offset 1149 |

## Nhiệm vụ

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p107"></a>P107 | `GET /missions/config` | HTTP 200 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [7963-55e712e1e6908b46.js](https://parroto.app/_next/static/chunks/7963-55e712e1e6908b46.js) · offset 700 |
| <a id="p108"></a>P108 | `POST /missions/dictation/submit` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [7963-55e712e1e6908b46.js](https://parroto.app/_next/static/chunks/7963-55e712e1e6908b46.js) · offset 1080 |
| <a id="p109"></a>P109 | `GET /missions/feed` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [7963-55e712e1e6908b46.js](https://parroto.app/_next/static/chunks/7963-55e712e1e6908b46.js) · offset 1485 |
| <a id="p110"></a>P110 | `POST /missions/shadowing/submit` | Client xác nhận; chưa gửi request ghi | POST multipart/form-data được xác nhận trong wrapper. | [7963-55e712e1e6908b46.js](https://parroto.app/_next/static/chunks/7963-55e712e1e6908b46.js) · offset 787 |
| <a id="p111"></a>P111 | `GET /missions/today` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [7963-55e712e1e6908b46.js](https://parroto.app/_next/static/chunks/7963-55e712e1e6908b46.js) · offset 741 |
| <a id="p112"></a>P112 | `POST /missions/vocabulary/submit` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [7963-55e712e1e6908b46.js](https://parroto.app/_next/static/chunks/7963-55e712e1e6908b46.js) · offset 939 |
| <a id="p113"></a>P113 | `POST /missions/{id}/claim` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [7963-55e712e1e6908b46.js](https://parroto.app/_next/static/chunks/7963-55e712e1e6908b46.js) · offset 1131 |

## Đề thi

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p037"></a>P037 | `GET /exams/comments/replies/{id}` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5554-67f09283b16fe43c.js](https://parroto.app/_next/static/chunks/5554-67f09283b16fe43c.js) · offset 4978 |
| <a id="p038"></a>P038 | `DELETE /exams/comments/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5554-67f09283b16fe43c.js](https://parroto.app/_next/static/chunks/5554-67f09283b16fe43c.js) · offset 5126 |
| <a id="p039"></a>P039 | `GET /exams/published/sets` | HTTP 200 | Query exam_type_code khi được truyền; không phải chỉ URL factory. | [5554-67f09283b16fe43c.js](https://parroto.app/_next/static/chunks/5554-67f09283b16fe43c.js) · offset 1893 |
| <a id="p040"></a>P040 | `GET /exams/published/{id}` | Client xác nhận; chưa thử GET của route này | getExamOverview nhận path argument; chưa khẳng định ID/slug qua runtime. | [5554-67f09283b16fe43c.js](https://parroto.app/_next/static/chunks/5554-67f09283b16fe43c.js) · offset 2049 |
| <a id="p041"></a>P041 | `GET /exams/sessions/analytics` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5554-67f09283b16fe43c.js](https://parroto.app/_next/static/chunks/5554-67f09283b16fe43c.js) · offset 4514 |
| <a id="p042"></a>P042 | `GET /exams/sessions/history` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5554-67f09283b16fe43c.js](https://parroto.app/_next/static/chunks/5554-67f09283b16fe43c.js) · offset 4379 |
| <a id="p043"></a>P043 | `POST /exams/sessions/start` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5554-67f09283b16fe43c.js](https://parroto.app/_next/static/chunks/5554-67f09283b16fe43c.js) · offset 2186 |
| <a id="p044"></a>P044 | `GET /exams/sessions/{id}` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5554-67f09283b16fe43c.js](https://parroto.app/_next/static/chunks/5554-67f09283b16fe43c.js) · offset 2318 |
| <a id="p045"></a>P045 | `POST /exams/sessions/{id}/abandon` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5554-67f09283b16fe43c.js](https://parroto.app/_next/static/chunks/5554-67f09283b16fe43c.js) · offset 3720 |
| <a id="p046"></a>P046 | `PUT /exams/sessions/{id}/answer` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5554-67f09283b16fe43c.js](https://parroto.app/_next/static/chunks/5554-67f09283b16fe43c.js) · offset 3194 |
| <a id="p047"></a>P047 | `PUT /exams/sessions/{id}/answers` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5554-67f09283b16fe43c.js](https://parroto.app/_next/static/chunks/5554-67f09283b16fe43c.js) · offset 3316 |
| <a id="p048"></a>P048 | `GET /exams/sessions/{id}/check/{id}` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5554-67f09283b16fe43c.js](https://parroto.app/_next/static/chunks/5554-67f09283b16fe43c.js) · offset 3561 |
| <a id="p049"></a>P049 | `PUT /exams/sessions/{id}/flag` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5554-67f09283b16fe43c.js](https://parroto.app/_next/static/chunks/5554-67f09283b16fe43c.js) · offset 3431 |
| <a id="p050"></a>P050 | `GET /exams/sessions/{id}/questions` | Client xác nhận; chưa thử GET của route này | Query part khi được truyền. | [5554-67f09283b16fe43c.js](https://parroto.app/_next/static/chunks/5554-67f09283b16fe43c.js) · offset 2544 |
| <a id="p051"></a>P051 | `GET /exams/sessions/{id}/result` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5554-67f09283b16fe43c.js](https://parroto.app/_next/static/chunks/5554-67f09283b16fe43c.js) · offset 3974 |
| <a id="p052"></a>P052 | `POST /exams/sessions/{id}/submit` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5554-67f09283b16fe43c.js](https://parroto.app/_next/static/chunks/5554-67f09283b16fe43c.js) · offset 3830 |
| <a id="p053"></a>P053 | `GET /exams/{id}/comments` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5554-67f09283b16fe43c.js](https://parroto.app/_next/static/chunks/5554-67f09283b16fe43c.js) · offset 4683 |
| <a id="p054"></a>P054 | `POST /exams/{id}/comments` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5554-67f09283b16fe43c.js](https://parroto.app/_next/static/chunks/5554-67f09283b16fe43c.js) · offset 4828 |

## Thông báo

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p114"></a>P114 | `GET /notifications` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 411210 |
| <a id="p115"></a>P115 | `DELETE /notifications/read-all` | Client xác nhận; chưa gửi request ghi | Wrapper dùng DELETE cho thao tác đọc tất cả. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 411384 |
| <a id="p116"></a>P116 | `GET /notifications/stats` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 411269 |
| <a id="p117"></a>P117 | `DELETE /notifications/{id}` | Client xác nhận; chưa gửi request ghi | Wrapper đặt tên markAsRead nhưng dùng DELETE; cần đọc semantics, không suy ra xóa dữ liệu. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 411321 |

## Xếp hạng

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p073"></a>P073 | `GET /leaderboard/home` | Client xác nhận; chưa thử GET của route này | Query period, metric, limit. | [2189-4fe1fa23085f5ad2.js](https://parroto.app/_next/static/chunks/2189-4fe1fa23085f5ad2.js) · offset 1411 |
| <a id="p074"></a>P074 | `GET /leaderboard/monthly` | Client xác nhận; chưa thử GET của route này | Query month, sortBy. | [2189-4fe1fa23085f5ad2.js](https://parroto.app/_next/static/chunks/2189-4fe1fa23085f5ad2.js) · offset 1040 |

## Trò chơi

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p066"></a>P066 | `GET /games/feed` | HTTP 200 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [games-0ac9d52dd6838747.js](https://parroto.app/_next/static/chunks/pages/games-0ac9d52dd6838747.js) · offset 550 |
| <a id="p067"></a>P067 | `POST /games/sessions` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [games-0ac9d52dd6838747.js](https://parroto.app/_next/static/chunks/pages/games-0ac9d52dd6838747.js) · offset 314 |
| <a id="p068"></a>P068 | `GET /games/top-players` | HTTP 200 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [games-0ac9d52dd6838747.js](https://parroto.app/_next/static/chunks/pages/games-0ac9d52dd6838747.js) · offset 844 |

## Vocab battle

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p198"></a>P198 | `GET /vocab-battle/activity/{id}` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [4793.a02c947aba75f9e0.js](https://parroto.app/_next/static/chunks/4793.a02c947aba75f9e0.js) · offset 3473 |
| <a id="p199"></a>P199 | `GET /vocab-battle/leaderboard` | HTTP 200 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [4793.a02c947aba75f9e0.js](https://parroto.app/_next/static/chunks/4793.a02c947aba75f9e0.js) · offset 3670 |

## Luyện nói cộng đồng

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p208"></a>P208 | `GET /voice-chat/activity/{id}` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [3421.f6dda72de716f38c.js](https://parroto.app/_next/static/chunks/3421.f6dda72de716f38c.js) · offset 5725 |
| <a id="p209"></a>P209 | `GET /voice-chat/topics` | HTTP 200 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [3421.f6dda72de716f38c.js](https://parroto.app/_next/static/chunks/3421.f6dda72de716f38c.js) · offset 5403 |
| <a id="p210"></a>P210 | `GET /voice-chat/topics/{id}` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [3421.f6dda72de716f38c.js](https://parroto.app/_next/static/chunks/3421.f6dda72de716f38c.js) · offset 5553 |

## Diễn đàn

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p118"></a>P118 | `GET /posts` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [6114-76e464e05e385b43.js](https://parroto.app/_next/static/chunks/6114-76e464e05e385b43.js) · offset 1399 |
| <a id="p119"></a>P119 | `POST /posts` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [6114-76e464e05e385b43.js](https://parroto.app/_next/static/chunks/6114-76e464e05e385b43.js) · offset 1130 |
| <a id="p120"></a>P120 | `GET /posts/categories` | HTTP 200 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [6114-76e464e05e385b43.js](https://parroto.app/_next/static/chunks/6114-76e464e05e385b43.js) · offset 1760 |
| <a id="p121"></a>P121 | `POST /posts/comments` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [6114-76e464e05e385b43.js](https://parroto.app/_next/static/chunks/6114-76e464e05e385b43.js) · offset 1910 |
| <a id="p122"></a>P122 | `GET /posts/comments/post/{id}` | Client xác nhận; chưa thử GET của route này | Query page, limit, ...; ID của post. | [6114-76e464e05e385b43.js](https://parroto.app/_next/static/chunks/6114-76e464e05e385b43.js) · offset 2326 |
| <a id="p123"></a>P123 | `DELETE /posts/comments/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [6114-76e464e05e385b43.js](https://parroto.app/_next/static/chunks/6114-76e464e05e385b43.js) · offset 3113 |
| <a id="p124"></a>P124 | `GET /posts/comments/{id}/replies` | Client xác nhận; chưa thử GET của route này | Query page, limit, ...; ID của comment. | [6114-76e464e05e385b43.js](https://parroto.app/_next/static/chunks/6114-76e464e05e385b43.js) · offset 2764 |
| <a id="p125"></a>P125 | `POST /posts/comments/{id}/vote` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [6114-76e464e05e385b43.js](https://parroto.app/_next/static/chunks/6114-76e464e05e385b43.js) · offset 2958 |
| <a id="p126"></a>P126 | `POST /posts/reports` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [6114-76e464e05e385b43.js](https://parroto.app/_next/static/chunks/6114-76e464e05e385b43.js) · offset 3394 |
| <a id="p127"></a>P127 | `DELETE /posts/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [6114-76e464e05e385b43.js](https://parroto.app/_next/static/chunks/6114-76e464e05e385b43.js) · offset 3736 |
| <a id="p128"></a>P128 | `GET /posts/{id}` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [6114-76e464e05e385b43.js](https://parroto.app/_next/static/chunks/6114-76e464e05e385b43.js) · offset 1608 |
| <a id="p129"></a>P129 | `POST /posts/{id}/vote` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [6114-76e464e05e385b43.js](https://parroto.app/_next/static/chunks/6114-76e464e05e385b43.js) · offset 3251 |

## Thống kê cộng đồng

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p034"></a>P034 | `GET /community-stats/my-stats` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [6114-76e464e05e385b43.js](https://parroto.app/_next/static/chunks/6114-76e464e05e385b43.js) · offset 3873 |

## Chat cộng đồng

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p012"></a>P012 | `GET /community-chat` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [9009-38caf9c3316e603e.js](https://parroto.app/_next/static/chunks/9009-38caf9c3316e603e.js) · offset 544 |
| <a id="p013"></a>P013 | `POST /community-chat` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [9009-38caf9c3316e603e.js](https://parroto.app/_next/static/chunks/9009-38caf9c3316e603e.js) · offset 764 |
| <a id="p014"></a>P014 | `POST /community-chat/ban/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [9009-38caf9c3316e603e.js](https://parroto.app/_next/static/chunks/9009-38caf9c3316e603e.js) · offset 1096 |
| <a id="p015"></a>P015 | `POST /community-chat/unban/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [9009-38caf9c3316e603e.js](https://parroto.app/_next/static/chunks/9009-38caf9c3316e603e.js) · offset 1185 |
| <a id="p016"></a>P016 | `PATCH /community-chat/{id}/hide` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [9009-38caf9c3316e603e.js](https://parroto.app/_next/static/chunks/9009-38caf9c3316e603e.js) · offset 919 |
| <a id="p017"></a>P017 | `PATCH /community-chat/{id}/unhide` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [9009-38caf9c3316e603e.js](https://parroto.app/_next/static/chunks/9009-38caf9c3316e603e.js) · offset 1012 |

## Bạn bè

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p058"></a>P058 | `GET /friends` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [8506-9e16008f47955a81.js](https://parroto.app/_next/static/chunks/8506-9e16008f47955a81.js) · offset 582 |
| <a id="p059"></a>P059 | `POST /friends/accept/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [8506-9e16008f47955a81.js](https://parroto.app/_next/static/chunks/8506-9e16008f47955a81.js) · offset 1592 |
| <a id="p060"></a>P060 | `POST /friends/reject/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [8506-9e16008f47955a81.js](https://parroto.app/_next/static/chunks/8506-9e16008f47955a81.js) · offset 1662 |
| <a id="p061"></a>P061 | `POST /friends/request` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [8506-9e16008f47955a81.js](https://parroto.app/_next/static/chunks/8506-9e16008f47955a81.js) · offset 1516 |
| <a id="p062"></a>P062 | `GET /friends/requests/incoming` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [8506-9e16008f47955a81.js](https://parroto.app/_next/static/chunks/8506-9e16008f47955a81.js) · offset 981 |
| <a id="p063"></a>P063 | `GET /friends/search` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [8506-9e16008f47955a81.js](https://parroto.app/_next/static/chunks/8506-9e16008f47955a81.js) · offset 1312 |
| <a id="p064"></a>P064 | `GET /friends/status/{id}` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [8506-9e16008f47955a81.js](https://parroto.app/_next/static/chunks/8506-9e16008f47955a81.js) · offset 1744 |
| <a id="p065"></a>P065 | `DELETE /friends/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [8506-9e16008f47955a81.js](https://parroto.app/_next/static/chunks/8506-9e16008f47955a81.js) · offset 1840 |

## Chat riêng

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p131"></a>P131 | `POST /private-chat` | Client xác nhận; chưa gửi request ghi | JSON {partner_id}. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 299834 |
| <a id="p132"></a>P132 | `GET /private-chat/block` | Client xác nhận; chưa thử GET của route này | POST {blocked_id}; GET query page, limit. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 301275 |
| <a id="p133"></a>P133 | `POST /private-chat/block` | Client xác nhận; chưa gửi request ghi | POST {blocked_id}; GET query page, limit. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 300981 |
| <a id="p134"></a>P134 | `GET /private-chat/block/check/{id}` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 301514 |
| <a id="p135"></a>P135 | `DELETE /private-chat/block/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 301057 |
| <a id="p136"></a>P136 | `GET /private-chat/conversations` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 300184 |
| <a id="p137"></a>P137 | `POST /private-chat/messages` | Client xác nhận; chưa gửi request ghi | JSON {conversation_id, text}. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 299934 |
| <a id="p138"></a>P138 | `DELETE /private-chat/messages/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 300906 |
| <a id="p139"></a>P139 | `GET /private-chat/unread-count` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 301618 |
| <a id="p140"></a>P140 | `GET /private-chat/{id}/messages` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 300635 |
| <a id="p141"></a>P141 | `POST /private-chat/{id}/read` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 300830 |

## Ghi chú câu

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p145"></a>P145 | `GET /sentence-notes` | HTTP 401 | GET có thể lọc lesson_id. | [5385-0712f564b7d3daea.js](https://parroto.app/_next/static/chunks/5385-0712f564b7d3daea.js) · offset 347 |
| <a id="p146"></a>P146 | `DELETE /sentence-notes/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5385-0712f564b7d3daea.js](https://parroto.app/_next/static/chunks/5385-0712f564b7d3daea.js) · offset 708 |
| <a id="p147"></a>P147 | `POST /sentence-notes/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5385-0712f564b7d3daea.js](https://parroto.app/_next/static/chunks/5385-0712f564b7d3daea.js) · offset 523 |
| <a id="p148"></a>P148 | `PUT /sentence-notes/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5385-0712f564b7d3daea.js](https://parroto.app/_next/static/chunks/5385-0712f564b7d3daea.js) · offset 869 |

## Báo lỗi câu

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p144"></a>P144 | `POST /sentence-errors` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [5385-0712f564b7d3daea.js](https://parroto.app/_next/static/chunks/5385-0712f564b7d3daea.js) · offset 1111 |

## Báo lỗi từ

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p207"></a>P207 | `POST /vocabulary-errors` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [6178-b8cb8f9b923191e8.js](https://parroto.app/_next/static/chunks/6178-b8cb8f9b923191e8.js) · offset 208 |

## Cửa hàng

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p154"></a>P154 | `GET /shop/items` | HTTP 200 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [shop-1f9804bb2dd0ea93.js](https://parroto.app/_next/static/chunks/pages/shop-1f9804bb2dd0ea93.js) · offset 1666 |
| <a id="p155"></a>P155 | `POST /shop/items/purchase` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [shop-1f9804bb2dd0ea93.js](https://parroto.app/_next/static/chunks/pages/shop-1f9804bb2dd0ea93.js) · offset 1996 |
| <a id="p156"></a>P156 | `GET /shop/items/purchased/by-type` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [shop-1f9804bb2dd0ea93.js](https://parroto.app/_next/static/chunks/pages/shop-1f9804bb2dd0ea93.js) · offset 1818 |
| <a id="p157"></a>P157 | `PATCH /shop/items/purchased/{id}/toggle` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [shop-1f9804bb2dd0ea93.js](https://parroto.app/_next/static/chunks/pages/shop-1f9804bb2dd0ea93.js) · offset 2156 |

## Giá

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p130"></a>P130 | `GET /prices` | HTTP 200 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 449120 |

## Thanh toán

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p212"></a>P212 | `POST /webhooks/sepay/generate-code` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 532957 |
| <a id="p213"></a>P213 | `GET /webhooks/sepay/payment-status` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 535212 |

## Khuyến mãi

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p142"></a>P142 | `GET /promo/active` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 302304 |
| <a id="p143"></a>P143 | `POST /promo/validate` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 303448 |

## Kích hoạt

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p001"></a>P001 | `POST /activation-codes/activate` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 309569 |

## Cộng tác viên

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p002"></a>P002 | `POST /affiliate/code` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 293474 |
| <a id="p003"></a>P003 | `GET /affiliate/commissions` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 294353 |
| <a id="p004"></a>P004 | `GET /affiliate/me` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 291192 |
| <a id="p005"></a>P005 | `GET /affiliate/packages` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 295675 |
| <a id="p006"></a>P006 | `GET /affiliate/payout-profile` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 294839 |
| <a id="p007"></a>P007 | `PUT /affiliate/payout-profile` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 295079 |
| <a id="p008"></a>P008 | `GET /affiliate/payouts` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 295386 |
| <a id="p009"></a>P009 | `POST /affiliate/payouts` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 295577 |
| <a id="p010"></a>P010 | `POST /affiliate/prepare-paddle-checkout` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 293566 |
| <a id="p011"></a>P011 | `GET /affiliate/referrals` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [_app-6589d8431d4dbd84.js](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 293863 |

## Phản hồi (ngoài phạm vi so sánh)

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p055"></a>P055 | `POST /feedback` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [feedbacks-e788805ae8b4d23c.js](https://parroto.app/_next/static/chunks/pages/feedbacks-e788805ae8b4d23c.js) · offset 2400 |
| <a id="p056"></a>P056 | `GET /feedback/my` | HTTP 401 | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [feedbacks-e788805ae8b4d23c.js](https://parroto.app/_next/static/chunks/pages/feedbacks-e788805ae8b4d23c.js) · offset 2226 |
| <a id="p057"></a>P057 | `GET /feedback/public` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [feedbacks-e788805ae8b4d23c.js](https://parroto.app/_next/static/chunks/pages/feedbacks-e788805ae8b4d23c.js) · offset 1622 |

## Comments qua wrapper generic

| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |
| --- | --- | --- | --- | --- |
| <a id="p069"></a>P069 | `GET /grammar/comments/replies/{id}` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [9893-a13a51e75c0c9e8b.js](https://parroto.app/_next/static/chunks/9893-a13a51e75c0c9e8b.js) · offset 37274 |
| <a id="p070"></a>P070 | `DELETE /grammar/comments/{id}` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [9893-a13a51e75c0c9e8b.js](https://parroto.app/_next/static/chunks/9893-a13a51e75c0c9e8b.js) · offset 37486 |
| <a id="p071"></a>P071 | `GET /grammar/{id}/comments` | Client xác nhận; chưa thử GET của route này | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [9893-a13a51e75c0c9e8b.js](https://parroto.app/_next/static/chunks/9893-a13a51e75c0c9e8b.js) · offset 37104 |
| <a id="p072"></a>P072 | `POST /grammar/{id}/comments` | Client xác nhận; chưa gửi request ghi | Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra. | [9893-a13a51e75c0c9e8b.js](https://parroto.app/_next/static/chunks/9893-a13a51e75c0c9e8b.js) · offset 37386 |

## URL factory / cache key: không tự coi là endpoint HTTP

Các entry này xuất hiện trong client nhưng không được thêm vào inventory chỉ vì có string URL. Nếu có lời gọi service độc lập, route đó đã được ghi ở các nhóm trên. Biểu thức giữ dạng minify để không bịa query/schema.

| Tên trong source | Biểu thức | Bằng chứng |
| --- | --- | --- |
| `vocabularyReviews` | `"/user/vocabulary-reviews"` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 397410 |
| `userProgress` | `"/user/lesson-progress/".concat(e)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 397730 |
| `userCompletedSentences` | `"/user/completed-sentences/".concat(e)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 397781 |
| `publicProfile` | `"/user/info/".concat(e)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 397846 |
| `affiliateMe` | `"/affiliate/me"` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 397887 |
| `affiliateReferrals` | `"/affiliate/referrals?page=".concat(e,"&limit=").concat(t)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 397919 |
| `affiliateCommissions` | `"/affiliate/commissions?".concat(new URLSearchParams(Object.entries(e).map(e=>{let[t,n]=e;return[t,String(n)]})).toString())` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 398004 |
| `affiliatePayoutProfile` | `"/affiliate/payout-profile"` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 398153 |
| `affiliatePayouts` | `"/affiliate/payouts?page=".concat(e,"&limit=").concat(t)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 398208 |
| `affiliatePackages` | `"/affiliate/packages"` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 398289 |
| `reviewSentences` | `"/sentences/review/".concat(e)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 398333 |
| `reviewSentencesCount` | `"/sentences/review/".concat(e,"/count")` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 398383 |
| `purchasedItems` | `"/shop/items/purchased"` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 398523 |
| `purchasedItemsByType` | `"/shop/items/purchased/by-type"` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 398566 |
| `shopItems` | `"/shop/items?".concat(new URLSearchParams(Object.entries(e\|\|{}).filter(e=>{let[t,n]=e;return void 0!==n}).map(e=>{let[t,n]=e;return[t,String(n)]})).toString())` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 398623 |
| `lessonsByTopic` | `"/lessons?topic_id=".concat(e)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 398796 |
| `lessonsProgressByTopic` | `"/lessons/progress?topic_id=".concat(e)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 398845 |
| `nextLessonSuggestion` | `"/lessons/suggest?lesson_id=".concat(e)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 398911 |
| `decks` | `"/vocabulary/decks?".concat(new URLSearchParams(Object.entries(e\|\|{}).filter(e=>{let[t,n]=e;return void 0!==n}).map(e=>{let[t,n]=e;return[t,String(n)]})).toString())` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 398975 |
| `deckById` | `"/vocabulary/deck/".concat(e)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 399150 |
| `deckGroups` | `"/vocabulary/deck/".concat(e,"/groups")` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 399192 |
| `groupsProgress` | `"/learning-vocabulary/groups-progress/".concat(e)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 399246 |
| `groupCards` | `"/learning-vocabulary/cards/new?deckId=".concat(e,"&groupId=").concat(t).concat(n?"&mode=".concat(n):"")` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 399314 |
| `vocabularyStats` | `"/learning-vocabulary/stats"` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 399439 |
| `vocabularyCurrentSession` | `"/learning-vocabulary/session/current"` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 399488 |
| `vocabularySessionHistory` | `"/learning-vocabulary/session/history"` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 399556 |
| `vocabularyLeaderboard` | `"/leaderboard/monthly?month=".concat(e,"&sortBy=vocabulary")` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 399624 |
| `leaderboard` | `"/leaderboard/monthly?month=".concat(e)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 399886 |
| `userDecks` | `"/user/vocabulary/decks?".concat(new URLSearchParams(Object.entries(e\|\|{}).filter(e=>{let[t,n]=e;return void 0!==n}).map(e=>{let[t,n]=e;return[t,String(n)]})).toString())` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 399941 |
| `userDeckById` | `"/user/vocabulary/decks/".concat(e)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 400125 |
| `userGroups` | `"/user/vocabulary/decks/".concat(e,"/groups")` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 400177 |
| `userGroupById` | `"/user/vocabulary/groups/".concat(e)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 400237 |
| `userCards` | `"/user/vocabulary/groups/".concat(e,"/cards")` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 400291 |
| `userCardById` | `"/user/vocabulary/cards/".concat(e)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 400350 |
| `publishedUserDecks` | `"/vocabulary/public/user-published?".concat(new URLSearchParams(Object.entries(e\|\|{}).filter(e=>{let[t,n]=e;return void 0!==n}).map(e=>{let[t,n]=e;return[t,String(n)]})).toString())` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 400402 |
| `examSets` | `"/exams/published/sets?include_draft=true".concat(e?"&exam_type_code=".concat(e):"")` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 400606 |
| `examsBySet` | `"/exams/published?exam_set_id=".concat(e)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 400703 |
| `examOverview` | `"/exams/published/".concat(e)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 400759 |
| `examSession` | `"/exams/sessions/".concat(e)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 400805 |
| `examSessionQuestions` | `"/exams/sessions/".concat(e,"/questions?part=").concat(t)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 400849 |
| `examResult` | `"/exams/sessions/".concat(e,"/result")` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 400935 |
| `examAnalytics` | `"/exams/sessions/analytics".concat(e?"?exam_type_code=".concat(e):"")` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 401207 |
| `examComments` | `"/exams/".concat(e,"/comments").concat(t?"?page=".concat(t):"")` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 401294 |
| `streakConfig` | `"/streak/config"` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 401378 |
| `streakState` | `"/streak/state"` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 401412 |
| `streakCalendar` | `"/streak/calendar?from=".concat(e,"&to=").concat(t)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 401444 |
| `streakMilestones` | `"/streak/milestones"` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 401518 |
| `wallet` | `"/wallet"` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 401560 |
| `levelState` | `"/level"` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 401581 |
| `levelMilestones` | `"/level/milestones"` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 401605 |
| `levelConfig` | `"/level/config"` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 401645 |
| `missionsConfig` | `"/missions/config"` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 401857 |
| `missionsToday` | `"/missions/today"` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 401895 |
| `missionsFeed` | `"/missions/feed?".concat(new URLSearchParams(Object.entries(e\|\|{}).filter(e=>{let[t,n]=e;return void 0!==n&&""!==n}).map(e=>{let[t,n]=e;return[t,String(n)]})).toString())` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 401931 |
| `communityLessons` | `"/community-lessons?".concat(new URLSearchParams(Object.entries(e\|\|{}).filter(e=>{let[t,n]=e;return void 0!==n&&""!==n}).map(e=>{let[t,n]=e;return[t,String(n)]})).toString())` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 402118 |
| `communityChannels` | `"/community-lessons/channels?".concat(new URLSearchParams(Object.entries(e\|\|{}).filter(e=>{let[t,n]=e;return void 0!==n}).map(e=>{let[t,n]=e;return[t,String(n)]})).toString())` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 402313 |
| `myCommunityLessons` | `"/community-lessons/mine?page=".concat(e,"&limit=").concat(t)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 402510 |
| `communityLessonDetail` | `"/community-lessons/".concat(e)` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 402598 |
| `communityLessonQuota` | `"/community-lessons/quota"` | [source](https://parroto.app/_next/static/chunks/pages/_app-6589d8431d4dbd84.js) · offset 402655 |

## Kiểm tra tính đầy đủ của extraction

Có 0 call record không chuẩn hóa được tự động; nếu khác 0 cần đọc source trước khi coi inventory hoàn chỉnh trong phạm vi đã khảo sát. Số raw call có thể trùng do cùng module nằm trong nhiều chunk. Không kiểm chứng rằng code nhánh generic /grammar đang được UI sử dụng. Socket.IO/WebRTC không được gộp vào bảng HTTP.
