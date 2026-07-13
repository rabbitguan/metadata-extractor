from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT_DIR / "tests" / "cases"
REPORTS_DIR = ROOT_DIR / "tests" / "reports"
CASE_PATHS = {
    "register": CASES_DIR / "register_cases.csv",
    "query": CASES_DIR / "query_cases.csv",
}


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
