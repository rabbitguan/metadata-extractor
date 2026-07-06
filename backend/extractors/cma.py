from __future__ import annotations

import re
from html import unescape
from typing import Any, Dict, Iterable, Optional
from urllib.parse import unquote, urljoin, urlparse

from bs4 import BeautifulSoup

from .base import MetadataDict


RULE_NAME = 'CMA Data Detail'

PUBLISHER_ZH = '国家气象信息中心'
PUBLISHER_EN = 'National Meteorological Information Center'


def _clean_text(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value)).replace('\xa0', ' ')
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
    parts = re.split(r'[;；,，、\|\s]+', text)
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


def _extract_data_code(url: str) -> Optional[str]:
    match = re.search(r'/dataCode/([^/?#]+)\.html', url or '', flags=re.IGNORECASE)
    if match:
        return _clean_text(unquote(match.group(1)))
    path = urlparse(url or '').path
    match = re.search(r'/dataCode/([^/?#]+)', path, flags=re.IGNORECASE)
    return _clean_text(unquote(match.group(1))) if match else None


def _extract_label_map(soup: BeautifulSoup) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for row in soup.select('.product-data-right ul.clearfix'):
        label_node = row.select_one('li.title')
        value_nodes = row.select('li.words, li.wordsfirst')
        label = _clean_text(label_node.get_text(' ', strip=True)) if label_node else None
        value = _clean_text(' '.join(node.get_text(' ', strip=True) for node in value_nodes))
        if label and value:
            values[label.rstrip('：:')] = value
    return values


def _extract_title(soup: BeautifulSoup, labels: Dict[str, str], fallback_title: str) -> Optional[str]:
    heading = _clean_text(soup.select_one('.search-term .serCeTi').get_text(' ', strip=True)) if soup.select_one('.search-term .serCeTi') else None
    if heading:
        heading = re.sub(r'^[◎\s]+', '', heading).strip()
    page_title = _clean_text(soup.title.string if soup.title and soup.title.string else None)
    if page_title == '国家气象信息中心-中国气象数据网':
        page_title = None
    return _first_non_empty(labels.get('数据名称'), heading, fallback_title, page_title)


def _extract_description(soup: BeautifulSoup) -> Optional[str]:
    node = soup.select_one('.element-data-brief p.font')
    return _clean_text(node.get_text(' ', strip=True)) if node else None


def _format_time_range(start: Optional[str], end: Optional[str]) -> Optional[str]:
    start_text = _clean_text(start)
    end_text = _clean_text(end)
    if start_text and end_text:
        return f'{start_text} - {end_text}'
    return start_text or end_text


