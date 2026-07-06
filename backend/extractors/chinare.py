from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Dict, Iterable, Optional
from urllib.parse import parse_qs, urlparse

import requests

from .base import MetadataDict


RULE_NAME = 'CHINARE Dataset Detail'

BASE_URL = 'https://datacenter.chinare.org.cn'
PUBLISHER_ZH = '国家极地科学数据中心'
PUBLISHER_EN = 'National Arctic and Antarctic Data Center'
CSTR_PATTERN = re.compile(r'\b(?:CSTR\s*[:：]\s*)?([A-Z0-9]{5}\.\d{2}\.[-._;()/:A-Z0-9]+)\b', re.IGNORECASE)
DOI_PATTERN = re.compile(r'\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b')
UUID_PATTERN = re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.I)
API_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json,text/plain,*/*',
    'Referer': f'{BASE_URL}/data-center/metadata',
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


def _split_terms(*values: Any) -> list[str]:
    terms: list[str] = []
    for value in values:
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


def _extract_detail_id(url: str, content: str = '') -> Optional[str]:
    parsed = urlparse(url or '')
    query_id = parse_qs(parsed.query).get('id')
    if query_id:
        cleaned = _clean_text(query_id[0])
        if cleaned and UUID_PATTERN.fullmatch(cleaned):
            return cleaned

    match = re.search(r'/api/dif/([0-9a-f-]{36})', parsed.path, re.I)
    if match and UUID_PATTERN.fullmatch(match.group(1)):
        return match.group(1)

    match = UUID_PATTERN.search(content or '')
    return match.group(0) if match else None


def _fetch_api_data(detail_id: str) -> Optional[Dict[str, Any]]:
    if not detail_id:
        return None
    response = requests.get(f'{BASE_URL}/api/dif/{detail_id}', headers=API_HEADERS, timeout=15)
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, dict) else None


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


def _page_url(detail_id: Optional[str], url: str) -> Optional[str]:
    if '/data-center/metadata' in (url or ''):
        return url
    if detail_id:
        return f'{BASE_URL}/data-center/metadata?id={detail_id}'
    return url or None


def _title_values(data: Dict[str, Any]) -> Optional[list[Dict[str, str]]]:
    values = []
    zh_title = _clean_text(data.get('entry_title'))
    en_title = _clean_text(data.get('entry_title_en'))
    if zh_title:
        values.append({'lang': 'zh', 'name': zh_title})
    if en_title:
        values.append({'lang': 'en', 'name': en_title})
    return values or None


def _description_values(data: Dict[str, Any]) -> Optional[list[Dict[str, str]]]:
    values = []
    zh_desc = _clean_text(data.get('summary'))
    en_desc = _clean_text(data.get('summary_en'))
    if zh_desc:
        values.append({'lang': 'zh', 'description': zh_desc})
    if en_desc:
        values.append({'lang': 'en', 'description': en_desc})
    return values or None


def _keyword_values(data: Dict[str, Any]) -> Optional[list[Dict[str, list[str]]]]:
    values = []
    zh_keywords = _split_terms(data.get('keyword_other'), data.get('keyword_place'))
    en_keywords = _split_terms(data.get('keyword_other_en'), data.get('keyword_place_en'))
    if zh_keywords:
        values.append({'lang': 'zh', 'keyword': zh_keywords})
    if en_keywords:
        values.append({'lang': 'en', 'keyword': en_keywords})
    return values or None


def _publisher() -> Dict[str, Any]:
    return {
        'names': [
            {'lang': 'zh', 'name': PUBLISHER_ZH},
            {'lang': 'en', 'name': PUBLISHER_EN},
        ],
        'identifiers': None,
    }


def _organization_agent(name: Optional[str], organization: Optional[str] = None) -> Dict[str, Any]:
    display_name = _first_non_empty(name, organization, PUBLISHER_ZH)
    affiliation_name = _first_non_empty(organization, name, PUBLISHER_ZH)
    return {
        'type': 'Organize',
        'affiliation': {
            'names': [{'lang': 'zh', 'name': affiliation_name}],
            'identifiers': None,
            'emails': None,
        },
        'person': None,
        'names': [{'lang': 'zh', 'name': display_name}],
    }


def _creators(data: Dict[str, Any]) -> list[Dict[str, Any]]:
    authors = data.get('authors') if isinstance(data.get('authors'), list) else []
    creators: list[Dict[str, Any]] = []
    for author in authors:
        if not isinstance(author, dict):
            continue
        name = _clean_text(author.get('name'))
        organization = _clean_text(author.get('organization'))
        if name or organization:
            creators.append(_organization_agent(name, organization))
    if creators:
        return creators
    return [_organization_agent(data.get('data_author_org'), PUBLISHER_ZH)]


def _contributors(data: Dict[str, Any]) -> Optional[list[Dict[str, Any]]]:
    contributors: list[Dict[str, Any]] = []
    distributor = _clean_text(data.get('data_distributor'))
    if distributor:
        contributors.append({
            'type': 'Organize',
            'contribution_type': 'Distributor',
            'affiliation': {
                'names': [{'lang': 'zh', 'name': distributor}],
                'identifiers': None,
            },
        })
    org = _clean_text(data.get('data_author_org'))
    if org and org != distributor:
        contributors.append({
            'type': 'Organize',
            'contribution_type': 'HostingInstitution',
            'affiliation': {
                'names': [{'lang': 'zh', 'name': org}],
                'identifiers': None,
            },
        })
    return contributors or None


def _spatial_range(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    values = {
        '地理范围描述': _first_non_empty(data.get('sites_name'), data.get('survey_station'), data.get('keyword_place')),
        '西部边界经度': _clean_text(data.get('longitude_west')),
        '东部边界经度': _clean_text(data.get('longitude_east')),
        '南部边界纬度': _clean_text(data.get('latitude_south')),
        '北部边界纬度': _clean_text(data.get('latitude_north')),
        '最小高度': _clean_text(data.get('sample_min_height')),
        '最大高度': _clean_text(data.get('sample_max_height')),
    }
    return {key: value for key, value in values.items() if value} or None


def _time_range(data: Dict[str, Any]) -> Optional[Dict[str, str]]:
    values = {
        '开始时间': _clean_text(data.get('survey_start_date')),
        '结束时间': _clean_text(data.get('survey_end_date')),
    }
    return {key: value for key, value in values.items() if value} or None


def _file_content(data: Dict[str, Any]) -> Optional[str]:
    return '；'.join(_unique_list([
        data.get('team_name'),
        data.get('sites_name'),
        data.get('survey_platform'),
        data.get('survey_project'),
        data.get('survey_station'),
        data.get('survey_method'),
        data.get('survey_instrument'),
        data.get('survey_factor'),
        data.get('quality_information'),
        data.get('normative_reference'),
    ])) or None


def _funders(data: Dict[str, Any]) -> Optional[list[Dict[str, Optional[str]]]]:
    items: list[Dict[str, Optional[str]]] = []
    funding_project = _clean_text(data.get('funding_project'))
    survey_project = _clean_text(data.get('survey_project'))
    project_code = _clean_text(data.get('project_code'))
    project_manager = _clean_text(data.get('project_manager'))
    if funding_project:
        items.append({'name': None, 'proj_type': None, 'proj_num': None, 'proj_name': funding_project})
    if survey_project or project_code or project_manager:
        items.append({
            'name': project_manager,
            'proj_type': '科学考察项目',
            'proj_num': project_code,
            'proj_name': survey_project,
        })
    return items or None


def _rights(data: Dict[str, Any]) -> Optional[list[Dict[str, Any]]]:
    share_method = _clean_text(data.get('share_method'))
    agreement = _clean_text(data.get('use_agreement'))
    protection = _clean_text(data.get('data_protection_period'))
    description = '；'.join(_unique_list([share_method, agreement, protection])) or None
    if not description:
        return None
    return [{
        'license_type': None,
        'license': agreement,
        'type': share_method,
        'description': description,
        'cert_num': None,
    }]


def _dataset_author(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    authors = data.get('authors') if isinstance(data.get('authors'), list) else []
    names = _unique_list(author.get('name') for author in authors if isinstance(author, dict))
    organizations = _unique_list(author.get('organization') for author in authors if isinstance(author, dict))
    if not names and not organizations:
        organizations = _unique_list([data.get('data_author_org'), data.get('data_distributor')])
    if not names and not organizations:
        return None
    return {
        '作者姓名': names or organizations,
        '工作单位': '；'.join(organizations) or _clean_text(data.get('data_author_org')),
        '电子邮箱': None,
        '工作贡献': '数据集建设、发布与服务',
        '作者简介': None,
    }


def _alternative_identifiers(doi: Optional[str]) -> Optional[list[Dict[str, str]]]:
    return [{'type': 'DOI', 'identifier': doi}] if doi else None


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').strip().lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()
    return bool(
        'datacenter.chinare.org.cn/data-center/metadata' in normalized_url
        or 'datacenter.chinare.org.cn/api/dif/' in normalized_url
        or (
            '中国极地业务服务平台' in combined
            and ('/api/dif/' in combined or 'data-center/metadata' in combined)
        )
        or (
            '"entry_title"' in combined
            and '"dif_id"' in combined
            and ('"doi_code"' in combined or '"cstr"' in combined)
        )
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[MetadataDict]:
    if not content and not url:
        return None

    data = _parse_json(content or '')
    detail_id = _extract_detail_id(url, content or '')
    if not data and detail_id:
        data = _fetch_api_data(detail_id)
    if not isinstance(data, dict):
        return None

    detail_id = _first_non_empty(data.get('id'), detail_id, data.get('dif_id'))
    page_url = _page_url(detail_id, url)
    api_url = f'{BASE_URL}/api/dif/{detail_id}' if detail_id else None
    cstr_identifier = _extract_cstr(data.get('CSTR'), data.get('cstr'))
    doi = _extract_doi(data.get('doi_code'), data.get('data_citation'), data.get('references_en'), data.get('references'))
    publish_date = (_clean_text(data.get('publish_date')) or '')[:10] or None
    title_values = _title_values(data) or ([{'lang': 'zh', 'name': _clean_text(title)}] if _clean_text(title) else None)
    description_values = _description_values(data)
    keyword_values = _keyword_values(data)
    zh_subjects = _unique_list([
        data.get('thematic_category'),
        data.get('subjects_name'),
        data.get('iso'),
        data.get('keyword_place'),
    ])
    en_subjects = _unique_list([
        data.get('thematic_category_en'),
        data.get('keyword_place_en'),
    ])
    language = _first_non_empty(data.get('meta_data_language'), '中文；英文' if data.get('entry_title_en') else '中文')
    rights = _rights(data)
    funders = _funders(data)
    urls = _unique_list([page_url, api_url])
    citation = _first_non_empty(data.get('data_citation'), data.get('citation_format'), data.get('references'), data.get('references_en'))
    data_amount = '；'.join(_unique_list([data.get('filesize_name'), data.get('filesize')])) or None
    data_format = _clean_text(data.get('format'))
    domain_identifier = cstr_identifier or doi or detail_id

    core_zh: Dict[str, Any] = {
        'titles': title_values,
        'identifier': cstr_identifier,
        'creators': _creators(data),
        'publisher': _publisher(),
        'publish_date': publish_date,
        'descriptions': description_values,
        'keywords': keyword_values,
        'subjects': [{'standard_gbt': zh_subjects or None, 'standard_oecd': en_subjects or None}] if zh_subjects or en_subjects else None,
        'language': language,
        'contributors': _contributors(data),
        'alternative_identifiers': _alternative_identifiers(doi),
        'related_identifiers': None,
        'rights': rights,
        'funders': funders,
        'version': None,
        'urls': urls or None,
        'resource_type': 'Dataset',
    }

    zh: Dict[str, Any] = {
        '核心元数据': {'metadatas': [core_zh]},
        '数据集基本信息': {
            '标识符': domain_identifier,
            '标题': title_values,
            '摘要': _first_non_empty(data.get('summary'), data.get('summary_en')),
            '关键词': keyword_values,
            '范围': {
                '时间范围': _time_range(data),
                '空间范围': _spatial_range(data),
            },
            '语种': language,
            '文件内容': _file_content(data),
            '基金项目': funders,
            '数据量': data_amount,
            '数据格式': data_format,
            '数据集作者': _dataset_author(data),
        },
        '数据集出版信息': {
            '发布日期': publish_date,
            '出版期刊': None,
            '版本信息': None,
        },
        '数据集服务信息': {
            '数据集引用格式': citation,
            '数据集共享许可协议': _clean_text(data.get('use_agreement')),
            '数据集使用声明': '；'.join(_unique_list([data.get('share_method'), data.get('use_agreement'), data.get('data_protection_period')])) or None,
            '数据集下载地址': None,
            '数据论文访问地址': page_url,
        },
    }

    en: Dict[str, Any] = {
        'Core Metadata': {'metadatas': [{
            **core_zh,
            'titles': [{'lang': 'en', 'name': data.get('entry_title_en')}] if _clean_text(data.get('entry_title_en')) else None,
            'descriptions': [{'lang': 'en', 'description': data.get('summary_en')}] if _clean_text(data.get('summary_en')) else None,
            'keywords': [{'lang': 'en', 'keyword': _split_terms(data.get('keyword_other_en'), data.get('keyword_place_en'))}] if _split_terms(data.get('keyword_other_en'), data.get('keyword_place_en')) else None,
            'publisher': {'names': [{'lang': 'en', 'name': PUBLISHER_EN}], 'identifiers': None},
        }]},
        'Dataset Basic Information': {
            'Identifier': domain_identifier,
            'Title': _clean_text(data.get('entry_title_en')),
            'Abstract': _clean_text(data.get('summary_en')),
            'Keywords': _split_terms(data.get('keyword_other_en'), data.get('keyword_place_en')) or None,
            'Coverage': {
                'Time Range': _time_range(data),
                'Spatial Range': _spatial_range(data),
            },
            'Language': language,
            'File Content': _file_content(data),
            'Project/Funder': funders,
            'Data Size': data_amount,
            'Data Format': data_format,
            'Dataset Authors': _dataset_author(data),
        },
        'Dataset Publication Information': {
            'Publication Date': publish_date,
            'Journal': None,
            'Version Information': None,
        },
        'Dataset Service Information': {
            'Dataset Citation Format': citation,
            'Dataset License': _clean_text(data.get('use_agreement')),
            'Dataset Usage Statement': '；'.join(_unique_list([data.get('share_method'), data.get('use_agreement'), data.get('data_protection_period')])) or None,
            'Dataset Download URL': None,
            'Dataset Paper URL': page_url,
        },
    }

    return {'zh': zh, 'en': en}
