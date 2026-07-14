from __future__ import annotations

import contextlib
import io
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
REPORTS_DIR = ROOT_DIR / "tests" / "reports"

sys.path.insert(0, str(BACKEND_DIR))

import backend as backend_app  # noqa: E402
from extractors.manager import detect_extractor, list_extractors  # noqa: E402


@dataclass(frozen=True)
class ExtractorCase:
    rule: str
    source_type: str
    url: str = ""
    title: str = ""
    content: str = ""
    note: str = ""


def crossref_fixture() -> str:
    return """Metadata Source: Crossref
DOI: 10.48550/arXiv.2303.14524
URL: https://doi.org/10.48550/arXiv.2303.14524
title: Chat-REC: Towards Interactive and Explainable LLMs-Augmented Recommender System
abstract: A recommender-system paper fixture used for extractor coverage.
subject: Computer Science; Information Retrieval
published-online: 2023-03-25
publisher: arXiv
author: Gao
type: Data Paper
"""


def cstr_fixture() -> str:
    return json.dumps(
        {
            "data": {
                "data": {
                    "content": {
                        "type": "CSTR",
                        "identifier": "31253.11.CSTR.2026.100001",
                        "resourceType": "11",
                        "identificationStatus": "registered",
                        "titleCN": "CSTR规则覆盖测试数据集",
                        "titleEN": "CSTR Extractor Coverage Dataset",
                        "abstractCN": "用于验证CSTR结构化元数据规则链路的样例。",
                        "abstractEN": "A fixture for validating the CSTR extractor path.",
                        "keywordsCN": ["元数据", "测试"],
                        "keywordsEN": ["metadata", "test"],
                        "creators": [
                            {
                                "creatorNameCN": "测试作者",
                                "creatorOrganizationCN": "测试机构",
                            }
                        ],
                        "registerOrganizationCN": "中国科学院计算机网络信息中心",
                        "publicationDate": "2026-07-13",
                        "urls": ["https://scids.bdware.cn/id/31253.11.CSTR.2026.100001"],
                    }
                }
            }
        },
        ensure_ascii=False,
    )


def cma_fixture() -> str:
    return """
<!doctype html>
<html>
<head><title>国家气象信息中心-中国气象数据网</title></head>
<body>
  <div class="search-term"><h1 class="serCeTi">中国地面气候资料日值数据集</h1></div>
  <div class="product-data-right">
    <ul class="clearfix"><li class="title">数据名称：</li><li class="words">中国地面气候资料日值数据集</li></ul>
    <ul class="clearfix"><li class="title">关键字：</li><li class="words">气温；降水；地面观测</li></ul>
    <ul class="clearfix"><li class="title">空间范围：</li><li class="words">中国</li></ul>
    <ul class="clearfix"><li class="title">数据起始时间：</li><li class="words">1951-01-01</li></ul>
    <ul class="clearfix"><li class="title">数据终止时间：</li><li class="words">2025-12-31</li></ul>
    <ul class="clearfix"><li class="title">数据资源登记编号：</li><li class="words">SURF_CLI_CHN_MUL_DAY_V3.0</li></ul>
    <ul class="clearfix"><li class="title">共享级别：</li><li class="words">开放共享</li></ul>
    <ul class="clearfix"><li class="title">更新频率：</li><li class="words">逐日</li></ul>
    <ul class="clearfix"><li class="title">制作时间：</li><li class="words">2026-01-01</li></ul>
    <ul class="clearfix"><li class="title">数据质量描述：</li><li class="words">经过质量控制。</li></ul>
    <ul class="clearfix"><li class="title">数据源：</li><li class="words">国家气象信息中心</li></ul>
  </div>
  <div class="element-data-brief"><p class="font">覆盖中国地面气候观测日值资料的规则测试样例。</p></div>
  <input class="searchData" url="/dataService/cdcindex/datacode/SURF_CLI_CHN_MUL_DAY_V3.0">
</body>
</html>
"""


