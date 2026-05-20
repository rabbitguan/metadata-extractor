"""
网站直接处理函数 - 对于常见网站，直接通过字符串匹配生成JSON
而不需要经过大模型处理
"""

from html import unescape
import json
import re
from typing import Dict, Optional


def build_base_metadata(
    resource_type_zh: str,
    resource_type_en: str,
    **kwargs
) -> Dict:
    """
    构建基础元数据JSON框架（新核心元数据结构）
    
    参数:
        resource_type_zh: 中文资源类型
        resource_type_en: 英文资源类型
        **kwargs: 其他元数据字段
    
    返回:
        完整的元数据JSON结构（包含zh和en）
    """
    # 提取参数
    titles_zh = kwargs.get('titles_zh', [])
    titles_en = kwargs.get('titles_en', [])
    identifier = kwargs.get('identifier')
    creators = kwargs.get('creators', [])
    publisher = kwargs.get('publisher')
    publish_date = kwargs.get('publish_date')
    descriptions_zh = kwargs.get('descriptions_zh', [])
    descriptions_en = kwargs.get('descriptions_en', [])
    keywords = kwargs.get('keywords', [])
    subjects = kwargs.get('subjects', [])
    language = kwargs.get('language')
    contributors = kwargs.get('contributors', [])
    alternative_identifiers = kwargs.get('alternative_identifiers', [])
    related_identifiers = kwargs.get('related_identifiers', [])
    rights = kwargs.get('rights', [])
    funders = kwargs.get('funders', [])
    version = kwargs.get('version')
    urls = kwargs.get('urls', [])
    
    metadata = {
        "zh": {
            "标题": titles_zh,
            "CSTR标识符": identifier,
            "创建者": creators,
            "发布机构": publisher,
            "发布日期": publish_date,
            "描述": descriptions_zh,
            "关键词": keywords,
            "学科": subjects,
            "语言": language,
            "贡献者": contributors,
            "替代标识符": alternative_identifiers,
            "关联标识符": related_identifiers,
            "权限": rights,
            "资助者": funders,
            "版本": version,
            "资源链接": urls,
            "资源类型": resource_type_zh
        },
        "en": {
            "titles": titles_en,
            "identifier": identifier,
            "creators": creators,
            "publisher": publisher,
            "publish_date": publish_date,
            "descriptions": descriptions_en,
            "keywords": keywords,
            "subjects": subjects,
            "language": language,
            "contributors": contributors,
            "alternative_identifiers": alternative_identifiers,
            "related_identifiers": related_identifiers,
            "rights": rights,
            "funders": funders,
            "version": version,
            "urls": urls,
            "ResourceType": resource_type_en
        }
    }
    
    return metadata


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _extract_meta_content(html: str, meta_name: str) -> Optional[str]:
    pattern = rf'<meta\s+name=["\']{re.escape(meta_name)}["\']\s+content=["\']([^"\']*)["\']'
    match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return _clean_text(match.group(1))
    return None


def _extract_first_match(html: str, pattern: str, flags=re.IGNORECASE | re.DOTALL) -> Optional[str]:
    match = re.search(pattern, html, flags=flags)
    if match:
        return _clean_text(match.group(1))
    return None


def _extract_arxiv_identifier(url: str, html: str) -> Optional[str]:
    url_match = re.search(r'arxiv\.org/abs/(\d{4}\.\d{4,5})(?:v\d+)?', url, flags=re.IGNORECASE)
    if url_match:
        return url_match.group(1)

    meta_id = _extract_meta_content(html, 'citation_arxiv_id')
    if meta_id:
        return meta_id

    return _extract_first_match(html, r'arXiv:(\d{4}\.\d{4,5})')


def _extract_arxiv_subjects(html: str) -> tuple[Optional[str], Optional[str]]:
    primary = _extract_first_match(html, r'<span class="primary-subject">([^<]+)</span>')
    if not primary:
        return None, None

    if '(' in primary and primary.endswith(')'):
        subject_name, code = primary.rsplit('(', 1)
        return _clean_text(subject_name), code.rstrip(')')
    return _clean_text(primary), None


def _extract_arxiv_version(html: str, url: str) -> Optional[str]:
    # First prefer explicit submission history marker like [v1]
    match = re.search(r'<strong>\s*\[(v\d+)\]\s*</strong>', html, flags=re.IGNORECASE)
    if match:
        return _clean_text(match.group(1))

    # Fallback to URL variants like /abs/2605.18659v1
    match = re.search(r'/abs/\d{4}\.\d{4,5}(v\d+)', url, flags=re.IGNORECASE)
    if match:
        return _clean_text(match.group(1))

    # Fallback to og:url meta tag if present
    og_url = _extract_first_match(html, r'<meta\s+property=["\']og:url["\']\s+content=["\']([^"\']+)["\']')
    if og_url:
        match = re.search(r'/abs/\d{4}\.\d{4,5}(v\d+)', og_url, flags=re.IGNORECASE)
        if match:
            return _clean_text(match.group(1))

    return None


