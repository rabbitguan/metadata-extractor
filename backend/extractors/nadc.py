from __future__ import annotations

import re
from html import unescape
from typing import Any, Dict, Iterable, Optional
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

from .base import MetadataDict


RULE_NAME = 'NADC Resource Detail'

BASE_URL = 'https://nadc.china-vo.org'
PUBLISHER_ZH = '国家天文科学数据中心'
PUBLISHER_EN = 'National Astronomical Data Center'
CSTR_PATTERN = re.compile(r'\b(?:CSTR\s*[:：]\s*)?([A-Z0-9]{5}\.\d{2}\.[-._;()/:A-Z0-9]+)\b', re.IGNORECASE)
DOI_PATTERN = re.compile(r'\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b')
FETCH_HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}


def _clean_text(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value))
    text = re.sub(r'[\u200b\xa0]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text or None


def _first_non_empty(*values: Optional[Any]) -> Optional[str]:
    for value in values:
        cleaned = _clean_text(value)
        if cleaned:
            return cleaned
    return None


def _unique_list(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = _clean_text(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def _text_or_none(element) -> Optional[str]:
    if not element:
        return None
    return _clean_text(element.get_text(' ', strip=True))


def _split_terms(value: Optional[Any]) -> list[str]:
    text = _clean_text(value)
    if not text:
        return []
    return _unique_list(re.split(r'[;；,，、|]+|\s{2,}', text))


def _extract_resource_id(url: str) -> Optional[str]:
    match = re.search(r'/res/(r\d+)/?', urlparse(url or '').path)
    return match.group(1) if match else None


def _extract_cstr(*values: Optional[Any]) -> Optional[str]:
    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        match = CSTR_PATTERN.search(text)
        if match:
            return match.group(1)
    return None


def _extract_doi(*values: Optional[Any]) -> Optional[str]:
    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        match = DOI_PATTERN.search(text)
        if match:
            return match.group(0)
    return None


def _valid_http_url(value: Optional[str], base_url: str = BASE_URL) -> Optional[str]:
    text = _clean_text(value)
    if not text or '@' in text and not text.startswith(('http://', 'https://')):
        return None
    absolute = urljoin(base_url, text)
    parsed = urlparse(absolute)
    if parsed.scheme in {'http', 'https'} and parsed.netloc:
        return absolute
    return None


def _selector_text(soup: BeautifulSoup, selector: str) -> Optional[str]:
    return _text_or_none(soup.select_one(selector))


def _has_chinese(value: Optional[str]) -> bool:
    return bool(value and re.search(r'[\u4e00-\u9fff]', value))


def _fetch_chinese_html(url: str) -> Optional[str]:
    parsed = urlparse(url or '')
    if parsed.netloc.lower() != 'nadc.china-vo.org':
        return None
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.pop('lang', None)
    query['language'] = 'zh'
    zh_url = urlunparse(parsed._replace(query=urlencode(query)))
    try:
        response = requests.get(zh_url, headers=FETCH_HEADERS, timeout=15)
        response.raise_for_status()
        response.encoding = response.encoding or 'utf-8'
        return response.text
    except Exception:
        return None


def _plain_lines(content: str) -> list[str]:
    return [line for line in (_clean_text(item) for item in re.split(r'[\r\n]+', content or '')) if line]


def _extract_plain_title(content: str) -> Optional[str]:
    for line in _plain_lines(content):
        if line in {'| NADC', 'NADC', '登录', '注册', 'English'}:
            continue
        if line.startswith(('http://', 'https://')):
            continue
        return line
    return None


def _extract_plain_label_value(content: str, labels: Iterable[str]) -> Optional[str]:
    normalized_labels = {label.strip().rstrip(':：') for label in labels}
    lines = _plain_lines(content)
    for index, line in enumerate(lines):
        normalized = line.rstrip(':：')
        for label in normalized_labels:
            prefix_match = re.match(rf'^{re.escape(label)}\s*[:：]\s*(.+)$', line, re.IGNORECASE)
            if prefix_match:
                return prefix_match.group(1)
        if normalized not in normalized_labels:
            continue
        for value in lines[index + 1:]:
            if value in {'♦', '· 数据访问 ·'}:
                continue
            return value
    return None


def _extract_paper_info_value(soup: BeautifulSoup, label: str) -> Optional[str]:
    normalized_label = label.strip().lower().rstrip(':：')
    for label_node in soup.select('.paperinfo-small-secName'):
        text = (_text_or_none(label_node) or '').strip().lower().rstrip(':：')
        if text != normalized_label:
            continue
        value_node = label_node.find_next_sibling(class_='paperinfo-small-secInfo')
        value = _text_or_none(value_node)
        if value:
            return value
    return None


def _extract_paper_files(soup: BeautifulSoup) -> tuple[list[str], list[str], Optional[str]]:
    file_descriptions: list[str] = []
    download_urls: list[str] = []
    formats: list[str] = []
    for holder in soup.select('#pd-files'):
        filename = _text_or_none(holder.select_one('.paperinfo-files-filename'))
        filesize = _text_or_none(holder.select_one('.paperinfo-files-filesize'))
        if filename or filesize:
            file_descriptions.append(' '.join(item for item in (filename, filesize) if item))
        anchor = holder.select_one('a[href]')
        href = _valid_http_url(anchor.get('href')) if anchor else None
        if href:
            download_urls.append(href)
        if filename and '.' in filename:
            suffix = filename.rsplit('.', 1)[-1].strip().lower()
            if suffix:
                formats.append(suffix)
    return _unique_list(file_descriptions), _unique_list(download_urls), '；'.join(_unique_list(formats)) or None


def _split_authors(value: Optional[Any]) -> list[str]:
    text = _clean_text(value)
    if not text:
        return []
    return _unique_list(re.split(r'\s*;\s*|\s*,\s*|、', text))


def _strip_updated_prefix(value: Optional[str]) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    text = re.sub(r'^发布时间[:：]\s*', '', text)
    return _clean_text(text)


def _extract_access_links(soup: BeautifulSoup) -> list[Dict[str, str]]:
    links: list[Dict[str, str]] = []
    for anchor in soup.select('.dataset-attribute-website a[href]'):
        href = _valid_http_url(anchor.get('href'))
        label = _text_or_none(anchor)
        if href and label:
            links.append({'label': label, 'url': href})
    return links


def _extract_license_links(soup: BeautifulSoup) -> list[Dict[str, str]]:
    links: list[Dict[str, str]] = []
    for anchor in soup.select('#data_usage_card a[href]'):
        href = _valid_http_url(anchor.get('href'))
        label = _text_or_none(anchor)
        if href and label:
            links.append({'label': label, 'url': href})
    return links


def _extract_tags(soup: BeautifulSoup) -> Dict[str, list[str]]:
    tags: Dict[str, list[str]] = {}
    for label_node in soup.select('#tags .dataset-tag-name'):
        label = _text_or_none(label_node)
        holder = label_node.find_parent('div')
        value_holder = holder.find_next_sibling('div') if holder else None
        values = [_text_or_none(node) for node in value_holder.select('.dataset-tagBlock')] if value_holder else []
        values = _unique_list(values)
        if label and values:
            tags[label] = values
    return tags


def _alternative_identifiers(doi: Optional[str]) -> Optional[list[Dict[str, str]]]:
    if not doi:
        return None
    return [{'type': 'DOI', 'identifier': doi}]


def _related_identifiers(ivo: Optional[str]) -> Optional[list[Dict[str, Any]]]:
    return None


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').strip().lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()
    return bool(
        'nadc.china-vo.org/res/r' in normalized_url
        or (
            '国家天文科学数据中心' in combined
            and 'dataset-headline-title' in combined
            and 'dataset-dataintro-name' in combined
        )
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[MetadataDict]:
    if not content:
        return None

    soup = BeautifulSoup(content, 'html.parser')
    full_text = soup.get_text('\n', strip=True)
    if not _has_chinese(_selector_text(soup, '#title') or _extract_plain_title(full_text)):
        chinese_html = _fetch_chinese_html(url)
        if chinese_html:
            chinese_soup = BeautifulSoup(chinese_html, 'html.parser')
            chinese_text = chinese_soup.get_text('\n', strip=True)
            if _has_chinese(_selector_text(chinese_soup, '#title') or _extract_plain_title(chinese_text)):
                soup = chinese_soup
                full_text = chinese_text
    paper_layout = bool(soup.select_one('#pd-title'))
    title_zh = _first_non_empty(
        _selector_text(soup, '#title'),
        _selector_text(soup, '#pd-title'),
        _extract_plain_title(full_text),
        title,
    )
    if not title_zh:
        return None

    title_en = _first_non_empty(
        _selector_text(soup, '#title_en'),
        _extract_plain_label_value(full_text, ['英文名称']),
        _selector_text(soup, '#pd-title') if paper_layout else None,
    )
    publish_date = _first_non_empty(
        _strip_updated_prefix(_selector_text(soup, '#updated')),
        _strip_updated_prefix(_extract_plain_label_value(full_text, ['发布时间'])),
        _extract_paper_info_value(soup, 'Publication Date') if paper_layout else None,
    )
    description = _first_non_empty(_selector_text(soup, '#description'), _selector_text(soup, '#pd-description'))
    if not description and publish_date:
        lines = _plain_lines(full_text)
        for index, line in enumerate(lines):
            if line == f'发布时间：{publish_date}' or line == f'发布时间:{publish_date}':
                description = lines[index + 1] if index + 1 < len(lines) else None
                break
    keywords = _split_terms(_first_non_empty(_selector_text(soup, '#keywords'), _extract_plain_label_value(full_text, ['关键字', '关键词'])))
    data_amount = _first_non_empty(_selector_text(soup, '#data_amount'), _extract_plain_label_value(full_text, ['数据量']))
    sharing_method = _first_non_empty(_selector_text(soup, '#sharemode'), _extract_plain_label_value(full_text, ['共享途径']))
    sharing_scope = _first_non_empty(_selector_text(soup, '#sharescope'), _extract_plain_label_value(full_text, ['共享范围']))
    procedure = _first_non_empty(_selector_text(soup, '#procedure'), _extract_plain_label_value(full_text, ['申请流程']))
    doi = _extract_doi(_selector_text(soup, '#doi'), _extract_plain_label_value(full_text, ['DOI']), _extract_paper_info_value(soup, 'DOI'), full_text)
    cstr_identifier = _extract_cstr(_selector_text(soup, '#cstr'), _extract_plain_label_value(full_text, ['CSTR']), _extract_paper_info_value(soup, 'CSTR'), full_text)
    ivo_identifier = _first_non_empty(
        _selector_text(soup, '#ivo'),
        _extract_plain_label_value(full_text, ['VO标识符', 'VO Identifier']),
        _extract_paper_info_value(soup, 'VO Identifier'),
    )
    author_name = _first_non_empty(
        _selector_text(soup, '#author_name'),
        _extract_plain_label_value(full_text, ['作者']),
        _selector_text(soup, '#pd-authors'),
    )
    author_email = _first_non_empty(_selector_text(soup, '#author_email'), _extract_plain_label_value(full_text, ['邮件']))
    resource_id = _extract_resource_id(url)
    page_url = _valid_http_url(url) or (urljoin(BASE_URL, f'/res/{resource_id}/') if resource_id else None)
    access_links = _extract_access_links(soup)
    paper_files, paper_download_urls, paper_data_format = _extract_paper_files(soup)
    license_links = _extract_license_links(soup)
    tags = _extract_tags(soup)

    access_urls = _unique_list([*(link['url'] for link in access_links), *paper_download_urls])
    all_urls = _unique_list([page_url])
    license_names = _unique_list(link['label'] for link in license_links)
    license_urls = _unique_list(link['url'] for link in license_links)
    subjects = _unique_list([
        *(tags.get('子学科') or []),
        *(tags.get('观测波段') or []),
        *(tags.get('观测装置和计划') or []),
    ])
    file_content = '；'.join(_unique_list([
        title_en,
        *paper_files,
        *(tags.get('观测波段') or []),
        *(tags.get('观测装置和计划') or []),
        *(tags.get('数据类型') or []),
        *(tags.get('生产年代') or []),
        *(tags.get('用户对象') or []),
    ])) or None
    usage_parts = {
        '共享途径': sharing_method,
        '共享范围': sharing_scope,
        '申请流程': procedure,
    }
    usage_description = '；'.join(f'{key}: {value}' for key, value in usage_parts.items() if value) or None
    license_text = '；'.join(license_names) or None
    if not data_amount and paper_files:
        sizes = []
        for item in paper_files:
            match = re.search(r'(\d+(?:\.\d+)?\s*(?:KB|MB|GB|TB))\b', item, flags=re.IGNORECASE)
            if match:
                sizes.append(match.group(1))
        data_amount = '；'.join(_unique_list(sizes)) or None
    download_url = '；'.join(access_urls) or None

    creator_name = author_name or PUBLISHER_ZH
    author_names = _split_authors(author_name)
    if paper_layout and author_names:
        creators = [
            {
                'type': 'Person',
                'person': {
                    'names': [{'lang': 'en', 'name': name}],
                    'emails': None,
                    'identifiers': None,
                    'affiliations': None,
                },
            }
            for name in author_names
        ]
    else:
        creators = [{
            'type': 'Organize',
            'affiliation': {
                'names': [{'lang': 'zh', 'name': creator_name}],
                'identifiers': None,
            },
        }]
    titles = [{'lang': 'zh', 'name': title_zh}]
    if title_en and title_en != title_zh:
        titles.append({'lang': 'en', 'name': title_en})
    cstr_display = f'CSTR:{cstr_identifier}' if cstr_identifier else None

    core_zh: Dict[str, Any] = {
        'titles': titles,
        'identifier': cstr_display,
        'creators': creators,
        'publisher': {
            'names': [
                {'lang': 'zh', 'name': PUBLISHER_ZH},
                {'lang': 'en', 'name': PUBLISHER_EN},
            ],
            'identifiers': None,
        },
        'publish_date': publish_date,
        'descriptions': [{'lang': 'zh', 'description': description}] if description else None,
        'keywords': [{'lang': 'zh', 'keyword': keywords}] if keywords else None,
        'subjects': [{'standard_gbt': subjects or None, 'standard_oecd': None}] if subjects else None,
        'language': 'zh; en' if title_en else 'zh',
        'contributors': [{
            'type': 'Organize',
            'contribution_type': 'HostingInstitution',
            'affiliation': {
                'names': [
                    {'lang': 'zh', 'name': PUBLISHER_ZH},
                    {'lang': 'en', 'name': PUBLISHER_EN},
                ],
                'identifiers': None,
            },
        }],
        'alternative_identifiers': _alternative_identifiers(doi),
        'related_identifiers': _related_identifiers(ivo_identifier),
        'rights': [{
            'license_type': None,
            'license': license_text,
            'type': sharing_scope,
            'description': usage_description,
            'cert_num': None,
        }] if (license_text or usage_description or sharing_scope) else None,
        'funders': None,
        'version': None,
        'urls': all_urls or None,
        'resource_type': 'Dataset',
    }

    dataset_author = {
        '作者姓名': author_names or [creator_name],
        '工作单位': None if paper_layout else creator_name,
        '电子邮箱': author_email,
        '工作贡献': '数据集建设、发布与服务',
        '作者简介': None,
    }
    domain_identifier = f'CSTR:{cstr_identifier}' if cstr_identifier else (f'DOI: {doi}' if doi else None)
    citation_format = _selector_text(soup, '#citation-plain') or (f'DOI: {doi}' if doi else None)

    zh: Dict[str, Any] = {
        '核心元数据': {'metadatas': [core_zh]},
        '数据集基本信息': {
            '标识符': domain_identifier,
            '标题': titles,
            '摘要': description,
            '关键词': [{'lang': 'zh', 'keyword': keywords}] if keywords else None,
            '范围': {
                '时间范围': None,
                '空间范围': None,
            },
            '语种': '中文；英文' if title_en else '中文',
            '文件内容': file_content,
            '基金项目': None,
            '数据量': data_amount,
            '数据格式': paper_data_format or '；'.join(tags.get('数据类型') or []) or None,
            '数据集作者': dataset_author,
        },
        '数据集出版信息': {
            '发布日期': publish_date,
            '出版期刊': None,
            '版本信息': None,
        },
        '数据集服务信息': {
            '数据集引用格式': citation_format,
            '数据集共享许可协议': license_text,
            '数据集使用声明': usage_description,
            '数据集下载地址': download_url,
            '数据论文访问地址': page_url,
        },
    }
    if license_urls:
        zh['数据集服务信息']['数据集共享许可协议'] = '；'.join(_unique_list([license_text, *license_urls]))

    core_en: Dict[str, Any] = {
        'titles': [{'lang': 'en', 'name': title_en}] if title_en else None,
        'identifier': cstr_display,
        'creators': creators,
        'publisher': {
            'names': [{'lang': 'en', 'name': PUBLISHER_EN}],
            'identifiers': None,
        },
        'publish_date': publish_date,
        'descriptions': None,
        'keywords': None,
        'subjects': None,
        'language': 'zh; en' if title_en else 'zh',
        'contributors': [{
            'type': 'Organize',
            'contribution_type': 'HostingInstitution',
            'affiliation': {
                'names': [{'lang': 'en', 'name': PUBLISHER_EN}],
                'identifiers': None,
            },
        }],
        'alternative_identifiers': _alternative_identifiers(doi),
        'related_identifiers': _related_identifiers(ivo_identifier),
        'rights': [{
            'license_type': None,
            'license': license_text,
            'type': sharing_scope,
            'description': usage_description,
            'cert_num': None,
        }] if (license_text or usage_description or sharing_scope) else None,
        'funders': None,
        'version': None,
        'urls': all_urls or None,
        'resource_type': 'Dataset',
    }

    en: Dict[str, Any] = {
        'Core Metadata': {'metadatas': [core_en]},
        'Dataset Basic Information': {
            'Identifier': domain_identifier,
            'Title': [{'lang': 'en', 'name': title_en}] if title_en else None,
            'Abstract': None,
            'Keywords': None,
            'Coverage': {
                'Time Range': None,
                'Spatial Range': None,
            },
            'Language': 'Chinese; English' if title_en else 'Chinese',
            'File Content': file_content,
            'Project/Funder': None,
            'Data Size': data_amount,
            'Data Format': paper_data_format or '；'.join(tags.get('数据类型') or []) or None,
            'Dataset Authors': {
                'Author Name': author_names or [creator_name],
                'Affiliation': None if paper_layout else creator_name,
                'Email': author_email,
                'Contribution': 'Dataset construction, publication, and service',
                'Biography': None,
            },
        },
        'Dataset Publication Information': {
            'Publication Date': publish_date,
            'Journal': None,
            'Version Information': None,
        },
        'Dataset Service Information': {
            'Dataset Citation Format': citation_format,
            'Dataset License': license_text,
            'Dataset Usage Statement': usage_description,
            'Dataset Download URL': download_url,
            'Dataset Paper URL': page_url,
        },
    }

    return {'zh': zh, 'en': en}
