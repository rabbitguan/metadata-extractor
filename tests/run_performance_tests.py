#!/usr/bin/env python3
"""Performance test runner for the metadata extractor HTTP API.

The script uses only Python standard library modules so it can run in the
deployment host without installing extra packages.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_URL = "https://arxiv.org/abs/2303.14524"
DEFAULT_IDENTIFIER = "CSTR:17081.11.photon.laue.dataset-20260120111231"


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * ratio))))
    return ordered[index]


def summarize(samples: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [item["elapsed_ms"] for item in samples if item["ok"]]
    errors = [item for item in samples if not item["ok"]]
    return {
        "total": len(samples),
        "success": len(latencies),
        "failed": len(errors),
        "success_rate": round(len(latencies) / len(samples), 4) if samples else 0,
        "avg_ms": round(statistics.mean(latencies), 2) if latencies else 0,
        "min_ms": round(min(latencies), 2) if latencies else 0,
        "p50_ms": round(percentile(latencies, 0.50), 2),
        "p95_ms": round(percentile(latencies, 0.95), 2),
        "max_ms": round(max(latencies), 2) if latencies else 0,
        "errors": errors[:5],
    }


def request_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 60,
) -> dict[str, Any]:
    body = None
    request_headers = {"X-User-Id": f"perf-{uuid.uuid4().hex}"}
    if headers:
        request_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    started = time.perf_counter()
    status = 0
    response_text = ""
    try:
        req = Request(url, data=body, headers=request_headers, method=method)
        with urlopen(req, timeout=timeout) as response:
            status = response.status
            response_text = response.read().decode("utf-8", errors="replace")
        ok = 200 <= status < 300
        error = None
    except HTTPError as exc:
        status = exc.code
        response_text = exc.read().decode("utf-8", errors="replace")
        ok = False
        error = response_text[:300]
    except (URLError, TimeoutError, OSError) as exc:
        ok = False
        error = str(exc)
    elapsed_ms = (time.perf_counter() - started) * 1000
    return {
        "ok": ok,
        "status": status,
        "elapsed_ms": elapsed_ms,
        "error": error,
        "response_preview": response_text[:300],
    }


def post_register(base_url: str, target_url: str, force_reanalyze: bool, timeout: float) -> dict[str, Any]:
    return request_json(
        "POST",
        f"{base_url}/register",
        {
            "source": "url",
            "mode": "common",
            "strategy": "auto",
            "force_reanalyze": force_reanalyze,
            "url": target_url,
        },
        timeout=timeout,
    )


def post_query(base_url: str, identifier: str, timeout: float) -> dict[str, Any]:
    return request_json(
        "POST",
        f"{base_url}/query",
        {
            "source": "identifier",
            "mode": "common",
            "identifiers": identifier,
        },
        timeout=timeout,
    )


def run_repeated(name: str, count: int, fn) -> dict[str, Any]:
    samples = []
    for _ in range(count):
        samples.append(fn())
    return {"name": name, "summary": summarize(samples), "samples": samples}


def run_concurrent(name: str, concurrency: int, fn) -> dict[str, Any]:
    samples = []
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(fn) for _ in range(concurrency)]
        for future in as_completed(futures):
            samples.append(future.result())
    wall_ms = (time.perf_counter() - started) * 1000
    result = {"name": name, "summary": summarize(samples), "samples": samples}
    result["summary"]["wall_ms"] = round(wall_ms, 2)
    result["summary"]["throughput_rps"] = round((len(samples) / wall_ms) * 1000, 2) if wall_ms else 0
    return result


def run_mixed_concurrent(
    name: str,
    concurrency: int,
    register_fn,
    query_fn,
) -> dict[str, Any]:
    samples = []
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for index in range(concurrency):
            futures.append(executor.submit(register_fn if index % 2 == 0 else query_fn))
        for future in as_completed(futures):
            samples.append(future.result())
    wall_ms = (time.perf_counter() - started) * 1000
    result = {"name": name, "summary": summarize(samples), "samples": samples}
    result["summary"]["wall_ms"] = round(wall_ms, 2)
    result["summary"]["throughput_rps"] = round((len(samples) / wall_ms) * 1000, 2) if wall_ms else 0
    return result


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# 性能测试报告",
        "",
        f"- API 基址：`{report['base_url']}`",
        f"- 生成时间：`{report['generated_at']}`",
        f"- 单接口并发数：`{report['concurrency']}`",
        f"- 混合并发数：`{report['mixed_concurrency']}`",
        "",
        "| 测试项 | 总数 | 成功 | 失败 | 成功率 | 平均(ms) | P50(ms) | P95(ms) | 最大(ms) | 吞吐(req/s) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in report["results"]:
        s = item["summary"]
        lines.append(
            f"| {item['name']} | {s['total']} | {s['success']} | {s['failed']} | "
            f"{s['success_rate']:.2%} | {s['avg_ms']} | {s['p50_ms']} | {s['p95_ms']} | "
            f"{s['max_ms']} | {s.get('throughput_rps', 0)} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run API performance tests.")
    parser.add_argument("--base-url", default="http://8.130.186.178:21005/", help="Backend base URL.")
    parser.add_argument("--target-url", default=DEFAULT_URL, help="URL used by /register tests.")
    parser.add_argument("--identifier", default=DEFAULT_IDENTIFIER, help="Identifier used by /query tests.")
    parser.add_argument("--repeats", type=int, default=3, help="Number of serial samples per API scenario.")
    parser.add_argument("--concurrency", type=int, default=100, help="Concurrent requests per endpoint.")
    parser.add_argument("--mixed-concurrency", type=int, default=100, help="Concurrent mixed /register and /query requests.")
    parser.add_argument("--timeout", type=float, default=60, help="Per-request timeout in seconds.")
    parser.add_argument("--output-dir", default="tests/reports", help="Directory for generated reports.")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    register_first = lambda: post_register(base_url, args.target_url, True, args.timeout)
    register_repeat = lambda: post_register(base_url, args.target_url, False, args.timeout)
    query_identifier = lambda: post_query(base_url, args.identifier, args.timeout)

    results = [
        run_repeated("TC-PERF-001 /register 首次 URL 解析", args.repeats, register_first),
        run_repeated("TC-PERF-002 /register 重复 URL 访问", args.repeats, register_repeat),
        run_repeated("TC-PERF-003 /query 标识符查询", args.repeats, query_identifier),
        run_concurrent("TC-CON-001 /register 并发访问", args.concurrency, register_repeat),
        run_concurrent("TC-CON-002 /query 并发访问", args.concurrency, query_identifier),
        run_mixed_concurrent("TC-CON-003 /register 与 /query 混合并发访问", args.mixed_concurrency, register_repeat, query_identifier),
    ]

    report = {
        "base_url": base_url,
        "target_url": args.target_url,
        "identifier": args.identifier,
        "repeats": args.repeats,
        "concurrency": args.concurrency,
        "mixed_concurrency": args.mixed_concurrency,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "results": results,
    }

    json_path = output_dir / "performance_test_report.json"
    md_path = output_dir / "performance_test_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(md_path, report)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
