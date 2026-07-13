from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from html import unescape
from typing import Any, Dict, Iterable, Optional
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from .base import MetadataDict


RULE_NAME = 'GEODATA Science Detail'

PUBLISHER_ZH = '国家地球系统科学数据中心'
PUBLISHER_EN = 'National Earth System Science Data Center'
CITATION_ZH = '国家地球系统科学数据中心(https://www.geodata.cn)'
CITATION_EN = 'National Earth System Science Data Center(https://www.geodata.cn)'
API_URL = 'https://www.geodata.cn/ManagerDev/comprehensive/api/scidata/entry/info'
CSTR_PATTERN = re.compile(r'(?:CSTR\s*[:：]\s*)?([A-Z0-9]{5}\.\d{2}\.[-._;()/:A-Z0-9]+)', re.IGNORECASE)

API_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/125.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json,text/plain,*/*',
    'Referer': 'https://www.geodata.cn/',
}


def _clean_text(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value))
    if '<' in text and '>' in text:
        text = BeautifulSoup(text, 'html.parser').get_text(' ', strip=True)
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


def _geodata_guid_from_url(url: str) -> Optional[str]:
    query = _parse_query(url)
    return query.get('guid') or query.get('dataguid')


def _is_geodata_detail_url(url: str) -> bool:
    normalized_url = (url or '').strip().lower()
    return bool(
        'geodata.cn/main/face_science_detail' in normalized_url
        or ('geodata.cn/data/datadetails.html' in normalized_url and _geodata_guid_from_url(url))
    )


def _is_geodata_api_url(url: str) -> bool:
    normalized_url = (url or '').strip().lower()
    return 'geodata.cn/managerdev/comprehensive/api/scidata/entry/info' in normalized_url


def _format_date(value: Optional[Any]) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    iso_text = re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', text.replace('Z', '+00:00'))
    try:
        parsed = datetime.fromisoformat(iso_text)
    except ValueError:
        parsed = None
    if parsed is not None and parsed.tzinfo is not None:
        return parsed.astimezone(timezone(timedelta(hours=8))).date().isoformat()
    match = re.match(r'^(\d{4})-(\d{2})-(\d{2})', text)
    if match:
        return f'{match.group(1)}-{match.group(2)}-{match.group(3)}'
    return text


def _iter_values(value: Any) -> Iterable[Any]:
    if isinstance(value, dict):
        for item in value.values():
            yield from _iter_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_values(item)
    else:
        yield value


def _extract_cstr(*values: Optional[Any]) -> Optional[str]:
    for value in values:
        for item in _iter_values(value):
            text = _clean_text(item)
            if not text:
                continue
            match = CSTR_PATTERN.search(text)
            if match:
                return f"CSTR:{match.group(1).rstrip('.,;，；')}"
    return None


def _format_size(value: Optional[Any]) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    try:
        size = float(text)
    except ValueError:
        return text
    if size <= 0:
        return text
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    return f'{size:.2f}{units[index]}'


def _file_names(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    return _unique_list(item.get('fileName') for item in items if isinstance(item, dict))


def _load_json_payload(content: str) -> Optional[Any]:
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for match in re.finditer(r'[\{\[]', content):
            try:
                payload, _ = decoder.raw_decode(content[match.start():])
                if isinstance(payload, (dict, list)):
                    return payload
            except json.JSONDecodeError:
                continue
    return None


def _load_data(payload: Any) -> Optional[Dict[str, Any]]:
    if isinstance(payload, str):
        payload = _load_json_payload(payload)
    if isinstance(payload, dict) and isinstance(payload.get('data'), dict):
        return payload['data']
    if isinstance(payload, dict) and ('title' in payload or 'guid' in payload):
        return payload
    return None


def _fetch_detail_data(url: str) -> Optional[Dict[str, Any]]:
    guid = _geodata_guid_from_url(url)
    if not guid:
        return None

    try:
        response = requests.get(
            API_URL,
            params={'guid': guid},
            headers={**API_HEADERS, 'Referer': url or API_HEADERS['Referer']},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as error:
        print(f"[WARNING] GEODATA detail API failed for guid={guid}: {error}")
        return None

    return _load_data(payload)


def _resource_url(url: str, guid: Optional[str]) -> Optional[str]:
    if _is_geodata_detail_url(url):
        return url
    if guid:
        return f'https://www.geodata.cn/main/face_science_detail?typeName=face_science&guid={guid}'
    return url or None


def _payload_from_data(data: Dict[str, Any], url: str, title: str) -> MetadataDict:
    guid = _first_non_empty(data.get('guid'), _geodata_guid_from_url(url))
    doi = _first_non_empty(data.get('doi'))
    cstr_identifier = _extract_cstr(
        data.get('cstr'),
        data.get('cstrId'),
        data.get('cstrIdentifier'),
        data.get('sciIdentification'),
        data,
    )
    identifier = cstr_identifier or doi or guid
    title_zh = _first_non_empty(data.get('title'), title, f'{PUBLISHER_ZH}数据集 {guid}' if guid else None)
    keywords = _unique_list(_split_terms(data.get('keywords')))
    description = _first_non_empty(data.get('description'))
    publish_date = _format_date(data.get('updatedTime') or data.get('createdTime'))
    created_date = _format_date(data.get('createdTime'))
    data_size = _format_size(data.get('fileSize'))
    entity_files = _file_names(data.get('entityData'))
    profile_files = _file_names(data.get('profileData'))
    file_content = entity_files + profile_files
    data_format = _unique_list(name.rsplit('.', 1)[-1] for name in file_content if '.' in name)
    authors = _unique_list([data.get('ownerName')])
    owner_org = _first_non_empty(data.get('ownerOrganization'), data.get('organizationName'))
    resource_url = _resource_url(url, guid)
    rights = '开放共享' if data.get('isOpened') is True else None
    time_range = _first_non_empty(data.get('dataTimeDescription'))
    if not time_range:
        start_time = _format_date(data.get('dataStartTime'))
        end_time = _format_date(data.get('dataEndTime'))
        time_range = f'{start_time} - {end_time}' if start_time and end_time else start_time or end_time

    zh: Dict[str, Any] = {
        '资源类型判定': '数据集',
        '领域判定': '数据集元数据',
        '标识符': identifier,
        'CSTR标识符': cstr_identifier,
        '资源名称': title_zh,
        '标题': title_zh,
        '创建者': authors or ([owner_org] if owner_org else None),
        '发布机构': PUBLISHER_ZH,
        '发布日期': publish_date,
        '描述': description,
        '关键词': keywords or None,
        '学科分类': _first_non_empty(data.get('disciplineName'), data.get('disciplineCode')),
        '语言': '中文',
        '贡献者': [data.get('organizationName')] if _clean_text(data.get('organizationName')) else None,
        '替代标识符': [{'type': 'DOI', 'identifier': doi}] if doi else ([{'type': 'GUID', 'identifier': guid}] if guid else None),
        '关联标识符': None,
        '权限': rights,
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
                '空间范围': _first_non_empty(data.get('placeName')),
            },
            '语种': '中文',
            '文件内容': file_content or None,
            '基金项目': None,
            '数据量': data_size,
            '数据格式': data_format or None,
            '数据集作者': {
                '作者姓名': authors or None,
                '工作单位': owner_org,
                '电子邮箱': _first_non_empty(data.get('ownerEmail'), data.get('contactEmail')),
                '工作贡献': None,
                '作者简介': None,
            },
        },
        '数据集出版信息': {
            '发布日期': publish_date,
            '出版期刊': None,
            '版本信息': None,
        },
        '数据集服务信息': {
            '数据集引用格式': CITATION_ZH,
            '数据集共享许可协议': rights,
            '数据集使用声明': _first_non_empty(data.get('ownerStatement')),
            '数据集下载地址': resource_url,
            '数据集访问地址': resource_url,
        },
        '扩展信息': {
            'GUID': guid,
            'DOI': doi,
            '数据来源': data.get('descDatasource'),
            '数据产生或加工方法': data.get('descMethod'),
            '数据空间投影': data.get('descProj') or data.get('descProjection'),
            '数据质量说明': data.get('descQuality'),
            '学科代码': data.get('disciplineCode'),
            '联系人': data.get('contactPerson'),
            '联系电话': data.get('contactTel'),
            '联系邮箱': data.get('contactEmail'),
            '联系地址': data.get('organizationAddr'),
            '邮政编码': data.get('organizationPostcode'),
            '浏览量': data.get('pvHits'),
            '独立访客量': data.get('uvHits'),
            '创建日期': created_date,
            '同步更新时间': _format_date(data.get('syncUpdatedTime')),
            '数据文件数量': len(entity_files) if entity_files else None,
            '文档文件数量': len(profile_files) if profile_files else None,
        },
    }

    en: Dict[str, Any] = {
        'Resource Type Classification': 'Dataset',
        'Domain Classification': 'Dataset Metadata',
        'Identifier': identifier,
        'CSTR Identifier': cstr_identifier,
        'Resource Name': title_zh,
        'Title': title_zh,
        'Creators': authors or None,
        'Publisher': PUBLISHER_EN,
        'Publication Date': publish_date,
        'Description': None,
        'Keywords': None,
        'Discipline Classification': _english_text(data.get('disciplineName')),
        'Language': 'Chinese',
        'Contributors': None,
        'Alternative Identifiers': [{'type': 'DOI', 'identifier': doi}] if doi else None,
        'Related Identifiers': None,
        'Rights': rights,
        'Funders': None,
        'Version': None,
        'Resource URL': resource_url,
        'ResourceType': 'Dataset',
        'Dataset Basic Information': {
            'Identifier': identifier,
            'Title': title_zh,
            'Abstract': None,
            'Keywords': None,
            'Coverage': {
                'Time Range': time_range,
                'Spatial Range': _english_text(data.get('placeName')),
            },
            'Language': 'Chinese',
            'File Content': file_content or None,
            'Project/Funder': None,
            'Data Size': data_size,
            'Data Format': data_format or None,
            'Dataset Authors': {
                'Author Name': authors or None,
                'Affiliation': _english_text(owner_org),
                'Email': _first_non_empty(data.get('ownerEmail'), data.get('contactEmail')),
                'Contribution': None,
                'Biography': None,
            },
        },
        'Dataset Publication Information': {
            'Publication Date': publish_date,
            'Journal': None,
            'Version Information': None,
        },
        'Dataset Service Information': {
            'Dataset Citation Format': CITATION_EN,
            'Dataset License': rights,
            'Dataset Usage Statement': _english_text(data.get('ownerStatement')),
            'Dataset Download URL': resource_url,
            'Dataset Access URL': resource_url,
        },
        'Extension Info': {
            'Chinese Title': title_zh,
            'GUID': guid,
            'DOI': doi,
            'Data Source': _english_text(data.get('descDatasource')),
            'Data Production or Processing Method': _english_text(data.get('descMethod')),
            'Spatial Projection': _english_text(data.get('descProj') or data.get('descProjection')),
            'Quality Description': _english_text(data.get('descQuality')),
            'Discipline Code': data.get('disciplineCode'),
            'Contact Person': _english_text(data.get('contactPerson')),
            'Contact Phone': data.get('contactTel'),
            'Contact Email': data.get('contactEmail'),
            'Views': data.get('pvHits'),
            'Unique Visitors': data.get('uvHits'),
            'Created Date': created_date,
            'Synced Update Date': _format_date(data.get('syncUpdatedTime')),
            'Data File Count': len(entity_files) if entity_files else None,
            'Document File Count': len(profile_files) if profile_files else None,
        },
    }

    return {'zh': zh, 'en': en}


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').strip().lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()
    return bool(
        _is_geodata_detail_url(url)
        or _is_geodata_api_url(url)
        or '国家地球系统科学数据中心' in combined
        and ('face_science_detail' in normalized_url or 'scidata/entry/info' in normalized_url or 'geodata.cn' in normalized_url)
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[MetadataDict]:
    data = _fetch_detail_data(url) if _is_geodata_detail_url(url) else None
    if not data:
        data = _load_data(content or '')
    if not data:
        return None

    return _payload_from_data(data, url, title)
