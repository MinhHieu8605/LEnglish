"""Read published Parroto web assets; never authenticate or mutate remote data."""
import concurrent.futures
import hashlib
import json
import pathlib
import re
import sys
import time
import urllib.request

cache = pathlib.Path(sys.argv[1])
output = pathlib.Path(__file__).parent
cache.mkdir(parents=True, exist_ok=True)


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


page_url = "https://parroto.app/dictation"
page = download(page_url)
scripts = re.findall(r'<script[^>]+src="([^"]+)"', page)
manifest_path = next(path for path in scripts if path.endswith("_buildManifest.js"))
manifest_url = "https://parroto.app" + manifest_path
manifest = download(manifest_url)
(cache / "manifest.js").write_text(manifest, encoding="utf-8")
assets = set(re.findall(r'"(static/chunks/[^"\s]+\.js)"', manifest))
urls = {"https://parroto.app/_next/" + path for path in assets}
urls.update("https://parroto.app" + path for path in scripts if path.startswith("/_next/") and path.endswith(".js"))
pages = sorted(set(re.findall(r'"(/[^"\s]*)":\[', manifest)))
results = []


def fetch_asset(url):
    name = hashlib.sha256(url.encode()).hexdigest()[:16] + ".js"
    path = cache / name
    try:
        source = path.read_text(encoding="utf-8") if path.exists() else download(url)
        path.write_text(source, encoding="utf-8")
        return {"url": url, "cache_file": name, "bytes": len(source.encode()), "status": "ok"}
    except Exception as error:
        return {"url": url, "status": "error", "error": str(error)}


with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    for index, result in enumerate(executor.map(fetch_asset, sorted(urls)), 1):
        results.append(result)
        if index % 20 == 0:
            print(f"Read {index}/{len(urls)} assets", flush=True)

# Discover lazy chunks from the exact filename maps in the published webpack runtime.
webpack = next(result for result in results if "/webpack-" in result["url"])
runtime = (cache / webpack["cache_file"]).read_text(encoding="utf-8")
runtime_start = runtime.index(".u=")
runtime_end = runtime.index(".miniCssF", runtime_start)
runtime_maps = re.findall(r'\{((?:\d+:"[a-f0-9]+",?)+)\}', runtime[runtime_start:runtime_end])
if len(runtime_maps) == 2:
    names, hashes = (dict(re.findall(r'(\d+):"([a-f0-9]+)"', mapping)) for mapping in runtime_maps)
    lazy_urls = {f"https://parroto.app/_next/static/chunks/{names.get(identifier, identifier)}.{digest}.js" for identifier, digest in hashes.items()} - urls
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results.extend(executor.map(fetch_asset, sorted(lazy_urls)))
    print(f"Read {len(lazy_urls)} additional lazy chunks", flush=True)
else:
    print("Runtime filename map not recognized", flush=True)


def first_argument(source, start):
    depth = 0
    quote = None
    escaped = False
    for pos in range(start, min(len(source), start + 4000)):
        char = source[pos]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in "\"'`":
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            if depth == 0:
                return source[start:pos]
            depth -= 1
        elif char in ",;" and depth == 0:
            return source[start:pos]
    return source[start:start + 300]


records = []
methods = re.compile(r'(?<![\w$])(?P<client>[\w$]+(?:\.[\w$]+)*)\.(?P<method>get|post|put|patch|delete|request|postWithFormData|putWithFormData)\(')
factories = re.compile(r'(?<![\w$])(?P<name>[\w$]+):(?:\([^)]*\)|[\w$]+)=>')
returns = re.compile(r'\breturn(?=["\x27`])')
for result in results:
    if result["status"] != "ok":
        continue
    source = (cache / result["cache_file"]).read_text(encoding="utf-8")
    if result["bytes"] > 1_000_000:
        print("Inspecting " + result["url"], flush=True)
    for pattern, kind in ((methods, "call"), (factories, "factory"), (returns, "return")):
        for match in pattern.finditer(source):
            expression = first_argument(source, match.end())
            literal = re.match(r'["\x27`]([^"\x27`]+)', expression)
            api_client = kind == "call" and (match.groupdict().get("client") or "").endswith(".E")
            if not api_client and (not literal or not (literal.group(1).startswith("/") or re.match(r'^(?:lessons|sentences|topics|dictionary|community-lessons|learning-vocabulary|vocabulary|user|exams)/', literal.group(1)))):
                continue
            records.append({
                "kind": kind,
                "method": match.groupdict().get("method", "UNKNOWN").upper(),
                "client": match.groupdict().get("client"),
                "name": match.groupdict().get("name"),
                "literal": literal.group(1) if literal else "<dynamic>",
                "expression": expression[:1800],
                "source": result["url"],
                "offset": match.start(),
                "context": source[max(0, match.start() - 170):match.start() + 550],
            })
    endpoint_prefixes = "lessons|sentences|topics|categories|tags|dictionary|community-lessons|learning-vocabulary|learning-time|vocabulary|vocabulary-errors|sentence-notes|sentence-errors|exams|user|auth|settings|preferences|streak|level|missions|wallet|notifications|private-chat|community-chat|community-stats|posts|friends|games|leaderboard|shop|affiliate|prices|webhooks|promo|activation-codes|feedback"
    literals = re.compile(r'["\x27`]((?:/)?(?:' + endpoint_prefixes + r')(?:[/?][^"\x27`]*|))(?=["\x27`])["\x27`]')
    already = {(row["literal"], row["source"]) for row in records}
    for match in literals.finditer(source):
        value = match.group(1)
        if (value, result["url"]) in already:
            continue
        records.append({"kind": "literal", "method": "UNKNOWN", "client": None, "name": None, "literal": value, "expression": first_argument(source, match.start())[:1800], "source": result["url"], "offset": match.start(), "context": source[max(0, match.start()-170):match.end()+380]})

report = {"page_url": page_url, "manifest_url": manifest_url, "pages": pages, "assets": results, "records": records, "note": "Static client references, not a server route inventory or proof of successful authenticated requests."}
(output / "frontend-evidence.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
(cache / "asset-index.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"pages": len(pages), "assets": len(results), "successful": sum(result["status"] == "ok" for result in results), "bytes": sum(result.get("bytes", 0) for result in results), "records": len(records), "errors": [result for result in results if result["status"] != "ok"]}, ensure_ascii=False), flush=True)
