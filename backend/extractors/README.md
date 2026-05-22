# Extractors

这个目录用于按网站类型拆分提取规则。

约定：

- 每个网站一个独立的 `.py` 文件，例如 `arxiv.py`、`kaggle.py`。
- 每个文件至少提供两个可调用对象：`matches(url, title, content)` 和 `extract(content, url, title)`。
- `matches` 负责判断网页类型。
- `extract` 负责返回完整的双语元数据 JSON；如果规则不适用，返回 `None`。


## 优先实现站点（高优先级）

下面是建议优先实现的站点列表，按实现优先级排序。将这些站点对应的提取器脚本放在本目录下可以方便自动发现：

- `arxiv` （已实现）
- `pubmed` / `pmc`
- `biorxiv` / `medrxiv`
- `crossref`（DOI 元数据抓取）
- `datacite`
- `zenodo`
- `figshare`
- `kaggle`
- `github`（仓库 README / raw 文件提取）
- `ieee`（IEEE Xplore）
- `acm`（ACM Digital Library）
- `springer` / `nature` / `science`（出版社页面）
- `plos`

建议把每个提取器命名为网站简称，例如 `pubmed.py`、`zenodo.py`，并实现 `matches` / `extract` 两个函数。测试时可使用 `backend/demo_extractors.py` 来验证单个页面的提取结果。

文件位置：`backend/extractors/README.md`（本文件）。
