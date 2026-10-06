"""Build a documented inventory from public client evidence; never executes JS."""
import ast
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BE = ROOT.parents[1]
evidence = json.loads((ROOT / 'frontend-evidence.json').read_text(encoding='utf-8'))
checks = json.loads((ROOT / 'http-read-checks.json').read_text(encoding='utf-8'))


def split_args(s):
    result, start, depth, quote, escaped = [], 0, 0, None, False
    for i, ch in enumerate(s):
        if quote:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == quote:
                quote = None
        elif ch in '\"\'':
            quote = ch
        elif ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        elif ch == ',' and depth == 0:
            result.append(s[start:i])
            start = i + 1
    return result + [s[start:]]


def normalize(r):
    expr, source = r['expression'], r['source'].split('/')[-1]
    if source.startswith('6114-'):
        if expr.startswith('l?'):
            return ['/posts']
        if expr == 'n':
            # Same local variable is used by two wrappers; select the nearest path.
            before = r['context'].split('a.E.get(n)', 1)[0]
            if '/replies' in before:
                return ['/posts/comments/{id}/replies']
            return ['/posts/comments/post/{id}']
    if expr == 'a' and source.startswith('9009-'):
        return ['/community-chat']
    community = any(v in source for v in ['5247-', 'edit-b88', '[channelId]-', 'shorts-61', '[slug]-deca83'])
    if expr in ['i', 'a', 'c'] and community:
        return ['/community-lessons']
    if 'basePath(' in expr:
        resource = '{resource}'
    else:
        resource = None
    first = re.match(r'"([^"\\]*)"', expr)
    if not first:
        return []
    path = first.group(1)
    rest = expr[first.end():]
    while rest.startswith('.concat('):
        depth, quote, escaped, end = 1, None, False, None
        for i, ch in enumerate(rest[8:], 8):
            if quote:
                if escaped:
                    escaped = False
                elif ch == '\\':
                    escaped = True
                elif ch == quote:
                    quote = None
            elif ch in '\"\'':
                quote = ch
            elif ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end is None:
            return []
        for arg in split_args(rest[8:end]):
            arg = arg.strip()
            if re.fullmatch(r'"[^"\\]*"', arg):
                path += arg[1:-1]
            elif not path and resource:
                path += '/' + resource
            elif not path and community:
                path += '/community-lessons'
            elif '?' not in path:
                path += '{id}'
        rest = rest[end + 1:]
    if rest:
        return []
    # These appended variables contain query strings, not resource identifiers.
    for p in ['/streak/calendar', '/missions/feed', '/affiliate/referrals', '/affiliate/commissions', '/affiliate/payouts', '/promo/active']:
        if path == p + '{id}':
            path = p
    path = '/' + path.lstrip('/')
    path = path.split('?')[0]
    if resource:
        return [path.replace('{resource}', p) for p in ['lessons', 'grammar']]
    return [path]


inventory = {}
unresolved = []
for r in evidence['records']:
    if r['kind'] != 'call':
        continue
    paths = normalize(r)
    if not paths:
        unresolved.append(r)
    for path in paths:
        method = r['method'].replace('WITHFORMDATA', '')
        key = (method, path)
        entry = inventory.setdefault(key, {'method': method, 'path': path, 'multipart': False, 'evidence': []})
        entry['multipart'] |= 'WITHFORMDATA' in r['method']
        ev = {k: r[k] for k in ['source', 'offset', 'expression']}
        if ev not in entry['evidence']:
            entry['evidence'].append(ev)

probe_status = {}
for r in checks['results']:
    path = r['path'].split('?')[0]
    probe_status.setdefault(path, set()).add(str(r['status']))


def status(method, path):
    values = probe_status.get(path) if method == 'GET' else None
    if values:
        return 'HTTP ' + '/'.join(sorted(values))
    if method != 'GET':
        return 'Client xác nhận; chưa gửi request ghi'
    return 'Client xác nhận; chưa thử GET của route này'


