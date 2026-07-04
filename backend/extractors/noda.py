from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .base import MetadataDict


RULE_NAME = 'NODA Dataset Detail'

BASE_URL = 'https://www.noda.ac.cn'
PUBLISHER_ZH = '国家对地观测科学数据中心'
PUBLISHER_EN = 'National Earth Observation Data Center'
CSTR_PATTERN = re.compile(r'\b(?:CSTR:)?(\d{5}\.\d{1,2}\.[A-Za-z0-9][A-Za-z0-9._-]*(?:\.[A-Za-z0-9][A-Za-z0-9._-]*)+)\b')
DOI_PATTERN = re.compile(r'\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b')
URL_PATTERN = re.compile(r'https?://[^\s,，。；;）)]+')
API_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json,text/javascript,*/*;q=0.01',
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': f'{BASE_URL}/datasharing/search',
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


def _nested(data: Dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _list_values(value: Any) -> list[str]:
    if isinstance(value, list):
        return _unique_list(value)
    return _unique_list([value])


def _extract_dataset_id(url: str, content: str = '') -> Optional[str]:
    match = re.search(r'/datasharing/datasetDetails/([A-Za-z0-9]+)', urlparse(url or '').path)
    if match:
        return match.group(1)

    match = re.search(r'/datasharing/getDataInfo/([A-Za-z0-9]+)', urlparse(url or '').path)
    if match:
        return match.group(1)

    match = re.search(r'\bdatasetId\s*=\s*[\'"]([A-Za-z0-9]+)[\'"]', content or '')
    if match:
        return match.group(1)

    return None


def _parse_json(content: str) -> Optional[Dict[str, Any]]:
    text = (content or '').strip()
    if not text.startswith('{'):
        return None
    try:
        payload = json.loads(text)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    body = payload.get('responseBody')
    return body if isinstance(body, dict) else payload


def _fetch_api_data(dataset_id: str) -> Optional[Dict[str, Any]]:
    if not dataset_id:
        return None
    response = requests.post(
        f'{BASE_URL}/datasharing/getDataInfo/{dataset_id}',
        headers={**API_HEADERS, 'Referer': f'{BASE_URL}/datasharing/datasetDetails/{dataset_id}'},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    body = payload.get('responseBody') if isinstance(payload, dict) else None
    return body if isinstance(body, dict) else None


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


def _extract_urls(*values: Optional[Any]) -> list[str]:
    urls: list[str] = []
    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        urls.extend(URL_PATTERN.findall(text))
    return _unique_list(urls)


def _page_url(dataset_id: Optional[str], url: str) -> Optional[str]:
    if 'datasetDetails' in (url or ''):
        return url
    if dataset_id:
        return f'{BASE_URL}/datasharing/datasetDetails/{dataset_id}'
    return url or None


def _alternative_identifiers(doi: Optional[str]) -> Optional[list[Dict[str, str]]]:
    if not doi:
        return None
    return [{'type': 'DOI', 'identifier': doi}]


def _related_identifiers(items: Any) -> Optional[list[Dict[str, Any]]]:
    related: list[Dict[str, Any]] = []
    if not isinstance(items, list):
        return None
    for item in items:
        if not isinstance(item, dict):
            continue
        identifier = _first_non_empty(item.get('masterId'), item.get('url'))
        title = _first_non_empty(item.get('masterTitle'), item.get('title'))
        if not identifier:
            continue
        doi = _extract_doi(identifier)
        if doi:
            related.append({
                'relation': _first_non_empty(item.get('associationDescription'), 'RelatedResource'),
                'type': 'DOI',
                'identifier': {'type': 'DOI', 'identifier': doi},
            })
        elif identifier.startswith(('http://', 'https://')):
            related.append({
                'relation': _first_non_empty(item.get('associationDescription'), 'RelatedResource'),
                'type': 'URL',
                'identifier': {'type': 'URL', 'identifier': identifier},
            })
        elif title:
            related.append({
                'relation': _first_non_empty(item.get('associationDescription'), 'RelatedResource'),
                'type': 'Other',
                'identifier': {'type': 'Other', 'identifier': title},
            })
    return related or None


def _organization_agent(name: Optional[str], email: Optional[str] = None) -> Dict[str, Any]:
    names = [{'lang': 'en', 'name': name}] if name else [{'lang': 'zh', 'name': PUBLISHER_ZH}, {'lang': 'en', 'name': PUBLISHER_EN}]
    return {
        'type': 'Organize',
        'affiliation': {
            'names': names,
            'identifiers': None,
            'emails': [email] if email else None,
        },
    }


def _contact_agent(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    contributor = data.get('contributor') if isinstance(data.get('contributor'), dict) else {}
    name = _clean_text(contributor.get('fullName'))
    email = _clean_text(contributor.get('email'))
    phone = _clean_text(contributor.get('contributorPhone'))
    unit = _clean_text(contributor.get('contributorUnitName'))
    if not any([name, email, unit]):
        return None
    return {
        'type': 'Person' if name else 'Organize',
        'contribution_type': 'ContactPerson',
        'person': {
            'names': [{'lang': 'en', 'name': name}] if name else None,
            'emails': [email] if email else None,
            'identifiers': None,
            'affiliations': [{
                'names': [{'lang': 'en', 'name': unit}],
                'identifiers': None,
            }] if unit else None,
            'phones': [phone] if phone else None,
        } if name else None,
        'affiliation': {
            'names': [{'lang': 'en', 'name': unit}],
            'identifiers': None,
        } if unit and not name else None,
    }


def _format_spatial_range(spatial: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(spatial, dict):
        return None
    values = {
        '地理范围描述': _clean_text(spatial.get('spatialLocation')),
        '西部边界经度': _clean_text(spatial.get('westLng')),
        '东部边界经度': _clean_text(spatial.get('eastLng')),
        '南部边界纬度': _clean_text(spatial.get('southLat')),
        '北部边界纬度': _clean_text(spatial.get('northLat')),
        '空间参考': _clean_text(spatial.get('projectInfo')),
        '空间分辨率': _clean_text(spatial.get('scale')),
    }
    return {key: value for key, value in values.items() if value} or None


def _funder(source_project: Any) -> Optional[list[Dict[str, Optional[str]]]]:
    if not isinstance(source_project, dict):
        return None
    item = {
        'name': _clean_text(source_project.get('projectOwner')),
        'proj_type': _clean_text(source_project.get('projectDept')),
        'proj_num': _clean_text(source_project.get('projectNo')),
        'proj_name': _clean_text(source_project.get('projectName')),
    }
    return [item] if any(item.values()) else None


def _source_note(data: Dict[str, Any]) -> Optional[str]:
    return '；'.join(_unique_list([
        _nested(data, 'dataSource', 'dataSource'),
        _nested(data, 'dataSource', 'dataProcess'),
        _nested(data, 'dataQuality', 'dataQuality'),
        _nested(data, 'category', 'productType'),
        *_list_values(_nested(data, 'category', 'categoryTheme')),
    ])) or None


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').strip().lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()
    return bool(
        'noda.ac.cn/datasharing/datasetdetails/' in normalized_url
        or 'noda.ac.cn/datasharing/getdatainfo/' in normalized_url
        or (
            '数据发现平台' in combined
            and '/datasharing/getdatainfo/' in combined
            and 'datasetid' in combined
        )
        or (
            '"responsebody"' in combined
            and '"copyRight"'.lower() in combined
            and '"cstr"' in combined
            and '"doi"' in combined
        )
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[MetadataDict]:
    if not content and not url:
        return None

    data = _parse_json(content or '')
    dataset_id = _extract_dataset_id(url, content or '')
    if not data and dataset_id:
        data = _fetch_api_data(dataset_id)
    if not isinstance(data, dict):
        return None

    dataset_id = _clean_text(data.get('id')) or dataset_id
    page_url = _page_url(dataset_id, url)
    title_text = _first_non_empty(data.get('title'), title, dataset_id)
    description = _clean_text(data.get('description'))
    doi = _extract_doi(data.get('doi'), _nested(data, 'copyRight', 'dataReference'))
    cstr_identifier = _extract_cstr(data.get('cstr'))
    publish_date = (_clean_text(data.get('commitDate')) or '')[:10] or None
    language = _first_non_empty(data.get('language'), _nested(data, 'dataFile', 'metaLanguage'), 'English')
    lang_code = 'zh' if language and 'chinese' in language.lower() else 'en'
    keywords = _list_values(data.get('keyword'))
    subjects = _unique_list([
        *_list_values(_nested(data, 'category', 'categorySubject')),
        *_list_values(_nested(data, 'category', 'categoryTheme')),
    ])
    version = _clean_text(_nested(data, 'dataQuality', 'dataVersion'))
    copyright_info = data.get('copyRight') if isinstance(data.get('copyRight'), dict) else {}
    citation = _clean_text(copyright_info.get('dataReference'))
    sharing_mode = _clean_text(copyright_info.get('dataSharingMod'))
    data_level = _clean_text(copyright_info.get('dataLevel'))
    redistribute_area = _clean_text(copyright_info.get('redistributeArea'))
    rights_description = '；'.join(_unique_list([sharing_mode, data_level, redistribute_area, citation])) or None
    source_urls = _extract_urls(citation, _nested(data, 'dataSource', 'dataSource'), data.get('url'), data.get('download'), data.get('ftp'), data.get('offlineFtp'))
    urls = _unique_list([page_url, data.get('url'), data.get('download'), *source_urls])

    org_list = data.get('dataOrganizationList') if isinstance(data.get('dataOrganizationList'), list) else []
    primary_org = next((item for item in org_list if isinstance(item, dict) and _clean_text(item.get('name'))), None)
    creator_name = _first_non_empty(
        primary_org.get('name') if primary_org else None,
        _nested(data, 'contributor', 'contributorUnitName'),
        _nested(data, 'contributor', 'fullName'),
        data.get('commitUser'),
        PUBLISHER_EN if lang_code == 'en' else PUBLISHER_ZH,
    )
    creator_email = _first_non_empty(
        primary_org.get('organizationEmail') if primary_org else None,
        _nested(data, 'contributor', 'email'),
    )
    contact = data.get('contributor') if isinstance(data.get('contributor'), dict) else {}
    author = data.get('dataFile') if isinstance(data.get('dataFile'), dict) else {}
    funders = _funder(data.get('sourceProject'))
    spatial_range = _format_spatial_range(data.get('spatialLocation'))
    time_range = _first_non_empty(_nested(data, 'timeInfo', 'timeRange'), _nested(data, 'dataFile', 'metaCreatedTime'))
    data_formats = _list_values(_nested(data, 'productFormat', 'productFormat'))
    file_count = _first_non_empty(_nested(data, 'dataDistribute', 'fileItemNum'), data.get('attachedFileNumber'))
    file_size = _first_non_empty(_nested(data, 'dataDistribute', 'fileSize'), data.get('attachedFileCapacity'))
    data_amount = '；'.join(_unique_list([file_size, f'{file_count} files' if file_count else None, _nested(data, 'spatialLocation', 'scale')])) or None
    domain_identifier = cstr_identifier or doi or dataset_id
    title_values = [{'lang': lang_code, 'name': title_text}] if title_text else None
    description_values = [{'lang': lang_code, 'description': description}] if description else None
    keyword_values = [{'lang': lang_code, 'keyword': keywords}] if keywords else None
    contact_agent = _contact_agent(data)

    core_zh: Dict[str, Any] = {
        'titles': title_values,
        'identifier': cstr_identifier,
        'creators': [_organization_agent(creator_name, creator_email)],
        'publisher': {
            'names': [
                {'lang': 'zh', 'name': PUBLISHER_ZH},
                {'lang': 'en', 'name': PUBLISHER_EN},
            ],
            'identifiers': None,
        },
        'publish_date': publish_date,
        'descriptions': description_values,
        'keywords': keyword_values,
        'subjects': [{'standard_gbt': subjects or None, 'standard_oecd': None}] if subjects else None,
        'language': language,
        'contributors': [contact_agent] if contact_agent else None,
        'alternative_identifiers': _alternative_identifiers(doi),
        'related_identifiers': _related_identifiers(data.get('associatedInformationList')),
        'rights': [{
            'license_type': None,
            'license': redistribute_area,
            'type': data_level,
            'description': rights_description,
            'cert_num': None,
        }] if rights_description else None,
        'funders': funders,
        'version': version,
        'urls': urls or None,
        'resource_type': 'Dataset',
    }

    dataset_author = {
        '作者姓名': [_first_non_empty(author.get('author'), contact.get('fullName'), creator_name)],
        '工作单位': _first_non_empty(contact.get('contributorUnitName'), creator_name),
        '电子邮箱': _first_non_empty(author.get('authorEmail'), contact.get('email'), creator_email),
        '工作贡献': '数据集建设、发布与服务',
        '作者简介': None,
    }
    zh: Dict[str, Any] = {
        '核心元数据': {'metadatas': [core_zh]},
        '数据集基本信息': {
            '标识符': domain_identifier,
            '标题': title_values,
            '摘要': description,
            '关键词': keyword_values,
            '范围': {
                '时间范围': time_range,
                '空间范围': spatial_range,
            },
            '语种': language,
            '文件内容': _source_note(data),
            '基金项目': funders,
            '数据量': data_amount,
            '数据格式': '；'.join(data_formats) or None,
            '数据集作者': dataset_author,
        },
        '数据集出版信息': {
            '发布日期': publish_date,
            '出版期刊': None,
            '版本信息': version,
        },
        '数据集服务信息': {
            '数据集引用格式': citation,
            '数据集共享许可协议': redistribute_area,
            '数据集使用声明': rights_description,
            '数据集下载地址': '；'.join(_unique_list([data.get('download'), data.get('ftp'), data.get('offlineFtp'), *source_urls])) or None,
            '数据论文访问地址': page_url,
        },
    }

    core_en: Dict[str, Any] = {
        'titles': title_values if lang_code == 'en' else None,
        'identifier': cstr_identifier,
        'creators': [_organization_agent(creator_name, creator_email)],
        'publisher': {
            'names': [{'lang': 'en', 'name': PUBLISHER_EN}],
            'identifiers': None,
        },
        'publish_date': publish_date,
        'descriptions': description_values if lang_code == 'en' else None,
        'keywords': keyword_values if lang_code == 'en' else None,
        'subjects': [{'standard_gbt': None, 'standard_oecd': subjects or None}] if subjects else None,
        'language': language,
        'contributors': [contact_agent] if contact_agent else None,
        'alternative_identifiers': _alternative_identifiers(doi),
        'related_identifiers': _related_identifiers(data.get('associatedInformationList')),
        'rights': [{
            'license_type': None,
            'license': redistribute_area,
            'type': data_level,
            'description': rights_description,
            'cert_num': None,
        }] if rights_description else None,
        'funders': funders,
        'version': version,
        'urls': urls or None,
        'resource_type': 'Dataset',
    }
    en: Dict[str, Any] = {
        'Core Metadata': {'metadatas': [core_en]},
        'Dataset Basic Information': {
            'Identifier': domain_identifier,
            'Title': title_values if lang_code == 'en' else None,
            'Abstract': description if lang_code == 'en' else None,
            'Keywords': keyword_values if lang_code == 'en' else None,
            'Coverage': {
                'Time Range': time_range,
                'Spatial Range': spatial_range,
            },
            'Language': language,
            'File Content': _source_note(data),
            'Project/Funder': funders,
            'Data Size': data_amount,
            'Data Format': '；'.join(data_formats) or None,
            'Dataset Authors': {
                'Author Name': [_first_non_empty(author.get('author'), contact.get('fullName'), creator_name)],
                'Affiliation': _first_non_empty(contact.get('contributorUnitName'), creator_name),
                'Email': _first_non_empty(author.get('authorEmail'), contact.get('email'), creator_email),
                'Contribution': 'Dataset construction, publication, and service',
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
            'Dataset License': redistribute_area,
            'Dataset Usage Statement': rights_description,
            'Dataset Download URL': '；'.join(_unique_list([data.get('download'), data.get('ftp'), data.get('offlineFtp'), *source_urls])) or None,
            'Dataset Paper URL': page_url,
        },
    }

    return {'zh': zh, 'en': en}
