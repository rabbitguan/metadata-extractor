from __future__ import annotations

import csv
import json
import mimetypes
import re
import sys
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import run_interface_tests as runner


HOST = "127.0.0.1"
PORT = 8765
ROOT_DIR = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT_DIR / "tests"
EDITOR_DIR = TESTS_DIR / "editor"
CASES_DIR = TESTS_DIR / "cases"
CASE_FILES = {
    "register": CASES_DIR / "register_cases.csv",
    "query": CASES_DIR / "query_cases.csv",
}
CASE_FIELDS = [
    "id",
    "enabled",
    "endpoint",
    "category",
    "input_type",
    "source",
    "mode",
    "strategy",
    "payload_or_file",
    "expected_status",
    "expected_checks",
    "description",
    "expected_nl",
    "manual_conclusion",
    "last_status",
    "last_run_at",
]


def normalize_case(row: dict[str, str], endpoint: str) -> dict[str, str]:
    normalized = {field: (row.get(field) or "") for field in CASE_FIELDS}
    normalized["endpoint"] = normalized.get("endpoint") or endpoint
    normalized["enabled"] = normalized.get("enabled") or "yes"
    normalized["mode"] = normalized.get("mode") or "common"
    normalized["expected_status"] = normalized.get("expected_status") or "200"
    return normalized


def load_case_rows(endpoint: str) -> list[dict[str, str]]:
    path = CASE_FILES[endpoint]
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as file_obj:
        return [normalize_case(row, endpoint) for row in csv.DictReader(file_obj)]


def write_case_rows(endpoint: str, rows: list[dict[str, str]]) -> None:
    path = CASE_FILES[endpoint]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=CASE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(normalize_case(row, endpoint))


def load_all_cases() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for endpoint in ("register", "query"):
        for row in load_case_rows(endpoint):
            row["case_file"] = CASE_FILES[endpoint].relative_to(ROOT_DIR).as_posix()
            rows.append(row)
    return rows


def generate_case_id(endpoint: str) -> str:
    prefix = "R" if endpoint == "register" else "Q"
    max_number = 0
    for row in load_case_rows(endpoint):
        case_id = row.get("id", "")
        if case_id.startswith(prefix) and case_id[1:].isdigit():
            max_number = max(max_number, int(case_id[1:]))
    return f"{prefix}{max_number + 1:03d}"


def safe_sample_name(name: str, fallback: str) -> str:
    suffix = Path(name or "").suffix.lower()
    if suffix not in {".json", ".xml", ".txt", ".html"}:
        suffix = ".txt"
    stem = Path(name or "").stem or fallback
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-._") or fallback
    return f"{stem}{suffix}"


def upsert_case(row: dict[str, str]) -> dict[str, str]:
    endpoint = row.get("endpoint", "")
    if endpoint not in CASE_FILES:
        raise ValueError("endpoint must be register or query")
    normalized = normalize_case(row, endpoint)
    if not normalized.get("id"):
        normalized["id"] = generate_case_id(endpoint)

    rows = load_case_rows(endpoint)
    replaced = False
    for index, existing in enumerate(rows):
        if existing.get("id") == normalized["id"]:
            rows[index] = normalized
            replaced = True
            break
    if not replaced:
        rows.append(normalized)
    write_case_rows(endpoint, rows)
    return normalized


def infer_contains_value(response_body) -> str:
    title = runner.find_first_non_empty_title(response_body)
    if title:
        if isinstance(title, list):
            for item in title:
                if isinstance(item, dict) and item.get("name"):
                    return str(item["name"])
            return str(title[0]) if title else ""
        return str(title)
    if isinstance(response_body, dict):
        message = response_body.get("message")
        if message:
            return str(message)
    return ""


def default_expected_checks(endpoint: str, status_code: int, response_body) -> str:
    if status_code >= 400:
        message = response_body.get("message") if isinstance(response_body, dict) else ""
        return f"message={message}" if message else ""

    if endpoint == "query":
        checks = ["items"]
        items = response_body.get("items") if isinstance(response_body, dict) else None
        if isinstance(items, list) and any(isinstance(item, dict) and item.get("status") == "ok" for item in items):
            checks.append("any_item_ok")
        return ";".join(checks)

    checks = []
    if isinstance(response_body, dict):
        if response_body.get("核心元数据"):
            checks.append("核心元数据")
        if response_body.get("领域元数据"):
            checks.append("领域元数据")
        if response_body.get("zh"):
            checks.append("zh.核心元数据")
        if response_body.get("en"):
            checks.append("en.Core Metadata")
    checks.append("title_non_empty")
    contains_value = infer_contains_value(response_body)
    if contains_value:
        checks.append(f"contains={contains_value.replace(';', ' ')}")
    return ";".join(checks)


