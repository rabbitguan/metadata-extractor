# 后端接口文档

- 服务地址：`http://127.0.0.1:4000`
- 通用返回：`application/json`
- CORS：已开启（`flask_cors.CORS`）

## 1. 提交内容分析

### `POST /register`

用于文本/网页/URL/上传内容的元数据提取。

#### 请求体

```json
{
  "source": "web",
  "mode": "common",
  "strategy": "auto",
  "force_reanalyze": false,
  "dynamic_render": "auto",
  "text": "页面文本内容",
  "html": "<html>...</html>",
  "url": "https://example.com/paper",
  "title": "页面标题"
}
```

#### 字段说明

- `source`：来源类型，常见值：`web` / `text` / `url` / `upload`
- `mode`：前端模式标识，常见值：`common` / `domain`（后端会透传给模型流程）
- `strategy`：提取策略，常见值：`auto` / `llm` / `rule`
- `force_reanalyze`：是否跳过历史缓存并强制重新分析（支持 `true/false`、`"1"`、`"true"` 等）
- `dynamic_render`：URL 直抓时是否使用浏览器动态渲染。支持 `auto` / `true` / `false`，默认 `auto`；显式传 `true` 会直接尝试动态渲染，`auto` 会按后端全局模式和域名配置判断
- `text`：待分析文本；当 `source` 为 `text` 或 `web` 时不能为空
- `html`：页面 HTML（用于规则提取与历史入库）
- `url`：页面 URL
- `title`：页面标题

#### URL 直抓模式（`source=url`）

当 `source=url` 时：

1. 必须提供 `url`
2. 后端会先抓取 URL 页面并提取文本，再进入分析流程
3. `text/html/title` 以抓取结果为准
4. CSTR 查询会继续访问配置好的补充源，例如 eScience；请求显式传 `dynamic_render=true` 或后端全局动态渲染开启后，这些网页会按规则尝试 Playwright 动态渲染

动态渲染运行时说明：

- 普通抓取先使用 `requests`，动态渲染作为兜底或指定域名增强。
- 默认 `auto` 请求不启用动态渲染；本地启动后端时加 `-d` 只表示“auto 请求访问指定域名网页后用浏览器渲染再解析”，不影响是否访问 NCDC/eScience 等数据源。
- 环境变量 `METADATA_DYNAMIC_RENDER_MODE` 仍支持 `auto` / `always` / `never`，默认 `never`。
- 环境变量 `METADATA_DYNAMIC_RENDER_DOMAINS` 可配置自动动态渲染域名，默认 `ncdc.ac.cn,escience.org.cn,mds.nmdis.org.cn`。
- 如果 Playwright/Chromium 不可用，后端会自动回退到静态抓取并打印 warning；首次启用前需要执行 `python -m playwright install chromium`。

本地直接运行 `backend.py` 时，需要动态渲染就加 `-d`：

```bash
python backend.py
python backend.py -d
```

#### 策略行为（`strategy`）

- `auto`：先走站点规则提取器（`extractors/*`），未命中再走 LLM
- `llm`：直接走 LLM
- `rule`：只走规则提取器；若未命中规则，当前实现会返回 400（表现为模型输出格式错误）
- `upload_rule`：上传 JSON/XML 专用规则解析；当 `source=upload` 时后端会强制使用该策略，不调用 LLM。

#### 上传文件模式（`source=upload`）

上传仅支持 JSON/XML 原始结构化内容，不支持 TXT 等非结构化文本。推荐 JSON 结构：

```json
{
  "resource_type": "dataset",
  "core": {
    "title": "Example Dataset",
    "cstr_identifier": "31253.11.CSTR.2026.000001",
    "creators": ["Alice"],
    "publisher": "Example Lab",
    "publication_date": "2026-06-20",
    "description": "A short description.",
    "keywords": ["metadata"],
    "subjects": ["Computer Science"],
    "language": "en",
    "alternative_identifiers": ["10.1234/example"],
    "resource_url": ["https://example.com/dataset"]
  },
  "domain": {
    "dataset_basic_information": {},
    "dataset_publication_information": {},
    "dataset_service_information": {}
  }
}
```

规则说明：

- `resource_type` 支持 `dataset` / `data_paper` / `other`，也兼容中文 `数据集` / `数据论文` / `其他`。
- `core.cstr_identifier` 只接受 CSTR 形态的标识符；如果用户误填 DOI，后端不会写入核心字段 `identifier`，会放入 `alternative_identifiers`。
- JSON 顶层也可传单元素数组；多资源数组会返回 400。
- XML 使用同名标签即可，例如 `<resource><resource_type>dataset</resource_type><core>...</core></resource>`。