def _extract_service_url(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    node = soup.select_one('input.searchData[url]')
    href = _clean_text(node.get('url')) if node else None
    return urljoin(base_url, href) if href else None


def _extract_related_documents(soup: BeautifulSoup, base_url: str) -> list[Dict[str, str]]:
    documents: list[Dict[str, str]] = []
    for anchor in soup.select('a[href]'):
        href = _clean_text(anchor.get('href'))
        text = _clean_text(anchor.get_text(' ', strip=True))
        if not href or not text:
            continue
        if '/article/showPDFFile.html' not in href and not href.lower().endswith('.pdf'):
            continue
        documents.append({'title': text, 'url': urljoin(base_url, href)})
    return documents


def _extract_escience_url(soup: BeautifulSoup) -> Optional[str]:
    for anchor in soup.select('a[href*="escience.org.cn/metadata/detail"]'):
        href = _clean_text(anchor.get('href'))
        if href:
            return href
    return None


def _payload_from_html(content: str, url: str, title: str) -> Optional[MetadataDict]:
    soup = BeautifulSoup(content or '', 'html.parser')
    labels = _extract_label_map(soup)
    if not labels:
        return None

    data_code = _extract_data_code(url)
    title_zh = _first_non_empty(_extract_title(soup, labels, title), data_code, '未提取到标题')
    description = _extract_description(soup)
    keywords = _unique_list(_split_terms(labels.get('关键字')))
    spatial_range = labels.get('空间范围')
    time_range = _format_time_range(labels.get('数据起始时间'), labels.get('数据终止时间'))
    registration_number = labels.get('数据资源登记编号')
    identifier = None
    sharing_level = labels.get('共享级别')
    update_frequency = labels.get('更新频率')
    production_time = labels.get('制作时间')
    quality_description = labels.get('数据质量描述')
    data_source = labels.get('数据源')
    service_url = _extract_service_url(soup, url)
    escience_url = _extract_escience_url(soup)
    related_documents = _extract_related_documents(soup, url)
    resource_url = url or None
    alternative_identifiers = None

    zh: Dict[str, Any] = {
        '资源类型判定': '数据集',
        '领域判定': '数据集元数据',
        '标识符': identifier,
        'CSTR标识符': None,
        '资源名称': title_zh,
        '标题': title_zh,
        '创建者': [PUBLISHER_ZH],
        '发布机构': PUBLISHER_ZH,
        '发布日期': production_time,
        '描述': description,
        '关键词': keywords or None,
        '学科分类': '气象学',
        '语言': '中文',
        '贡献者': None,
        '替代标识符': alternative_identifiers,
        '关联标识符': None,
        '权限': sharing_level,
        '资助者': None,
        '版本': None,
        '资源链接': resource_url,
        '资源类型': '数据集',
        '数据集基本信息': {
            '标识符': identifier,
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
            '数据量': None,
            '数据格式': None,
            '数据集作者': {
                '作者姓名': [PUBLISHER_ZH],
                '工作单位': PUBLISHER_ZH,
                '电子邮箱': 'datacenter@cma.gov.cn',
                '工作贡献': None,
                '作者简介': None,
            },
        },
        '数据集出版信息': {
            '发布日期': production_time,
            '出版期刊': None,
            '版本信息': None,
        },
        '数据集服务信息': {
            '数据集引用格式': None,
            '数据集共享许可协议': sharing_level,
            '数据集使用声明': quality_description,
            '数据集下载地址': service_url,
            '数据集访问地址': resource_url,
        },
        '扩展信息': {
            '数据代码': data_code,
            '数据资源登记编号': registration_number,
            '制作时间': production_time,
            '更新频率': update_frequency,
            '数据源': data_source,
            '数据质量描述': quality_description,
            '服务入口': service_url,
            '中国科技资源共享网注册数据集': escience_url,
            '相关文档': related_documents or None,
        },
    }

    english_keywords = [_english_text(item) for item in keywords]
    english_keywords = [item for item in english_keywords if item]
    en: Dict[str, Any] = {
        'Resource Type Classification': 'Dataset',
        'Domain Classification': 'Dataset Metadata',
        'Identifier': identifier,
        'CSTR Identifier': None,
        'Resource Name': None,
        'Title': None,
        'Creators': None,
        'Publisher': PUBLISHER_EN,
        'Publication Date': production_time,
        'Description': None,
        'Keywords': english_keywords or None,
        'Discipline Classification': 'Meteorology',
        'Language': 'Chinese',
        'Contributors': None,
        'Alternative Identifiers': alternative_identifiers,
        'Related Identifiers': None,
        'Rights': sharing_level,
        'Funders': None,
        'Version': None,
        'Resource URL': resource_url,
        'ResourceType': 'Dataset',
        'Dataset Basic Information': {
            'Identifier': identifier,
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
            'Data Size': None,
            'Data Format': None,
            'Dataset Authors': {
                'Author Name': None,
                'Affiliation': PUBLISHER_EN,
                'Email': 'datacenter@cma.gov.cn',
                'Contribution': None,
                'Biography': None,
            },
        },
        'Dataset Publication Information': {
            'Publication Date': production_time,
            'Journal': None,
            'Version Information': None,
        },
        'Dataset Service Information': {
            'Dataset Citation Format': None,
            'Dataset License': sharing_level,
            'Dataset Usage Statement': None,
            'Dataset Download URL': service_url,
            'Dataset Access URL': resource_url,
        },
        'Extension Info': {
            'Chinese Title': title_zh,
            'Data Code': data_code,
            'Registration Number': registration_number,
            'Production Time': production_time,
            'Update Frequency': update_frequency,
            'Data Source': None,
            'Service URL': service_url,
            'Escience Metadata URL': escience_url,
            'Related Documents': related_documents or None,
        },
    }

    return {'zh': zh, 'en': en}


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').strip().lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()
    return bool(
        'data.cma.cn/data/cdcdetail/datacode/' in normalized_url
        or 'data.cma.cn' in normalized_url and '/data/cdcdetail/' in normalized_url
        or '中国气象数据网' in combined and '数据资源登记编号' in combined
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[MetadataDict]:
    if not content:
        return None
    return _payload_from_html(content, url, title)
