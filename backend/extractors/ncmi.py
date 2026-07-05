from __future__ import annotations

import re
from html import unescape
from typing import Any, Dict, Iterable, Optional
from urllib.parse import parse_qs, quote, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from .base import MetadataDict


RULE_NAME = 'NCMI Data Detail'

PUBLISHER_ZH = '国家人口健康科学数据中心'
PUBLISHER_EN = 'National Population Health Data Center'
ARCHIVE_ZH = 'PHDA人口健康科学数据仓储'
ARCHIVE_EN = 'Population Health Data Archive of National Population Health Data Center'
DETAIL_URL = 'https://www.ncmi.cn/phda/dataDetails.do'

REQUEST_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/125.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://www.ncmi.cn/',
}


def _clean_text(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value)).replace('\xa0', ' ')
    if '<' in text and '>' in text:
        text = BeautifulSoup(text, 'html.parser').get_text(' ', strip=True)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\s+复制$', '', text).strip()
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
    parts = re.split(r'[;；,，、\|\n\r]+', text)
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
    result: Dict[str, str] = {}
    for key, values in parse_qs(urlparse(url).query).items():
        for value in values:
            cleaned = _clean_text(unquote(value))
            if cleaned:
                result[key] = cleaned
                break
    return result


def _is_ncmi_detail_url(url: str) -> bool:
    normalized_url = (url or '').strip().lower()
    return 'ncmi.cn/phda/datadetails.do' in normalized_url


def _extract_identifier_from_url(url: str) -> Optional[str]:
    query_id = _parse_query(url).get('id')
    if query_id:
        return query_id
    match = re.search(r'CSTR[:%3A]+[A-Za-z0-9._-]+', url or '', flags=re.IGNORECASE)
    return unquote(match.group(0)) if match else None


def _detail_url(identifier: Optional[str]) -> Optional[str]:
    if not identifier:
        return None
    return f'{DETAIL_URL}?id={quote(identifier, safe="")}'


def _fetch_detail_html(url: str) -> Optional[str]:
    identifier = _extract_identifier_from_url(url)
    request_url = _detail_url(identifier)
    if not request_url:
        return None
    try:
        response = requests.get(request_url, headers=REQUEST_HEADERS, timeout=15)
        response.raise_for_status()
    except Exception as error:
        print(f"[WARNING] NCMI detail page failed for id={identifier}: {error}")
        return None
    if '页面错误' in response.text and len(response.text) < 2000:
        return None
    return response.text


def _row_cells(row: Any) -> list[str]:
    cells = []
    for cell in row.find_all(['td', 'th'], recursive=False):
        text = _clean_text(cell.get_text(' ', strip=True))
        if text:
            cells.append(text)
    return cells


def _label_map(soup: BeautifulSoup) -> Dict[str, str]:
    labels: Dict[str, str] = {}
    section_names = {'基本信息', '描述信息', '创建者信息', '联系信息', '服务信息', '关联信息'}
    for row in soup.select('tr'):
        cells = _row_cells(row)
        if not cells:
            continue
        if len(cells) >= 2 and cells[0] in section_names:
            cells = cells[1:]
        if len(cells) < 2:
            continue
        for index in range(0, len(cells) - 1, 2):
            label = cells[index].rstrip(':：')
            value = cells[index + 1]
            if label and value and label not in section_names:
                labels[label] = value
    return labels


def _element_text(soup: BeautifulSoup, selector: str) -> Optional[str]:
    node = soup.select_one(selector)
    return _clean_text(node.get_text(' ', strip=True)) if node else None


def _citation_text(soup: BeautifulSoup) -> Optional[str]:
    for row in soup.select('tr'):
        cells = _row_cells(row)
        if cells and '引用格式' in cells[0]:
            text = ' '.join(cells[1:]) if len(cells) > 1 else cells[0]
            text = re.sub(r'^选择引用格式\s+EndNote XML\s+RIS\s+BibTex\s+', '', text)
            text = re.sub(r'\s+复制$', '', text)
            return _clean_text(text)
    node = soup.select_one('.statement_content_info .other_info_text')
    return _clean_text(node.get_text(' ', strip=True)) if node else None