def handle_arxiv(content: str, url: str, title: str) -> Optional[Dict]:
    """
    处理 arXiv 论文
    
    策略：
    - 从 URL/content 中提取 arXiv ID
    - 解析 DOI（如果存在）
    - 提取标题、作者、摘要等
    """
    
    html = content or ""
    arxiv_id = _extract_arxiv_identifier(url, html)
    title_text = _extract_meta_content(html, 'citation_title') or _extract_first_match(html, r'<h1 class="title[^>]*>\s*<span class="descriptor">Title:</span>(.*?)</h1>') or title
    abstract_text = _extract_meta_content(html, 'citation_abstract') or _extract_first_match(html, r'<blockquote class="abstract[^>]*>\s*<span class="descriptor">Abstract:</span>(.*?)</blockquote>')
    authors = re.findall(r'<meta\s+name=["\']citation_author["\']\s+content=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    if not authors:
        authors = re.findall(r'<div class="authors">.*?<a[^>]*>([^<]+)</a>', html, flags=re.IGNORECASE | re.DOTALL)
    authors = [_clean_text(author) for author in authors if _clean_text(author)]
    subject_name, subject_code = _extract_arxiv_subjects(html)
    version_info = _extract_arxiv_version(html, url)
    submitted_date = _extract_meta_content(html, 'citation_date') or _extract_first_match(html, r'\[Submitted on\s+([^\]]+)\]')
    publication_date = _clean_text(submitted_date)
    doi = _extract_first_match(html, r'<a[^>]+id="arxiv-doi-link"[^>]*>(https://doi\.org/[^<]+)</a>')
    pdf_url = _extract_meta_content(html, 'citation_pdf_url') or (f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else None)
    license_url = _extract_first_match(html, r'<div class="abs-license">.*?<a[^>]+href="([^"]+)"', flags=re.IGNORECASE | re.DOTALL)
    current_browse = _extract_first_match(html, r'<div class="current">([^<]+)</div>')
    journal_ref = _extract_meta_content(html, 'citation_journal_title')
    keywords = [item for item in [subject_name, subject_code] if item]

    # 构建新核心元数据
    metadata = build_base_metadata(
        resource_type_zh="数据论文",
        resource_type_en="Data Paper",
        titles_zh=[_clean_text(title_text) or arxiv_id or url],
        titles_en=[_clean_text(title_text) or arxiv_id or url],
        identifier=doi or arxiv_id or url,
        creators=authors if authors else [],
        publisher=None,
        publish_date=publication_date,
        descriptions_zh=[_clean_text(abstract_text)] if _clean_text(abstract_text) else [],
        descriptions_en=[_clean_text(abstract_text)] if _clean_text(abstract_text) else [],
        keywords=keywords,
        subjects=[_clean_text(subject_name)] if _clean_text(subject_name) else [],
        language=None,
        contributors=[],
        alternative_identifiers=[doi] if doi else [],
        related_identifiers=[],
        rights=[license_url] if license_url else [],
        funders=[],
        version=version_info,
        urls=[url, pdf_url] if pdf_url else [url]
    )

    metadata["zh"]["数据论文内容信息"] = {
        "标识符": arxiv_id or url,
        "标题": _clean_text(title_text) or arxiv_id or url,
        "摘要": _clean_text(abstract_text),
        "关键词": keywords,
        "数据论文作者": {
            "作者姓名": authors if authors else None,
            "工作单位": None,
            "电子邮箱": None,
            "工作贡献": None,
            "作者简介": None,
        },
        "引言": None,
        "数据采集和处理方法": None,
        "数据样本描述": None,
        "数据质量控制和评估": None,
        "数据使用方法和建议": None,
        "参考文献": None,
        "致谢": None,
    }

    metadata["en"]["Data Paper Content Information"] = {
        "Identifier": arxiv_id or url,
        "Title": _clean_text(title_text) or arxiv_id or url,
        "Abstract": _clean_text(abstract_text),
        "Keywords": keywords,
        "Data Paper Authors": {
            "Author Name": authors if authors else None,
            "Affiliation": None,
            "Email": None,
            "Contribution": None,
            "Biography": None,
        },
        "Introduction": None,
        "Data Collection and Processing Methods": None,
        "Data Sample Description": None,
        "Data Quality Control and Evaluation": None,
        "Data Use Methods and Recommendations": None,
        "References": None,
        "Acknowledgements": None,
    }

    metadata["zh"]["数据论文出版信息"] = {
        "收稿日期": publication_date,
        "同评日期": None,
        "录用日期": None,
        "出版日期": publication_date,
        "版本信息": version_info,
        "出版期刊": journal_ref,
    }

    metadata["en"]["Data Paper Publication Information"] = {
        "Received Date": publication_date,
        "Review Date": None,
        "Accepted Date": None,
        "Publication Date": publication_date,
        "Version Information": version_info,
        "Journal": journal_ref,
    }

    metadata["zh"]["数据论文服务信息"] = {
        "数据论文引用格式": f"arXiv:{arxiv_id}" if arxiv_id else url,
        "数据论文下载地址": pdf_url,
        "数据论文共享许可协议": _clean_text(license_url),
        "数据集访问地址": None,
    }

    metadata["en"]["Data Paper Service Information"] = {
        "Data Paper Citation": f"arXiv:{arxiv_id}" if arxiv_id else url,
        "Data Paper Download URL": pdf_url,
        "Data Paper License": _clean_text(license_url),
        "Dataset Access URL": None,
    }

    return metadata


def handle_kaggle(content: str, url: str, title: str) -> Optional[Dict]:
    """
    处理 Kaggle 数据集
    
    策略：
    - 从 URL 中提取数据集 ID
    - 识别是否有下载链接
    """
    
    # 从 URL 解析数据集标识
    dataset_id = None
    if "kaggle.com/datasets/" in url:
        parts = url.split("kaggle.com/datasets/")
        if len(parts) > 1:
            dataset_id = parts[1].rstrip("/")
    
    metadata = build_base_metadata(
        resource_type_zh="数据集",
        domain_zh="数据集元数据",
        resource_type_en="Dataset",
        domain_en="Dataset Metadata",
        identifier=dataset_id or url,
        url=url,
        title_zh=title or "Kaggle Dataset",
        title_en=title or "Kaggle Dataset",
        description_zh="Kaggle 数据集",
        description_en="Kaggle Dataset"
    )
    
    # 添加数据集特定字段
    metadata["zh"]["数据集基本信息"] = {
        "标识符": dataset_id or url,
        "资源名称": title,
        "描述": "Kaggle平台发布的数据集"
    }
    
    metadata["en"]["Dataset Basic Information"] = {
        "Identifier": dataset_id or url,
        "Resource Name": title,
        "Description": "Dataset published on Kaggle platform"
    }
    
    return metadata


def handle_zenodo(content: str, url: str, title: str) -> Optional[Dict]:
    """
    处理 Zenodo 开放获取存储库
    
    策略：
    - 从 URL 中提取记录 ID
    - 识别 DOI
    """
    
    record_id = None
    doi = None
    
    # 从 URL 解析记录ID
    if "zenodo.org/record/" in url:
        parts = url.split("zenodo.org/record/")
        if len(parts) > 1:
            record_id = parts[1].rstrip("/").split("?")[0]
    
    # 从 content 或 URL 中寻找 DOI
    doi_pattern = r'10\.\d+/zenodo\.\d+'
    match = re.search(doi_pattern, content + " " + url)
    if match:
        doi = match.group(0)
    
    metadata = build_base_metadata(
        resource_type_zh="数据集",
        resource_type_en="Dataset",
        titles_zh=[title or "Zenodo Repository Record"],
        titles_en=[title or "Zenodo Repository Record"],
        identifier=doi or record_id or url,
        descriptions_zh=["Zenodo 开放获取存储库中的资源"],
        descriptions_en=["Resource in Zenodo Open Access Repository"],
        urls=[url]
    )
    
    # 添加数据集特定字段
    metadata["zh"]["数据集基本信息"] = {
        "标识符": doi or record_id or url,
        "资源名称": title
    }
    
    metadata["en"]["Dataset Basic Information"] = {
        "Identifier": doi or record_id or url,
        "Resource Name": title
    }
    
    return metadata


def handle_figshare(content: str, url: str, title: str) -> Optional[Dict]:
    """
    处理 Figshare 数据共享平台
    """
    
    article_id = None
    doi = None
    
    # 从 URL 解析 article ID
    if "figshare.com" in url:
        match = re.search(r'(\d+)(?:/v\d+)?/?$', url.rstrip("/"))
        if match:
            article_id = match.group(1)
    
    # 寻找 DOI
    doi_pattern = r'10\.6084/m9\.figshare\.\d+'
    match = re.search(doi_pattern, content + " " + url)
    if match:
        doi = match.group(0)
    
    metadata = build_base_metadata(
        resource_type_zh="数据集",
        resource_type_en="Dataset",
        titles_zh=[title or "Figshare Article"],
        titles_en=[title or "Figshare Article"],
        identifier=doi or article_id or url,
        descriptions_zh=["Figshare 数据共享平台资源"],
        descriptions_en=["Resource shared on Figshare platform"],
        urls=[url]
    )
    
    metadata["zh"]["数据集基本信息"] = {
        "标识符": doi or article_id or url,
        "资源名称": title
    }
    
    metadata["en"]["Dataset Basic Information"] = {
        "Identifier": doi or article_id or url,
        "Resource Name": title
    }
    
    return metadata


def handle_github(content: str, url: str, title: str) -> Optional[Dict]:
    """
    处理 GitHub 仓库
    
    策略：
    - 识别是否是数据集仓库（通过 README 或文件类型）
    """
    
    # 从 URL 提取所有者和仓库名
    repo_path = None
    if "github.com/" in url:
        parts = url.split("github.com/")[1].rstrip("/")
        repo_path = parts
    
    metadata = build_base_metadata(
        resource_type_zh="数据集",
        resource_type_en="Dataset",
        titles_zh=[title or "GitHub Repository"],
        titles_en=[title or "GitHub Repository"],
        identifier=url,
        descriptions_zh=["GitHub 上共享的数据或代码仓库"],
        descriptions_en=["Data or code repository shared on GitHub"],
        urls=[url]
    )
    
    metadata["zh"]["数据集基本信息"] = {
        "标识符": repo_path or url,
        "资源名称": title
    }
    
    metadata["en"]["Dataset Basic Information"] = {
        "Identifier": repo_path or url,
        "Resource Name": title
    }
    
    return metadata


def handle_openml(content: str, url: str, title: str) -> Optional[Dict]:
    """
    处理 OpenML 数据集
    """
    
    dataset_id = None
    
    # 从 URL 解析数据集ID
    if "openml.org/d/" in url:
        match = re.search(r'/d/(\d+)', url)
        if match:
            dataset_id = match.group(1)
    
    metadata = build_base_metadata(
        resource_type_zh="数据集",
        resource_type_en="Dataset",
        titles_zh=[title or "OpenML Dataset"],
        titles_en=[title or "OpenML Dataset"],
        identifier=dataset_id or url,
        descriptions_zh=["OpenML 机器学习数据集"],
        descriptions_en=["Machine learning dataset from OpenML"],
        urls=[url]
    )
    
    metadata["zh"]["数据集基本信息"] = {
        "标识符": dataset_id or url,
        "资源名称": title
    }
    
    metadata["en"]["Dataset Basic Information"] = {
        "Identifier": dataset_id or url,
        "Resource Name": title
    }
    
    return metadata


# 处理器映射表
HANDLERS = {
    'handle_arxiv': handle_arxiv,
    'handle_kaggle': handle_kaggle,
    'handle_zenodo': handle_zenodo,
    'handle_figshare': handle_figshare,
    'handle_github': handle_github,
    'handle_openml': handle_openml,
}


def detect_and_handle_website(content: str, url: str, title: str, handlers_config: Dict) -> Optional[Dict]:
    """
    检测网站并调用相应的处理器
    
    参数:
        content: 网页内容
        url: 网页URL
        title: 网页标题
        handlers_config: 网站处理器配置（从 website_handlers.json 加载）
    
    返回:
        如果匹配到已知网站，返回生成的元数据；否则返回 None（由调用方决定是否使用大模型）
    """
    
    combined = (url + " " + title + " " + content).lower()
    normalized_url = url.lower().strip()
    
    for website in handlers_config.get('websites', []):
        if website.get('name') == 'arXiv':
            if not re.search(r'^https?://arxiv\.org/abs/\d{4}\.\d{4,5}(?:v\d+)?/?$', normalized_url):
                continue
            if not re.search(r'arxiv\.org/abs/\d{4}\.\d{4,5}(?:v\d+)?', normalized_url):
                continue
            handler_name = website.get('handler')
            handler_func = HANDLERS.get(handler_name)
            if handler_func:
                try:
                    result = handler_func(content, url, title)
                    print(f"[Website Handler] 匹配到 {website['name']}，使用直接处理（无大模型调用）")
                    return result
                except Exception as e:
                    print(f"[Website Handler] {website['name']} 处理失败: {e}，将回退到大模型处理")
                    return None
            continue

        # 检查是否匹配任何模式
        patterns = website.get('patterns', [])
        matched = False
        
        for pattern in patterns:
            if pattern.lower() in combined:
                matched = True
                break
        
        if matched:
            handler_name = website.get('handler')
            handler_func = HANDLERS.get(handler_name)
            
            if handler_func:
                try:
                    result = handler_func(content, url, title)
                    print(f"[Website Handler] 匹配到 {website['name']}，使用直接处理（无大模型调用）")
                    return result
                except Exception as e:
                    print(f"[Website Handler] {website['name']} 处理失败: {e}，将回退到大模型处理")
                    return None
    
    # 未匹配到任何已知网站
    return None