GROUP_NAMES = {
    'lessons': 'Bài học', 'sentences': 'Chấm và ôn câu', 'community-lessons': 'Bài học cộng đồng / shorts',
    'dictionary': 'Từ điển', 'vocabulary': 'Catalog từ công khai', 'learning-vocabulary': 'Học / ôn từ',
    'user': 'Hồ sơ / từ cá nhân / thống kê', 'learning-time': 'Thời gian học', 'streak': 'Streak',
    'level': 'Level và XP', 'wallet': 'Ví điểm', 'missions': 'Nhiệm vụ', 'exams': 'Đề thi',
    'notifications': 'Thông báo', 'leaderboard': 'Xếp hạng', 'games': 'Trò chơi',
    'vocab-battle': 'Vocab battle', 'voice-chat': 'Luyện nói cộng đồng', 'posts': 'Diễn đàn',
    'community-stats': 'Thống kê cộng đồng', 'community-chat': 'Chat cộng đồng', 'friends': 'Bạn bè',
    'private-chat': 'Chat riêng', 'sentence-notes': 'Ghi chú câu', 'sentence-errors': 'Báo lỗi câu',
    'vocabulary-errors': 'Báo lỗi từ', 'shop': 'Cửa hàng', 'prices': 'Giá', 'webhooks': 'Thanh toán',
    'promo': 'Khuyến mãi', 'activation-codes': 'Kích hoạt', 'affiliate': 'Cộng tác viên',
    'feedback': 'Phản hồi (ngoài phạm vi so sánh)', 'grammar': 'Comments qua wrapper generic',
}

NOTES = {
    '/lessons': 'Query: topic_slug, difficulty, title, page, limit, sort_by=order. Có cơ chế token do client sinh; probe không có token trả 401.',
    '/lessons/progress': 'Query topic_id; tiến độ bài theo chủ đề, khác vị trí phát video.',
    '/lessons/suggest': 'Query lesson_id.',
    '/lessons/reset': 'JSON {lesson_id, type}.',
    '/lessons/complete': 'JSON {data: ...} qua helper đóng gói; chưa xác minh đầy đủ nội dung nghiệp vụ.',
    '/sentences/submit': 'JSON {data: ...} qua helper đóng gói.',
    '/sentences/submit-shadowing': 'JSON {data: ...}; wrapper này không dùng postWithFormData.',
    '/sentences/review/submit': 'JSON {data: ...}; source dùng đường dẫn không có slash đầu, đã chuẩn hóa theo baseURL.',
    '/sentences/review/submit-shadowing': 'JSON {data: ...}; source dùng đường dẫn không có slash đầu.',
    '/vocabulary/enc/public': 'GET catalog; wrapper truyền object query; có thể trả envelope mã hóa.',
    '/vocabulary/enc/public/{id}': 'Query incrementView.',
    '/vocabulary/enc/public/by-slug/{id}': 'Tham số path là slug; query incrementView.',
    '/vocabulary/enc/public/{id}/groups/{id}/cards': 'Hai {id} lần lượt là deck_id, group_id.',
    '/learning-vocabulary/enc/new': 'Wrapper nhận object query; route thực dùng, không đồng nhất cache key /cards/new.',
    '/learning-vocabulary/enc/due': 'Wrapper nhận object query; route thực dùng, không đồng nhất cache key /cards/due.',
    '/learning-vocabulary/submit': 'JSON từ caller; có lời gọi submitReview, chưa xác minh contract runtime.',
    '/learning-vocabulary/session/start': 'JSON từ caller; không tự suy ra payload tương đương LEnglish.',
    '/learning-vocabulary/group/{id}/{id}': 'Hai {id} lần lượt là deck_id, group_id.',
    '/learning-vocabulary/cards/remove': 'JSON {cardIds: [...]}.',
    '/learning-vocabulary/cards/reset': 'JSON {cardIds: [...]}.',
    '/dictionary/search': 'Query word, locale; GET hello/locale=en trả 200.',
    '/dictionary/word/{id}': 'Path là word đã normalize; probe /hello trả 401. Wrapper bật generateKey.',
    '/learning-time/start': 'Caller có activity_type, source và ref_id khi có.',
    '/learning-time/heartbeat': 'JSON {session_id, sequence, delta_seconds}; FE mặc định heartbeat 240 giây.',
    '/learning-time/end': 'JSON có session_id, final_delta_seconds; có xử lý end khi rời trang.',
    '/streak/calendar': 'Query from, to.',
    '/streak/milestones/{id}/claim': 'Query cycle.',
    '/missions/shadowing/submit': 'POST multipart/form-data được xác nhận trong wrapper.',
    '/exams/published/sets': 'Query exam_type_code khi được truyền; không phải chỉ URL factory.',
    '/exams/published/{id}': 'getExamOverview nhận path argument; chưa khẳng định ID/slug qua runtime.',
    '/exams/sessions/{id}/questions': 'Query part khi được truyền.',
    '/leaderboard/monthly': 'Query month, sortBy.',
    '/leaderboard/home': 'Query period, metric, limit.',
    '/notifications/{id}': 'Wrapper đặt tên markAsRead nhưng dùng DELETE; cần đọc semantics, không suy ra xóa dữ liệu.',
    '/notifications/read-all': 'Wrapper dùng DELETE cho thao tác đọc tất cả.',
    '/community-lessons/from-youtube': 'POST object từ caller; khác import admin LEnglish về quyền sở hữu/quota.',
    '/community-lessons/{id}/transcript': 'Query after_order, limit; caller đọc sentences, has_more và các trường start_ms/end_ms.',
    '/community-lessons/shorts': 'Query có exclude từ danh sách excludeIds.',
    '/private-chat': 'JSON {partner_id}.',
    '/private-chat/messages': 'JSON {conversation_id, text}.',
    '/private-chat/block': 'POST {blocked_id}; GET query page, limit.',
    '/user/lesson-progress': 'POST JSON {lessonIds: [...]}; đọc batch tiến độ, không phải lưu vị trí xem.',
    '/user/info': 'GET hồ sơ; PUT multipart cập nhật thông tin. Một số setting học được lưu ở đây.',
    '/sentence-notes': 'GET có thể lọc lesson_id.',
    '/posts/comments/post/{id}': 'Query page, limit, ...; ID của post.',
    '/posts/comments/{id}/replies': 'Query page, limit, ...; ID của comment.',
}

