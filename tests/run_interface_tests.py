from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT_DIR / "tests" / "cases"
REPORTS_DIR = ROOT_DIR / "tests" / "reports"
CASE_PATHS = {
    "register": CASES_DIR / "register_cases.csv",
    "query": CASES_DIR / "query_cases.csv",
}
DEFAULT_BASE_URL = "http://127.0.0.1:4000"
DEFAULT_TIMEOUT_SECONDS = 60


@dataclass
class TestCase:
    id: str
    endpoint: str
    category: str
    input_type: str
    source: str
    mode: str
    strategy: str
    payload_or_file: str
    expected_status: int
    expected_checks: list[str]
    description: str


def resolve_case_file(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT_DIR / path
    return path


def read_payload_text(value: str) -> str:
    if not value:
        return ""
    path = resolve_case_file(value)
    if path.exists():
        return path.read_text(encoding="utf-8-sig")
    return value


def parse_identifier_value(value: str) -> Any:
    text = value.strip()
    if text.startswith("["):
        return json.loads(text)
    return read_payload_text(text)


def build_json_payload(case: TestCase) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source": case.source or ("identifier" if case.endpoint == "query" else "text"),
        "mode": case.mode or "common",
    }
    if case.strategy:
        payload["strategy"] = case.strategy

    if case.endpoint == "query":
        if case.input_type == "identifier":
            payload["identifiers"] = parse_identifier_value(case.payload_or_file)
        elif case.input_type == "text":
            payload["text"] = read_payload_text(case.payload_or_file)
        elif case.input_type == "html":
            payload["html"] = read_payload_text(case.payload_or_file)
        else:
            payload["text"] = read_payload_text(case.payload_or_file)
        return payload

    if case.input_type == "url":
        payload["url"] = case.payload_or_file
    elif case.input_type == "text":
        payload["text"] = read_payload_text(case.payload_or_file)
        payload["title"] = Path(case.payload_or_file).name if case.payload_or_file else ""
    elif case.input_type == "web":
        payload["text"] = read_payload_text(case.payload_or_file)
        payload["html"] = read_payload_text(case.payload_or_file)
    elif case.input_type == "upload_json_body":
        payload["text"] = read_payload_text(case.payload_or_file)
        payload["title"] = Path(case.payload_or_file).name if case.payload_or_file else ""
    else:
        payload["text"] = read_payload_text(case.payload_or_file)
    return payload


def send_case(case: TestCase, base_url: str, timeout: int) -> tuple[int, Any, str]:
    url = f"{base_url.rstrip('/')}/{case.endpoint}"
    headers = {
        "X-User-Id": "interface-test-user",
        "X-User-Name": "interface-test",
        "X-User-Email": "interface-test@example.com",
    }

    if case.endpoint == "register" and case.input_type == "upload":
        file_path = resolve_case_file(case.payload_or_file)
        data = {
            "source": case.source or "upload",
            "mode": case.mode or "common",
        }
        if case.strategy:
            data["strategy"] = case.strategy
        with file_path.open("rb") as file_obj:
            response = requests.post(
                url,
                headers=headers,
                data=data,
                files={"file": (file_path.name, file_obj)},
                timeout=timeout,
            )
    else:
        response = requests.post(url, headers=headers, json=build_json_payload(case), timeout=timeout)

    try:
        body = response.json()
    except ValueError:
        body = response.text
    return response.status_code, body, response.text


