# 元数据双向映射工具用户使用手册

[![在线服务](https://img.shields.io/badge/在线服务-可访问-2ea44f)](http://8.130.186.178:21005)
![文件上传](https://img.shields.io/badge/文件上传-JSON%20%2F%20XML-1f6feb)
![解析方式](https://img.shields.io/badge/解析方式-规则解析-f97316)

## 服务入口

`http://8.130.186.178:21005` 

用户可通过浏览器访问该地址使用网页工具，也可通过接口方式调用服务。

> [!NOTE]
> 本手册面向网页用户和接口对接方，说明线上服务的使用方式。

## 功能概览

本工具用于将科技资源网页、JSON/XML 数据文件、DOI/CSTR 标识符解析为统一的元数据结构。

| 功能 | 说明 |
| --- | --- |
| URL 分析 | 输入科技资源详情页 URL，提取并映射元数据 |
| 文件上传 | 上传 JSON/XML 文件，转换为核心元数据格式 |
| 标识符查询 | 输入 DOI/CSTR，解析资源并整理元数据 |
| 结果展示 | 查看核心元数据、领域专用元数据及中英文结果 |
| 结果下载 | 下载当前结果 JSON 文件 |
| 历史记录 | 查看近期任务记录 |

## 网页端使用方法

### URL 分析

适用于已经配置规则的科技资源详情页。

1. 进入服务首页。
2. 选择“领域元数据到核心元数据”。
3. 选择“输入 URL”。
4. 输入资源详情页 URL。
5. 点击“确认并分析”。

说明：

- 如果网页已配置专门规则，会优先使用规则提取。
- 如果该网站暂未覆盖规则，可能出现提取失败或部分字段为空。
- 需要登录或无法公开访问的页面可能无法完整提取。

> [!TIP]
> URL 分析更适合公开可访问的资源详情页。需要登录的页面建议改用文件上传，或提供示例页面补充规则。

### 文件上传

适用于上传本地 JSON/XML 元数据文件，并转换为核心元数据格式。
文末有一个可供参考的json样例。

1. 进入服务首页。
2. 选择“领域元数据到核心元数据”。
3. 选择“上传数据”。
4. 点击“选择文件”，选择 `.json` 或 `.xml` 文件。
5. 点击“确认并分析”。

说明：

- 仅支持 `.json` / `.xml` 文件。
- 文件上传不会调用大模型，会使用结构化规则解析。
- JSON 字段名不必完全符合标准，系统会尝试识别常见别名，例如 `title`、`name`、`datasetName`、`description`、`abstract` 等。

> [!IMPORTANT]
> 文件上传仅支持 `.json` / `.xml`。接口调用时必须使用 `multipart/form-data`，文件字段名固定为 `file`。

### DOI/CSTR 查询

适用于通过 DOI 或 CSTR 标识符解析资源。

1. 选择“输入 DOI/CSTR”。
2. 输入一个或多个 DOI/CSTR。
3. 多个标识符可用换行、空格或逗号分隔。
4. 点击“确认并分析”。

说明：

- CSTR 可以带或不带 `CSTR:` 前缀。
- 如果标识符解析服务无法返回资源页面，可能会查询失败。

## 结果查看与下载

分析完成后，页面会展示：

- 核心元数据项目表
- 领域专用元数据项目表
- 中文/英文结果切换

点击“下载”可导出当前结果的 JSON 文件。

## 接口调用

### 文件上传接口

| 项目 | 内容 |
| --- | --- |
| 接口地址 | `POST http://8.130.186.178:21005/register` |
| 请求类型 | `multipart/form-data` |
| 文件字段名 | `file` |
| `source` | 固定传 `upload` |
| `mode` | 通常传 `common` |

示例：

```bash
curl -X POST http://8.130.186.178:21005/register \
  -H "X-User-Id: test-user" \
  -H "X-User-Name: test" \
  -H "X-User-Email: test@example.com" \
  -F "source=upload" \
  -F "mode=common" \
  -F "file=@metadata.json"
```

注意：

- 上传模式不使用 `text` 字段。
- 文件字段名必须是 `file`。
- 后端会固定使用 `upload_rule` 解析，不调用大模型。

> [!WARNING]
> `source=upload` 不能把 JSON/XML 原文放在 `text` 字段里，请通过 `file=@metadata.json` 上传文件。

### DOI/CSTR 查询接口

| 项目 | 内容 |
| --- | --- |
| 接口地址 | `POST http://8.130.186.178:21005/query` |
| 请求类型 | `application/json` |

示例：

```bash
curl -X POST http://8.130.186.178:21005/query \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test-user" \
  -H "X-User-Name: test" \
  -H "X-User-Email: test@example.com" \
  -d '{"source":"identifier","identifiers":"10.48550/arXiv.2303.14524","mode":"common"}'
```

### URL 分析接口

| 项目 | 内容 |
| --- | --- |
| 接口地址 | `POST http://8.130.186.178:21005/register` |
| 请求类型 | `application/json` |

示例：

```bash
curl -X POST http://8.130.186.178:21005/register \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test-user" \
  -H "X-User-Name: test" \
  -H "X-User-Email: test@example.com" \
  -d '{"source":"url","url":"https://example.com/resource","mode":"common"}'
```

## 常见问题

### 上传文件时报 “Missing file”

表示请求中没有收到文件。请确认使用 `multipart/form-data`，并且文件字段名为 `file`。

### 上传文件时报 “source=upload requires multipart/form-data with file field”

表示上传模式不能把 JSON/XML 原文放在 `text` 字段里，需要通过文件字段 `file` 上传。

### URL 分析失败

可能原因：

- URL 无法被服务访问。
- 页面需要登录。
- 该网站暂未配置规则。
- 页面结构发生变化。

如果是未覆盖的网站，可以提供示例页面，由维护方补充规则。

### 某些字段显示“未提取到”

表示原始页面或文件中没有明确字段，或当前规则暂未覆盖该字段。

### 是否会调用大模型

当前线上环境主要使用规则解析。大语言模型接口仅作为内部测试备用，面向公众的服务默认不依赖大模型。

> [!NOTE]
> 如果遇到暂未支持的网站或特殊 JSON/XML 格式，可提供样例页面或样例文件，由维护方补充规则。

## 上传 JSON 样例

可将以下内容保存为 `metadata.json`，用于测试“上传数据”功能：

```json
{
  "resource_type": "dataset",
  "core": {
    "title": "湖泊水质长期观测数据集",
    "creators": [
      {
        "name": "张三",
        "affiliation": "示例数据中心",
        "email": "zhangsan@example.com"
      }
    ],
    "publisher": "示例数据中心",
    "publication_date": "2026-07-01",
    "description": "该数据集包含某湖泊水温、pH、溶解氧等水质指标的长期观测记录。",
    "keywords": ["湖泊", "水质", "长期观测"],
    "subjects": ["环境科学", "水文学"],
    "language": "zh",
    "doi": "10.1234/example.dataset",
    "resource_url": ["https://example.com/datasets/lake-water-quality"],
    "rights": "开放共享"
  },
  "domain": {
    "dataset_basic_information": {
      "title": "湖泊水质长期观测数据集",
      "identifier": "10.1234/example.dataset",
      "abstract": "湖泊水质长期观测数据，包含多项水环境指标。",
      "keywords": ["湖泊", "水质", "观测"]
    },
    "dataset_publication_information": {
      "publisher": "示例数据中心",
      "publication_date": "2026-07-01",
      "version_information": "V1.0"
    },
    "dataset_service_information": {
      "dataset_access_url": "https://example.com/datasets/lake-water-quality",
      "dataset_license": "CC BY 4.0"
    }
  }
}
```