items = sorted(inventory.values(), key=lambda r: (r['path'].split('/')[1], r['path'], r['method']))
for i, row in enumerate(items, 1):
    row['id'] = f'P{i:03}'
    row['group'] = GROUP_NAMES.get(row['path'].split('/')[1], row['path'].split('/')[1])
    row['verification'] = status(row['method'], row['path'])
    row['note'] = NOTES.get(row['path'], 'Có method/path trong service client; schema đầy đủ và response nghiệp vụ chưa được kiểm tra.')
    if row['multipart'] and 'multipart' not in row['note']:
        row['note'] += ' Wrapper dùng multipart/form-data.'

(ROOT / 'endpoint-inventory.json').write_text(json.dumps({'scope': 'HTTP calls exposed by inspected public web bundles, not private backend inventory', 'endpoints': items, 'unresolved_calls': unresolved}, ensure_ascii=False, indent=2), encoding='utf-8')
with (ROOT / 'endpoint-inventory.csv').open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['ID', 'Nhóm', 'Method', 'Path tương đối /api', 'Kiểm tra', 'Ghi chú', 'Source URL', 'Offset'])
    for r in items:
        writer.writerow([r['id'], r['group'], r['method'], r['path'], r['verification'], r['note'], r['evidence'][0]['source'], r['evidence'][0]['offset']])


def refs(spec):
    output = []
    for part in spec.split(';'):
        if not part:
            continue
        method, path = part.split(' ', 1)
        row = inventory[(method, path)]
        output.append(f"`{method} {path}` ([{row['id']}](endpoint-inventory.md#{row['id'].lower()}))")
    return '<br>'.join(output)


