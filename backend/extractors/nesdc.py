from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Dict, Iterable, Optional
from urllib.parse import parse_qs, urlparse

import requests

from .base import MetadataDict


RULE_NAME = 'NESDC Dataset Detail'

BASE_URL = 'https://www.nesdc.org.cn'
PUBLISHER_ZH = '国家生态科学数据中心'
PUBLISHER_EN = 'National Ecosystem Science Data Center'
CSTR_PATTERN = re.compile(r'\b(?:CSTR:)?(\d{5}\.\d{1,2}\.[A-Za-z0-9][A-Za-z0-9._-]*(?:\.[A-Za-z0-9][A-Za-z0-9._-]*)+)\b')
DOI_PATTERN = re.compile(r'\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b')
ID_PATTERN = re.compile(r'\b[0-9a-f]{24}\b', re.I)
API_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json,text/javascript,*/*;q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': f'{BASE_URL}/sdo/list',
}


def _clean_text(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value))
    text = re.sub(r'[\u200b\xa0]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text if text and text not in {' ', '[]', 'null', 'None'} else None


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


def _split_terms(*values: Any) -> list[str]:
    terms: list[str] = []
    for value in values:
        if isinstance(value, list):
            terms.extend(value)
            continue
        text = _clean_text(value)
        if not text:
            continue
        terms.extend(part for part in re.split(r'[、,，;；|]+', text) if part.strip())
    return _unique_list(terms)


def _parse_json(content: str) -> Optional[Dict[str, Any]]:
    text = (content or '').strip()
    if not text.startswith('{'):
        return None
    try:
        payload = json.loads(text)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _extract_dataset_id(url: str, content: str = '') -> Optional[str]:
    parsed = urlparse(url or '')
    query_id = parse_qs(parsed.query).get('id')
    if query_id:
        cleaned = _clean_text(query_id[0])
        if cleaned and ID_PATTERN.fullmatch(cleaned):
            return cleaned

    match = re.search(r'/api/sdoMetadata/([0-9a-f]{24})', parsed.path, re.I)
    if match:
        return match.group(1)

    match = re.search(r'\bsdoId\s*=\s*[\'"]([0-9a-f]{24})[\'"]', content or '', re.I)
    if match:
        return match.group(1)

    match = ID_PATTERN.search(content or '')
    return match.group(0) if match else None


def _fetch_visit_data(dataset_id: str) -> Optional[Dict[str, Any]]:
    if not dataset_id:
        return None
    response = requests.get(
        f'{BASE_URL}/sdo/visitSdo',
        params={'id': dataset_id},
        headers={**API_HEADERS, 'Referer': f'{BASE_URL}/sdo/detail?id={dataset_id}'},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, dict) else None


def _fetch_meta_data(dataset_id: str) -> Optional[Dict[str, Any]]:
    if not dataset_id:
        return None
    response = requests.get(
        f'{BASE_URL}/sdo/getSdoDetailsMeta',
        params={'id': dataset_id},
        headers={**API_HEADERS, 'Referer': f'{BASE_URL}/sdo/detail?id={dataset_id}'},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, dict) else None


def _meta_value_map(meta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    if not isinstance(meta, dict):
        return values
    for item in meta.get('map') or []:
        if not isinstance(item, dict):
            continue
        field = _clean_text(item.get('field'))
        if not field:
            continue
        value = item.get('value')
        cleaned = _clean_text(value)
        if cleaned:
            values[field] = cleaned
    return values


def _custom_value_map(data: Dict[str, Any]) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    sdo = data.get('sdo') if isinstance(data.get('sdo'), dict) else {}
    custom_items = sdo.get('customConfigurationData') or data.get('customConfigurationData') or []
    if not isinstance(custom_items, list):
        return values
    for item in custom_items:
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            if key == 'classificationName':
                continue
            cleaned = _clean_text(value)
            if cleaned:
                values[key] = value
    return values


def _value(values: Dict[str, Any], data: Dict[str, Any], *keys: str) -> Optional[Any]:
    sdo = data.get('sdo') if isinstance(data.get('sdo'), dict) else {}
    for key in keys:
        if key in values:
            return values.get(key)
        if key in data:
            return data.get(key)
        if key in sdo:
            return sdo.get(key)
    return None


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
            return match.group(0).rstrip('.')
    return None


def _page_url(dataset_id: Optional[str], url: str) -> Optional[str]:
    if '/sdo/detail' in (url or ''):
        return url
    if dataset_id:
        return f'{BASE_URL}/sdo/detail?id={dataset_id}'
    return url or None


def _publisher() -> Dict[str, Any]:
    return {
        'names': [
            {'lang': 'zh', 'name': PUBLISHER_ZH},
            {'lang': 'en', 'name': PUBLISHER_EN},
        ],
        'identifiers': None,
    }


def _person_agent(name: str, email: Optional[str] = None) -> Dict[str, Any]:
    return {
        'type': 'Person',
        'person': {
            'names': [{'lang': 'zh', 'name': name}],
            'identifiers': None,
            'emails': [email] if email else None,
            'affiliations': None,
        },
    }


def _organization_agent(name: Optional[str], contribution_type: Optional[str] = None) -> Dict[str, Any]:
    return {
        'type': 'Organize',
        'contribution_type': contribution_type,
        'affiliation': {
            'names': [{'lang': 'zh', 'name': _first_non_empty(name, PUBLISHER_ZH)}],
            'identifiers': None,
        },
    }


def _creators(creator_text: Optional[str], email: Optional[str] = None) -> list[Dict[str, Any]]:
    creators = [_person_agent(name, email if index == 0 else None) for index, name in enumerate(_split_terms(creator_text))]
    return creators or [_organization_agent(PUBLISHER_ZH)]


def _contributors(contributor_text: Optional[str], organization: Optional[str]) -> Optional[list[Dict[str, Any]]]:
    contributors: list[Dict[str, Any]] = []
    for name in _split_terms(contributor_text):
        contributors.append(_person_agent(name))
    if organization:
        contributors.append(_organization_agent(organization, 'HostingInstitution'))
    return contributors or None


def _list_or_text(value: Any) -> Optional[str]:
    if isinstance(value, list):
        return '；'.join(_unique_list(value)) or None
    text = _clean_text(value)
    if not text:
        return None
    if text.startswith('[') and text.endswith(']'):
        return '；'.join(_split_terms(text.strip('[]'))) or None
    return text


def _funder(project_text: Optional[str]) -> Optional[list[Dict[str, Optional[str]]]]:
    text = _clean_text(project_text)
    if not text or text == '暂无资助信息':
        return None
    return [{'name': None, 'proj_type': None, 'proj_num': None, 'proj_name': text}]


def _rights(share_method: Optional[str], license_name: Optional[str], protect_time: Optional[Any]) -> Optional[list[Dict[str, Any]]]:
    description = '；'.join(_unique_list([
        share_method,
        license_name,
        f'保护期（月）：{protect_time}' if _clean_text(protect_time) is not None else None,
    ])) or None
    if not description:
        return None
    return [{
        'license_type': None,
        'license': license_name,
        'type': share_method,
        'description': description,
        'cert_num': None,
    }]


def _related_identifiers(values: Dict[str, Any]) -> Optional[list[Dict[str, Any]]]:
    related: list[Dict[str, Any]] = []
    paper_doi = _extract_doi(values.get('paperDOI'))
    if paper_doi:
        related.append({
            'relation': 'IsReferencedBy',
            'type': 'DOI',
            'identifier': {'type': 'DOI', 'identifier': paper_doi},
        })
    return related or None


def _dataset_author(creator_text: Optional[str], email: Optional[str], contributor_text: Optional[str]) -> Optional[Dict[str, Any]]:
    names = _split_terms(creator_text)
    if not names:
        return None
    return {
        '作者姓名': names,
        '工作单位': None,
        '电子邮箱': email,
        '工作贡献': '数据生产、整理与发布',
        '作者简介': '；'.join(_split_terms(contributor_text)) or None,
    }


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').strip().lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()
    return bool(
        'nesdc.org.cn/sdo/detail' in normalized_url
        or 'nesdc.org.cn/sdo/visitsdo' in normalized_url
        or (
            '国家生态数据中心资源共享服务平台' in combined
            and ('/sdo/visitsdo' in combined or 'sdoid' in combined)
        )
        or (
            '"sdo"' in combined
            and '"datasetdesc"' in combined
            and ('"customconfigurationdata"' in combined or '"creator"' in combined)
        )
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[MetadataDict]:
    if not content and not url:
        return None

    data = _parse_json(content or '')
    dataset_id = _extract_dataset_id(url, content or '')
    if not data and dataset_id:
        data = _fetch_visit_data(dataset_id)
    if not isinstance(data, dict):
        return None

    if 'map' in data and 'sdo' not in data:
        return None

    dataset_id = _first_non_empty(data.get('id'), dataset_id, data.get('sdo', {}).get('id') if isinstance(data.get('sdo'), dict) else None)
    custom_values = _custom_value_map(data)
    meta_values = _meta_value_map(_fetch_meta_data(dataset_id)) if dataset_id and not custom_values else {}
    values = {**meta_values, **custom_values}

    page_url = _page_url(dataset_id, url)
    api_url = f'{BASE_URL}/sdo/visitSdo?id={dataset_id}' if dataset_id else None
    title_zh = _first_non_empty(_value(values, data, 'dataSetTitle'), data.get('title'), title)
    title_en = _clean_text(_value(values, data, 'dataSetTitleEn'))
    description = _first_non_empty(_value(values, data, 'dataSetDesc'), data.get('desc'))
    creator_text = _first_non_empty(_value(values, data, 'creator'), data.get('creator'))
    contributor_text = _clean_text(_value(values, data, 'contributor'))
    email = _clean_text(_value(values, data, 'email'))
    cstr_identifier = _extract_cstr(_value(values, data, 'cstr'), data.get('quote'))
    doi = _extract_doi(_value(values, data, 'doi'), data.get('quote'))
    publish_date = _first_non_empty(_value(values, data, 'publishDate'), data.get('time'))
    version = _clean_text(_value(values, data, 'version'))
    keywords = _split_terms(_value(values, data, 'keyword'), data.get('tags'))
    subjects = _unique_list([
        *_split_terms(_value(values, data, 'catalogId')),
        *_split_terms(_value(values, data, 'tag')),
        _value(values, data, 'dataSource'),
        _value(values, data, 'ecosystemType'),
        _value(values, data, 'ecosystemElements'),
    ])
    share_method = _first_non_empty(_value(values, data, 'shareMethod'), data.get('condition'), data.get('sdo', {}).get('sharePermission') if isinstance(data.get('sdo'), dict) else None)
    license_name = 'CC BY-NC 4.0'
    protect_time = _value(values, data, 'protectTime')
    funders = _funder(_first_non_empty(_value(values, data, 'projectFundInfo'), _value(values, data, 'projectFundString')))
    storage_format = _list_or_text(_value(values, data, 'storageFormat'))
    storage_type = _list_or_text(_value(values, data, 'storageType'))
    data_size = _first_non_empty(_value(values, data, 'totalMemorySize'), data.get('mSize'), data.get('toMemorySize'))
    if data_size and data_size.replace('.', '', 1).isdigit():
        data_size = f'{data_size}MB'
    citation = _clean_text(_value(values, data, 'citation'))
    dataset_citation = None
    if creator_text and title_zh and doi and cstr_identifier:
        dataset_citation = f'{creator_text}. {title_zh}[DS/OL]. {PUBLISHER_ZH}, {publish_date[:4] if publish_date else ""}. https://doi.org/{doi}. https://cstr.cn/{cstr_identifier}.'

    title_values = [{'lang': 'zh', 'name': title_zh}] if title_zh else []
    if title_en:
        title_values.append({'lang': 'en', 'name': title_en})
    description_values = [{'lang': 'zh', 'description': description}] if description else None
    keyword_values = [{'lang': 'zh', 'keyword': keywords}] if keywords else None
    urls = _unique_list([page_url, api_url])
    rights = _rights(share_method, license_name, protect_time)

    core_zh: Dict[str, Any] = {
        'titles': title_values or None,
        'identifier': cstr_identifier,
        'creators': _creators(creator_text, email),
        'publisher': _publisher(),
        'publish_date': publish_date,
        'descriptions': description_values,
        'keywords': keyword_values,
        'subjects': [{'standard_gbt': subjects or None, 'standard_oecd': None}] if subjects else None,
        'language': '中文',
        'contributors': _contributors(contributor_text, _first_non_empty(_value(values, data, 'createdByOrganization'), _value(values, data, 'publishOrganization'))),
        'alternative_identifiers': [{'type': 'DOI', 'identifier': doi}] if doi else None,
        'related_identifiers': _related_identifiers(values),
        'rights': rights,
        'funders': funders,
        'version': version,
        'urls': urls or None,
        'resource_type': 'Dataset',
    }

    zh: Dict[str, Any] = {
        '核心元数据': {'metadatas': [core_zh]},
        '数据集基本信息': {
            '标识符': cstr_identifier or doi or dataset_id,
            '标题': title_values or None,
            '摘要': description,
            '关键词': keyword_values,
            '范围': {
                '时间范围': _clean_text(_value(values, data, 'temporalCoverage')),
                '空间范围': {
                    '地理范围描述': _clean_text(_value(values, data, 'spatialCoverage')),
                    '空间分辨率': _clean_text(_value(values, data, 'spatialResolution')),
                },
            },
            '语种': '中文',
            '文件内容': '；'.join(_unique_list([_value(values, data, 'dataSource'), _value(values, data, 'tag'), storage_type])) or None,
            '基金项目': funders,
            '数据量': data_size,
            '数据格式': storage_format,
            '数据集作者': _dataset_author(creator_text, email, contributor_text),
        },
        '数据集出版信息': {
            '发布日期': publish_date,
            '出版期刊': _clean_text(_value(values, data, 'paperJournal')),
            '版本信息': version,
        },
        '数据集服务信息': {
            '数据集引用格式': dataset_citation or citation,
            '数据集共享许可协议': license_name,
            '数据集使用声明': '；'.join(_unique_list([share_method, citation])) or None,
            '数据集下载地址': None,
            '数据论文访问地址': page_url,
        },
    }

    en: Dict[str, Any] = {
        'Core Metadata': {'metadatas': [{
            **core_zh,
            'titles': [{'lang': 'en', 'name': title_en}] if title_en else None,
            'descriptions': None,
            'keywords': None,
            'publisher': {'names': [{'lang': 'en', 'name': PUBLISHER_EN}], 'identifiers': None},
            'language': 'Chinese',
        }]},
        'Dataset Basic Information': {
            'Identifier': cstr_identifier or doi or dataset_id,
            'Title': title_en,
            'Abstract': None,
            'Keywords': None,
            'Coverage': {
                'Time Range': _clean_text(_value(values, data, 'temporalCoverage')),
                'Spatial Range': _clean_text(_value(values, data, 'spatialCoverage')),
            },
            'Language': 'Chinese',
            'File Content': '；'.join(_unique_list([_value(values, data, 'dataSource'), _value(values, data, 'tag'), storage_type])) or None,
            'Project/Funder': funders,
            'Data Size': data_size,
            'Data Format': storage_format,
            'Dataset Authors': _dataset_author(creator_text, email, contributor_text),
        },
        'Dataset Publication Information': {
            'Publication Date': publish_date,
            'Journal': _clean_text(_value(values, data, 'paperJournal')),
            'Version Information': version,
        },
        'Dataset Service Information': {
            'Dataset Citation Format': dataset_citation or citation,
            'Dataset License': license_name,
            'Dataset Usage Statement': '；'.join(_unique_list([share_method, citation])) or None,
            'Dataset Download URL': None,
            'Dataset Paper URL': page_url,
        },
    }

    return {'zh': zh, 'en': en}