def nedc_fixture() -> str:
    return """
<!doctype html>
<html>
<head><title>国家地震科学数据中心</title></head>
<body>
  <main class="inner-content">
    <h2>中国大陆地震目录数据集</h2>
    <section>数据基本信息</section>
    <div class="data_div"><span class="frist">数据名称：</span><span class="second">中国大陆地震目录数据集</span></div>
    <div class="data_div"><span class="frist">数据标识：</span><span class="second">CSTR:31000.11.NEDC.eq.catalog</span></div>
    <div class="data_div"><span class="frist">所属分类：</span><span class="second">地震科学 (EQ)</span></div>
    <div class="data_div"><span class="frist">空间范围：</span><span class="second">中国大陆</span></div>
    <div class="data_div"><span class="frist">时间范围：</span><span class="second">2000-2025</span></div>
    <div class="data_div"><span class="frist">联系人：</span><span class="second">数据服务组</span></div>
    <div class="data_div"><span class="frist">邮箱：</span><span class="second">data@example.org</span></div>
    <div class="data_div"><span class="frist">单位：</span><span class="second">国家地震科学数据中心</span></div>
    <ul id="data-factors">
      <li>最新更新时间<span>2026-01-01</span></li>
      <li>数据量<span>12 MB</span></li>
      <li>数据共享方式<span>开放共享</span></li>
    </ul>
    <div class="floatWrap"><h4>数据摘要</h4><div class="break"><p>覆盖中国大陆地震目录的结构化样例。</p></div></div>
    <div class="floatWrap"><h4>数据生产者</h4><div class="break"><p>国家地震科学数据中心</p></div></div>
    <div class="floatWrap"><h4>数据来源</h4><div class="break"><p>观测台网</p></div></div>
  </main>
</body>
</html>
"""


def pku_fixture() -> str:
    return """
<!doctype html>
<html>
<head><title>北京大学学位论文数据库</title></head>
<body>
  <div class="title-box"><h1 class="title">面向科学数据的元数据映射方法研究</h1></div>
  <ul class="paper-detail-list">
    <li><label>中文题名：</label><span class="text">面向科学数据的元数据映射方法研究</span></li>
    <li><label>外文题名：</label><span class="text">Research on Metadata Mapping for Scientific Data</span></li>
    <li><label>作者：</label><span class="text">王测试</span></li>
    <li><label>培养单位：</label><span class="text">北京大学</span></li>
    <li><label>专业：</label><span class="text">情报学</span></li>
    <li><label>中文摘要：</label><span class="text">论文研究元数据映射流程与字段对齐方法。</span></li>
    <li><label>中文关键词：</label><span class="text">元数据；映射；科学数据</span></li>
    <li><label>论文总页数：</label><span class="text">120</span></li>
    <li><label>开放日期：</label><span class="text">2026-07-13</span></li>
  </ul>
  <a href="/fulltext/fixture.pdf">查看全文</a>
</body>
</html>
"""


def pubmed_fixture() -> str:
    return """
<!doctype html>
<html>
<head>
  <title>PubMed fixture</title>
  <meta name="citation_title" content="A PubMed extractor coverage article">
  <meta name="citation_authors" content="Zhang S; Li Q">
  <meta name="citation_author_institution" content="Institute of Metadata">
  <meta name="citation_abstract" content="A compact fixture for PubMed extractor coverage.">
  <meta name="citation_pmid" content="31452104">
  <meta name="citation_doi" content="10.1000/pubmed.fixture">
  <meta name="citation_journal_title" content="Journal of Metadata Tests">
  <meta name="citation_date" content="2026">
  <meta name="citation_keywords" content="metadata; extractor">
</head>
<body><h1 class="heading-title">A PubMed extractor coverage article</h1></body>
</html>
"""