def default_expected_text(endpoint: str, response_body) -> str:
    if endpoint == "query":
        return "应返回标识符查询结果，至少包含 items 列表和每个标识符的处理状态。"
    title = infer_contains_value(response_body)
    if title:
        return f"应返回元数据结果，并包含资源标题或核心内容：{title}"
    return "应返回元数据结果，并包含核心元数据结构。"


def capture_case(payload: dict) -> dict[str, str]:
    endpoint = payload.get("endpoint") or "register"
    if endpoint not in CASE_FILES:
        raise ValueError("endpoint must be register or query")

    case_id = generate_case_id(endpoint)
    request_payload = payload.get("request_payload") or {}
    response_body = payload.get("response_body")
    status_code = int(payload.get("status_code") or 200)
    source = payload.get("source") or request_payload.get("source") or ("identifier" if endpoint == "query" else "text")
    input_type = payload.get("input_type") or source
    payload_or_file = payload.get("payload_or_file") or ""

    if endpoint == "query":
        if request_payload.get("identifiers") is not None:
            identifiers = request_payload.get("identifiers")
            payload_or_file = json.dumps(identifiers, ensure_ascii=False) if isinstance(identifiers, list) else str(identifiers)
            input_type = "identifier"
        elif request_payload.get("text"):
            payload_or_file = str(request_payload.get("text"))
            input_type = "text"
        elif request_payload.get("html"):
            payload_or_file = str(request_payload.get("html"))
            input_type = "html"
    elif input_type == "upload":
        file_content = payload.get("file_content") or ""
        file_name = safe_sample_name(payload.get("file_name") or "", case_id)
        sample_path = TESTS_DIR / "samples" / "upload" / file_name
        if file_content:
            sample_path.write_text(file_content, encoding="utf-8")
        payload_or_file = sample_path.relative_to(ROOT_DIR).as_posix()
    elif request_payload.get("url"):
        payload_or_file = str(request_payload.get("url"))
        input_type = "url"
    elif request_payload.get("text"):
        payload_or_file = str(request_payload.get("text"))
        input_type = "text"
    elif request_payload.get("html"):
        payload_or_file = str(request_payload.get("html"))
        input_type = "web"

    row = normalize_case({
        "id": case_id,
        "enabled": "yes",
        "endpoint": endpoint,
        "category": payload.get("category") or "前端捕获",
        "input_type": input_type,
        "source": source,
        "mode": payload.get("mode") or request_payload.get("mode") or "common",
        "strategy": payload.get("strategy") or request_payload.get("strategy") or "",
        "payload_or_file": payload_or_file,
        "expected_status": str(status_code),
        "expected_checks": payload.get("expected_checks") or default_expected_checks(endpoint, status_code, response_body),
        "description": payload.get("description") or f"前端捕获 {endpoint} {case_id}",
        "expected_nl": payload.get("expected_nl") or default_expected_text(endpoint, response_body),
        "manual_conclusion": payload.get("manual_conclusion") or "",
        "last_status": payload.get("last_status") or "",
        "last_run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if payload.get("last_status") else "",
    }, endpoint)
    return upsert_case(row)


def delete_case(endpoint: str, case_id: str) -> bool:
    if endpoint not in CASE_FILES:
        raise ValueError("endpoint must be register or query")
    rows = load_case_rows(endpoint)
    next_rows = [row for row in rows if row.get("id") != case_id]
    write_case_rows(endpoint, next_rows)
    return len(next_rows) != len(rows)


def as_runner_case(row: dict[str, str]) -> runner.TestCase:
    expected_status = row.get("expected_status") or "200"
    expected_checks = [
        item.strip()
        for item in (row.get("expected_checks") or "").split(";")
        if item.strip()
    ]
    return runner.TestCase(
        id=row.get("id", ""),
        endpoint=row.get("endpoint", ""),
        category=row.get("category", ""),
        input_type=row.get("input_type", ""),
        source=row.get("source", ""),
        mode=row.get("mode", "common"),
        strategy=row.get("strategy", ""),
        payload_or_file=row.get("payload_or_file", ""),
        expected_status=int(str(expected_status).strip() or "200"),
        expected_checks=expected_checks,
        description=row.get("description", ""),
    )


