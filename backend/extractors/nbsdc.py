from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Dict, Iterable, Optional
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from .base import MetadataDict


RULE_NAME = 'NBSDC Metadata Detail'

PUBLISHER_ZH = '国家基础学科公共科学数据中心'
PUBLISHER_EN = 'National Basic Science Data Center'
API_URL = 'https://www.nbsdc.cn/api/general/searchDataDetail'
DETAIL_URL_TEMPLATE = 'https://www.nbsdc.cn/general/dataDetail?id={id}&type={type}'

API_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/125.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json,text/plain,*/*',
    'Referer': 'https://www.nbsdc.cn/',
}


def _clean_text(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value))
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


def _identifier_item(value: Optional[Any]) -> Optional[Dict[str, str]]:
    text = _clean_text(value)
    if not text:
        return None
    doi_match = re.search(r'10\.\d{4,9}/[^\s<>"\']+', text, flags=re.IGNORECASE)
    if doi_match:
        return {'type': 'DOI', 'identifier': doi_match.group(0).rstrip('.,;。；')}
    cstr_match = re.search(r'(?:CSTR\s*[:：]\s*)?([A-Z0-9]{5}\.\d{2}\.[-._;()/:A-Z0-9]+)', text, flags=re.IGNORECASE)
    if cstr_match:
        return {'type': 'CSTR', 'identifier': cstr_match.group(1).strip().strip('.,;，；')}
    return None


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


def _is_nbsdc_detail_url(url: str) -> bool:
    normalized_url = (url or '').strip().lower()
    return 'nbsdc.cn/general/datadetail' in normalized_url


def _is_nbsdc_api_url(url: str) -> bool:
    normalized_url = (url or '').strip().lower()
    return 'nbsdc.cn/api/general/searchdatadetail' in normalized_url


def _format_date(value: Optional[Any]) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    match = re.match(r'^(\d{4})-(\d{2})-(\d{2})', text)
    if match:
        return f'{match.group(1)}-{match.group(2)}-{match.group(3)}'
    return text


def _extract_id_from_html(content: str) -> Optional[str]:
    if not content:
        return None
    soup = BeautifulSoup(content, 'html.parser')
    node = soup.select_one('#dataId')
    return _clean_text(node.get('value')) if node else None


def _resource_url(url: str, data: Dict[str, Any], dataset_id: Optional[str]) -> Optional[str]:
    if _is_nbsdc_detail_url(url):
        return url
    data_type = _first_non_empty(data.get('dataTypeId'), _parse_query(url).get('type'), '1')
    if dataset_id:
        return DETAIL_URL_TEMPLATE.format(id=dataset_id, type=data_type)
    return url or None


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


def _load_result(payload: Any) -> Optional[Dict[str, Any]]:
    if isinstance(payload, str):
        payload = _load_json_payload(payload)
    if isinstance(payload, dict) and isinstance(payload.get('result'), dict):
        return payload['result']
    if isinstance(payload, dict) and isinstance(payload.get('dataInfoMap'), dict):
        return payload
    return None


def _fetch_detail_data(url: str, content: str = '') -> Optional[Dict[str, Any]]:
    query = _parse_query(url)
    dataset_id = query.get('id') or query.get('dataId') or _extract_id_from_html(content)
    if not dataset_id:
        return None

    try:
        response = requests.get(
            API_URL,
            params={'id': dataset_id},
            headers={**API_HEADERS, 'Referer': url or API_HEADERS['Referer']},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as error:
        print(f"[WARNING] NBSDC detail API failed for id={dataset_id}: {error}")
        return None

    return _load_result(payload)


def _subject_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    subjects: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _clean_text(item.get('subjectName'))
        code = _clean_text(item.get('subjectCode'))
        if name and code and code != '-1':
            subjects.append(f'{code} {name}')
        else:
            subjects.append(name)
    return _unique_list(subjects)


def _people(value: Optional[Any]) -> list[str]:
    return _unique_list(_split_terms(value))


def _org_names(orgs: Any, key: str) -> list[str]:
    if not isinstance(orgs, list):
        return []
    return _unique_list(item.get(key) for item in orgs if isinstance(item, dict))


def _storage_size(storage: Dict[str, Any]) -> Optional[str]:
    capacity = _clean_text(storage.get('storageCapacity'))
    if not capacity:
        return None
    unit = _clean_text(storage.get('storageCapacityUnit'))
    return f'{capacity}{unit}' if unit else capacity


def _license_text(strategy: Dict[str, Any]) -> Optional[str]:
    share_range = _first_non_empty(strategy.get('shareRange'))
    share_channel = _first_non_empty(strategy.get('shareChannel'))
    if share_range and share_channel:
        return f'{share_range}，{share_channel}'
    return share_range or share_channel


def _citation(
    authors: list[str],
    title: Optional[str],
    orgs: list[str],
    update_date: Optional[str],
    cstr_identifier: Optional[str],
) -> Optional[str]:
    if not title:
        return None
    parts = []
    if authors:
        parts.append(f'{",".join(authors)}.')
    parts.append(f'{title}.')
    parts.append('(V1).')
    if orgs:
        parts.append(f'{",".join(orgs)}[创建机构],')
    if update_date:
        parts.append(f'{update_date}.')
    parts.append(f'{PUBLISHER_ZH}[发布机构]')
    if cstr_identifier:
        cstr_url = f'https://cstr.cn/{cstr_identifier.replace("CSTR:", "", 1)}'
        parts.append(f',{cstr_url}')
    return ''.join(parts)


def _payload_from_data(data: Dict[str, Any], url: str, title: str) -> MetadataDict:
    info = data.get('dataInfoMap') if isinstance(data.get('dataInfoMap'), dict) else {}
    identifiers = data.get('dataBaoShiMap') if isinstance(data.get('dataBaoShiMap'), dict) else {}
    strategy = data.get('dataStrategyMap') if isinstance(data.get('dataStrategyMap'), dict) else {}
    storage = data.get('dataStorageSizeMap') if isinstance(data.get('dataStorageSizeMap'), dict) else {}
    statistics = data.get('dataStatisticMap') if isinstance(data.get('dataStatisticMap'), dict) else {}
    authors_map = data.get('authorList') if isinstance(data.get('authorList'), dict) else {}
    file_map = data.get('dataFileMap') if isinstance(data.get('dataFileMap'), dict) else {}
    projects = data.get('projectObj') if isinstance(data.get('projectObj'), list) else []
    relations = data.get('dataRelationMap') if isinstance(data.get('dataRelationMap'), list) else []
    orgs_raw = data.get('dataOrgUnitMap') if isinstance(data.get('dataOrgUnitMap'), list) else []

    dataset_id = _first_non_empty(data.get('id'), _parse_query(url).get('id'))
    title_zh = _first_non_empty(info.get('dataSetCnName'), title, f'{PUBLISHER_ZH}数据集 {dataset_id}' if dataset_id else None)
    title_en = _first_non_empty(_english_text(info.get('dataSetEnName')), title_zh)
    abstract = _first_non_empty(info.get('contentCn'))
    abstract_en = _english_text(info.get('contentEn'))
    keywords = _unique_list(_split_terms(info.get('keywordCn')))
    keywords_en = _unique_list(_split_terms(info.get('keywordEn')))
    if not keywords_en:
        keywords_en = keywords
    subjects = _subject_names(info.get('subject'))
    authors = _people(authors_map.get('authorsCn'))
    authors_en = _people(authors_map.get('authorsEn'))
    orgs = _org_names(orgs_raw, 'orgUnitCn')
    orgs_en = _org_names(orgs_raw, 'orgUnitEn')
    project = projects[0] if projects and isinstance(projects[0], dict) else {}

    cstr_identifier = _first_non_empty(identifiers.get('cstr'))
    doi = _first_non_empty(identifiers.get('doi'))
    data_no = _first_non_empty(identifiers.get('dataNo'))
    identifier = cstr_identifier or doi or data_no or dataset_id
    alternative_identifiers = [item for item in (_identifier_item(doi), _identifier_item(data_no), _identifier_item(dataset_id)) if item]
    resource_url = _resource_url(url, data, dataset_id)
    access_url = _first_non_empty(file_map.get('externalLink'), info.get('url'), resource_url)
    update_date = _format_date(data.get('updateTime'))
    publish_date = _format_date(
        data.get('publishTime')
        or data.get('publishDate')
        or data.get('releaseTime')
        or data.get('releaseDate')
    )
    data_size = _storage_size(storage)
    file_count = _first_non_empty(storage.get('filesNum'))
    record_count = _first_non_empty(storage.get('recordsNum'))
    rights = _license_text(strategy)
    org_email = _first_non_empty(*(item.get('orgUnitEmail') for item in orgs_raw if isinstance(item, dict)))
    author_email = org_email if authors else None
    citation = _citation(authors or orgs, title_zh, orgs if authors else [], publish_date, cstr_identifier)
    related_identifiers = []
    for item in relations:
        if isinstance(item, dict):
            identifier_item = _identifier_item(item.get('dataId') or item.get('id') or item.get('name'))
            if identifier_item:
                related_identifiers.append({
                    'relation': _first_non_empty(item.get('relation'), item.get('type'), 'RelatedResource'),
                    'type': identifier_item['type'],
                    'identifier': identifier_item,
                })

    zh: Dict[str, Any] = {
        '资源类型判定': '数据集',
        '领域判定': '数据集元数据',
        '标识符': identifier,
        'CSTR标识符': cstr_identifier,
        '资源名称': title_zh,
        '标题': title_zh,
        '创建者': authors or orgs or None,
        '发布机构': PUBLISHER_ZH,
        '发布日期': publish_date,
        '描述': abstract,
        '关键词': keywords or None,
        '学科分类': subjects or None,
        '语言': '中文',
        '贡献者': orgs or None,
        '替代标识符': alternative_identifiers or None,
        '关联标识符': related_identifiers or None,
        '权限': rights,
        '资助者': _first_non_empty(project.get('projectCnName'), project.get('projectNumber')),
        '版本': 'V1',
        '资源链接': resource_url,
        '资源类型': '数据集',
        '数据集基本信息': {
            '标识符': identifier,
            '标题': title_zh,
            '摘要': abstract,
            '关键词': keywords or None,
            '范围': {
                '时间范围': None,
                '空间范围': None,
            },
            '语种': '中文',
            '文件内容': f'{file_count}个文件' if file_count else None,
            '基金项目': _first_non_empty(project.get('projectCnName'), project.get('projectNumber')),
            '数据量': data_size,
            '数据格式': _first_non_empty(info.get('dataFormat')),
            '数据集作者': {
                '作者姓名': authors or orgs or None,
                '工作单位': orgs or None,
                '电子邮箱': author_email,
                '工作贡献': None,
                '作者简介': None,
            },
        },
        '数据集出版信息': {
            '发布日期': publish_date,
            '出版期刊': None,
            '版本信息': 'V1',
        },
        '数据集服务信息': {
            '数据集引用格式': citation,
            '数据集共享许可协议': rights,
            '数据集使用声明': strategy.get('reason'),
            '数据集下载地址': access_url,
            '数据集访问地址': resource_url,
        },
        '扩展信息': {
            '英文名称': info.get('dataSetEnName'),
            '英文摘要': info.get('contentEn'),
            '英文关键词': keywords_en or None,
            '数据编号': data_no,
            'DOI': doi,
            '数据生产方法': info.get('dataProduction'),
            '数据中心访问地址': info.get('url'),
            '封面图片': info.get('coverImage'),
            '共享范围': strategy.get('shareRange'),
            '共享渠道': strategy.get('shareChannel'),
            '共享策略类型': strategy.get('strategyType'),
            '许可协议标记': strategy.get('agreement'),
            '文件数量': file_count,
            '记录数量': record_count,
            '浏览量': statistics.get('viewingCount'),
            '下载量': statistics.get('downloadCount'),
            '收藏量': statistics.get('collectionCount'),
            '引用量': statistics.get('quotedCount'),
            '评分': statistics.get('score'),
            '评价数': statistics.get('reviewCount'),
            '项目类型': project.get('projectTypeName'),
            '项目编号': project.get('projectNumber'),
            '项目主管部门': project.get('competentDepart'),
            '最近更新时间': update_date,
            '机构邮箱': org_email,
            '机构地址': _first_non_empty(*(item.get('orgUnitAddress') for item in orgs_raw if isinstance(item, dict))),
            '机构电话': _first_non_empty(*(item.get('orgUnitPhone') for item in orgs_raw if isinstance(item, dict))),
        },
    }

    en: Dict[str, Any] = {
        'Resource Type Classification': 'Dataset',
        'Domain Classification': 'Dataset Metadata',
        'Identifier': identifier,
        'CSTR Identifier': cstr_identifier,
        'Resource Name': title_en,
        'Title': title_en,
        'Creators': authors_en or authors or None,
        'Publisher': PUBLISHER_EN,
        'Publication Date': publish_date,
        'Description': abstract_en,
        'Keywords': keywords_en or None,
        'Discipline Classification': None,
        'Language': 'Chinese',
        'Contributors': orgs_en or None,
        'Alternative Identifiers': alternative_identifiers or None,
        'Related Identifiers': related_identifiers or None,
        'Rights': rights,
        'Funders': _english_text(project.get('projectCnName')) or project.get('projectNumber'),
        'Version': 'V1',
        'Resource URL': resource_url,
        'ResourceType': 'Dataset',
        'Dataset Basic Information': {
            'Identifier': identifier,
            'Title': title_en,
            'Abstract': abstract_en,
            'Keywords': keywords_en or None,
            'Coverage': {
                'Time Range': None,
                'Spatial Range': None,
            },
            'Language': 'Chinese',
            'File Content': f'{file_count} files' if file_count else None,
            'Project/Funder': project.get('projectNumber'),
            'Data Size': data_size,
            'Data Format': _first_non_empty(info.get('dataFormat')),
            'Dataset Authors': {
                'Author Name': authors_en or authors or orgs_en or orgs or None,
                'Affiliation': orgs_en or orgs or None,
                'Email': author_email,
                'Contribution': None,
                'Biography': None,
            },
        },
        'Dataset Publication Information': {
            'Publication Date': publish_date,
            'Journal': None,
            'Version Information': 'V1',
        },
        'Dataset Service Information': {
            'Dataset Citation Format': citation,
            'Dataset License': rights,
            'Dataset Usage Statement': _english_text(strategy.get('reason')),
            'Dataset Download URL': access_url,
            'Dataset Access URL': resource_url,
        },
        'Extension Info': {
            'Chinese Title': title_zh,
            'Chinese Abstract': abstract,
            'Data Number': data_no,
            'DOI': doi,
            'Data Production': _english_text(info.get('dataProduction')),
            'Data Center URL': info.get('url'),
            'Cover Image': info.get('coverImage'),
            'Share Range': rights,
            'File Count': file_count,
            'Record Count': record_count,
            'Views': statistics.get('viewingCount'),
            'Downloads': statistics.get('downloadCount'),
            'Collections': statistics.get('collectionCount'),
            'Citations': statistics.get('quotedCount'),
            'Score': statistics.get('score'),
            'Review Count': statistics.get('reviewCount'),
            'Project Type': _english_text(project.get('projectTypeName')),
            'Project Number': project.get('projectNumber'),
            'Project Department': _english_text(project.get('competentDepart')),
            'Last Updated': update_date,
            'Organization Email': org_email,
            'Organization Address': _english_text(_first_non_empty(*(item.get('orgUnitAddress') for item in orgs_raw if isinstance(item, dict)))),
            'Organization Phone': _first_non_empty(*(item.get('orgUnitPhone') for item in orgs_raw if isinstance(item, dict))),
        },
    }

    return {'zh': zh, 'en': en}


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').strip().lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()
    if normalized_url:
        if _is_nbsdc_detail_url(url) or _is_nbsdc_api_url(url):
            return True
        if 'nbsdc.cn' not in normalized_url:
            return False
    return bool(
        '国家基础学科公共科学数据中心' in combined
        and ('datasetcnname' in combined or 'datainfomap' in combined or 'dataid' in combined)
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[MetadataDict]:
    data = _fetch_detail_data(url, content) if _is_nbsdc_detail_url(url) or content else None
    if not data:
        data = _load_result(content or '')
    if not data:
        return None

    return _payload_from_data(data, url, title)