CASES: list[ExtractorCase] = [
    ExtractorCase("arXiv", "url", url="https://arxiv.org/abs/2303.14524"),
    ExtractorCase("CHINARE Dataset Detail", "url", url="https://datacenter.chinare.org.cn/data-center/metadata?id=f6b318b5-1ba7-46b8-9566-b16728db0989"),
    ExtractorCase("CMA Data Detail", "fixture", url="https://data.cma.cn/data/cdcdetail/dataCode/SURF_CLI_CHN_MUL_DAY_V3.0.html", title="中国气象数据网", content=cma_fixture()),
    ExtractorCase("CNCB Database Detail", "url", url="https://www.cncb.ac.cn/api/biodb/1"),
    ExtractorCase("Crossref", "fixture", url="https://doi.org/10.48550/arXiv.2303.14524", title="Crossref fixture", content=crossref_fixture()),
    ExtractorCase("CSTR", "fixture", url="https://scids.bdware.cn/id/31253.11.CSTR.2026.100001", title="CSTR fixture", content=cstr_fixture()),
    ExtractorCase("eScience Metadata Detail", "url", url="https://www.escience.org.cn/metadata/detail?cstrId=33221.11.sciencedb.01767"),
    ExtractorCase("GEODATA Science Detail", "url", url="https://www.geodata.cn/main/face_science_detail?typeName=face_science&guid=274461948639522"),
    ExtractorCase("NADC Resource Detail", "url", url="https://nadc.china-vo.org/res/r100451/"),
    ExtractorCase("NASDC Metadata Detail", "url", url="https://www.agridata.cn/data.html#/datadetail?id=292598"),
    ExtractorCase("NBSDC Metadata Detail", "url", url="https://www.nbsdc.cn/general/dataDetail?id=63f4697887c4324cadaeda85&type=1"),
    ExtractorCase("NCDC Metadata Detail", "url", url="https://www.ncdc.ac.cn/portal/metadata/59e517ca-aaf6-44f0-8676-16e647f4f426"),
    ExtractorCase("NCMI Data Detail", "url", url="https://www.ncmi.cn/phda/dataDetails.do?id=CSTR:A0006.11.A0001.202006.001024"),
    ExtractorCase("NEDC Metadata Detail", "fixture", url="https://data.earthquake.cn/datashare/report.shtml?PAGEID=datasourceEdaReport&dt=fixture", title="国家地震科学数据中心", content=nedc_fixture()),
    ExtractorCase("NESDC Dataset Detail", "url", url="https://www.nesdc.org.cn/sdo/detail?id=60f68d757e28174f0e7d8d49"),
    ExtractorCase("NFGSDC Data Detail", "url", url="https://www.forestdata.cn/dataDetail.html?id=a47fe3ac-b57d-4a35-81ba-513e15e576d5"),
    ExtractorCase("NHEPSDC Resource Detail", "url", url="https://www.nhepsdc.cn/resource/photon/heps/b7"),
    ExtractorCase("NMDC", "url", url="https://nmdc.cn/metadata/detail?id=CSTR:15732.11.nmdc.2021.000346"),
    ExtractorCase("NMDIS Metadata Detail", "url", url="https://mds.nmdis.org.cn/pages/dataViewDetail.html?dataSetId=35"),
    ExtractorCase("NODA Dataset Detail", "url", url="https://www.noda.ac.cn/datasharing/datasetDetails/6a51f07f6e9d28541b592582"),
    ExtractorCase("PKU Thesis", "fixture", url="https://thesis.lib.pku.edu.cn/detail/fixture", title="北京大学学位论文数据库", content=pku_fixture()),
    ExtractorCase("TPDC Dataset Detail", "url", url="https://data.tpdc.ac.cn/zh-hans/data/b0f1d740-0928-4c47-8085-11f55d16f735/"),
    ExtractorCase("VSSO Metadata Detail", "url", url="https://vsso.nssdc.ac.cn/nssdc_zh/html/vssoinfo.html?16242"),
    ExtractorCase("pubmed", "fixture", url="https://pubmed.ncbi.nlm.nih.gov/31452104/", title="PubMed fixture", content=pubmed_fixture()),
]


def value_exists(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def get_path_value(data: Any, path: str) -> tuple[bool, Any]:
    current = data
    for segment in path.split("."):
        if "[" in segment and segment.endswith("]"):
            key, index_text = segment[:-1].split("[", 1)
            index = int(index_text)
        else:
            key, index = segment, None

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
        "核心元数据.metadatas[0].titles",
        "核心元数据.metadatas[0].标题",
        "核心元数据.metadatas[0].Title",
        "核心元数据.metadatas[0].资源名称",
        "领域元数据.metadatas[0].标题",
        "领域元数据.metadatas[0].Title",
        "领域元数据.metadatas[0].资源名称",
    ]
    for path in preferred_paths:
        found, value = get_path_value(data, path)
        if found and value_exists(value):
            return value

    if isinstance(data, dict):
        for key in ("标题", "Title", "title", "资源名称", "name"):
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


def compact_value(value: Any, max_len: int = 90) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value or "")
    text = " ".join(text.split())
    return text if len(text) <= max_len else f"{text[:max_len - 1]}…"


def load_case_content(case: ExtractorCase) -> tuple[str, str, str, str]:
    if case.source_type == "url":
        page = backend_app.fetch_url_content(case.url, dynamic_render="never")
        return page.get("html") or page.get("text") or "", page.get("text") or "", page.get("title") or case.title, page.get("render_method") or "static"
    return case.content, case.content, case.title, "fixture"


