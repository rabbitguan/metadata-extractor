# 用户上传 JSON 标准

上传功能只支持结构化 `JSON` 或 `XML`。推荐使用 JSON；TXT、CSV、Markdown 等非结构化文本不再支持上传解析。

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

## 字段说明

`resource_type` 必填，支持：

- `dataset` 或 `数据集`
- `data_paper` 或 `数据论文`
- `other` 或 `其他`

`core` 是核心元数据对象，建议提供以下字段：

- `title`：标题，字符串或字符串数组
- `cstr_identifier`：CSTR 标识符，只能填写 CSTR，不要填写 DOI
- `creators`：创建者，字符串数组
- `publisher`：发布机构
- `publication_date`：发布日期，建议使用 `YYYY-MM-DD`
- `description`：描述，字符串或字符串数组
- `keywords`：关键词，字符串数组
- `subjects`：学科，字符串数组
- `language`：语言，例如 `zh` / `en`
- `alternative_identifiers`：替代标识符，例如 DOI、Handle 等
- `related_identifiers`：关联标识符
- `rights`：权限或许可
- `funders`：资助者，字符串数组
- `version`：版本
- `resource_url`：资源链接，字符串或字符串数组

`domain` 是可选的领域元数据对象。不同资源类型建议使用不同分组：

数据集：

- `dataset_basic_information`
- `dataset_publication_information`
- `dataset_service_information`

数据论文：

- `data_paper_content_information`
- `data_paper_publication_information`
- `data_paper_service_information`

## 标识符注意事项

`cstr_identifier` 会被严格检查：

- 合法 CSTR 示例：`31253.11.CSTR.2026.000001`
- DOI 示例：`10.1234/example.dataset`

如果把 DOI 填进 `cstr_identifier`，后端不会把它放进 `CSTR标识符` / `Identifier` 字段，而是会转入 `替代标识符` / `Alternative Identifiers`。

正确写法：

```json
{
  "core": {
    "cstr_identifier": "31253.11.CSTR.2026.000001",
    "alternative_identifiers": ["10.1234/example.dataset"]
  }
}
```

错误写法：

```json
{
  "core": {
    "cstr_identifier": "10.1234/example.dataset"
  }
}
```

## 测试文件

本目录提供以下测试 JSON：

- `dataset-valid.json`：标准数据集样例，含合法 CSTR 和 DOI 替代标识符
- `data-paper-valid.json`：标准数据论文样例
- `doi-in-cstr-field.json`：故意把 DOI 填入 `cstr_identifier`，用于验证后端不会误写 CSTR 字段
- `minimal-other.json`：最小可解析样例，资源类型为其他