# Exactly one row per registered LEnglish endpoint in the requested scope.
comparison_data = '''lesson|GET /lessons|GET /lessons|Cùng catalog; LEnglish dùng keyword/page_size, Parroto dùng title/topic_slug/difficulty/limit.|P1: Giữ URL; thêm category_slug/tag_slug/difficulty, thống nhất metadata phân trang.
lesson|POST /lessons/import/youtube|POST /community-lessons/from-youtube|LEnglish chỉ admin; Parroto là bài cộng đồng với quota/mine/submit/retry.|P3: Giữ import admin; chỉ thêm bài cá nhân khi cần owner/quota/trạng thái duyệt.
lesson|GET /lessons/resume|GET /lessons/progress;POST /user/lesson-progress|Chỉ tương đương một phần: Parroto đọc tiến độ bài; chưa thấy API riêng trả bài gần nhất và vị trí video.|Giữ resume; nối FE. Không đổi sang progress chỉ vì tên gần giống.
lesson|GET /lessons/{lesson_slug}||Không tìm thấy service HTTP chi tiết bài curated tương ứng; frontend dùng trang Next tạo sẵn/pageProps. Không thấy source server fetch.|Giữ endpoint chi tiết + transcript. Không bịa GET /lessons/{slug} của Parroto.
lesson|GET /lessons/{lesson_slug}/progress|GET /user/completed-sentences/{id};GET /lessons/progress|Parroto đọc câu hoàn thành/tiến độ chủ đề; LEnglish lưu vị trí phát và subtitle.|Giữ. Có thể bổ sung tỷ lệ/câu hoàn thành; không gộp vị trí video với completion.
lesson|PUT /lessons/{lesson_slug}/progress||Chưa tìm thấy service tương đương lưu vị trí xem trong client đã khảo sát.|Giữ; FE cập nhật khi dừng/rời bài, chống ghi lùi do request trễ.
lesson|POST /lessons/{lesson_slug}/sessions||Chưa tìm thấy API start session cho dictation/shadowing curated; Parroto nộp câu trực tiếp.|Giữ session để quản lý lịch sử/mode; không bỏ vì Parroto không lộ start API.
lesson|POST /lessons/{lesson_slug}/sessions/{session_id}/answers|POST /sentences/submit;POST /sentences/submit-shadowing|LEnglish chấm chuỗi text (equality + similarity); enum shadowing hiện chưa nhận/chấm audio. Parroto có 2 luồng nộp câu, body qua {data: ...}.|P1: Hoàn thiện dictation feedback theo từ. P2: API nhận audio/chấm phát âm riêng; giữ answer theo session.
lesson|POST /lessons/{lesson_slug}/sessions/{session_id}/complete|POST /lessons/complete|Kết thúc session LEnglish chưa tự cập nhật LessonProgress; hoàn thành bài Parroto là thao tác riêng.|P1: Chốt điều kiện hoàn thành bài, đồng bộ progress/completed_at và chống retry trùng. Giữ URL.
lesson|DELETE /lessons/{lesson_slug}|DELETE /community-lessons/{id}|Không cùng tài nguyên/quyền: LEnglish xóa catalog admin; Parroto xóa bài cộng đồng.|Giữ quyền admin; nếu thêm bài cá nhân phải kiểm tra owner.
vocabulary|GET /vocabulary/books|GET /vocabulary/enc/public|Book ↔ deck về vai trò catalog. LEnglish thiếu thống kê học/đến hạn/thành thạo ở mức book và lọc category rõ ràng.|P1 SEnglish: Giữ books; bổ sung category và thống kê/progress trên card bộ từ.
vocabulary|GET /vocabulary/books/{book_slug}/topics|GET /vocabulary/enc/public/{id}/groups;GET /learning-vocabulary/groups-progress/{id}|Topic ↔ group. LEnglish trả count tiến độ cùng topic; Parroto có catalog nhóm và API progress riêng.|P1 SEnglish: Giữ topics và count; kiểm tra join ReviewProgress để chủ đề chưa học vẫn hiện.
vocabulary|GET /vocabulary/books/{book_slug}/topics/{topic_slug}/words|GET /vocabulary/enc/public/{id}/groups/{id}/cards|Word ↔ card về nội dung. Parroto dùng IDs; LEnglish dùng slug và Vocabulary ID.|Giữ URL; hoàn thiện nghĩa/IPA/audio/ví dụ và trạng thái SRS theo nhu cầu giao diện.
vocabulary|GET /vocabulary/topics/{topic_slug}/words|GET /vocabulary/enc/public/{id}/groups/{id}/cards|Shortcut LEnglish không cần book_slug; không có counterpart một-một trong service catalog Parroto.|Giữ alias nếu FE dùng; chuẩn hóa cùng response với route đầy đủ.
review|GET /review/today|GET /learning-vocabulary/stats;GET /learning-vocabulary/enc/due;GET /learning-vocabulary/enc/new|Today LEnglish thiên về số đến hạn/mục tiêu; Parroto tách thống kê và 2 hàng đợi.|P1 SEnglish: Thêm learned/due/mastered; thêm GET /review/queue toàn bộ books cho nút Ôn ngay. Đây là đề xuất mới.
review|GET /review/books/{book_slug}/topics/{topic_slug}/queue|GET /learning-vocabulary/enc/new;GET /learning-vocabulary/enc/due|LEnglish queue trong 1 topic; Parroto tách new/due và nhận query object. Chưa xác minh toàn bộ query runtime.|Giữ queue theo topic; mở rộng lọc status=new/due và bổ sung queue toàn cục, không cần đổi sang đường dẫn enc.
review|POST /review/books/{book_slug}/topics/{topic_slug}/words/{vocabulary_id}/check|POST /learning-vocabulary/submit|LEnglish endpoint chấm typing riêng; Parroto wrapper submitReview chung. Chưa chứng minh cùng rating/thuật toán.|P1: Chuẩn hóa response correct/feedback/next_review_at; tiến tới 1 contract attempt có mode nếu hợp lý.
review|POST /review/books/{book_slug}/topics/{topic_slug}/words/{vocabulary_id}/cloze|POST /learning-vocabulary/submit|LEnglish chấm cloze riêng; Parroto không lộ endpoint cloze riêng trong service đã đọc.|Giữ cloze. Đừng xóa feature chỉ để khớp URL; có thể chung xử lý với attempt.
review|POST /review/words/{vocabulary_id}|POST /learning-vocabulary/submit|LEnglish ghi rating SRS; Parroto submit review. Tương đương mục đích, chưa xác minh thuật toán.|P1 SEnglish: Giữ again/hard/good/easy; thống nhất chống ghi trùng và quyền sở hữu với attempts.
review|POST /review/books/{book_slug}/topics/{topic_slug}/sessions|POST /learning-vocabulary/session/start|Cùng bắt đầu ôn. Session LEnglish cố định topic; schema start Parroto được caller truyền vào.|P1 SEnglish: Giữ; thêm session tổng hợp due từ nhiều bộ cho Ôn ngay.
review|GET /review/sessions/{session_id}|GET /learning-vocabulary/session/current|LEnglish đọc phiên theo ID; Parroto đọc phiên hiện tại.|P2: Có thể thêm GET /review/sessions/current để resume; đặt route trước /{session_id}.
review|POST /review/sessions/{session_id}/attempts|POST /learning-vocabulary/submit|LEnglish có attempt_id chống retry; Parroto submitReview không để session ID trong path.|Giữ attempts; hợp nhất quy tắc rating/chấm với các endpoint check/cloze/review hiện có.
review|POST /review/sessions/{session_id}/complete||Không thấy wrapper HTTP session/complete của learning-vocabulary; không suy ra rằng backend không có.|Giữ hoàn thành phiên. P2: thêm lịch sử tương ứng GET /learning-vocabulary/session/history nếu sản phẩm cần.
wordlist|POST /word-lists|POST /user/vocabulary/decks|Tương đương một phần: list từ đã lưu LEnglish khác deck tự biên soạn Parroto có group/card/publish.|Giữ word-lists cho lưu từ trong bài; custom deck là feature riêng, chưa cần tách vội.
wordlist|GET /word-lists|GET /user/vocabulary/decks;GET /user/vocabulary-review|Parroto tách deck cá nhân và từ lưu nhanh; LEnglish dùng list có ngữ cảnh.|Giữ; bổ sung word_count/due_count nếu FE cần.
wordlist|POST /word-lists/{word_list_id}/words|POST /user/vocabulary-review;POST /user/vocabulary/cards|Từ lưu nhanh ↔ vocabulary-review; thẻ tự tạo ↔ vocabulary/cards. LEnglish lưu context và subtitle nguồn.|Giữ ngữ cảnh. P2: thêm xóa item/chuyển list/chống lưu trùng; không coi hai chức năng Parroto là một.
wordlist|GET /word-lists/{word_list_id}/words|GET /user/vocabulary-review;GET /user/vocabulary/groups/{id}/cards|LEnglish lọc list; Parroto lưu nhanh phân trang hoặc card theo group.|Giữ; kiểm tra pagination/search trên danh sách lớn.
wordlist|POST /word-lists/{word_list_id}/words/{vocabulary_id}/review|POST /learning-vocabulary/submit|LEnglish tái sử dụng ReviewProgress cho từ trong list; Parroto luồng học từ qua submitReview.|Giữ cùng SRS với books; tránh 2 lịch ôn cho cùng vocabulary_id.
wordlist|GET /word-lists/{word_list_id}/review/due|GET /learning-vocabulary/enc/due|LEnglish due theo list; Parroto due endpoint chung nhận query.|Giữ; queue tổng hợp cần bao gồm saved words và loại bỏ từ trùng.
dictionary|GET /dictionary/lookup|GET /dictionary/search;GET /dictionary/word/{id}|LEnglish lookup?word=...; Parroto search gợi ý và chi tiết word tách riêng. Search 200, detail hello 401.|P2: Giữ lookup; thêm GET /dictionary/search?word=...&locale=... nếu cần autocomplete.
engagement|POST /engagement/activity|POST /learning-time/start;POST /learning-time/heartbeat;POST /learning-time/end|LEnglish batch event_id chống trùng; Parroto session/sequence/delta_seconds.|Giữ batch hiện có. Nối FE với thời gian active, không cần đổi thành 3 API.
engagement|GET /engagement/summary|GET /user/stats;GET /streak;GET /level;GET /learning-vocabulary/stats|LEnglish tổng hợp goal/phút học/completion/streak; Parroto tách nhiều service.|Giữ summary; P2 bổ sung XP/level khi có nghiệp vụ cấp điểm phía server.
engagement|GET /engagement/activity|GET /streak/calendar|LEnglish query days và timezone preferences; Parroto from/to.|Giữ heatmap; thêm from/to nếu cần khoảng ngày tùy chọn, thống nhất timezone.
preferences|GET /preferences||UI settings Parroto chủ yếu ở localStorage parroto-app-config; một số setting học theo hồ sơ PUT /user/info. Không có service /preferences tương ứng tìm thấy.|Giữ đồng bộ goal/new words/timezone trên BE. UI playback/tooltip có thể lưu local.
preferences|PUT /preferences||Không có API preferences riêng tìm thấy; không thể coi localStorage là endpoint backend.|Giữ và mở rộng có chọn lọc. Không đổi sang user/info chỉ để giống Parroto.
'''
comparisons = []
for line in comparison_data.strip().splitlines():
    module, current, equivalent, difference, recommendation = line.split('|')
    comparisons.append({'module': module, 'current': current, 'parroto': equivalent, 'difference': difference, 'recommendation': recommendation})