#### 历史命中逻辑

- 默认会尝试按 URL 命中历史记录（`force_reanalyze=false`）
- 命中时直接返回历史结果，并附加：
  - `from_history: true`
  - `history_record_id`
  - `history_requested_url`
  - `history_page_title`
  - `history_created_at`

#### 历史入库条件

- 仅当本次请求最终进入分析流程且同时具备 `url` 和 `html` 时才写入历史库。
- 典型会入库：`source=url`、来自当前网页且携带 HTML 的请求。
- 典型不入库：纯文本分析（无 `html`）、仅上传文本但未提供网页 HTML 的请求。

#### 成功响应（200）

```json
{
  "核心元数据": {
    "metadatas": [
      {
        "titles": [
          {"lang": "zh", "name": "示例标题"},
          {"lang": "en", "name": "Example Title"}
        ],
        "identifier": "未提取到",
        "creators": [
          {
            "type": "Person",
            "person": {
              "names": [
                {"lang": "zh", "name": "张三"},
                {"lang": "en", "name": "San Zhang"}
              ],
              "emails": "未提取到",
              "identifiers": "未提取到",
              "affiliations": "未提取到"
            }
          }
        ],
        "publisher": {
          "names": [
            {"lang": "zh", "name": "示例机构"},
            {"lang": "en", "name": "Example Organization"}
          ],
          "identifiers": "未提取到"
        },
        "publish_date": "2026-06-20",
        "descriptions": [
          {"lang": "zh", "description": "示例描述"},
          {"lang": "en", "description": "Example description"}
        ],
        "keywords": [
          {"lang": "zh", "keyword": ["元数据"]},
          {"lang": "en", "keyword": ["metadata"]}
        ],
        "subjects": [{"standard_gbt": ["520"], "standard_oecd": ["102"]}],
        "language": "zh",
        "contributors": "未提取到",
        "alternative_identifiers": "未提取到",
        "related_identifiers": "未提取到",
        "rights": "未提取到",
        "funders": "未提取到",
        "version": "未提取到",
        "urls": ["https://example.org/resource"],
        "resource_type": "Data Paper"
      }
    ]
  },
  "数据论文元数据": {
    "数据论文内容信息": {
      "摘要": [
        {"lang": "zh", "description": "..."},
        {"lang": "en", "description": "..."}
      ]
    }
  }
}
```

说明：

- `核心元数据` 下保持与规范示例一致的 `metadatas` 数组结构。
- `metadatas[0]` 只包含核心元数据 17 个字段，不包含领域判定、扩展信息等辅助字段。
- 后端会保证核心字段存在，空值会被填充为占位文本 `未提取到`。
- 返回体不再按顶层 `zh` / `en` 分块；需要中英文的字段值在字段内部用 `lang` 区分。
- 领域结构是否存在，取决于规则/模型提取结果。

#### 失败响应

- 400：请求参数错误或模型返回格式不合法

```json
{
  "status": "error",
  "message": "Missing text"
}
```

```json
{
  "status": "error",
  "message": "Invalid bilingual JSON format from LLM"
}
```

- 500：后端处理异常

```json
{
  "status": "error",
  "message": "Failed to process text: ..."
}
```

---

## 2. DOI/CSTR 标识符解析并分析

### `POST /query`

从输入内容中提取 DOI/CSTR，逐个解析后分析元数据。

#### 请求体

```json
{
  "source": "identifier",
  "mode": "common",
  "identifiers": [
    "10.1000/xyz123",
    "12345.12.ABCD-2024"
  ]
}
```

也支持不传 `identifiers`，改为 `text` 或 `html`，后端会自动正则提取。

提取规则说明：

- 仅处理 `DOI` 和 `CSTR`，不会处理专利号。
- `identifiers` 为数组时优先使用该数组；否则回退使用 `identifiers` 字符串或 `text/html` 内容。

#### 成功响应（200）

```json
{
  "items": [
    {
      "identifier": "10.1000/xyz123",
      "type": "doi",
      "resolved_url": "https://doi.org/10.1000/xyz123",
      "source": "doi.org",
      "status": "ok",
      "payload": {
        "zh": {
          "核心元数据": {}
        },
        "en": {
          "Core Metadata": {}
        }
      },
      "updated_at": "2026-06-09T12:00:00.000000Z"
    },
    {
      "identifier": "12345.12.ABCD-2024",
      "type": "cstr",
      "status": "error",
      "message": "Failed to resolve CSTR ..."
    }
  ]
}
```

说明：

