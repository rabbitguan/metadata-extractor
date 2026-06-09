# 前端接口文档

本文档面向前端联调用，接口基于当前 Flask 后端实现整理。

## 基础信息

- Base URL: `http://127.0.0.1:4000`
- 数据格式: JSON
- 字符编码: UTF-8
- 跨域: 后端已启用 CORS

通用请求头:

```http
Content-Type: application/json
```

## 接口总览

| 功能 | 方法 | 路径 |
| --- | --- | --- |
| 文本/网页/上传内容元数据提取 | POST | `/register` |
| DOI/CSTR 标识符解析并提取 | POST | `/query` |
| 查询模型服务状态 | GET | `/features` |
| 按 URL 查询历史结果 | GET | `/history/lookup` |
| 查询历史记录列表 | GET | `/history` |

## POST /register

用于从文本、当前网页、输入 URL、上传文件内容中提取元数据。

### 请求参数

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `text` | string | 条件必填 | `""` | 待分析文本。`source` 为 `text` 或 `web` 时不能为空。 |
| `html` | string | 否 | `""` | 页面 HTML。传入 `url` 和 `html` 时，成功结果会写入历史库。 |
| `url` | string | 条件必填 | `""` | 资源 URL。`source` 为 `url` 时必填。 |
| `title` | string | 否 | `""` | 页面标题，用于辅助提取和历史记录展示。 |
| `source` | string | 否 | `text` | 来源类型: `text`、`web`、`url`、`upload`。 |
| `mode` | string | 否 | `common` | 元数据模式: `common` 或 `domain`。当前返回体同时包含核心和领域结果。 |
| `strategy` | string | 否 | `auto` | 提取策略，默认自动。 |
| `force_reanalyze` | boolean/string | 否 | `false` | 是否跳过历史结果重新分析。字符串 `true`、`1`、`yes`、`on` 会被识别为真。 |

### 请求示例: 当前网页/文本

```http
POST /register HTTP/1.1
Content-Type: application/json
```

```json
{
  "source": "web",
  "mode": "common",
  "text": "页面正文内容...",
  "html": "<html>...</html>",
  "url": "https://example.com/resource/1",
  "title": "资源页面标题",
  "strategy": "auto"
}
```

### 请求示例: URL

`source=url` 时后端会直接抓取 `url` 并分析，无需前端先抓取页面内容。

```json
{
  "source": "url",
  "mode": "common",
  "url": "https://example.com/resource/1",
  "force_reanalyze": false
}
```

### 请求示例: 上传文件

上传接口本身不接收二进制文件。前端应先读取文件为文本，再调用本接口。

```json
{
  "source": "upload",
  "mode": "common",
  "text": "文件内容...",
  "title": "sample.json"
}
```

### 成功响应

成功时返回中英文双语元数据对象。

```json
{
  "zh": {
    "核心元数据": {
      "标题": [
        {
          "lang": "zh",
          "name": "示例资源"
        }
      ],
      "CSTR标识符": "未提取到",
      "创建者": [],
      "发布机构": "未提取到",
      "发布日期": "未提取到",
      "描述": [],
      "关键词": [],
      "学科": [],
      "语言": "zh",
      "贡献者": [],
      "替代标识符": [],
      "关联标识符": [],
      "权限": [],
      "资助者": [],
      "版本": "未提取到",
      "资源链接": [
        "https://example.com/resource/1"
      ],
      "资源类型": "数据集",
      "领域判定": "数据集元数据",
      "扩展信息": "未提取到"
    },
    "数据集元数据": {
      "数据集基本信息": {}
    }
  },
  "en": {
    "Core Metadata": {
      "Title": [
        {
          "lang": "en",
          "name": "Example Resource"
        }
      ],
      "Identifier": "Not extracted",
      "ResourceType": "Dataset",
      "Domain Classification": "Dataset Metadata",
      "Extension Info": "Not extracted"
    },
    "Dataset Metadata": {
      "Dataset Basic Information": {}
    }
  }
}
```

### 历史命中响应

如果命中历史库，响应会在原元数据对象上追加以下字段:

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `from_history` | boolean | 固定为 `true`，表示结果来自历史库。 |
| `history_record_id` | number | 历史记录 ID。 |
| `history_requested_url` | string | 历史记录中的请求 URL。 |
| `history_page_title` | string/null | 历史记录中的页面标题。 |
| `history_created_at` | string | 历史记录创建时间。 |