actual = set()
prefixes = {'lesson': '/lessons', 'vocabulary': '/vocabulary', 'review': '/review', 'wordlist': '/word-lists', 'dictionary': '/dictionary', 'engagement': '/engagement', 'preferences': '/preferences'}
for module, prefix in prefixes.items():
    tree = ast.parse((BE / 'app/api/v1/endpoint' / (module + '.py')).read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for deco in node.decorator_list:
                if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute) and deco.func.attr in ['get', 'post', 'put', 'patch', 'delete'] and deco.args and isinstance(deco.args[0], ast.Constant):
                    actual.add(deco.func.attr.upper() + ' ' + prefix + deco.args[0].value)
expected = {r['current'] for r in comparisons}
if '--verify-workspace' in sys.argv:
    # Opt-in: this comparison records the pre-rename audit snapshot.
    assert actual == expected, {'missing': sorted(actual - expected), 'extra': sorted(expected - actual)}
assert len(comparisons) == 35

def safe(s):
    return s.replace('|', '\\|').replace('\n', ' ')

head = f'''# Kiểm tra lại endpoint Parroto và đối chiếu LEnglish

> Bảng này lưu snapshot trước đợt đổi URL. Endpoint LEnglish hiện tại và cách chuyển caller nằm trong [endpoint-renames.md](../endpoint-renames.md).

Ngày: 06/10/2026. Đây là báo cáo khảo sát, chưa thay đổi API runtime hay database.

## Phạm vi và mức xác minh

- Đọc manifest của **78 mục trang** và **208 asset JavaScript công khai** (gồm chunk tải bổ sung), trong web build `PI7un_8VTrLhTgj2L-BVI` của [Parroto](https://parroto.app/).
- Chuẩn hóa thành **{len(items)} cặp method + path template** từ các service HTTP tìm thấy. Đây là inventory của client web được khảo sát, **không phải cam kết tất cả endpoint backend**: admin, mobile, server-only và code không được publish không thể liệt kê đầy đủ từ web client.
- Base API Parroto: `https://api.parroto.app/api`; LEnglish: `/api/v1`. Path trong bảng đã bỏ base/prefix cho dễ đối chiếu.
- Đã gửi **51 GET không đăng nhập**: **16 HTTP 200, 35 HTTP 401**. 401 chỉ xác minh chốt xác thực của request; không chứng minh query/payload/response nghiệp vụ đúng. HTTP 200 của envelope mã hóa cũng không xác minh schema đã giải mã.
- POST/PUT/PATCH/DELETE: method và route được xác nhận từ source client, **chưa gọi để kiểm tra nghiệp vụ**. Không có tài khoản/token được cung cấp cho khảo sát.
- `{{id}}` trong inventory là placeholder chuẩn hóa từ biến minify, không khẳng định ID dạng UUID/int. Với nhiều ID, đọc ghi chú hoặc biểu thức source; bảng đối chiếu dùng đúng placeholder của LEnglish.
- Đối chiếu đủ **35 API LEnglish hiện có**, trừ user/feedback/token, dựa trên source workspace hiện tại, gồm cả thay đổi chưa commit. Endpoint Parroto có prefix `/user` nhưng phục vụ từ vựng/tiến độ vẫn được dùng làm tham chiếu chức năng; quản lý account không nằm trong phạm vi đề xuất sửa.
- Vocabulary: hướng sản phẩm vẫn theo [SEnglish](https://senglish.net/app/vocabulary); **chưa xác minh API backend của SEnglish**, các đề xuất dưới đây là thiết kế LEnglish dựa trên UI mong muốn.

## Những kết luận thay thế bảng cũ

1. Catalog từ thực dùng `GET /vocabulary/enc/public`, detail by ID/by slug, groups và cards. Các `/vocabulary/decks`, `/vocabulary/deck/...` cũ là URL factory/cache-key tham chiếu, không đủ bằng chứng để gọi là service HTTP hiện dùng.
2. Học từ mới/đến hạn thực dùng `GET /learning-vocabulary/enc/new` và `/enc/due`, không phải chỉ `/cards/new` và `/cards/due`.
3. Từ điển đã thấy `GET /dictionary/search` và `GET /dictionary/word/{{word}}`. Không còn ghi chung là chưa khảo sát.
4. Đã thấy các service streak, level, missions, notes, community lessons, custom deck, exam, social, shop và affiliate; inventory đính kèm có từng route và source.
5. Chưa thấy service HTTP chi tiết curated lesson, start lesson session, lưu vị trí video hoặc `/preferences` trong client. Với trang Next dựng sẵn, endpoint được server dùng để lấy pageProps **không lộ trong source client**. Không thể kết luận backend không có.
6. Không xác định được tên database/tables backend Parroto. Không cần đổi DB hoặc bảng LEnglish chỉ để đổi cách đặt URL.

## Bảng đối chiếu từng API LEnglish

P1: đợt ưu tiên đầu; P2: đợt sau; P3: tùy nhu cầu. “Giữ” nghĩa là chức năng/hợp đồng hiện có hợp lý, không cần đổi URL. Link Pxxx trỏ tới method, source và mức kiểm tra Parroto cụ thể.

| # | API LEnglish hiện có | API Parroto đối chiếu | Khác biệt / bằng chứng | Hướng sửa dần |
| --- | --- | --- | --- | --- |
'''
body = []
for i, r in enumerate(comparisons, 1):
    equivalent = refs(r['parroto']) if r['parroto'] else 'Không tìm thấy counterpart HTTP trong client đã đọc'
    body.append(f"| {i} | `{r['current']}` | {equivalent} | {safe(r['difference'])} | {safe(r['recommendation'])} |")