- `items` 可同时包含 `status=ok` 和 `status=error`。
- 单个 `item` 只有在进入元数据分析流程时才会带 `updated_at`。

#### 失败响应（400）

- 未识别到 DOI/CSTR：

```json
{
  "status": "error",
  "message": "No DOI or CSTR identifier found"
}
```

- 全部解析失败：

```json
{
  "status": "error",
  "message": "Failed to resolve any DOI or CSTR identifier",
  "errors": [
    {
      "identifier": "10.1000/xyz123",
      "type": "doi",
      "message": "..."
    }
  ]
}
```

---

## 3. 历史记录查询（按 URL/文本）

### `GET /history/lookup`

按 URL（或文本中抽取 URL）查当前用户最新一条历史分析结果。用户由网关透传的 `X-User-Id` 请求头识别。

#### Query 参数

- `url`：可选，目标 URL
- `text`：可选，后端会从文本中提取 URL 参与匹配

#### 响应（命中）

```json
{
  "found": true,
  "zh": {},
  "en": {},
  "from_history": true,
  "history_record_id": 12,
  "history_requested_url": "https://example.com",
  "history_page_title": "Example",
  "history_created_at": "2026-06-09 12:00:00"
}
```

#### 响应（未命中）

```json
{
  "found": false
}
```

---

## 4. 用户查询记录

### `GET /history`

分页返回当前用户的查询/转换记录，包含前端日志页需要展示的完整结果 JSON。用户由网关透传的 `X-User-Id` 请求头识别。

#### Query 参数

- `limit`：默认 `20`，最大 `200`
- `offset`：默认 `0`

说明：

- 实际查询会强制限制为 `1..200` 条。
- 返回体中的 `limit` 是请求参数的整型回显值，不一定等于实际查询上限。

#### 成功响应（200）

```json
{
  "records": [
    {
      "id": 15,
      "source": "url",
      "mode": "common",
      "strategy": "url",
      "title": "Example Paper",
      "requested_url": "https://example.com/paper",
      "identifier_input": "",
      "input_preview": "https://example.com/paper",
      "payload": {
        "核心元数据": {}
      },
      "created_at": "2026-06-09 12:00:00"
    }
  ],
  "limit": 20,
  "offset": 0
}
```

### `POST /history`

保存一条当前用户的查询/转换记录。

#### 请求体

```json
{
  "source": "url",
  "mode": "common",
  "strategy": "url",
  "title": "Example Paper",
  "url": "https://example.com/paper",
  "identifierInput": "",
  "inputPreview": "https://example.com/paper",
  "payload": {
    "核心元数据": {}
  }
}
```

#### 成功响应（200）

```json
{
  "status": "ok",
  "id": 16
}
```

### `DELETE /history`

清空当前用户的查询/转换记录。

#### 成功响应（200）

```json
{
  "status": "ok",
  "deleted": 3
}
```

#### 失败响应（500）

```json
{
  "status": "error",
  "message": "Failed to load history: ..."
}
```

---

## 5. 状态码约定

- `200`：成功（包括部分项失败但整体请求可返回结果的场景，如 `/query` 的 `items` 中混合 `ok/error`）
- `400`：请求参数错误、标识符不可解析、模型响应格式错误
- `500`：服务端内部错误

补充：

- `/history/lookup` 未命中时是 `200` + `{"found": false}`（不是 404）

---

## 6. 调用示例（cURL）

### 6.1 当前页面文本分析

```bash
curl -X POST http://127.0.0.1:4000/register \
  -H "Content-Type: application/json" \
  -d '{
    "source":"web",
    "mode":"common",
    "strategy":"auto",
    "text":"This is a dataset paper ...",
    "url":"https://example.com/page",
    "title":"Example Page"
  }'
```

### 6.2 URL 直接分析

```bash
curl -X POST http://127.0.0.1:4000/register \
  -H "Content-Type: application/json" \
  -d '{
    "source":"url",
    "mode":"domain",
    "url":"https://example.com/page"
  }'
```

### 6.3 DOI/CSTR 批量分析

```bash
curl -X POST http://127.0.0.1:4000/query \
  -H "Content-Type: application/json" \
  -d '{
    "source":"identifier",
    "mode":"common",
    "identifiers":["10.1000/xyz123","12345.12.ABCD-2024"]
  }'
```

### 6.4 查询历史命中

```bash
curl "http://127.0.0.1:4000/history/lookup?url=https%3A%2F%2Fexample.com%2Fpage"
```

### 6.5 分页获取历史列表

```bash
curl "http://127.0.0.1:4000/history?limit=20&offset=0"
```