def run_case(row: dict[str, str], base_url: str, timeout: int) -> dict:
    case = as_runner_case(normalize_case(row, row.get("endpoint", "")))
    request_preview = {
        "url": f"{base_url.rstrip('/')}/{case.endpoint}",
        "endpoint": case.endpoint,
        "input_type": case.input_type,
        "headers": {
            "X-User-Id": "interface-test-user",
            "X-User-Name": "interface-test",
            "X-User-Email": "interface-test@example.com",
        },
    }
    if case.endpoint == "register" and case.input_type == "upload":
        request_preview["form"] = {
            "source": case.source or "upload",
            "mode": case.mode or "common",
            "strategy": case.strategy,
            "file": case.payload_or_file,
        }
    else:
        request_preview["json"] = runner.build_json_payload(case)

    status_code, body, raw_text = runner.send_case(case, base_url, timeout)
    passed, passed_checks, failed_checks = runner.evaluate(case, status_code, body)
    conclusion = "通过" if passed else "失败"

    saved_row = normalize_case(row, case.endpoint)
    saved_row["last_status"] = conclusion
    saved_row["last_run_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    upsert_case(saved_row)

    return {
        "case": saved_row,
        "request": request_preview,
        "status_code": status_code,
        "response_body": body,
        "response_text": raw_text,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "conclusion": conclusion,
        "summary": runner.compact_body(body),
    }


def resolve_under_tests(raw_path: str) -> Path:
    if not raw_path:
        raise ValueError("path is required")
    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT_DIR / path
    resolved = path.resolve()
    tests_root = TESTS_DIR.resolve()
    if resolved != tests_root and tests_root not in resolved.parents:
        raise ValueError("path must be under tests/")
    if not resolved.is_file():
        raise FileNotFoundError(raw_path)
    return resolved


class Handler(BaseHTTPRequestHandler):
    server_version = "MetadataTestEditor/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/cases":
            self.send_json({"cases": load_all_cases()})
            return
        if parsed.path == "/api/sample":
            params = parse_qs(parsed.query)
            try:
                sample_path = resolve_under_tests((params.get("path") or [""])[0])
                self.send_json({
                    "path": sample_path.relative_to(ROOT_DIR).as_posix(),
                    "content": sample_path.read_text(encoding="utf-8-sig"),
                })
            except Exception as error:
                self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        self.serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = self.read_json()
            if parsed.path == "/api/cases/capture":
                saved = capture_case(payload)
                self.send_json({"case": saved, "cases": load_all_cases()})
                return
            if parsed.path == "/api/cases/save":
                saved = upsert_case(payload.get("case") or payload)
                self.send_json({"case": saved, "cases": load_all_cases()})
                return
            if parsed.path == "/api/cases/new":
                endpoint = payload.get("endpoint") or "register"
                if endpoint not in CASE_FILES:
                    raise ValueError("endpoint must be register or query")
                row = normalize_case({
                    "id": generate_case_id(endpoint),
                    "endpoint": endpoint,
                    "enabled": "yes",
                    "category": "临时",
                    "input_type": "url" if endpoint == "register" else "identifier",
                    "source": "url" if endpoint == "register" else "identifier",
                    "mode": "common",
                    "expected_status": "200",
                    "description": "新测试用例",
                }, endpoint)
                saved = upsert_case(row)
                self.send_json({"case": saved, "cases": load_all_cases()})
                return
            if parsed.path == "/api/cases/delete":
                deleted = delete_case(payload.get("endpoint", ""), payload.get("id", ""))
                self.send_json({"deleted": deleted, "cases": load_all_cases()})
                return
            if parsed.path == "/api/cases/run":
                result = run_case(
                    payload.get("case") or payload,
                    payload.get("base_url") or runner.DEFAULT_BASE_URL,
                    int(payload.get("timeout") or runner.DEFAULT_TIMEOUT_SECONDS),
                )
                self.send_json(result)
                return
            self.send_json({"error": "unknown endpoint"}, HTTPStatus.NOT_FOUND)
        except Exception as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_cors_headers()
        self.end_headers()

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or "0")
        if not length:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(data)

    def send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def serve_static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        relative = path.lstrip("/")
        target = (EDITOR_DIR / relative).resolve()
        editor_root = EDITOR_DIR.resolve()
        if target != editor_root and editor_root not in target.parents:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not target.exists() or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = target.read_bytes()
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args) -> None:
        print(f"[editor] {self.address_string()} - {format % args}")


def main() -> int:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Test editor running at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping test editor.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