tail = '''

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
'''
(ROOT / 'comparison.md').write_text(head + '\n'.join(body) + tail, encoding='utf-8')
inventory_md = f'''# Inventory HTTP Parroto từ web client

06/10/2026: **{len(items)} cặp method/path template** trong {len(evidence['assets'])} asset JS đọc thành công. Không đồng nghĩa tất cả endpoint backend. Base URL: `https://api.parroto.app/api`.

Xem [phạm vi, giới hạn và đối chiếu đủ 35 API LEnglish](comparison.md). `{{id}}` là biến path đã chuẩn hóa; không xác minh kiểu ID. Offset là vị trí ký tự trong file JavaScript minified, không phải số dòng.

HTTP 200/401 chỉ áp dụng GET mẫu đã ghi trong [log](http-read-checks.json). Các method ghi chỉ kiểm tra ở source. Mỗi source link bên dưới hỗ trợ method/path; phần kiến nghị LEnglish là thiết kế riêng.

'''
for group, title in GROUP_NAMES.items():
    rows = [r for r in items if r['path'].split('/')[1] == group]
    if not rows:
        continue
    inventory_md += f'## {title}\n\n| ID | Method và endpoint | Mức kiểm tra | Chi tiết đã thấy / giới hạn | Bằng chứng |\n| --- | --- | --- | --- | --- |\n'
    for r in rows:
        ev = r['evidence'][0]
        source_name = ev['source'].split('/')[-1]
        inventory_md += f"| <a id=\"{r['id'].lower()}\"></a>{r['id']} | `{r['method']} {r['path']}` | {r['verification']} | {safe(r['note'])} | [{source_name}]({ev['source']}) · offset {ev['offset']} |\n"
    inventory_md += '\n'
