from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup


RULE_NAME = 'TPDC Dataset Detail'

SECTION_LABELS = [
    'Datasets Summary',
    'Outline',
    'How to name and use data files',
    'Reference way',
    'Required reading for data reference',
    'Reference of data',
    'Article citation',
    'Funded project',
    'Statement for data usage',
    'License agreement',
    'Data files',
    'Data comment',
    'Keywords',
    'Related resources',
    'Exporting metadata',
    'Attachment information',
    'Contact information',
]


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value))
    text = re.sub(r'\s+', ' ', text).strip()
    return text or None


def _plain_text(content: str) -> str:
    soup = BeautifulSoup(content or '', 'html.parser')
    return _clean_text(soup.get_text(' ', strip=True)) or _clean_text(content) or ''


def _load_json_ld(content: str) -> Dict[str, Any]:
    soup = BeautifulSoup(content or '', 'html.parser')
    for script in soup.find_all('script', {'type': 'application/ld+json'}):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if isinstance(data, dict) and data.get('@type') == 'Dataset':
            return data
    return {}


def _first(values: list[Any]) -> Optional[str]:
    for value in values:
        cleaned = _clean_text(value)
        if cleaned:
            return cleaned
    return None


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in (_clean_text(item) for item in value) if item]
    cleaned = _clean_text(value)
    if not cleaned:
        return []
    return [item for item in re.split(r'[;；,，、|]+', cleaned) if _clean_text(item)]


def _section(text: str, start_label: str, end_labels: Optional[list[str]] = None) -> Optional[str]:
    if not text:
        return None
    labels = end_labels or SECTION_LABELS
    start = re.search(rf'\b{re.escape(start_label)}\b', text, flags=re.IGNORECASE)
    if not start:
        return None
    start_index = start.end()
    end_index = len(text)
    for label in labels:
        if label == start_label:
            continue
        match = re.search(rf'\b{re.escape(label)}\b', text[start_index:], flags=re.IGNORECASE)
        if match:
            end_index = min(end_index, start_index + match.start())
    return _clean_text(text[start_index:end_index])


def _extract_info_value(text: str, label: str) -> Optional[str]:
    if not text:
        return None
    info_labels = [
        'Temporal resolution',
        'Spatial resolution',
        'Sharing way',
        'Size',
        'Data time range',
        'Metadata update time',
        'Subscribe',
        'Download',
        'Datasets Summary',
    ]
    next_labels = [item for item in info_labels if item != label]
    pattern = rf'\b{re.escape(label)}\b\s*(.*?)\s*(?=(?:{"|".join(re.escape(item) for item in next_labels)})\b|$)'
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return _clean_text(match.group(1))


def _extract_doi(text: str, json_ld: Dict[str, Any]) -> Optional[str]:
    identifier = _clean_text(json_ld.get('identifier'))
    sources = [identifier, text]
    for source in sources:
        if not source:
            continue
        match = re.search(r'(?:doi\.org/|doi:?\s*)?(10\.\d{4,9}/[^\s。；;,，)）]+)', source, flags=re.IGNORECASE)
        if match:
            return match.group(1).rstrip('.')
    return None


def _extract_cstr(text: str, url: str) -> Optional[str]:
    for source in [text, url]:
        if not source:
            continue
        match = re.search(r'(?:CSTR\s*[:：]\s*|cstr\.cn/)([A-Za-z0-9._-]+\.[A-Za-z0-9._-]+)', source, flags=re.IGNORECASE)
        if match:
            return match.group(1).rstrip('.')
    return None


def _extract_chinese_title(content: str) -> Optional[str]:
    soup = BeautifulSoup(content or '', 'html.parser')
    node = soup.select_one('.title-cn')
    title = _clean_text(node.get('title') if node else None) or _clean_text(node.get_text(' ', strip=True) if node else None)
    return title


