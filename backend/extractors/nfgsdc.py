from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Dict, Iterable, Optional
from urllib.parse import parse_qs, urlparse

import requests

from .base import MetadataDict


RULE_NAME = 'NFGSDC Data Detail'

BASE_URL = 'https://www.forestdata.cn'
API_URL = 'https://api.forestdata.cn/ssl/portal.unauth/api/v1/Data/detail'
PUBLISHER_ZH = '国家林业和草原科学数据中心'
PUBLISHER_EN = 'National Forestry and Grassland Science Data Center'
CSTR_PATTERN = re.compile(r'\b(?:CSTR\s*[:：]\s*)?([A-Z0-9]{5}\.\d{2}\.[-._;()/:A-Z0-9]+)\b', re.IGNORECASE)
DOI_PATTERN = re.compile(r'\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b')

API_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/125.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json,text/plain,*/*',
    'Referer': BASE_URL,
}


def _clean_text(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    text = str(value)
    for _ in range(3):
        text = unescape(text)
    text = re.sub(r'[\u200b\xa0]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text if text and text not in {'null', 'None', '[]'} else None


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


def _split_terms(value: Optional[Any]) -> list[str]:
    if isinstance(value, list):
        if any(_clean_text(item) is None for item in value):
            phrases: list[str] = []
            current: list[str] = []
            for item in value:
                cleaned = _clean_text(item)
                if cleaned:
                    current.append(cleaned)
                    continue
                if current:
                    phrases.append(' '.join(current))
                    current = []
            if current:
                phrases.append(' '.join(current))
            return _unique_list(phrases)
        return _unique_list(value)
    text = _clean_text(value)
    if not text:
        return []
    return _unique_list(re.split(r'[;；,，、|]+|\s{2,}', text))


def _query_id(url: str) -> Optional[str]:
    query = parse_qs(urlparse(url or '').query)
    for key in ('id', 'dataId'):
        values = query.get(key)
        if values:
            return _clean_text(values[0])
    return None


def _load_json_payload(content: str) -> Optional[Dict[str, Any]]:
    text = (content or '').strip()
    if not text.startswith('{'):
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _payload_data(payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return None
    data = payload.get('data')
    if isinstance(data, dict) and isinstance(data.get('data'), dict):
        return data
    if isinstance(payload.get('data'), dict) and any(key in payload['data'] for key in ('title', 'dataset', 'meta')):
        return payload
    return None


def _fetch_detail_data(dataset_id: str, referer: str = '', language: str = 'zh_CN') -> Optional[Dict[str, Any]]:
    response = requests.get(
        API_URL,
        params={'id': dataset_id, 'language': language},
        headers={**API_HEADERS, 'Referer': referer or f'{BASE_URL}/dataDetail.html?id={dataset_id}'},
        timeout=15,
    )
    response.raise_for_status()
    return _payload_data(response.json())


def _kv_map(items: Any) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    if not isinstance(items, list):
        return values
    for item in items:
        if not isinstance(item, dict):
            continue
        key = _clean_text(item.get('key'))
        if not key:
            continue
        value = _clean_text(item.get('value'))
        if value:
            values[key] = value
    return values


def _named_values(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    return _unique_list(
        item.get('value') if isinstance(item, dict) else item
        for item in items
    )


def _extract_cstr(*values: Optional[Any]) -> Optional[str]:
    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        match = CSTR_PATTERN.search(text)
        if match:
            return match.group(1).rstrip('.,;。；')
    return None


def _extract_doi(*values: Optional[Any]) -> Optional[str]:
    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        match = DOI_PATTERN.search(text)
        if match:
            return match.group(0).rstrip('.,;。；')
    return None


def _publisher(lang: str = 'both') -> Dict[str, Any]:
    names = []
    if lang in {'both', 'zh'}:
        names.append({'lang': 'zh', 'name': PUBLISHER_ZH})
    if lang in {'both', 'en'}:
        names.append({'lang': 'en', 'name': PUBLISHER_EN})
    return {'names': names, 'identifiers': None}


def _person_agent(name: str, email: Optional[str] = None, affiliation: Optional[str] = None) -> Dict[str, Any]:
    return {
        'type': 'Person',
        'person': {
            'names': [{'lang': 'zh', 'name': name}],
            'emails': [email] if email else None,
            'identifiers': None,
            'affiliations': [{'names': [{'lang': 'zh', 'name': affiliation}], 'identifiers': None}] if affiliation else None,
        },
    }


def _organization_agent(name: Optional[str], lang: str = 'zh') -> Dict[str, Any]:
    return {
        'type': 'Organize',
        'affiliation': {
            'names': [{'lang': lang, 'name': _first_non_empty(name, PUBLISHER_ZH if lang == 'zh' else PUBLISHER_EN)}],
            'identifiers': None,
        },
    }


def _rights(
    share_type: Optional[str],
    access_method: Optional[str],
    share_level: Optional[str],
    lang: str = 'zh',
) -> Optional[list[Dict[str, Any]]]:
    separator = '; ' if lang == 'en' else '；'
    description = separator.join(_unique_list([share_type, access_method, share_level])) or None
    if not description:
        return None
    return [{
        'license_type': None,
        'license': None,
        'type': None,
        'description': description,
        'cert_num': None,
    }]


def _resource_url(url: str, dataset_id: Optional[str]) -> Optional[str]:
    if 'forestdata.cn/datadetail.html' in (url or '').lower():
        return url
    if dataset_id:
        return f'{BASE_URL}/dataDetail.html?id={dataset_id}'
    return url or None


def _payload_from_data(payload: Dict[str, Any], url: str, title: str, payload_en: Optional[Dict[str, Any]] = None) -> MetadataDict:
    data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
    dataset = payload.get('dataset') if isinstance(payload.get('dataset'), dict) else {}
    contact = payload.get('contact') if isinstance(payload.get('contact'), dict) else {}
    meta = _kv_map(payload.get('meta'))
    index = _kv_map(payload.get('index'))
    en_payload = payload_en if isinstance(payload_en, dict) else {}
    en_data = en_payload.get('data') if isinstance(en_payload.get('data'), dict) else {}
    en_meta = _kv_map(en_payload.get('meta'))

    dataset_id = _first_non_empty(data.get('id'), _query_id(url))
    title_zh = _first_non_empty(data.get('title'), dataset.get('name'), title, dataset_id)
    title_en = _clean_text(en_data.get('title'))
    description = _clean_text(data.get('desc'))
    description_en = _clean_text(en_data.get('desc'))
    quote = _clean_text(data.get('quote'))
    quote_en = _clean_text(en_data.get('quote')) or quote
    cstr_identifier = _extract_cstr(index.get('CSTR标识'), dataset.get('code'), quote)
    doi = _extract_doi(quote)
    identifier = cstr_identifier or _first_non_empty(dataset.get('code'), dataset_id)
    publish_date = _first_non_empty(data.get('publishTime'), meta.get('数据汇交时间'))
    keywords = _split_terms(payload.get('keyword'))
    keywords_en = _split_terms(en_payload.get('keyword'))
    subjects = _unique_list([meta.get('学科分类')])
    subjects_en = _unique_list([en_meta.get('Subject Type')])
    catalog_subjects = _named_values(payload.get('catalog'))
    catalog_subjects_en = _named_values(en_payload.get('catalog'))
    spatial_extent = '；'.join(_named_values(payload.get('extent'))) or None
    spatial_extent_en = '; '.join(_named_values(en_payload.get('extent'))) or spatial_extent
    time_extent = _clean_text(meta.get('数据时间'))
    time_extent_en = _clean_text(en_meta.get('Data Time')) or time_extent
    data_format = _clean_text(meta.get('数据格式'))
    data_format_en = _clean_text(en_meta.get('Data Type')) or data_format
    data_size = _clean_text(meta.get('数据量'))
    data_size_en = _clean_text(en_meta.get('Data Amount')) or data_size
    data_source = _clean_text(meta.get('数据来源'))
    resource_kind = _clean_text(meta.get('数据资源'))
    resource_kind_en = _clean_text(en_meta.get('Resource Type')) or resource_kind
    share_type = _first_non_empty(data.get('shareType'), meta.get('共享级别'))
    share_type_en = _first_non_empty(en_data.get('shareType'), en_meta.get('Share Level')) or share_type
    access_method = _clean_text(meta.get('获取方式'))
    access_method_en = _clean_text(en_meta.get('Get Type')) or access_method
    quality = _clean_text(meta.get('数据质量'))
    quality_en = _clean_text(en_meta.get('Data Quality'))
    process = _clean_text(meta.get('数据加工方法'))
    process_en = _clean_text(en_meta.get('Data Processing Method'))
    resource_url = _resource_url(url, dataset_id)
    contact_name = _clean_text(contact.get('name'))
    contact_address = _clean_text(contact.get('address'))
    organization = None
    if quote and title_zh:
        prefix = quote.split(title_zh, 1)[0].strip(' ，,.;；')
        organization = _clean_text(prefix)
    creators = [_organization_agent(organization)] if organization else [_organization_agent(PUBLISHER_ZH)]
    contributors = [_person_agent(contact_name, None, organization)] if contact_name else None
    rights = _rights(share_type, access_method, meta.get('共享级别'), 'zh')
    rights_en = _rights(share_type_en, access_method_en, en_meta.get('Share Level'), 'en')
    alternative_identifiers = [{'type': 'DOI', 'identifier': doi}] if doi else None

    core_zh: Dict[str, Any] = {
        'titles': [{'lang': 'zh', 'name': title_zh}] if title_zh else None,
        'identifier': cstr_identifier,
        'creators': creators,
        'publisher': _publisher(),
        'publish_date': publish_date,
        'descriptions': [{'lang': 'zh', 'description': description}] if description else None,
        'keywords': [{'lang': 'zh', 'keyword': keywords}] if keywords else None,
        'subjects': [{'lang': 'zh', 'value': subjects}] if subjects else None,
        'language': 'zh',
        'contributors': contributors,
        'alternative_identifiers': alternative_identifiers,
        'related_identifiers': None,
        'rights': rights,
        'funders': None,
        'version': _clean_text(payload.get('version')),
        'urls': [resource_url] if resource_url else None,
        'resource_type': 'Dataset',
    }

    zh: Dict[str, Any] = {
        '核心元数据': {'metadatas': [core_zh]},
        '数据集基本信息': {
            '标识符': identifier or dataset_id,
            '标题': title_zh,
            '摘要': description,
            '关键词': keywords or None,
            '范围': {
                '时间范围': time_extent,
                '空间范围': spatial_extent,
            },
            '语种': '中文',
            '文件内容': resource_kind,
            '基金项目': None,
            '数据量': data_size,
            '数据格式': data_format,
            '数据集作者': {
                '作者姓名': [organization] if organization else None,
                '工作单位': organization,
                '电子邮箱': None,
                '工作贡献': '数据生产、汇交与发布',
                '作者简介': None,
            },
        },
        '数据集出版信息': {
            '发布日期': publish_date,
            '出版期刊': None,
            '版本信息': _clean_text(payload.get('version')),
        },
        '数据集服务信息': {
            '数据集引用格式': quote,
            '数据集共享许可协议': share_type,
            '数据集使用声明': access_method,
            '数据集下载地址': resource_url,
            '数据论文访问地址': None,
        },
        '扩展信息': {
            '联系人': contact_name,
            '联系地址': contact_address,
            '联系电话': _clean_text(contact.get('tele')),
            '浏览量': data.get('visitCount'),
            '下载量': data.get('downloadCount'),
            '收藏量': data.get('favoriteCount'),
            '数据质量': quality,
            '数据加工方法': process,
            '目录分类': catalog_subjects or None,
            '封面图片': _clean_text(data.get('image')),
        },
    }

    core_en: Dict[str, Any] = {
        **core_zh,
        'titles': [{'lang': 'en', 'name': title_en}] if title_en else None,
        'descriptions': [{'lang': 'en', 'description': description_en}] if description_en else None,
        'keywords': [{'lang': 'en', 'keyword': keywords_en}] if keywords_en else None,
        'subjects': [{'lang': 'en', 'value': subjects_en}] if subjects_en else None,
        'publisher': _publisher('en'),
        'creators': [_organization_agent(PUBLISHER_EN, 'en')],
        'contributors': None,
        'rights': rights_en,
        'language': 'English',
    }
    en: Dict[str, Any] = {
        'Core Metadata': {'metadatas': [core_en]},
        'Dataset Basic Information': {
            'Identifier': identifier or dataset_id,
            'Title': title_en,
            'Abstract': description_en,
            'Keywords': keywords_en or None,
            'Coverage': {
                'Time Range': time_extent_en,
                'Spatial Range': spatial_extent_en,
            },
            'Language': 'English',
            'File Content': resource_kind_en,
            'Project/Funder': None,
            'Data Size': data_size_en,
            'Data Format': data_format_en,
            'Dataset Authors': {
                'Author Name': [organization] if organization else None,
                'Affiliation': organization,
                'Email': None,
                'Contribution': 'Data production, submission, and publication',
                'Biography': None,
            },
        },
        'Dataset Publication Information': {
            'Publication Date': publish_date,
            'Journal': None,
            'Version Information': _clean_text(payload.get('version')),
        },
        'Dataset Service Information': {
            'Dataset Citation Format': quote_en,
            'Dataset License': share_type_en,
            'Dataset Usage Statement': access_method_en,
            'Dataset Download URL': resource_url,
            'Dataset Paper URL': None,
        },
        'Extension Info': {
            'Contact': contact_name,
            'Contact Address': contact_address,
            'Contact Phone': _clean_text(contact.get('tele')),
            'Views': data.get('visitCount'),
            'Downloads': data.get('downloadCount'),
            'Collections': data.get('favoriteCount'),
            'Data Quality': quality_en,
            'Data Processing Method': process_en,
            'Catalog Classification': catalog_subjects_en or None,
            'Cover Image': _clean_text(data.get('image')),
        },
    }

    return {'zh': zh, 'en': en}


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').strip().lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()
    return bool(
        'forestdata.cn/datadetail.html' in normalized_url
        or 'api.forestdata.cn/ssl/portal.unauth/api/v1/data/detail' in normalized_url
        or (
            '国家林业和草原科学数据' in combined
            and ('datadetail' in combined or 'data/detail' in combined)
        )
        or (
            '"buttonstatus"' in combined
            and '"dataset"' in combined
            and '"meta"' in combined
            and '"forestdata' in combined
        )
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[MetadataDict]:
    payload = _payload_data(_load_json_payload(content or ''))
    payload_en = None
    dataset_id = _query_id(url)
    if not payload and dataset_id:
        payload = _fetch_detail_data(dataset_id, url, 'zh_CN')
        try:
            payload_en = _fetch_detail_data(dataset_id, url, 'en_US')
        except Exception:
            payload_en = None
    if not isinstance(payload, dict):
        return None
    return _payload_from_data(payload, url, title, payload_en)
