from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


RULE_NAME = 'TPDC Dataset Detail'
BASE_URL = 'https://data.tpdc.ac.cn'
DETAIL_API = f'{BASE_URL}/view/metadataView/detail/'
UUID_PATTERN = re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.I)
API_HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/json,text/plain,*/*',
    'Content-Type': 'application/json',
    'Referer': f'{BASE_URL}/',
}

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


def _load_json_payload(content: str) -> Optional[Dict[str, Any]]:
    text = (content or '').strip()
    if not text.startswith('{'):
        return None
    try:
        payload = json.loads(text)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _detail_id(url: str, content: str = '') -> Optional[str]:
    parsed = urlparse(url or '')
    for part in reversed([item for item in parsed.path.split('/') if item]):
        if UUID_PATTERN.fullmatch(part):
            return part
    match = UUID_PATTERN.search(content or '')
    return match.group(0) if match else None


def _fetch_detail_context(metadata_id: str) -> Optional[Dict[str, Any]]:
    if not metadata_id:
        return None
    response = requests.post(
        DETAIL_API,
        json={'userId': '', 'metadataId': metadata_id},
        headers=API_HEADERS,
        timeout=20,
    )
    response.raise_for_status()
    response.encoding = 'utf-8'
    payload = response.json()
    if not isinstance(payload, dict) or payload.get('code') != '200':
        return None
    context = payload.get('context')
    return context if isinstance(context, dict) else None


def _first(values: list[Any]) -> Optional[str]:
    for value in values:
        cleaned = _clean_text(value)
        if cleaned:
            return cleaned
    return None


def _unique(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = _clean_text(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


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
        match = re.search(r'(?:CSTR\s*[:：]\s*|cstr\.cn/)([A-Z0-9]{5}\.\d{2}\.[-._;()/:A-Z0-9]+)', source, flags=re.IGNORECASE)
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


def _date_only(value: Any) -> Optional[str]:
    cleaned = _clean_text(value)
    return cleaned[:10] if cleaned else None


def _bytes_to_size(value: Any) -> Optional[str]:
    try:
        size = float(value)
    except (TypeError, ValueError):
        return _clean_text(value)
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    return f'{size:.2f}{units[index]}' if index else f'{int(size)}B'


def _keyword_values(items: Any, zh_key: str, en_key: str) -> tuple[list[str], list[str]]:
    if not isinstance(items, list):
        return [], []
    zh = _unique([item.get(zh_key) for item in items if isinstance(item, dict)])
    en = _unique([item.get(en_key) for item in items if isinstance(item, dict)])
    return zh, en


def _temporal_keyword_values(items: Any) -> tuple[list[str], list[str]]:
    if not isinstance(items, list):
        return [], []
    zh_values: list[Any] = []
    en_values: list[Any] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        zh = _clean_text(item.get('keyword'))
        en = _clean_text(item.get('keywordEn'))
        zh_values.append(zh)
        if zh and re.fullmatch(r'\d{4}(?:-\d{4})?', zh):
            en_values.append(zh)
        else:
            en_values.append(en)
    return _unique(zh_values), _unique(en_values)


def _api_creator_agents(authors: Any) -> list[Dict[str, Any]]:
    agents = []
    items = authors if isinstance(authors, list) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        names = []
        name_zh = _clean_text(item.get('name'))
        name_en = _clean_text(item.get('nameEn'))
        if name_zh:
            names.append({'lang': 'zh', 'name': name_zh})
        if name_en:
            names.append({'lang': 'en', 'name': name_en})
        if not names:
            continue
        affiliations = []
        unit_zh = _clean_text(item.get('unit'))
        unit_en = _clean_text(item.get('unitEn'))
        affiliation_names = []
        if unit_zh:
            affiliation_names.append({'lang': 'zh', 'name': unit_zh})
        if unit_en:
            affiliation_names.append({'lang': 'en', 'name': unit_en})
        if affiliation_names:
            affiliations.append({'names': affiliation_names, 'identifiers': None})
        agents.append({
            'type': 'Person',
            'person': {
                'names': names,
                'emails': [item.get('email')] if _clean_text(item.get('email')) else None,
                'identifiers': [{'type': 'DAID', 'identifier': item.get('daid')}] if _clean_text(item.get('daid')) else None,
                'affiliations': affiliations or None,
            },
        })
    return agents


def _dataset_author(authors: Any, lang: str) -> Optional[Dict[str, Any]]:
    if not isinstance(authors, list) or not authors:
        return None
    name_key = 'nameEn' if lang == 'en' else 'name'
    unit_key = 'unitEn' if lang == 'en' else 'unit'
    names = _unique([item.get(name_key) for item in authors if isinstance(item, dict)])
    units = _unique([item.get(unit_key) for item in authors if isinstance(item, dict)])
    if not names and lang == 'en':
        names = _unique([item.get('name') for item in authors if isinstance(item, dict)])
    if not units and lang == 'en':
        units = _unique([item.get('unit') for item in authors if isinstance(item, dict)])
    if not names and not units:
        return None
    return {
        '作者姓名' if lang == 'zh' else 'Author Name': names or None,
        '工作单位' if lang == 'zh' else 'Affiliation': '；'.join(units) or None,
        '电子邮箱' if lang == 'zh' else 'Email': '；'.join(_unique([item.get('email') for item in authors if isinstance(item, dict)])) or None,
        '工作贡献' if lang == 'zh' else 'Contribution': None,
        '作者简介' if lang == 'zh' else 'Biography': None,
    }


def _spatial_range_from_metadata(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    values = {
        '西部边界经度': _clean_text(metadata.get('west')),
        '东部边界经度': _clean_text(metadata.get('east')),
        '南部边界纬度': _clean_text(metadata.get('south')),
        '北部边界纬度': _clean_text(metadata.get('north')),
    }
    return {key: value for key, value in values.items() if value} or None


def _spatial_range_from_metadata_en(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    values = {
        'West Bounding Longitude': _clean_text(metadata.get('west')),
        'East Bounding Longitude': _clean_text(metadata.get('east')),
        'South Bounding Latitude': _clean_text(metadata.get('south')),
        'North Bounding Latitude': _clean_text(metadata.get('north')),
    }
    return {key: value for key, value in values.items() if value} or None


def _time_range_from_metadata(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    values = {
        '起始时间': _date_only(metadata.get('startTime')),
        '结束时间': _date_only(metadata.get('endTime')),
    }
    return {key: value for key, value in values.items() if value} or None


def _time_range_from_metadata_en(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    values = {
        'Start Time': _date_only(metadata.get('startTime')),
        'End Time': _date_only(metadata.get('endTime')),
    }
    return {key: value for key, value in values.items() if value} or None


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


def _payload_from_api_context(context: Dict[str, Any], url: str) -> Optional[Dict[str, Any]]:
    metadata = context.get('metadataVO') if isinstance(context.get('metadataVO'), dict) else {}
    word = context.get('metadataWordVO') if isinstance(context.get('metadataWordVO'), dict) else {}
    if not metadata:
        return None

    metadata_id = _clean_text(metadata.get('id')) or _detail_id(url)
    page_url = f'{BASE_URL}/en/data/{metadata_id}' if metadata_id else (url or None)
    cstr = _clean_text(metadata.get('cstr'))
    doi = _clean_text(metadata.get('doi'))
    title_zh = _first([metadata.get('title')])
    title_en = _first([metadata.get('titleEn'), word.get('title')])
    desc_zh = _first([metadata.get('description')])
    desc_en = _first([word.get('description')])
    instructions_zh = _first([metadata.get('instructions')])
    instructions_en = _first([word.get('instructions')])
    usage_zh = _first([metadata.get('userLimit'), metadata.get('useTerms')])
    usage_en = _first([word.get('userLimit'), word.get('useTerms')])
    license_text = _clean_text(metadata.get('license'))
    publish_date = _date_only(metadata.get('tsPublish')) or _date_only(metadata.get('tsCreated'))
    update_time = _date_only(metadata.get('tsUpdated'))
    data_amount = _bytes_to_size(context.get('fileSize') or metadata.get('fileSize'))
    temporal_resolution = _clean_text(metadata.get('temporalResolution'))
    spatial_resolution = _clean_text(metadata.get('spatialResolution'))
    data_format = _clean_text(metadata.get('dataFormat'))
    creators = _api_creator_agents(context.get('authorVOList'))
    authors = context.get('authorVOList')
    funders_zh = [
        {
            'name': _clean_text(item.get('titleCn')),
            'proj_type': None,
            'proj_num': _clean_text(item.get('code')),
            'proj_name': _clean_text(item.get('titleCn')),
        }
        for item in (context.get('fundVOList') if isinstance(context.get('fundVOList'), list) else [])
        if isinstance(item, dict) and (_clean_text(item.get('titleCn')) or _clean_text(item.get('code')))
    ] or None
    funders_en = [
        {
            'name': _clean_text(item.get('titleEn')),
            'proj_type': None,
            'proj_num': _clean_text(item.get('code')),
            'proj_name': _clean_text(item.get('titleEn')),
        }
        for item in (context.get('fundVOList') if isinstance(context.get('fundVOList'), list) else [])
        if isinstance(item, dict) and (_clean_text(item.get('titleEn')) or _clean_text(item.get('code')))
    ] or None

    subject_zh, subject_en = _keyword_values(context.get('keywordStandVOList'), 'name', 'enName')
    theme_zh, theme_en = _keyword_values(context.get('themeList'), 'name', 'enName')
    place_zh, place_en = _keyword_values(context.get('placeKeywordVOList'), 'keyword', 'keywordEn')
    temporal_zh, temporal_en = _temporal_keyword_values(context.get('temporalKeywordVOList'))
    keywords_zh = _unique([*theme_zh, *place_zh, *temporal_zh])
    keywords_en = _unique([*theme_en, *place_en, *temporal_en])
    keyword_values = []
    if keywords_zh:
        keyword_values.append({'lang': 'zh', 'keyword': keywords_zh})
    if keywords_en:
        keyword_values.append({'lang': 'en', 'keyword': keywords_en})

    title_values = []
    if title_zh:
        title_values.append({'lang': 'zh', 'name': title_zh})
    if title_en:
        title_values.append({'lang': 'en', 'name': title_en})

    description_values = []
    if desc_zh:
        description_values.append({'lang': 'zh', 'description': desc_zh})
    if desc_en:
        description_values.append({'lang': 'en', 'description': desc_en})

    publisher = {
        'names': [
            {'lang': 'zh', 'name': '国家青藏高原科学数据中心'},
            {'lang': 'en', 'name': 'National Tibetan Plateau / Third Pole Environment Data Center'},
        ],
        'identifiers': None,
    }
    alternative_identifiers = [{'type': 'DOI', 'identifier': doi}] if doi else None
    time_range = _time_range_from_metadata(metadata)
    time_range_en = _time_range_from_metadata_en(metadata)
    spatial_range = _spatial_range_from_metadata(metadata)
    spatial_range_en = _spatial_range_from_metadata_en(metadata)
    identifier = cstr or doi or metadata_id or page_url

    core = {
        'titles': title_values or None,
        'identifier': cstr,
        'creators': creators or None,
        'publisher': publisher,
        'publish_date': publish_date,
        'descriptions': description_values or None,
        'keywords': keyword_values or None,
        'subjects': [{'standard_gbt': None, 'standard_oecd': subject_en}] if subject_en else None,
        'language': metadata.get('language') or word.get('language') or 'zh/en',
        'contributors': None,
        'alternative_identifiers': alternative_identifiers,
        'related_identifiers': None,
        'rights': [{
            'license_type': None,
            'license': license_text,
            'type': metadata.get('shareType'),
            'description': license_text,
            'cert_num': None,
        }] if license_text else None,
        'funders': funders_zh,
        'version': None,
        'urls': [page_url] if page_url else None,
        'resource_type': 'Dataset',
    }
    core_en = {
        **core,
        'titles': [{'lang': 'en', 'name': title_en}] if title_en else None,
        'descriptions': [{'lang': 'en', 'description': desc_en}] if desc_en else None,
        'keywords': [{'lang': 'en', 'keyword': keywords_en}] if keywords_en else None,
        'subjects': [{'standard_gbt': None, 'standard_oecd': subject_en}] if subject_en else None,
        'language': word.get('language') or 'en',
        'rights': [{
            'license_type': None,
            'license': license_text,
            'type': metadata.get('shareType'),
            'description': license_text,
            'cert_num': None,
        }] if license_text else None,
        'publisher': {
            'names': [{'lang': 'en', 'name': 'National Tibetan Plateau / Third Pole Environment Data Center'}],
            'identifiers': None,
        },
        'creators': None,
        'contributors': None,
        'funders': funders_en,
    }

    zh_payload: Dict[str, Any] = {
        '核心元数据': {'metadatas': [core]},
        '数据集基本信息': {
            '标识符': identifier,
            '标题': title_zh or title_en,
            '摘要': desc_zh,
            '关键词': [{'lang': 'zh', 'keyword': keywords_zh}] if keywords_zh else None,
            '范围': {
                '时间范围': time_range,
                '空间范围': spatial_range,
            },
            '语种': metadata.get('language') or 'zh',
            '文件内容': None,
            '基金项目': funders_zh,
            '数据量': data_amount,
            '数据格式': data_format,
            '数据集作者': _dataset_author(authors, 'zh'),
        },
        '数据集出版信息': {
            '发布日期': publish_date,
            '最新发布日期': update_time,
            '版本信息': None,
        },
        '数据集服务信息': {
            '数据集引用格式': _clean_text(metadata.get('reference')),
            '数据集共享许可协议': license_text,
            '数据集使用声明': usage_zh,
            '数据集下载地址': None,
            '数据集访问地址': page_url,
        },
        '扩展信息': {
            'TPDC元数据ID': metadata_id,
            '时间分辨率': temporal_resolution,
            '空间分辨率': spatial_resolution,
            '文件命名与使用说明': instructions_zh,
        },
    }

    en_payload: Dict[str, Any] = {
        'Core Metadata': {'metadatas': [core_en]},
        'Dataset Basic Information': {
            'Identifier': identifier,
            'Title': title_en or title_zh,
            'Abstract': desc_en,
            'Keywords': [{'lang': 'en', 'keyword': keywords_en}] if keywords_en else None,
            'Scope': {
                'Time Range': time_range_en,
                'Spatial Range': spatial_range_en,
            },
            'Language': word.get('language') or 'en',
            'File Content': None,
            'Funding Project': funders_en,
            'Data Volume': data_amount,
            'Data Format': data_format,
            'Dataset Authors': _dataset_author(authors, 'en'),
        },
        'Dataset Publication Information': {
            'Publication Date': publish_date,
            'Latest Release Date': update_time,
            'Version Information': None,
        },
        'Dataset Service Information': {
            'Dataset Citation Format': _clean_text(word.get('reference') or metadata.get('reference')),
            'Dataset License': license_text,
            'Dataset Usage Statement': usage_en,
            'Dataset Download URL': None,
            'Dataset Access URL': page_url,
        },
        'Extension Info': {
            'TPDC Metadata ID': metadata_id,
            'Temporal Resolution': temporal_resolution,
            'Spatial Resolution': spatial_resolution,
            'File Naming And Usage': instructions_en,
        },
    }

    return {'zh': zh_payload, 'en': en_payload}


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = str(url or '').lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()
    return bool(
        'data.tpdc.ac.cn' in normalized_url
        or 'national tibetan plateau' in combined
        or 'third pole environment data center' in combined
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[Dict[str, Any]]:
    payload = _load_json_payload(content or '')
    if payload:
        context = payload.get('context') if isinstance(payload.get('context'), dict) else payload
        api_payload = _payload_from_api_context(context, url)
        if api_payload:
            return api_payload

    metadata_id = _detail_id(url, content or '')
    if metadata_id:
        try:
            context = _fetch_detail_context(metadata_id)
        except Exception:
            context = None
        api_payload = _payload_from_api_context(context or {}, url) if context else None
        if api_payload:
            return api_payload

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
            'Scope': {
                'Time Range': data_time_range,
                'Spatial Range': geo_box,
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
            'Dataset License': license_text,
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