def value_exists(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def parse_path_segment(segment: str) -> tuple[str, int | None]:
    if "[" in segment and segment.endswith("]"):
        key, index_text = segment[:-1].split("[", 1)
        return key, int(index_text)
    return segment, None


def get_path_value(data: Any, path: str) -> tuple[bool, Any]:
    current = data
    for segment in path.split("."):
        key, index = parse_path_segment(segment)
        if key:
            if not isinstance(current, dict) or key not in current:
                return False, None
            current = current[key]
        if index is not None:
            if not isinstance(current, list) or index >= len(current):
                return False, None
            current = current[index]
    return True, current


def find_first_non_empty_title(data: Any) -> Any:
    preferred_paths = [
        "zh.核心元数据.标题",
        "en.Core Metadata.Title",
        "zh.核心元数据.metadatas[0].标题",
        "en.Core Metadata.metadatas[0].Title",
        "核心元数据.metadatas[0].标题",
        "核心元数据.metadatas[0].Title",
        "核心元数据.metadatas[0].titles[0].name",
        "领域元数据.metadatas[0].标题",
        "领域元数据.metadatas[0].Title",
        "领域元数据.metadatas[0].titles[0].name",
    ]
    for path in preferred_paths:
        found, value = get_path_value(data, path)
        if found and value_exists(value):
            return value

    if isinstance(data, dict):
        for key in ("标题", "Title", "title", "name"):
            value = data.get(key)
            if value_exists(value):
                return value
        for value in data.values():
            title = find_first_non_empty_title(value)
            if value_exists(title):
                return title
    if isinstance(data, list):
        for item in data:
            title = find_first_non_empty_title(item)
            if value_exists(title):
                return title
    return None


def response_text_for_search(data: Any) -> str:
    if isinstance(data, (dict, list)):
        return json.dumps(data, ensure_ascii=False, sort_keys=True)
    return str(data)


def check_one(data: Any, check: str) -> tuple[bool, str]:
    if check == "title_non_empty":
        title = find_first_non_empty_title(data)
        return value_exists(title), f"title_non_empty={title!r}"

    if check.startswith("contains="):
        expected = check.split("=", 1)[1].strip()
        passed = expected in response_text_for_search(data)
        return passed, f"contains={expected}"

    if check.startswith("not_contains="):
        unexpected = check.split("=", 1)[1].strip()
        passed = unexpected not in response_text_for_search(data)
        return passed, f"not_contains={unexpected}"

    if "~=" in check:
        path, expected = check.split("~=", 1)
        found, value = get_path_value(data, path.strip())
        passed = found and expected.strip() in response_text_for_search(value)
        return passed, f"{path.strip()}~={expected.strip()}"

    if check == "any_item_ok":
        items = data.get("items") if isinstance(data, dict) else None
        passed = isinstance(items, list) and any(item.get("status") == "ok" for item in items if isinstance(item, dict))
        return passed, "any_item_ok"

    if check == "any_item_error":
        items = data.get("items") if isinstance(data, dict) else None
        passed = isinstance(items, list) and any(item.get("status") == "error" for item in items if isinstance(item, dict))
        return passed, "any_item_error"

    if "=" in check:
        path, expected = check.split("=", 1)
        found, value = get_path_value(data, path.strip())
        passed = found and str(value) == expected.strip()
        return passed, f"{path.strip()}={value!r}"

    found, value = get_path_value(data, check)
    return found and value_exists(value), check


def evaluate(case: TestCase, status_code: int, body: Any) -> tuple[bool, list[str], list[str]]:
    passed_checks: list[str] = []
    failed_checks: list[str] = []

    status_ok = status_code == case.expected_status
    if status_ok:
        passed_checks.append(f"HTTP {case.expected_status}")
    else:
        failed_checks.append(f"HTTP expected {case.expected_status}, got {status_code}")

    for check in case.expected_checks:
        passed, detail = check_one(body, check)
        if passed:
            passed_checks.append(detail)
        else:
            failed_checks.append(detail)

    return status_ok and not failed_checks, passed_checks, failed_checks


def compact_body(body: Any) -> str:
    if isinstance(body, dict):
        if "message" in body:
            return f"message={body.get('message')}"
        if isinstance(body.get("items"), list):
            statuses = [
                f"{item.get('identifier', '')}:{item.get('status', '')}"
                for item in body["items"]
                if isinstance(item, dict)
            ]
            return "items=" + ", ".join(statuses[:5])
        title = find_first_non_empty_title(body)
        if value_exists(title):
            return f"title={title}"
        return "JSON object"
    text = str(body).replace("\n", " ").strip()
    return text[:200] if text else ""


def markdown_escape(value: Any) -> str:
    text = str(value or "")
    text = text.replace("\r", " ").replace("\n", "<br>")
    text = text.replace("|", "\\|")
    return text


def normalize_status(value: str) -> str:
    text = value.strip()
    if text in {"通过", "pass", "passed", "ok"}:
        return "通过"
    if text in {"失败", "不通过", "fail", "failed", "error"}:
        return "不通过"
    return "未填写"


def read_case_results(endpoint_filter: str | None, category_filter: str | None) -> list[dict[str, str]]:
    selected_paths = {
        endpoint: path
        for endpoint, path in CASE_PATHS.items()
        if not endpoint_filter or endpoint == endpoint_filter
    }

    results: list[dict[str, str]] = []
    for endpoint, path in selected_paths.items():
        if not path.exists():
            raise FileNotFoundError(f"Case file not found: {path}")
        with path.open("r", encoding="utf-8-sig", newline="") as file_obj:
            for row in csv.DictReader(file_obj):
                if (row.get("enabled") or "").strip().lower() != "yes":
                    continue
                category = (row.get("category") or "").strip()
                if category_filter and category != category_filter:
                    continue
                status = normalize_status(row.get("last_status") or "")
                results.append(
                    {
                        "id": (row.get("id") or "").strip(),
                        "endpoint": (row.get("endpoint") or endpoint).strip(),
                        "category": category,
                        "mode": (row.get("mode") or "").strip(),
                        "input": (row.get("payload_or_file") or "").strip(),
                        "case": (row.get("description") or "").strip(),
                        "expected": (row.get("expected_nl") or row.get("expected_checks") or "").strip(),
                        "conclusion": status,
                        "reason": (row.get("manual_conclusion") or "").strip(),
                        "last_run_at": (row.get("last_run_at") or "").strip(),
                    }
                )
    return results


def write_reports(results: list[dict[str, str]]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    latest_edit_time = max((item["last_run_at"] for item in results if item["last_run_at"]), default="未填写")
    passed = sum(1 for item in results if item["conclusion"] == "通过")
    failed = sum(1 for item in results if item["conclusion"] == "不通过")
    pending = sum(1 for item in results if item["conclusion"] == "未填写")

    json_path = REPORTS_DIR / "interface_test_report.json"
    json_path.write_text(
        json.dumps(
            {
                "generated_at": generated_at,
                "sources": [str(path.relative_to(ROOT_DIR)) for path in CASE_PATHS.values()],
                "latest_edit_time": latest_edit_time,
                "summary": {
                    "total": len(results),
                    "passed": passed,
                    "failed": failed,
                    "pending": pending,
                },
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    lines = [
        "# 元数据接口人工测试报告",
        "",
        f"- 报告生成时间：{generated_at}",
        "- 结果来源：`tests\\cases\\register_cases.csv`、`tests\\cases\\query_cases.csv`",
        f"- 最近编辑时间：{latest_edit_time}",
        f"- 总用例数：{len(results)}",
        f"- 通过：{passed}",
        f"- 不通过：{failed}",
        f"- 未填写：{pending}",
        "",
    ]

    for endpoint in ("register", "query"):
        endpoint_results = [item for item in results if item["endpoint"] == endpoint]
        if not endpoint_results:
            continue
        lines.extend(
            [
                f"## /{endpoint} 人工测试结果",
                "",
                "| 用例 | 类别 | 输入 | 预期 | 人工结论 | 原因 | 编辑时间 |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for item in endpoint_results:
            lines.append(
                "| {case} | {category} | {input} | {expected} | {conclusion} | {reason} | {last_run_at} |".format(
                    case=markdown_escape(f"{item['id']}：{item['case']}"),
                    category=markdown_escape(item["category"]),
                    input=markdown_escape(item["input"]),
                    expected=markdown_escape(item["expected"]),
                    conclusion=markdown_escape(item["conclusion"]),
                    reason=markdown_escape(item["reason"] or "无"),
                    last_run_at=markdown_escape(item["last_run_at"] or "未填写"),
                )
            )
        lines.append("")

    md_path = REPORTS_DIR / "interface_test_report.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    try:
        results = read_case_results(args.endpoint, args.category)
    except OSError as error:
        print(str(error), file=sys.stderr)
        return 2

    if not results:
        print("No enabled case results matched the selected filters.", file=sys.stderr)
        return 2

    write_reports(results)
    print(f"Report written from edited CSV results: {REPORTS_DIR / 'interface_test_report.md'}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the interface report from edited CSV results.")
    parser.add_argument("--endpoint", choices=["register", "query"], help="Include only one endpoint.")
    parser.add_argument("--category", help="Include only cases with this category.")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