factories = {}
for r in evidence['records']:
    if r['kind'] == 'factory':
        factories.setdefault(r['expression'], r)
inventory_md += '## URL factory / cache key: không tự coi là endpoint HTTP\n\nCác entry này xuất hiện trong client nhưng không được thêm vào inventory chỉ vì có string URL. Nếu có lời gọi service độc lập, route đó đã được ghi ở các nhóm trên. Biểu thức giữ dạng minify để không bịa query/schema.\n\n| Tên trong source | Biểu thức | Bằng chứng |\n| --- | --- | --- |\n'
for r in factories.values():
    inventory_md += f"| `{r.get('name') or ''}` | `{safe(r['expression'])}` | [source]({r['source']}) · offset {r['offset']} |\n"
inventory_md += '\n## Kiểm tra tính đầy đủ của extraction\n\n'
inventory_md += f'Có {len(unresolved)} call record không chuẩn hóa được tự động; nếu khác 0 cần đọc source trước khi coi inventory hoàn chỉnh trong phạm vi đã khảo sát. Số raw call có thể trùng do cùng module nằm trong nhiều chunk. Không kiểm chứng rằng code nhánh generic /grammar đang được UI sử dụng. Socket.IO/WebRTC không được gộp vào bảng HTTP.\n'
(ROOT / 'endpoint-inventory.md').write_text(inventory_md, encoding='utf-8')
print(json.dumps({'parroto_method_path_pairs': len(items), 'lenglish_endpoints_compared': len(comparisons), 'unresolved_call_records': len(unresolved), 'status_counts': dict(Counter(r['status'] for r in checks['results']))}, ensure_ascii=True))
