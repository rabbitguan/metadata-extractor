from __future__ import annotations

import re
from html import unescape
from typing import Any, Dict, Iterable, Optional
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from bs4 import BeautifulSoup

from .base import MetadataDict


RULE_NAME = 'NEDC Metadata Detail'

PUBLISHER_ZH = '国家地震科学数据中心'
PUBLISHER_EN = 'National Earthquake Data Center'


def _clean_text(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value))
    text = re.sub(r'\s+', ' ', text).strip()
    if text in {'-', '—', '无', '暂无', 'null', 'None'}:
        return None
    return text or None


def _has_cjk(value: Optional[str]) -> bool:
    return bool(re.search(r'[\u4e00-\u9fff]', str(value or '')))


def _english_text(value: Optional[Any]) -> Optional[str]:
    cleaned = _clean_text(value)
    if not cleaned or _has_cjk(cleaned):
        return None
    return cleaned


def _first_non_empty(*values: Optional[Any]) -> Optional[str]:
    for value in values:
        cleaned = _clean_text(value)
        if cleaned:
            return cleaned
    return None


def _split_terms(value: Optional[Any]) -> list[str]:
    text = _clean_text(value)
    if not text:
        return []
    parts = re.split(r'[;；,，、\|\s]+|\s{2,}', text)
    return [item for item in (_clean_text(part) for part in parts) if item]


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


def _identifier_list(*values: Optional[Any]) -> Optional[list[str]]:
    identifiers = _unique_list(value for value in values if _clean_text(value))
    return identifiers or None


