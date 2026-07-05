from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .base import MetadataDict


RULE_NAME = 'CNCB Database Detail'

BASE_URL = 'https://www.cncb.ac.cn'
PUBLISHER_ZH = '国家生物信息中心'
PUBLISHER_EN = 'China National Center for Bioinformation'
CSTR_PATTERN = re.compile(r'\b(?:CSTR:)?(\d{5}\.\d{2}\.[A-Za-z0-9][A-Za-z0-9._-]*(?:\.[A-Za-z0-9][A-Za-z0-9._-]*)+)\b')
API_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json,text/plain,*/*',
    'Referer': f'{BASE_URL}/resources',
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


def _strip_html(value: Optional[Any]) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    soup = BeautifulSoup(text, 'html.parser')
    return _clean_text(soup.get_text(' ', strip=True))


def _parse_json(content: str) -> Optional[Dict[str, Any]]:
    text = (content or '').strip()
    if not text.startswith('{'):
        return None
    try:
        data = json.loads(text)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _extract_resource_id(url: str, content: str = '') -> Optional[str]:
    parsed_path = urlparse(url or '').path
    match = re.search(r'/resource/detail/id/(\d+)', parsed_path)
    if match:
        return match.group(1)

    match = re.search(r'/api/biodb/(\d+)', parsed_path)
    if match:
        return match.group(1)

    match = re.search(r'\blet\s+dbId\s*=\s*(\d+)\s*;', content or '')
    if match:
        return match.group(1)

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


def _fetch_api_data(resource_id: str) -> Optional[Dict[str, Any]]:
    if not resource_id:
        return None
    response = requests.get(f'{BASE_URL}/api/biodb/{resource_id}', headers=API_HEADERS, timeout=15)
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, dict) else None


def _category_terms(data: Dict[str, Any], key: str) -> list[str]:
    terms: list[str] = []
    for category in data.get('dbCategories') or []:
        if isinstance(category, dict):
            terms.append(category.get(key))
    return _unique_list(terms)


def _org_names(data: Dict[str, Any]) -> tuple[str, str]:
    organization = data.get('organization') if isinstance(data.get('organization'), dict) else {}
    zh_name = _first_non_empty(
        data.get('dbInstitution'),
        organization.get('name'),
        PUBLISHER_ZH,
    ) or PUBLISHER_ZH
    en_name = _first_non_empty(
        organization.get('enName'),
        PUBLISHER_EN,
    ) or PUBLISHER_EN
    return zh_name, en_name


def _title_values(data: Dict[str, Any]) -> list[Dict[str, str]]:
    values: list[Dict[str, str]] = []
    zh_title = _first_non_empty(data.get('dbZhTitle'), data.get('dbName'))
    en_title = _first_non_empty(data.get('dbEnTitle'), data.get('dbName'))
    if zh_title:
        values.append({'lang': 'zh', 'name': zh_title})
    if en_title and en_title != zh_title:
        values.append({'lang': 'en', 'name': en_title})
    return values


def _description_values(data: Dict[str, Any]) -> list[Dict[str, str]]:
    values: list[Dict[str, str]] = []
    zh_description = _strip_html(data.get('dbZhDescription'))
    en_description = _strip_html(data.get('dbEnDescription'))
    if zh_description:
        values.append({'lang': 'zh', 'description': zh_description})
    if en_description and en_description != zh_description:
        values.append({'lang': 'en', 'description': en_description})
    return values


def _keyword_values(data: Dict[str, Any]) -> list[Dict[str, list[str]]]:
    zh_terms = _unique_list([
        data.get('dbZhTitle'),
        data.get('dbName'),
        data.get('dbType', {}).get('zhName') if isinstance(data.get('dbType'), dict) else None,
        *_category_terms(data, 'zhName'),
    ])
    en_terms = _unique_list([
        data.get('dbEnTitle'),
        data.get('dbName'),
        data.get('dbType', {}).get('enName') if isinstance(data.get('dbType'), dict) else None,
        *_category_terms(data, 'enName'),
    ])
    values: list[Dict[str, list[str]]] = []
    if zh_terms:
        values.append({'lang': 'zh', 'keyword': zh_terms})
    if en_terms:
        values.append({'lang': 'en', 'keyword': en_terms})
    return values


def _subjects(data: Dict[str, Any]) -> Optional[list[Dict[str, Optional[list[str]]]]]:
    zh_categories = _category_terms(data, 'zhName')
    en_categories = _category_terms(data, 'enName')
    if not zh_categories and not en_categories:
        return None
    return [{'standard_gbt': zh_categories or None, 'standard_oecd': en_categories or None}]


def _contact_agent(data: Dict[str, Any], zh_org: str, en_org: str) -> Dict[str, Any]:
    contact = _first_non_empty(data.get('dbContact'), data.get('dbMaintainer'), data.get('maintainer'))
    email = _first_non_empty(data.get('dbContactEmail'), data.get('dbEmail'), data.get('email'))
    if contact:
        return {
            'type': 'Person',
            'person': {
                'names': [{'lang': 'en', 'name': contact}],
                'emails': [email] if email else None,
                'identifiers': None,
                'affiliations': [{
                    'names': [
                        {'lang': 'zh', 'name': zh_org},
                        {'lang': 'en', 'name': en_org},
                    ],
                    'identifiers': None,
                }],
            },
        }
    return {
        'type': 'Organize',
        'affiliation': {
            'names': [
                {'lang': 'zh', 'name': zh_org},
                {'lang': 'en', 'name': en_org},
            ],
            'identifiers': None,
        },
    }


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').strip().lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()
    return bool(
        'cncb.ac.cn/resource/detail/id/' in normalized_url
        or 'cncb.ac.cn/api/biodb/' in normalized_url
        or (
            'database detail - 国家生物信息中心' in combined
            and '/api/biodb/' in combined
            and 'db-description' in combined
        )
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[MetadataDict]:
    api_data = _parse_json(content or '')
    if not api_data:
        resource_id = _extract_resource_id(url, content or '')
        if not resource_id:
            return None
        api_data = _fetch_api_data(resource_id)
    if not api_data:
        return None

    resource_id = str(api_data.get('id') or _extract_resource_id(url, content or '') or '')
    page_url = url if 'resource/detail/id/' in (url or '') else f'{BASE_URL}/resource/detail/id/{resource_id}'
    access_url = _first_non_empty(api_data.get('dbUrl'), page_url)
    db_name = _clean_text(api_data.get('dbName'))
    accession = _first_non_empty(api_data.get('dbcAccession'), api_data.get('dbAccession'), api_data.get('accession'))
    cstr_identifier = _extract_cstr(accession, db_name, access_url, page_url)
    domain_identifier = cstr_identifier or accession or resource_id or db_name

    zh_org, en_org = _org_names(api_data)
    department = _first_non_empty(api_data.get('dbDepartment'), (api_data.get('organization') or {}).get('department') if isinstance(api_data.get('organization'), dict) else None)
    release_date = _first_non_empty(api_data.get('dbReleaseDate'), api_data.get('releaseDate'))
    version = _clean_text(api_data.get('dbVersion'))
    db_type = api_data.get('dbType') if isinstance(api_data.get('dbType'), dict) else {}
    type_zh = _clean_text(db_type.get('zhName'))
    type_en = _clean_text(db_type.get('enName'))
    zh_categories = _category_terms(api_data, 'zhName')
    en_categories = _category_terms(api_data, 'enName')
    titles = _title_values(api_data)
    descriptions = _description_values(api_data)
    keywords = _keyword_values(api_data)
    subjects = _subjects(api_data)
    contact_agent = _contact_agent(api_data, zh_org, en_org)
    contact_name = _first_non_empty(api_data.get('dbContact'), api_data.get('dbMaintainer'), api_data.get('maintainer'))
    contact_email = _first_non_empty(api_data.get('dbContactEmail'), api_data.get('dbEmail'), api_data.get('email'))
    search_url = f'{BASE_URL}/search/specific?q=&dbId={api_data.get("sid")}' if api_data.get('sid') else None

    core_zh: Dict[str, Any] = {
        'titles': titles or None,
        'identifier': cstr_identifier,
        'creators': [{
            'type': 'Organize',
            'affiliation': {
                'names': [
                    {'lang': 'zh', 'name': zh_org},
                    {'lang': 'en', 'name': en_org},
                ],
                'identifiers': None,
            },
        }],
        'publisher': {
            'names': [
                {'lang': 'zh', 'name': PUBLISHER_ZH},
                {'lang': 'en', 'name': PUBLISHER_EN},
            ],
            'identifiers': None,
        },
        'publish_date': release_date,
        'descriptions': descriptions or None,
        'keywords': keywords or None,
        'subjects': subjects,
        'language': 'zh; en',
        'contributors': [contact_agent],
        'alternative_identifiers': None,
        'related_identifiers': None,
        'rights': None,
        'funders': None,
        'version': version,
        'urls': _unique_list([page_url, access_url, search_url]) or None,
        'resource_type': 'Dataset',
    }

    dataset_author = {
        '作者姓名': [contact_name] if contact_name else [zh_org],
        '工作单位': '；'.join(_unique_list([zh_org, department])),
        '电子邮箱': contact_email,
        '工作贡献': '数据库维护与数据服务' if contact_name else None,
        '作者简介': None,
    }

    zh: Dict[str, Any] = {
        '核心元数据': {'metadatas': [core_zh]},
        '数据集基本信息': {
            '标识符': domain_identifier,
            '标题': titles or None,
            '摘要': descriptions or None,
            '关键词': keywords or None,
            '范围': {
                '时间范围': None,
                '空间范围': None,
            },
            '语种': '中文；英文',
            '文件内容': '；'.join(_unique_list([
                db_name,
                type_zh,
                type_en,
                *zh_categories,
                *en_categories,
            ])) or None,
            '基金项目': None,
            '数据量': None,
            '数据格式': '数据库',
            '数据集作者': dataset_author,
        },
        '数据集出版信息': {
            '发布日期': release_date,
            '出版期刊': None,
            '版本信息': version,
        },
        '数据集服务信息': {
            '数据集引用格式': None,
            '数据集共享许可协议': None,
            '数据集使用声明': None,
            '数据集下载地址': access_url,
            '数据论文访问地址': page_url,
        },
    }

    core_en: Dict[str, Any] = {
        'titles': [{'lang': 'en', 'name': item['name']} for item in titles if item.get('lang') == 'en'] or None,
        'identifier': cstr_identifier,
        'creators': [{
            'type': 'Organize',
            'affiliation': {
                'names': [{'lang': 'en', 'name': en_org}],
                'identifiers': None,
            },
        }],
        'publisher': {
            'names': [{'lang': 'en', 'name': PUBLISHER_EN}],
            'identifiers': None,
        },
        'publish_date': release_date,
        'descriptions': [{'lang': 'en', 'description': item['description']} for item in descriptions if item.get('lang') == 'en'] or None,
        'keywords': [{'lang': 'en', 'keyword': item['keyword']} for item in keywords if item.get('lang') == 'en'] or None,
        'subjects': [{'standard_gbt': None, 'standard_oecd': en_categories}] if en_categories else None,
        'language': 'zh; en',
        'contributors': [contact_agent],
        'alternative_identifiers': None,
        'related_identifiers': None,
        'rights': None,
        'funders': None,
        'version': version,
        'urls': _unique_list([page_url, access_url, search_url]) or None,
        'resource_type': 'Dataset',
    }

    en: Dict[str, Any] = {
        'Core Metadata': {'metadatas': [core_en]},
        'Dataset Basic Information': {
            'Identifier': domain_identifier,
            'Title': titles or None,
            'Abstract': descriptions or None,
            'Keywords': keywords or None,
            'Coverage': {
                'Time Range': None,
                'Spatial Range': None,
            },
            'Language': 'Chinese; English',
            'File Content': '；'.join(_unique_list([
                db_name,
                type_en,
                *en_categories,
            ])) or None,
            'Project/Funder': None,
            'Data Size': None,
            'Data Format': 'Database',
            'Dataset Authors': {
                'Author Name': [contact_name] if contact_name else [en_org],
                'Affiliation': en_org,
                'Email': contact_email,
                'Contribution': 'Database maintenance and data service' if contact_name else None,
                'Biography': None,
            },
        },
        'Dataset Publication Information': {
            'Publication Date': release_date,
            'Journal': None,
            'Version Information': version,
        },
        'Dataset Service Information': {
            'Dataset Citation Format': None,
            'Dataset License': None,
            'Dataset Usage Statement': None,
            'Dataset Download URL': access_url,
            'Dataset Paper URL': page_url,
        },
    }

    return {'zh': zh, 'en': en}