前端可以用 `from_history` 控制是否展示“重新分析”按钮。

### 错误响应

| HTTP 状态码 | 场景 | 响应示例 |
| --- | --- | --- |
| 400 | 缺少 URL、缺少文本、URL 抓取失败、模型返回 JSON 格式异常 | `{"status":"error","message":"Missing URL"}` |
| 422 | 当前内容格式不支持 | `{"status":"error","message":"尚未支持该网页或资源格式"}` |
| 500 | 处理过程异常 | `{"status":"error","message":"Failed to process text: ..."}` |

## POST /query

用于输入 DOI/CSTR 编号，后端解析标识符对应页面后提取元数据。

### 请求参数

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `identifiers` | string/string[] | 条件必填 | - | DOI/CSTR 列表。可以传字符串、数组。 |
| `text` | string | 条件必填 | `""` | 未传 `identifiers` 时，会从 `text` 中识别 DOI/CSTR。 |
| `html` | string | 否 | `""` | 未传 `identifiers` 和 `text` 时，会从 `html` 中识别。 |
| `source` | string | 否 | - | 前端可传 `identifier`，后端当前不依赖该字段。 |
| `mode` | string | 否 | `common` | 元数据模式: `common` 或 `domain`。 |

### 请求示例

```json
{
  "source": "identifier",
  "mode": "common",
  "identifiers": "10.1234/example\nCSTR:12345.11.demo"
}
```

### 成功响应

返回 `items` 数组，每个标识符对应一个解析结果。部分标识符失败时，成功项和失败项会同时返回。

```json
{
  "items": [
    {
      "identifier": "10.1234/example",
      "type": "doi",
      "resolved_url": "https://example.com/paper",
      "source": "crossref",
      "status": "ok",
      "payload": {
        "zh": {
          "核心元数据": {}
        },
        "en": {
          "Core Metadata": {}
        }
      },
      "updated_at": "2026-06-09T02:30:00.000000Z"
    },
    {
      "identifier": "CSTR:12345.11.demo",
      "type": "cstr",
      "status": "error",
      "message": "解析失败原因"
    }
  ]
}
```

### 顶层错误响应

当没有识别到任何 DOI/CSTR，或全部解析失败时返回 400。

```json
{
  "status": "error",
  "message": "No DOI or CSTR identifier found"
}
```

全部解析失败时会额外返回 `errors` 数组:

```json
{
  "status": "error",
  "message": "Failed to resolve any DOI or CSTR identifier",
  "errors": [
    {
      "identifier": "10.1234/example",
      "type": "doi",
      "message": "解析失败原因"
    }
  ]
}
```

## GET /features

用于查询后端模型服务是否启用。

### 请求示例

```http
GET /features
```

### 成功响应

```json
{
  "llm_enabled": true
}
```

字段说明:

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `llm_enabled` | boolean | 是否启用大模型提取服务。 |

## GET /history/lookup

按 URL 查询最近一次历史分析结果。

### Query 参数

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `url` | string | 否 | 资源 URL。 |
| `text` | string | 否 | 可选文本。后端会从文本中提取 URL 作为历史查询候选。 |

### 请求示例

```http
GET /history/lookup?url=https%3A%2F%2Fexample.com%2Fresource%2F1
```

### 未命中响应

```json
{
  "found": false
}
```

### 命中响应

命中时返回 `found=true`，并合并 `/register` 的历史命中响应字段和元数据内容。

```json
{
  "found": true,
  "from_history": true,
  "history_record_id": 12,
  "history_requested_url": "https://example.com/resource/1",
  "history_page_title": "资源页面标题",
  "history_created_at": "2026-06-09 10:30:00",
  "zh": {
    "核心元数据": {}
  },
  "en": {
    "Core Metadata": {}
  }
}
```

## GET /history

分页查询历史记录列表。该接口只返回列表摘要，不返回完整元数据结果。

### Query 参数

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `limit` | number/string | 否 | `20` | 每页条数。后端会限制在 `1` 到 `200`。 |
| `offset` | number/string | 否 | `0` | 偏移量。小于 0 会按 0 处理。 |