def _format_date(value: Optional[Any]) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    match = re.search(r'\d{4}-\d{2}-\d{2}', text)
    return match.group(0) if match else text


def _payload_from_html(content: str, url: str, title: str) -> Optional[MetadataDict]:
    soup = BeautifulSoup(content or '', 'html.parser')
    labels = _label_map(soup)
    if not labels and 'dataSetNameZh' not in content:
        return None

    cstr_identifier = _first_non_empty(labels.get('科技资源标识符'), _extract_identifier_from_url(url))
    doi = _first_non_empty(labels.get('DOI'))
    title_zh = _first_non_empty(_element_text(soup, '#dataSetNameZh'), labels.get('数据集中文名称'), title)
    title_en = _first_non_empty(_element_text(soup, '#dataSetNameEn'), labels.get('数据集英文名称'), _english_text(title_zh), title_zh)
    identifier = cstr_identifier or doi or _extract_identifier_from_url(url)
    keywords = _unique_list(_split_terms(labels.get('关键词')))
    description = _first_non_empty(_element_text(soup, '#describe'), labels.get('数据描述'))
    citation = _citation_text(soup)
    publish_date = _format_date(labels.get('最新修订日期') or labels.get('创建时间'))
    created_date = _format_date(labels.get('创建时间'))
    version = _first_non_empty(labels.get('版本'))
    resource_url = _detail_url(identifier) or url
    data_size = _first_non_empty(labels.get('数据大小'))
    data_format = _first_non_empty(labels.get('数据格式'))
    language = _first_non_empty(labels.get('语种'))
    rights = _first_non_empty(labels.get('实体数据共享方式'), labels.get('数据使用许可'))
    license_text = _first_non_empty(labels.get('数据使用许可'))
    creators = _unique_list(_split_terms(labels.get('资源创建者')))
    creator_org = _first_non_empty(labels.get('数据资源创建机构'), labels.get('资源创建者单位'))
    contact_org = _first_non_empty(labels.get('联系单位'))
    access_url = _first_non_empty(labels.get('数据链接'), resource_url)
    alternative_identifiers = []
    if doi:
        alternative_identifiers.append({'type': 'DOI', 'identifier': doi})
    for item in _split_terms(labels.get('其他标识符')):
        alternative_identifiers.append({'type': 'Other', 'identifier': item})

    zh: Dict[str, Any] = {
        '资源类型判定': '数据集',
        '领域判定': '数据集元数据',
        '标识符': identifier,
        'CSTR标识符': cstr_identifier,
        '资源名称': title_zh,
        '标题': title_zh,
        '创建者': creators or ([creator_org] if creator_org else None),
        '发布机构': PUBLISHER_ZH,
        '发布日期': publish_date,
        '描述': description,
        '关键词': keywords or None,
        '学科分类': _first_non_empty(labels.get('学科分类'), labels.get('科学数据分类')),
        '语言': language,
        '贡献者': [creator_org] if creator_org and creator_org not in creators else None,
        '替代标识符': alternative_identifiers or None,
        '关联标识符': None,
        '权限': rights,
        '资助者': None,
        '版本': version,
        '资源链接': resource_url,
        '资源类型': '数据集',
        '数据集基本信息': {
            '标识符': identifier,
            '标题': title_zh,
            '摘要': description,
            '关键词': keywords or None,
            '范围': {
                '时间范围': _first_non_empty(labels.get('时间范围')),
                '空间范围': _first_non_empty(labels.get('地理范围')),
            },
            '语种': language,
            '文件内容': None,
            '基金项目': None,
            '数据量': data_size,
            '数据格式': data_format,
            '数据集作者': {
                '作者姓名': creators or None,
                '工作单位': creator_org,
                '电子邮箱': _first_non_empty(labels.get('联系人邮箱')),
                '工作贡献': None,
                '作者简介': None,
            },
        },
        '数据集出版信息': {
            '发布日期': publish_date,
            '出版期刊': None,
            '版本信息': version,
        },
        '数据集服务信息': {
            '数据集引用格式': citation,
            '数据集共享许可协议': license_text,
            '数据集使用声明': _first_non_empty(labels.get('数据使用说明')),
            '数据集下载地址': access_url,
            '数据集访问地址': resource_url,
        },
        '扩展信息': {
            '英文名称': title_en,
            '创建时间': created_date,
            '数据记录描述': labels.get('数据记录描述'),
            '更新频率': labels.get('更新频率'),
            '科学数据分类': labels.get('科学数据分类'),
            '物种': labels.get('物种'),
            '是否特色数据': labels.get('是否特色数据'),
            '数据标准': labels.get('数据标准'),
            '数据质量描述': labels.get('数据质量描述'),
            '数据资源联系人': labels.get('数据资源联系人'),
            '联系单位': contact_org,
            '联系人办公电话': labels.get('联系人办公电话'),
            '公开时间': labels.get('公开时间'),
            '收费方式': labels.get('收费方式'),
            '申请流程': labels.get('申请流程'),
            '数据链接': labels.get('数据链接'),
        },
    }

    en: Dict[str, Any] = {
        'Resource Type Classification': 'Dataset',
        'Domain Classification': 'Dataset Metadata',
        'Identifier': identifier,
        'CSTR Identifier': cstr_identifier,
        'Resource Name': title_en,
        'Title': title_en,
        'Creators': creators or None,
        'Publisher': PUBLISHER_EN,
        'Publication Date': publish_date,
        'Description': _english_text(description),
        'Keywords': [_english_text(item) for item in keywords if _english_text(item)] or None,
        'Discipline Classification': _english_text(labels.get('学科分类')),
        'Language': 'English' if language == '英文' else language,
        'Contributors': [_english_text(creator_org)] if _english_text(creator_org) else None,
        'Alternative Identifiers': alternative_identifiers or None,
        'Related Identifiers': None,
        'Rights': rights,
        'Funders': None,
        'Version': version,
        'Resource URL': resource_url,
        'ResourceType': 'Dataset',
        'Dataset Basic Information': {
            'Identifier': identifier,
            'Title': title_en,
            'Abstract': _english_text(description),
            'Keywords': [_english_text(item) for item in keywords if _english_text(item)] or None,
            'Coverage': {
                'Time Range': _first_non_empty(labels.get('时间范围')),
                'Spatial Range': _english_text(labels.get('地理范围')),
            },
            'Language': 'English' if language == '英文' else language,
            'File Content': None,
            'Project/Funder': None,
            'Data Size': data_size,
            'Data Format': data_format,
            'Dataset Authors': {
                'Author Name': creators or None,
                'Affiliation': _english_text(creator_org),
                'Email': _first_non_empty(labels.get('联系人邮箱')),
                'Contribution': None,
                'Biography': None,
            },
        },
        'Dataset Publication Information': {
            'Publication Date': publish_date,
            'Journal': None,
            'Version Information': version,
        },
        'Dataset Service Information': {
            'Dataset Citation Format': citation,
            'Dataset License': license_text,
            'Dataset Usage Statement': _english_text(labels.get('数据使用说明')),
            'Dataset Download URL': access_url,
            'Dataset Access URL': resource_url,
        },
        'Extension Info': {
            'Chinese Title': title_zh,
            'Archive': ARCHIVE_EN,
            'Created Date': created_date,
            'Update Frequency': _english_text(labels.get('更新频率')),
            'Science Data Category': _english_text(labels.get('科学数据分类')),
            'Species': _english_text(labels.get('物种')),
            'Contact Person': _english_text(labels.get('数据资源联系人')),
            'Contact Organization': _english_text(contact_org),
            'Contact Phone': labels.get('联系人办公电话'),
            'Open Time': _english_text(labels.get('公开时间')),
            'Data URL': labels.get('数据链接'),
        },
    }

    return {'zh': zh, 'en': en}


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').strip().lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()
    return bool(
        _is_ncmi_detail_url(url)
        or '国家人口健康科学数据中心' in combined
        and ('科技资源标识符' in content or 'phda' in normalized_url)
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[MetadataDict]:
    html = _fetch_detail_html(url) if _is_ncmi_detail_url(url) else None
    if not html:
        html = content or ''
    return _payload_from_html(html, url, title)
