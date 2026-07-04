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
        paragraphs = [
            _clean_text(node.get_text(' ', strip=True))
            for node in section.select('.break p')
        ]
        paragraphs = [item for item in paragraphs if item]
        if paragraphs:
            return '\n'.join(paragraphs)
        block = section.select_one('.break')
        return _clean_text(block.get_text(' ', strip=True)) if block else None
    return None


def _extract_citation_format(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    citations: Dict[str, Optional[str]] = {'zh': None, 'en': None}
    for section in soup.select('.floatWrap'):
        heading = _clean_text(section.find('h4').get_text(' ', strip=True)) if section.find('h4') else None
        if heading != '数据引用方式':
            continue

        norm_heading = section.find('h4', string=re.compile(r'一、\s*引用规范'))
        if not norm_heading:
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
    return None


def _extract_image_url(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    for image in soup.select('.inner-content img[src]'):
        src = _clean_text(image.get('src'))
        if src:
            return urljoin(base_url, src)
    return None


def _extract_subject(value: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    text = _clean_text(value)
    if not text:
        return None, None
    match = re.search(r'(.+?)\s*\(([A-Za-z0-9._-]+)\)', text)
    if match:
        return _clean_text(match.group(1)), _clean_text(match.group(2))
    return text, None


def _payload_from_html(content: str, url: str, title: str) -> Optional[MetadataDict]:
    soup = BeautifulSoup(content or '', 'html.parser')
    labels = _extract_label_map(soup)
    if not labels:
        return None

    query = _parse_query(url)
    resource_id = query.get('dt')
    factors = _extract_data_factors(soup)

    title_zh = _first_non_empty(labels.get('数据名称'), title, resource_id, '未提取到标题')
    subject, subject_code = _extract_subject(labels.get('所属分类'))
    spatial_range = labels.get('空间范围')
    time_range = labels.get('时间范围')
    contact = labels.get('联系人')
    phone = labels.get('电话')
    email = labels.get('邮箱')
    organization = labels.get('单位')
    description = _section_text(soup, '数据描述')
    citations = _extract_citation_format(soup)
    localized_citations = _localized_descriptions(citations.get('zh'), citations.get('en'))
    data_size = factors.get('数据量')
    update_time = factors.get('最新更新时间')
    access_count = factors.get('数据访问量')
    sharing_mode = factors.get('数据共享方式')
    download_url = _extract_download_url(soup, url)
    image_url = _extract_image_url(soup, url)

    keywords = _unique_list([
        *(re.split(r'[、；;，,\s]+', title_zh or '') if title_zh else []),
        subject,
    ])
    keywords = [item for item in keywords if len(item) > 1]
    publisher_zh = organization or PUBLISHER_ZH
    resource_url = url or None

    zh: Dict[str, Any] = {
        '资源类型判定': '数据集',
        '领域判定': '数据集元数据',
        '标识符': resource_id,
        'CSTR标识符': None,
        '资源名称': title_zh,
        '标题': title_zh,
        '创建者': [publisher_zh] if publisher_zh else None,
        '发布机构': publisher_zh,
        '发布日期': update_time,
        '描述': description,
        '关键词': keywords or None,
        '学科分类': subject,
        '语言': '中文',
        '贡献者': [contact] if contact else None,
        '替代标识符': None,
        '关联标识符': None,
        '权限': sharing_mode,
        '资助者': None,
        '版本': None,
        '资源链接': resource_url,
        '资源类型': '数据集',
        '数据集基本信息': {
            '标识符': resource_id,
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
            '数据格式': None,
            '数据集作者': {
                '作者姓名': [contact] if contact else None,
                '工作单位': publisher_zh,
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
            '数据访问量': access_count,
            '预览图': image_url,
        },
    }

    english_keywords = [_english_text(item) for item in keywords]
    english_keywords = [item for item in english_keywords if item]
    en: Dict[str, Any] = {
        'Resource Type Classification': 'Dataset',
        'Domain Classification': 'Dataset Metadata',
        'Identifier': resource_id,
        'CSTR Identifier': None,
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
        'Alternative Identifiers': None,
        'Related Identifiers': None,
        'Rights': sharing_mode,
        'Funders': None,
        'Version': None,
        'Resource URL': resource_url,
        'ResourceType': 'Dataset',
        'Dataset Basic Information': {
            'Identifier': resource_id,
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
            'Data Format': None,
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