### 请求示例

```http
GET /history?limit=20&offset=0
```

### 成功响应

```json
{
  "records": [
    {
      "id": 12,
      "requested_url": "https://example.com/resource/1",
      "page_title": "资源页面标题",
      "html_sha256": "a1b2...",
      "mode": "common",
      "strategy": "auto",
      "resource_type_zh": "数据集",
      "resource_type_en": "Dataset",
      "domain_classification_zh": "数据集元数据",
      "domain_classification_en": "Dataset Metadata",
      "created_at": "2026-06-09 10:30:00"
    }
  ],
  "limit": 20,
  "offset": 0
}
```

### 错误响应

```json
{
  "status": "error",
  "message": "Failed to load history: ..."
}
```

## 元数据返回结构说明

### 顶层结构

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `zh` | object | 中文元数据结果。 |
| `en` | object | 英文元数据结果。 |
| `from_history` | boolean | 可选。历史命中时存在。 |

### 中文结果常见分区

| 分区 | 说明 |
| --- | --- |
| `核心元数据` | 所有资源共有的核心字段。 |
| `数据集元数据` | 资源类型为数据集时可能返回。 |
| `数据论文元数据` | 资源类型为数据论文时可能返回。 |
| `标准文献元数据` | 资源类型为标准文献时可能返回。 |
| `生态科学数据元数据` | 资源类型为生态科学数据时可能返回。 |

### 英文结果常见分区

| 分区 | 说明 |
| --- | --- |
| `Core Metadata` | 所有资源共有的核心字段。 |
| `Dataset Metadata` | 资源类型为数据集时可能返回。 |
| `Data Paper Metadata` | 资源类型为数据论文时可能返回。 |
| `Standard Literature Metadata` | 资源类型为标准文献时可能返回。 |
| `Ecological Science Data Metadata` | 资源类型为生态科学数据时可能返回。 |

### 核心字段对照

| 中文字段 | 英文字段 | 说明 |
| --- | --- | --- |
| `标题` | `Title` | 资源标题。 |
| `CSTR标识符` | `Identifier` | CSTR 或其他主标识符。 |
| `创建者` | `Creators` | 作者、创建者。 |
| `发布机构` | `Publisher` | 发布或产出机构。 |
| `发布日期` | `Publication Date` | 资源发布日期。 |
| `描述` | `Description` | 摘要或描述。 |
| `关键词` | `Keywords` | 关键词。 |
| `学科` | `Subjects` | 学科分类。 |
| `语言` | `Language` | 资源语言。 |
| `贡献者` | `Contributors` | 次要贡献者。 |
| `替代标识符` | `Alternative Identifiers` | DOI、Handle 等其他标识符。 |
| `关联标识符` | `Related Identifiers` | 关联资源标识符。 |
| `权限` | `Rights` | 许可协议、版权等。 |
| `资助者` | `Funders` | 基金、项目、资助机构。 |
| `版本` | `Version` | 版本号。 |
| `资源链接` | `Resource URL` | 资源访问地址。 |
| `资源类型` | `ResourceType` | 数据集、数据论文、标准文献、生态科学数据、其他。 |
| `领域判定` | `Domain Classification` | 应使用的领域元数据分区。 |
| `扩展信息` | `Extension Info` | 非标准字段或补充信息。 |

## 前端接入建议

- 当前插件中已使用的后端地址为:
  - `BACKEND_REGISTER_URL = http://127.0.0.1:4000/register`
  - `BACKEND_QUERY_URL = http://127.0.0.1:4000/query`
  - `BACKEND_FEATURES_URL = http://127.0.0.1:4000/features`
  - `HISTORY_LOOKUP_URL = http://127.0.0.1:4000/history/lookup`
- 调用 `/register` 后，如果响应体含 `from_history: true`，建议展示“重新分析”按钮；重新分析时传 `force_reanalyze: true`。
- 渲染字段时不要假设所有字段都有值。空值可能是 `未提取到`、`Not extracted`、空数组或空对象。
- `/query` 的 `items` 可以混合成功和失败项，前端应按 `item.status` 分别处理。
- `/history` 是摘要列表接口；如需完整结果，使用 `/history/lookup` 按 URL 查询。
