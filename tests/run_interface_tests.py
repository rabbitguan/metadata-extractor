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


def read_cases(endpoint_filter: str | None, category_filter: str | None) -> list[TestCase]:
    cases: list[TestCase] = []
    for path in (CASES_DIR / "register_cases.csv", CASES_DIR / "query_cases.csv"):
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as file_obj:
            for row in csv.DictReader(file_obj):
                if (row.get("enabled") or "").strip().lower() != "yes":
                    continue
                endpoint = (row.get("endpoint") or "").strip()
                category = (row.get("category") or "").strip()
                if endpoint_filter and endpoint != endpoint_filter:
                    continue
                if category_filter and category != category_filter:
                    continue
                cases.append(
                    TestCase(
                        id=(row.get("id") or "").strip(),
                        endpoint=endpoint,
                        category=category,
                        input_type=(row.get("input_type") or "").strip(),
                        source=(row.get("source") or "").strip(),
                        mode=(row.get("mode") or "common").strip(),
                        strategy=(row.get("strategy") or "").strip(),
                        payload_or_file=(row.get("payload_or_file") or "").strip(),
                        expected_status=int((row.get("expected_status") or "200").strip()),
                        expected_checks=[
                            item.strip()
                            for item in (row.get("expected_checks") or "").split(";")
                            if item.strip()
                        ],
                        description=(row.get("description") or "").strip(),
                    )
                )
    return cases


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
        json_payload = build_json_payload(case)
        response = requests.post(url, headers=headers, json=json_payload, timeout=timeout)

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
    text = str(value)
    text = text.replace("\r", " ").replace("\n", "<br>")
    text = text.replace("|", "\\|")
    return text


def write_reports(results: list[dict[str, Any]], base_url: str) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    json_path = REPORTS_DIR / "interface_test_report.json"
    json_path.write_text(
        json.dumps(
            {
                "generated_at": now,
                "base_url": base_url,
                "summary": {
                    "total": len(results),
                    "passed": sum(1 for item in results if item["conclusion"] == "通过"),
                    "failed": sum(1 for item in results if item["conclusion"] == "失败"),
                },
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    lines = [
        "# 元数据提取接口测试报告",
        "",
        f"- 生成时间：{now}",
        f"- 服务地址：`{base_url}`",
        f"- 总用例数：{len(results)}",
        f"- 通过：{sum(1 for item in results if item['conclusion'] == '通过')}",
        f"- 失败：{sum(1 for item in results if item['conclusion'] == '失败')}",
        "",
    ]

    for endpoint in ("register", "query"):
        endpoint_results = [item for item in results if item["endpoint"] == endpoint]
        if not endpoint_results:
            continue
        lines.extend(
            [
                f"## /{endpoint} 测试结果",
                "",
                "| 测试例子 | 预期 | 实际 | 结论 |",
                "|---|---|---|---|",
            ]
        )
        for item in endpoint_results:
            lines.append(
                "| {case} | {expected} | {actual} | {conclusion} |".format(
                    case=markdown_escape(item["case"]),
                    expected=markdown_escape(item["expected"]),
                    actual=markdown_escape(item["actual"]),
                    conclusion=markdown_escape(item["conclusion"]),
                )
            )
        lines.append("")

    md_path = REPORTS_DIR / "interface_test_report.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    cases = read_cases(args.endpoint, args.category)
    if not cases:
        print("No enabled cases matched the selected filters.", file=sys.stderr)
        return 2

    results: list[dict[str, Any]] = []
    for case in cases:
        try:
            status_code, body, raw_text = send_case(case, args.base_url, args.timeout)
            passed, passed_checks, failed_checks = evaluate(case, status_code, body)
            actual_parts = [f"HTTP {status_code}"]
            if passed_checks:
                actual_parts.append("通过检查：" + "；".join(passed_checks))
            if failed_checks:
                actual_parts.append("失败检查：" + "；".join(failed_checks))
            body_summary = compact_body(body)
            if body_summary:
                actual_parts.append(body_summary)
            conclusion = "通过" if passed else "失败"
            response_body = body
            response_text = raw_text
        except Exception as error:
            conclusion = "失败"
            passed_checks = []
            failed_checks = [str(error)]
            actual_parts = [f"请求异常：{error}"]
            response_body = None
            response_text = ""

        result = {
            "id": case.id,
            "endpoint": case.endpoint,
            "category": case.category,
            "case": f"{case.id}：{case.description}",
            "expected": "HTTP {status}；{checks}".format(
                status=case.expected_status,
                checks="；".join(case.expected_checks) if case.expected_checks else "无额外检查",
            ),
            "actual": "；".join(actual_parts),
            "conclusion": conclusion,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "response_body": response_body,
            "response_text": response_text,
        }
        results.append(result)
        print(f"[{conclusion}] {case.id} {case.description}")

    write_reports(results, args.base_url)
    failed = sum(1 for item in results if item["conclusion"] == "失败")
    print(f"Report written to {REPORTS_DIR / 'interface_test_report.md'}")
    return 1 if failed else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run metadata extractor interface test cases.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"Backend base URL, default: {DEFAULT_BASE_URL}")
    parser.add_argument("--endpoint", choices=["register", "query"], help="Run only one endpoint.")
    parser.add_argument("--category", help="Run only cases with this category.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS, help="Request timeout in seconds.")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