def _dedupe_repeated_text(value: Optional[str]) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    parts = text.split()
    if len(parts) == 2 and parts[0] == parts[1]:
        return parts[0]
    if len(text) % 2 == 1 and text[len(text) // 2] == ' ':
        left = text[:len(text) // 2]
        right = text[len(text) // 2 + 1:]
        if left == right:
            return left
    return text


def _parse_query(url: str) -> Dict[str, str]:
    if not url:
        return {}
    query = parse_qs(urlparse(url).query)
    result: Dict[str, str] = {}
    for key, values in query.items():
        for value in values:
            cleaned = _clean_text(unquote(value))
            if cleaned:
                result[key] = cleaned
                break
    return result


def _label_text(node) -> Optional[str]:
    text = _clean_text(node.get_text(' ', strip=True)) if node else None
    if not text:
        return None
    text = re.sub(r'[\s\xa0]+', '', text)
    return text.rstrip('：:')


def _extract_label_map(soup: BeautifulSoup) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for row in soup.select('.data_div'):
        label_node = row.select_one('.frist, .frist_a')
        value_node = row.select_one('.second')
        label = _label_text(label_node)
        value = _clean_text(value_node.get_text(' ', strip=True)) if value_node else None
        if label and value:
            values[label] = value
    return values


def _section_text(soup: BeautifulSoup, heading_text: str) -> Optional[str]:
    for section in soup.select('.floatWrap'):
        heading = _clean_text(section.find('h4').get_text(' ', strip=True)) if section.find('h4') else None
        if heading != heading_text:
            continue
        block = section.select_one('.break')
        if block:
            fragment = BeautifulSoup(str(block), 'html.parser')
            for table in fragment.find_all('table'):
                table.decompose()
            paragraphs = [
                _dedupe_repeated_text(node.get_text(' ', strip=True))
                for node in fragment.find_all('p')
                if not node.find('p') and not node.find_parent('table')
            ]
            paragraphs = _unique_list(item for item in paragraphs if item)
            if paragraphs:
                return '\n'.join(paragraphs)
        paragraphs = [
            _dedupe_repeated_text(node.get_text(' ', strip=True))
            for node in section.select('.break p')
        ]
        paragraphs = _unique_list(item for item in paragraphs if item)
        if paragraphs:
            return '\n'.join(paragraphs)
        block = section.select_one('.break')
        return _dedupe_repeated_text(block.get_text(' ', strip=True)) if block else None
    return None


def _extract_title(soup: BeautifulSoup, fallback_title: str, resource_id: Optional[str]) -> Optional[str]:
    for selector in ('.inner-content h2', 'h2[data-bind*="title"]', 'h1'):
        node = soup.select_one(selector)
        title = _clean_text(node.get_text(' ', strip=True)) if node else None
        if title and title != PUBLISHER_ZH:
            return title
    return _clean_text(fallback_title) if _clean_text(fallback_title) != PUBLISHER_ZH else resource_id


def _extract_doi(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    match = re.search(r'\bDOI\s*[:：]\s*(10\.\S+)', value, flags=re.IGNORECASE)
    if not match:
        match = re.search(r'\b(10\.\d{4,9}/\S+)', value, flags=re.IGNORECASE)
    return match.group(1).rstrip('.,;。；') if match else None


def _extract_cstr(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    match = re.search(r'\bCSTR\s*[:：]\s*([A-Z0-9]{5}\.\d{2}\.[-._;()/:A-Z0-9]+)', value, flags=re.IGNORECASE)
    if match:
        return f'CSTR:{match.group(1).rstrip(".,;。；")}'
    match = re.search(r'\b[A-Z0-9]{5}\.\d{2}\.[-._;()/:A-Z0-9]+\b', value, flags=re.IGNORECASE)
    return match.group(0).rstrip('.,;。；') if match else None


def _extract_citation_format(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    citations: Dict[str, Optional[str]] = {'zh': None, 'en': None}
    for section in soup.select('.floatWrap'):
        heading = _clean_text(section.find('h4').get_text(' ', strip=True)) if section.find('h4') else None
        if heading != '数据引用方式':
            continue

        norm_heading = section.find('h4', string=re.compile(r'一、\s*引用规范'))
        if not norm_heading:
            citations['zh'] = _section_text(soup, '数据引用方式')
            return citations

        for node in norm_heading.find_all_next(['p', 'h4']):
            if node.name == 'h4':
                break
            text = _clean_text(node.get_text(' ', strip=True))
            if not text:
                continue
            if text.startswith('中文：'):
                citations['zh'] = _clean_text(text.removeprefix('中文：'))
            elif text.startswith('英文：'):
                citations['en'] = _clean_text(text.removeprefix('英文：'))
            if citations['zh'] and citations['en']:
                break

        return citations
    return citations


def _localized_descriptions(zh: Optional[str], en: Optional[str]) -> Optional[list[Dict[str, str]]]:
    values: list[Dict[str, str]] = []
    if zh:
        values.append({'lang': 'zh', 'description': zh})
    if en:
        values.append({'lang': 'en', 'description': en})
    return values or None


def _extract_data_factors(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    factors: Dict[str, Optional[str]] = {
        '最新更新时间': None,
        '数据量': None,
        '数据访问量': None,
        '数据共享方式': None,
    }

    for item in soup.select('#data-factors li'):
        text = _clean_text(item.get_text(' ', strip=True))
        span_text = _clean_text(item.find('span').get_text(' ', strip=True)) if item.find('span') else None
        if not text:
            continue
        if '最新更新时间' in text:
            factors['最新更新时间'] = span_text
        elif '数据量' in text:
            factors['数据量'] = span_text
        elif '数据访问量' in text:
            factors['数据访问量'] = _clean_text(re.sub(r'^数据访问量', '', span_text or text))
        elif '数据共享方式' in text:
            factors['数据共享方式'] = _clean_text(re.sub(r'^数据共享方式', '', text))

    return factors


def _extract_download_url(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    for anchor in soup.find_all('a', href=True):
        text = _clean_text(anchor.get_text(' ', strip=True))
        href = _clean_text(anchor.get('href'))
        if text == '在线下载' and href:
            return urljoin(base_url, href)
    for anchor in soup.select('.floatWrap a[href]'):
        href = _clean_text(anchor.get('href'))
        if href and '/datafile/' in href:
            return urljoin(base_url, href)
    return None


def _extract_image_url(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    for image in soup.select('.inner-content img[src*="/uploadfile/image/"]'):
        src = _clean_text(image.get('src'))
        if src:
            return urljoin(base_url, src)
    for image in soup.select('.inner-content img[src]'):
        src = _clean_text(image.get('src'))
        if src and 'website/img/' not in src:
            return urljoin(base_url, src)
    return None


def _extract_subject(value: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    text = _clean_text(value)
    if not text:
        return None, None
    match = re.search(r'(.+?)\s*\(\s*([A-Za-z0-9._-]+)\s*\)', text)
    if match:
        return _clean_text(match.group(1)), _clean_text(match.group(2))
    return text, None


def _format_from_url(url: Optional[str]) -> Optional[str]:
    text = _clean_text(url)
    if not text:
        return None
    match = re.search(r'\.([A-Za-z0-9]+)(?:[?#]|$)', text)
    return match.group(1).lower() if match else None


def _payload_from_html(content: str, url: str, title: str) -> Optional[MetadataDict]:
    soup = BeautifulSoup(content or '', 'html.parser')
    labels = _extract_label_map(soup)
    if not labels:
        return None

    query = _parse_query(url)
    resource_id = query.get('dt')
    factors = _extract_data_factors(soup)

    title_zh = _first_non_empty(_extract_title(soup, title, resource_id), labels.get('数据名称'), resource_id, '未提取到标题')
    raw_identifier = labels.get('数据标识')
    doi_identifier = _extract_doi(raw_identifier)
    cstr_identifier = _extract_cstr(raw_identifier)
    subject, subject_code = _extract_subject(labels.get('所属分类'))
    spatial_range = labels.get('空间范围')
    time_range = labels.get('时间范围')
    contact = labels.get('联系人')
    phone = labels.get('电话')
    email = labels.get('邮箱')
    organization = labels.get('单位')
    data_producer = _section_text(soup, '数据生产者')
    data_source = _section_text(soup, '数据来源')
    description = _first_non_empty(_section_text(soup, '数据摘要'), _section_text(soup, '数据描述'))
    citations = _extract_citation_format(soup)
    localized_citations = _localized_descriptions(citations.get('zh'), citations.get('en'))
    data_size = factors.get('数据量')
    update_time = factors.get('最新更新时间')
    access_count = factors.get('数据访问量')
    sharing_mode = factors.get('数据共享方式')
    download_url = _extract_download_url(soup, url)
    image_url = _extract_image_url(soup, url)
    data_format = _format_from_url(download_url)
    creator = _first_non_empty(data_producer, contact, data_source, organization, PUBLISHER_ZH)
    publisher_zh = _first_non_empty(data_source, organization, PUBLISHER_ZH)
    alternative_identifiers = _unique_list([item for item in (resource_id,) if item and item != doi_identifier]) or None
    primary_identifier = doi_identifier or cstr_identifier or resource_id
    domain_identifiers = _identifier_list(doi_identifier, cstr_identifier) or _identifier_list(primary_identifier)

    keywords = _unique_list([
        *(re.split(r'[、；;，,\s]+', title_zh or '') if title_zh else []),
        subject,
    ])
    keywords = [item for item in keywords if len(item) > 1]
    resource_url = url or None

    zh: Dict[str, Any] = {
        '资源类型判定': '数据集',
        '领域判定': '数据集元数据',
        '标识符': primary_identifier,
        'CSTR标识符': cstr_identifier,
        '资源名称': title_zh,
        '标题': title_zh,
        '创建者': [creator] if creator else None,
        '发布机构': publisher_zh,
        '发布日期': update_time,
        '描述': description,
        '关键词': keywords or None,
        '学科分类': subject,
        '语言': '中文',
        '贡献者': [contact] if contact and contact != creator else None,
        '替代标识符': alternative_identifiers,
        '关联标识符': None,
        '权限': sharing_mode,
        '资助者': None,
        '版本': None,
        '资源链接': resource_url,
        '资源类型': '数据集',
        '数据集基本信息': {
            '标识符': domain_identifiers or primary_identifier,
            '标题': title_zh,
            '摘要': description,
            '关键词': keywords or None,
            '范围': {
                '时间范围': time_range,
                '空间范围': spatial_range,
            },
            '语种': '中文',
            '文件内容': None,
            '基金项目': None,
            '数据量': data_size,
            '数据格式': data_format,
            '数据集作者': {
                '作者姓名': [creator] if creator else None,
                '工作单位': organization or publisher_zh,
                '电子邮箱': email,
                '工作贡献': None,
                '作者简介': None,
            },
        },
        '数据集出版信息': {
            '发布日期': update_time,
            '出版期刊': None,
            '版本信息': None,
        },
        '数据集服务信息': {
            '数据集引用格式': localized_citations,
            '数据集共享许可协议': sharing_mode,
            '数据集使用声明': None,
            '数据集下载地址': download_url,
            '数据集访问地址': resource_url,
        },
        '扩展信息': {
            '所属分类代码': subject_code,
            '空间范围': spatial_range,
            '时间范围': time_range,
            '联系人': contact,
            '联系电话': phone,
            '联系邮箱': email,
            '联系单位': organization,
            '数据生产者': data_producer,
            '数据来源': data_source,
            '数据访问量': access_count,
            '预览图': image_url,
        },
    }

    english_keywords = [_english_text(item) for item in keywords]
    english_keywords = [item for item in english_keywords if item]
    if not english_keywords:
        english_keywords = keywords
    en: Dict[str, Any] = {
        'Resource Type Classification': 'Dataset',
        'Domain Classification': 'Dataset Metadata',
        'Identifier': primary_identifier,
        'CSTR Identifier': cstr_identifier,
        'Resource Name': None,
        'Title': None,
        'Creators': None,
        'Publisher': PUBLISHER_EN if publisher_zh == PUBLISHER_ZH else None,
        'Publication Date': update_time,
        'Description': None,
        'Keywords': english_keywords or None,
        'Discipline Classification': None,
        'Language': 'Chinese',
        'Contributors': None,
        'Alternative Identifiers': alternative_identifiers,
        'Related Identifiers': None,
        'Rights': sharing_mode,
        'Funders': None,
        'Version': None,
        'Resource URL': resource_url,
        'ResourceType': 'Dataset',
        'Dataset Basic Information': {
            'Identifier': domain_identifiers or primary_identifier,
            'Title': None,
            'Abstract': None,
            'Keywords': english_keywords or None,
            'Coverage': {
                'Time Range': time_range,
                'Spatial Range': spatial_range,
            },
            'Language': 'Chinese',
            'File Content': None,
            'Project/Funder': None,
            'Data Size': data_size,
            'Data Format': data_format,
            'Dataset Authors': {
                'Author Name': None,
                'Affiliation': PUBLISHER_EN if publisher_zh == PUBLISHER_ZH else None,
                'Email': email,
                'Contribution': None,
                'Biography': None,
            },
        },
        'Dataset Publication Information': {
            'Publication Date': update_time,
            'Journal': None,
            'Version Information': None,
        },
        'Dataset Service Information': {
            'Dataset Citation Format': citations.get('en'),
            'Dataset License': sharing_mode,
            'Dataset Usage Statement': None,
            'Dataset Download URL': download_url,
            'Dataset Access URL': resource_url,
        },
        'Extension Info': {
            'Chinese Title': title_zh,
            'Subject Category': None,
            'Subject Code': subject_code,
            'Spatial Coverage': spatial_range,
            'Temporal Coverage': time_range,
            'Contact': None,
            'Contact Phone': phone,
            'Contact Email': email,
            'Contact Organization': None,
            'Page Views': access_count,
            'Preview Image': image_url,
        },
    }

    return {'zh': zh, 'en': en}


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').strip().lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()
    return bool(
        'data.earthquake.cn/datashare/report.shtml' in normalized_url
        or '国家地震科学数据中心' in combined
        and '数据基本信息' in combined
        and '数据名称' in combined
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[MetadataDict]:
    if not content:
        return None
    return _payload_from_html(content, url, title)
