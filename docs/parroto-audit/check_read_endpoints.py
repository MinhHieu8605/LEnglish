"""Probe read-only client-referenced routes without credentials or bypass headers."""
import concurrent.futures
import datetime
import json
import pathlib
import urllib.error
import urllib.request

output = pathlib.Path(__file__).parent
evidence = json.loads((output / "frontend-evidence.json").read_text(encoding="utf-8"))
paths = sorted({record["literal"] for record in evidence["records"] if record["kind"] == "call" and record["method"] == "GET" and record["expression"] == json.dumps(record["literal"]) and record["literal"].startswith("/")})
# Use one small-page request for collection routes. Do not substitute invented IDs.
collection = {"/lessons", "/vocabulary/enc/public", "/vocabulary/enc/public/user-published", "/learning-vocabulary/cards", "/learning-vocabulary/enc/new", "/learning-vocabulary/enc/due", "/learning-vocabulary/session/history", "/exams/published/sets", "/exams/sessions/history", "/notifications", "/user/vocabulary/decks", "/games/feed", "/posts"}
query = {"/dictionary/search": "?word=hello&locale=en"}
paths = [path + query.get(path, "?limit=1&page=1" if path in collection else "") for path in paths]
paths.extend(["/dictionary/word/hello", "/lessons/progress?topic_id=", "/community-lessons?limit=1&page=1"])
paths = sorted(set(paths))


def probe(path):
    url = "https://api.parroto.app/api" + path
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json", "X-User-Timezone": "Asia/Ho_Chi_Minh"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read(16384).decode("utf-8", errors="replace")
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
        body = error.read(16384).decode("utf-8", errors="replace")
    except Exception as error:
        return {"path": path, "url": url, "error": str(error)}
    result = {"path": path, "url": url, "status": status}
    try:
        data = json.loads(body)
        result["top_level_keys"] = list(data) if isinstance(data, dict) else ["array"]
        if isinstance(data, dict):
            for key in ("status", "code", "message", "error"):
                if isinstance(data.get(key), (str, int, bool)):
                    result[key if key != "status" else "body_status"] = data[key]
    except ValueError:
        result["body_format"] = "non-JSON or truncated JSON"
    return result


with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(probe, paths))
(output / "http-read-checks.json").write_text(json.dumps({"checked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "authentication": "none", "methods": ["GET"], "bypass_headers": False, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
for result in results:
    print(result.get("status", "ERROR"), result["path"], result.get("message", result.get("error", "")))