def run_case(case: ExtractorCase) -> dict[str, Any]:
    started = time.perf_counter()
    result: dict[str, Any] = {
        "rule": case.rule,
        "source_type": case.source_type,
        "url": case.url,
        "status": "failed",
        "matched_rule": None,
        "standard_shape": False,
        "title_non_empty": False,
        "title": None,
        "domain_type": None,
        "error": "",
        "duration_seconds": None,
    }
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            html, text, title, render_method = load_case_content(case)
            matched = detect_extractor(case.url, title, html or text)
            result["matched_rule"] = matched.name if matched else None
            result["render_method"] = render_method
            if not matched:
                raise AssertionError("no extractor matched")
            if matched.name != case.rule:
                raise AssertionError(f"expected {case.rule}, got {matched.name}")

            payload = backend_app.build_rule_metadata_payload(text, "common", url=case.url, title=title, html=html)

        core = payload.get("核心元数据") if isinstance(payload, dict) else None
        domain = payload.get("领域元数据") if isinstance(payload, dict) else None
        core_items = core.get("metadatas") if isinstance(core, dict) else None
        domain_items = domain.get("metadatas") if isinstance(domain, dict) else None
        standard_shape = isinstance(core_items, list) and isinstance(domain_items, list)
        title_value = find_first_non_empty_title(payload)

        result.update(
            {
                "status": "passed" if standard_shape and value_exists(title_value) else "failed",
                "standard_shape": standard_shape,
                "title_non_empty": value_exists(title_value),
                "title": compact_value(title_value),
                "domain_type": domain.get("metadata_type") if isinstance(domain, dict) else None,
            }
        )
        if result["status"] != "passed":
            result["error"] = "standard_shape/title_non_empty check failed"
    except Exception as error:
        result["error"] = str(error)
    finally:
        result["duration_seconds"] = round(time.perf_counter() - started, 2)
    return result


def markdown_escape(value: Any) -> str:
    text = str(value or "")
    return text.replace("|", "\\|").replace("\n", " ")


def build_markdown(summary: dict[str, Any], results: list[dict[str, Any]]) -> str:
    lines = [
        "# Extractor 覆盖测试报告",
        "",
        f"- 生成时间：{summary['generated_at']}",
        f"- 当前规则数：{summary['registered_rule_count']}",
        f"- 覆盖用例数：{summary['case_count']}",
        f"- 通过：{summary['passed']}",
        f"- 失败：{summary['failed']}",
        f"- 缺少用例的规则：{', '.join(summary['missing_rules']) if summary['missing_rules'] else '无'}",
        "",
        "## 结果明细",
        "",
        "| 规则 | 来源 | 结果 | 命中规则 | 标准结构 | 标题 | 领域类型 | 耗时(s) | 错误 |",
        "| --- | --- | --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for item in results:
        lines.append(
            "| {rule} | {source} | {status} | {matched} | {shape} | {title} | {domain} | {duration} | {error} |".format(
                rule=markdown_escape(item.get("rule")),
                source=markdown_escape(item.get("source_type")),
                status="通过" if item.get("status") == "passed" else "失败",
                matched=markdown_escape(item.get("matched_rule")),
                shape="是" if item.get("standard_shape") else "否",
                title=markdown_escape(item.get("title")),
                domain=markdown_escape(item.get("domain_type")),
                duration=item.get("duration_seconds"),
                error=markdown_escape(item.get("error")),
            )
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    registered_rules = list_extractors()
    case_rules = [case.rule for case in CASES]
    missing_rules = sorted(set(registered_rules) - set(case_rules))
    extra_case_rules = sorted(set(case_rules) - set(registered_rules))

    results = [run_case(case) for case in CASES]
    passed = sum(1 for item in results if item.get("status") == "passed")
    failed = len(results) - passed
    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "registered_rules": registered_rules,
        "registered_rule_count": len(registered_rules),
        "case_count": len(CASES),
        "passed": passed,
        "failed": failed,
        "missing_rules": missing_rules,
        "extra_case_rules": extra_case_rules,
    }
    report = {"summary": summary, "results": results}

    (REPORTS_DIR / "extractor_coverage_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (REPORTS_DIR / "extractor_coverage_report.md").write_text(
        build_markdown(summary, results),
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if failed == 0 and not missing_rules and not extra_case_rules else 1


if __name__ == "__main__":
    raise SystemExit(main())
