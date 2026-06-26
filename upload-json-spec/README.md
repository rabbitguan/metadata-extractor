# 用户上传 JSON 测试样例

本目录提供用于验证“用户上传 JSON 映射分析”的标准测试文件。上传功能只支持结构化 `JSON` 或 `XML`，推荐使用 JSON；TXT、CSV、Markdown 等非结构化文本不作为上传解析格式。

## 推荐结构

```json
{
  "resource_type": "dataset",
  "core": {
    "title": "Example Dataset",
    "cstr_identifier": "31253.11.CSTR.2026.000001",
    "creators": ["Alice Zhang", "Bob Li"],
    "publisher": "Example Data Center",
    "publication_date": "2026-06-20",
    "description": "A short description of the resource.",
    "keywords": ["metadata", "dataset"],
    "subjects": ["Computer Science"],
    "language": "en",
    "alternative_identifiers": ["10.1234/example.dataset"],
    "resource_url": ["https://example.org/datasets/001"]
  },
  "domain": {
    "dataset_basic_information": {},
    "dataset_publication_information": {},
    "dataset_service_information": {}
  },
  "extension_info": "Optional extra information."
}
```

## 支持的资源类型

`resource_type` 必填，支持以下写法：

| 门类 | 推荐值 | 兼容值 |
| --- | --- | --- |
| 数据集 | `dataset` | `数据集`, `data set` |
| 数据论文 | `data_paper` | `数据论文`, `data paper`, `paper` |
| 标准文献 | `standard_literature` | `标准文献`, `standard literature`, `standard` |
| 生态科学数据 | `ecological_data` | `生态科学数据`, `ecological data`, `ecological science data` |

## 核心元数据字段

`core` 是核心元数据对象，建议提供以下字段：

- `title`：标题，字符串或字符串数组
- `cstr_identifier`：CSTR 标识符，只能填写 CSTR，不要填写 DOI
- `creators`：创建者，字符串数组
- `publisher`：发布机构
- `publication_date`：发布日期，建议使用 `YYYY-MM-DD`
- `description`：描述，字符串或字符串数组
- `keywords`：关键词，字符串数组
- `subjects`：学科，字符串数组
- `language`：语言，例如 `zh` / `en` / `zh; en`
- `contributors`：贡献者，字符串数组
- `alternative_identifiers`：替代标识符，例如 DOI、Handle、标准号等
- `related_identifiers`：关联标识符
- `rights`：权限或许可
- `funders`：资助者，字符串数组
- `version`：版本
- `resource_url`：资源链接，字符串或字符串数组

## 领域元数据分组

不同资源类型建议使用不同领域分组。字段名可使用英文、中文或 snake_case，后端会尽量做中英文映射。

### 数据集

- `dataset_basic_information`
- `dataset_publication_information`
- `dataset_service_information`

### 数据论文

- `data_paper_content_information`
- `data_paper_publication_information`
- `data_paper_service_information`

### 标准文献

- `standard_literature_information`

标准文献条目较多，样例中覆盖了记录状态、标准号、发布日期、发布机构、标准名称、分类号、摘要、主题词、馆藏、出版信息等字段。

### 生态科学数据

- `ecological_identification_information`
- `ecological_data_content_information`
- `ecological_data_quality_and_methods`
- `ecological_spatial_and_temporal_coverage`
- `ecological_project_and_funding_information`
- `ecological_distribution_and_citation_information`

## 标识符规则

`core.cstr_identifier` 会被严格检查：

- 合法 CSTR 示例：`31253.11.CSTR.2026.000001`
- DOI 示例：`10.1234/example.dataset`

规则：

- 如果 `cstr_identifier` 是合法 CSTR，核心元数据的 `CSTR标识符` / `Identifier` 会写入该值。
- 如果 `cstr_identifier` 误填 DOI，核心元数据不会写入 CSTR 字段，该 DOI 会转入 `替代标识符` / `Alternative Identifiers`。
- 领域元数据中的 `标识符` / `Identifier` 会优先使用 CSTR。
- 如果没有 CSTR，但有 DOI 或其他替代标识符，领域 `标识符` 会使用替代标识符；DOI 会标注为 `（doi）` / `(doi)`。

## 测试文件

本目录提供以下测试 JSON：

- `dataset-complete.json`：完整数据集样例，覆盖核心元数据、数据集基本信息、出版信息和服务信息。
- `data-paper-complete.json`：完整数据论文样例，覆盖数据论文内容、嵌套数据集信息、出版信息和服务信息。
- `standard-literature-complete.json`：完整标准文献样例，覆盖标准文献大部分条目。
- `ecological-data-complete.json`：完整生态科学数据样例，覆盖标识信息、数据内容、质量方法、时空范围、项目资助、分发引用。
- `doi-in-cstr-field-flawed.json`：有瑕疵样例，故意把 DOI 填入 `cstr_identifier`，用于验证 CSTR 严格校验和 DOI 兜底显示。

## 快速验证

启动后端后，可用任一测试文件验证上传解析：

```bash
cd /Users/guanguanmiss/Desktop/metadata

python - <<'PY'
import json
from pathlib import Path
import requests

path = Path("upload-json-spec/dataset-complete.json")
payload = {
    "source": "upload",
    "mode": "common",
    "title": path.name,
    "text": path.read_text(encoding="utf-8")
}
response = requests.post("http://127.0.0.1:4000/register", json=payload, timeout=60)
print(response.status_code)
print(json.dumps(response.json(), ensure_ascii=False, indent=2))
PY
```

也可以直接使用 `curl`：

```bash
curl -X POST http://127.0.0.1:4000/register \
  -H "Content-Type: application/json" \
  --data-binary @<(python - <<'PY'
import json
from pathlib import Path
path = Path("upload-json-spec/data-paper-complete.json")
print(json.dumps({
  "source": "upload",
  "mode": "common",
  "title": path.name,
  "text": path.read_text(encoding="utf-8")
}, ensure_ascii=False))
PY
)
```
