# Interface Test Workflow

这个目录保存 `/register` 和 `/query` 的样例驱动接口测试。

## 目录

- `cases/register_cases.csv`: `/register` 测试样例。
- `cases/query_cases.csv`: `/query` 测试样例。
- `samples/text/`: 文本输入样例。
- `samples/upload/`: 上传文件样例。
- `reports/`: 自动生成的测试报告。
- `run_interface_tests.py`: 根据 `register_cases.csv` 和 `query_cases.csv` 中保留的人工编辑结果生成同一张报告，不会重新请求接口。

## 使用方法

根据两个 CSV 中的人工编辑结果生成报告：

```powershell
py -3.12 tests/run_interface_tests.py
```

只生成某个接口或某类样例的报告：

```powershell
py -3.12 tests/run_interface_tests.py --endpoint register
py -3.12 tests/run_interface_tests.py --endpoint query
py -3.12 tests/run_interface_tests.py --category 已写extractor
```

脚本只读取 `tests/cases/register_cases.csv` 和 `tests/cases/query_cases.csv` 中 `enabled=yes` 的行，不会重新运行用例，也不会请求后端服务。报告中的人工结论来自 `last_status`，原因来自 `manual_conclusion`，预期说明优先来自 `expected_nl`。

报告会生成到：

- `tests/reports/interface_test_report.md`
- `tests/reports/interface_test_report.json`

## 可视化编辑器

如果不想手动编辑 CSV，可以启动本地编辑器：

```powershell
py -3.12 tests/test_editor_server.py
```

然后访问：

```text
http://127.0.0.1:8765
```

编辑器可以新增、复制、删除、保存测试用例，单条调用 `/register` 或 `/query`，展示请求 JSON、响应 JSON、自动检查结果，并保存自然语言预期和人工结论。

启动编辑器后，`web-frontend` 页面里的“添加到测试记录”按钮也会把当前成功的 `/register` 或 `/query` 调用一键保存到测试用例 CSV。按钮只会连接本机 `http://127.0.0.1:8765`，不会把 API Key 写入测试记录。

## 维护样例

日常只需要编辑 `tests/cases/*.csv`。`enabled` 不是 `yes` 的样例会被跳过。

当前测试范围按实际仍在使用的入口维护：

- `/register`: 只保留 `source=url` 的 URL 分析和文件上传用例。
- `/query`: 只保留 DOI/CSTR 标识符查询用例。
- 已停用的 `text`、`web` 输入路径不再作为默认测试用例维护。

`expected_checks` 用分号分隔，支持：

- `核心元数据`: 检查字段路径存在。
- `领域元数据`: 检查字段路径存在。
- `zh.核心元数据`: 兼容旧格式，检查字段路径存在。
- `en.Core Metadata`: 兼容旧格式，检查字段路径存在。
- `items`: 检查顶层字段存在。
- `items[0].status=ok`: 检查数组字段值。
- `message=Missing URL`: 检查错误信息。
- `title_non_empty`: 检查核心标题字段非空。
- `any_item_ok`: 检查 `/query` 至少一个结果成功。
- `any_item_error`: 检查 `/query` 至少一个结果失败。
- `contains=China Urban Heat Island`: 检查整个 JSON 响应中包含这段文本。
- `not_contains=Invalid token`: 检查整个 JSON 响应中不包含这段文本。
- `核心元数据.metadatas[0].titles~=Chat-REC`: 检查指定字段路径下包含这段文本。

例如，要写“输入某网站，期望最终结果包含某段自然语言内容”，可以这样写：

```csv
id,enabled,endpoint,category,input_type,source,mode,strategy,payload_or_file,expected_status,expected_checks,description
R101,yes,register,已写extractor,url,url,common,auto,https://example.org/detail/1,200,核心元数据;title_non_empty;contains=青藏高原多年冻土数据集;contains=空间分辨率,检查某网站返回内容
```

如果只想检查某个字段，而不是整个返回体：

```csv
R102,yes,register,已写extractor,url,url,common,auto,https://example.org/detail/2,200,核心元数据.metadatas[0].titles~=青藏高原;领域元数据~=冻土,检查标题和领域描述
```