def _extract_geo_box(json_ld: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    geo = (
        (json_ld.get('spatialCoverage') or {}).get('geo')
        if isinstance(json_ld.get('spatialCoverage'), dict)
        else None
    )
    box = _clean_text((geo or {}).get('box') if isinstance(geo, dict) else None)
    if not box:
        return None
    parts = [item for item in re.split(r'\s+', box) if item]
    if len(parts) != 4:
        return {'地理范围描述': box}
    south, north, west, east = parts
    return {
        '南部边界纬度': south,
        '北部边界纬度': north,
        '西部边界经度': west,
        '东部边界经度': east,
        '地理范围描述': None,
    }


def _creator_agents(creators: Any) -> list[Dict[str, Any]]:
    agents = []
    items = creators if isinstance(creators, list) else [creators]
    for item in items:
        if not isinstance(item, dict):
            name = _clean_text(item)
            email = None
        else:
            name = _clean_text(item.get('name'))
            email = _clean_text(item.get('email'))
        if not name:
            continue
        agents.append({
            'type': 'Person',
            'person': {
                'names': [{'lang': 'en', 'name': name}],
                'emails': [email] if email else None,
                'identifiers': None,
                'affiliations': None,
            },
        })
    return agents


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = str(url or '').lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()
    return bool(
        'data.tpdc.ac.cn' in normalized_url
        or 'national tibetan plateau' in combined
        or 'third pole environment data center' in combined
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[Dict[str, Any]]:
    text = _plain_text(content)
    json_ld = _load_json_ld(content)
    if not json_ld and 'Datasets Summary' not in text:
        return None

    title_en = _first([json_ld.get('name'), title])
    title_zh = _extract_chinese_title(content)
    description = _first([json_ld.get('description'), _section(text, 'Datasets Summary')])
    file_note = _section(text, 'How to name and use data files')
    reference = _section(text, 'Reference of data', ['Article citation', 'Funded project', 'Statement for data usage'])
    statement = _section(text, 'Statement for data usage', ['License agreement', 'Data files', 'Data comment', 'Keywords'])
    license_text = _section(text, 'License agreement', ['Data files', 'Data comment', 'Keywords', 'Related resources'])

    doi = _extract_doi(text, json_ld)
    cstr = _extract_cstr(text, url)
    keywords = _as_list(json_ld.get('keywords'))
    creators = _creator_agents(json_ld.get('creator'))
    publisher_name = _clean_text((json_ld.get('publisher') or {}).get('disambiguatingDescription')) if isinstance(json_ld.get('publisher'), dict) else None
    publisher_name = publisher_name or _clean_text((json_ld.get('publisher') or {}).get('name')) if isinstance(json_ld.get('publisher'), dict) else publisher_name
    resource_url = _first([json_ld.get('url'), url])
    publish_date = _clean_text(json_ld.get('datePublished'))
    sharing_way = _extract_info_value(text, 'Sharing way')
    size = _extract_info_value(text, 'Size')
    data_time_range = _extract_info_value(text, 'Data time range')
    update_time = _extract_info_value(text, 'Metadata update time')
    temporal_resolution = _extract_info_value(text, 'Temporal resolution')
    spatial_resolution = _extract_info_value(text, 'Spatial resolution')
    geo_box = _extract_geo_box(json_ld)

    zh_payload: Dict[str, Any] = {
        '资源类型判定': '数据集',
        '领域判定': '数据集元数据',
        'CSTR标识符': cstr,
        '标识符': cstr or doi or resource_url,
        'DOI': doi,
        '标题': title_zh or title_en,
        '资源名称': title_zh or title_en,
        '创建者': creators or None,
        '发布机构': publisher_name,
        '发布日期': publish_date,
        '描述': description,
        '关键词': keywords or None,
        '学科': None,
        '语种': json_ld.get('inLanguage') or 'en',
        '替代标识符': [{'identifier': doi, 'type': 'DOI'}] if doi else None,
        '权限': [{'description': license_text, 'license_type': license_text}] if license_text else None,
        '资源访问地址': resource_url,
        '数据集基本信息': {
            '标识符': cstr or doi or resource_url,
            '标题': title_zh or title_en,
            '资源名称': title_zh or title_en,
            '资源名称（外文）': title_en,
            '摘要': description,
            '描述': description,
            '关键词': keywords or None,
            '数据量': size,
            '文件内容': file_note,
            '范围': {
                '时间范围': data_time_range,
                '空间范围': geo_box,
            },
        },
        '数据集出版信息': {
            '发布日期': publish_date,
            '最新发布日期': update_time,
            '版本信息': None,
            '生成日期': None,
        },
        '数据集服务信息': {
            '资源访问地址': resource_url,
            '数据集访问地址': resource_url,
            '共享途径': sharing_way,
            '数据集共享许可协议': license_text,
            '数据集使用声明': statement,
            '数据集引用格式': reference,
        },
        '扩展信息': {
            '时间分辨率': temporal_resolution,
            '空间分辨率': spatial_resolution,
            '数据时间范围': data_time_range,
            '文件命名与使用说明': file_note,
        },
    }

    en_payload: Dict[str, Any] = {
        'Resource Type Classification': 'Dataset',
        'Domain Classification': 'Dataset Metadata',
        'CSTR Identifier': cstr,
        'Identifier': cstr or doi or resource_url,
        'DOI': doi,
        'Title': title_en,
        'Resource Name': title_en,
        'Creators': creators or None,
        'Publisher': publisher_name,
        'Publication Date': publish_date,
        'Description': description,
        'Keywords': keywords or None,
        'Language': json_ld.get('inLanguage') or 'en',
        'Alternative Identifiers': [{'identifier': doi, 'type': 'DOI'}] if doi else None,
        'Rights': [{'description': license_text, 'license_type': license_text}] if license_text else None,
        'Resource Access URL': resource_url,
        'Dataset Basic Information': {
            'Identifier': cstr or doi or resource_url,
            'Title': title_en,
            'Resource Name': title_en,
            'Abstract': description,
            'Description': description,
            'Keywords': keywords or None,
            'Data Volume': size,
            'File Content': file_note,
            'Coverage': {
                'Temporal Coverage': data_time_range,
                'Spatial Coverage': geo_box,
            },
        },
        'Dataset Publication Information': {
            'Publication Date': publish_date,
            'Latest Release Date': update_time,
            'Version Information': None,
            'Generation Date': None,
        },
        'Dataset Service Information': {
            'Resource Access URL': resource_url,
            'Dataset Access URL': resource_url,
            'Sharing Channel': sharing_way,
            'Dataset Sharing License': license_text,
            'Dataset Usage Statement': statement,
            'Dataset Citation Format': reference,
        },
        'Extension Info': {
            'Temporal Resolution': temporal_resolution,
            'Spatial Resolution': spatial_resolution,
            'Data Time Range': data_time_range,
            'File Naming And Usage': file_note,
        },
    }

    return {
        'zh': zh_payload,
        'en': en_payload,
    }
