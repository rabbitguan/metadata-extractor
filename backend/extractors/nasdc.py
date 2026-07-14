from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Dict, Iterable, Optional
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .base import MetadataDict


RULE_NAME = 'NASDC Metadata Detail'

PUBLISHER_ZH = '国家农业科学数据中心'
PUBLISHER_EN = 'National Data Center for Agricultural Sciences'
API_URL = 'https://www.agridata.cn/api/DataBaseManageService.asmx/GetSubjectDbInfoByID'
DETAIL_URL_TEMPLATE = 'https://www.agridata.cn/data.html#/datadetail?id={id}'
RESOURCE_BASE = 'https://www.agridata.cn/api/File'

API_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/125.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json,text/plain,*/*',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Platform': 'front',
    'Referer': 'https://www.agridata.cn/data.html',
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


def _parse_query(url: str) -> Dict[str, str]:
    if not url:
        return {}

    parsed = urlparse(url)
    query_text = parsed.query
    if parsed.fragment and '?' in parsed.fragment:
        query_text = parsed.fragment.split('?', 1)[1]

    result: Dict[str, str] = {}
    for key, values in parse_qs(query_text).items():
        for value in values:
            cleaned = _clean_text(unquote(value))
            if cleaned:
                result[key] = cleaned
                break
    return result


def _is_nasdc_detail_url(url: str) -> bool:
    normalized = (url or '').strip().lower()
    return 'agridata.cn/data.html' in normalized and 'datadetail' in normalized


def _format_date(value: Optional[Any]) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    match = re.match(r'^(\d{4})/(\d{1,2})/(\d{1,2})', text)
    if match:
        return f'{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}'
    return text


def _extract_cstr(value: Optional[Any]) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    match = re.search(r'CSTR\s*[:：]\s*([A-Z0-9]{5}\.\d{2}\.[-._;()/:A-Z0-9]+)', text, flags=re.IGNORECASE)
    if match:
        return match.group(1).rstrip('.,;。；')
    match = re.search(r'\b[A-Z0-9]{5}\.\d{2}\.[-._;()/:A-Z0-9]+\b', text, flags=re.IGNORECASE)
    if match:
        return match.group(0).rstrip('.,;。；')
    return None


def _extract_doi(value: Optional[Any]) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    match = re.search(r'10\.\d{4,9}/[^\s<>"\']+', text)
    if match:
        return match.group(0).rstrip('.,;。；')
    return None


def _parse_jsonish(value: Optional[Any]) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def _load_result_data(payload: Any) -> Optional[Any]:
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return None

    if isinstance(payload, dict) and 'resultData' in payload:
        return _load_result_data(payload.get('resultData'))
    return payload


def _extract_payload_dict(content: str) -> Optional[Dict[str, Any]]:
    payload = _load_result_data(content)
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return payload[0]
    if isinstance(payload, dict) and ('DataBaseName' in payload or 'Identification' in payload):
        return payload
    return None


def _fetch_detail_data(url: str) -> Optional[Dict[str, Any]]:
    dataset_id = _parse_query(url).get('id')
    if not dataset_id:
        return None

    try:
        response = requests.post(
            API_URL,
            data={'ID': dataset_id, 'loginUserId': ''},
            headers=API_HEADERS,
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as error:
        print(f"[WARNING] NASDC detail API failed for id={dataset_id}: {error}")
        return None

    data = _load_result_data(payload)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return data if isinstance(data, dict) else None


def _parse_class_names(value: Optional[Any]) -> list[str]:
    classes: list[str] = []
    for segment in str(value or '').split('-'):
        if ':' in segment:
            _, name = segment.split(':', 1)
        else:
            name = segment
        cleaned = _clean_text(name)
        if cleaned:
            classes.append(cleaned)
    return _unique_list(classes)


def _parse_people(value: Any, fallback: Optional[str] = None) -> list[str]:
    parsed = _parse_jsonish(value)
    names: list[str] = []
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict):
                names.extend(_split_terms(item.get('name')))
            else:
                names.extend(_split_terms(item))
    elif parsed:
        names.extend(_split_terms(parsed))
    if fallback:
        names.extend(_split_terms(fallback))
    return _unique_list(names)


def _absolute_resource_url(value: Optional[Any]) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    if text.startswith(('http://', 'https://')):
        return text
    return urljoin(RESOURCE_BASE + '/', text.lstrip('/'))


def _download_urls(data: Dict[str, Any]) -> list[str]:
    urls = []
    for item in _split_terms(str(data.get('DianCangLink') or '').replace('?', ',')):
        urls.append(_absolute_resource_url(item))
    for item in _split_terms(data.get('Link')):
        urls.append(_absolute_resource_url(item))
    return [item for item in _unique_list(urls) if item]


def _attachment_names(data: Dict[str, Any]) -> list[str]:
    parsed = _parse_jsonish(data.get('DataFJ'))
    names: list[str] = []
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict):
                names.append(item.get('name') or item.get('fileName'))
            else:
                names.append(item)
    return _unique_list(names)


def _payload_from_data(data: Dict[str, Any], url: str, title: str) -> MetadataDict:
    dataset_id = _first_non_empty(data.get('Identification'), data.get('ID'), _parse_query(url).get('id'))
    resource_url = url or (DETAIL_URL_TEMPLATE.format(id=dataset_id) if dataset_id else None)
    title_zh = _first_non_empty(data.get('DataBaseName'), title, f'{PUBLISHER_ZH}数据集 {dataset_id}' if dataset_id else None)
    title_en = _first_non_empty(_english_text(data.get('EnglishName')), title_zh)
    description = _first_non_empty(data.get('DataIntroduce'), data.get('DataSummary'))
    keywords = _unique_list(_split_terms(data.get('Antistop')))
    class_names = _parse_class_names(data.get('ClassName'))

    cstr_identifier = _extract_cstr(data.get('SciIdentification'))
    dataset_doi = _extract_doi(data.get('DataBaseDOI'))
    paper_doi = _extract_doi(data.get('PaperDOI'))
    identifier = cstr_identifier or dataset_doi or dataset_id
    other_id = data.get('OtherID')
    alternative_identifiers = _unique_list([
        dataset_doi,
        _extract_doi(other_id),
        _extract_cstr(other_id),
    ])
    related_identifiers = [
        {
            'relation': 'RelatedPaper',
            'type': 'DOI',
            'identifier': {'type': 'DOI', 'identifier': paper_doi},
        }
    ] if paper_doi else None

    authors = _parse_people(data.get('DataPropertyRight'), data.get('Author'))
    producer = _first_non_empty(data.get('Producer'), data.get('PropertyRightUnit'), data.get('Origin'))
    creators = authors or (_split_terms(producer) if producer else None)
    publisher = PUBLISHER_ZH
    publish_date = _format_date(data.get('IssueTime') or data.get('UpdateTime') or data.get('BuildTime'))
    build_time = _format_date(data.get('BuildTime'))
    update_time = _format_date(data.get('UpdateTime'))
    data_time = _first_non_empty(data.get('DataTime'))
    rights = _first_non_empty(data.get('UseInstruction'), data.get('DataShareName'))
    citation = _first_non_empty(data.get('ReferStandard'), data.get('CitationFormat'))
    thanks = _first_non_empty(data.get('ThankWay'))
    download_urls = _download_urls(data)
    attachment_names = _attachment_names(data)
    file_content = attachment_names or ([url.rsplit('/', 1)[-1] for url in download_urls] if download_urls else None)

    english_keywords = [_english_text(item) for item in keywords]
    english_keywords = [item for item in english_keywords if item]
    if not english_keywords:
        english_keywords = keywords

    zh: Dict[str, Any] = {
        '资源类型判定': '数据集',
        '领域判定': '数据集元数据',
        '标识符': identifier,
        'CSTR标识符': cstr_identifier,
        '资源名称': title_zh,
        '标题': title_zh,
        '创建者': creators,
        '发布机构': publisher,
        '发布日期': publish_date,
        '描述': description,
        '关键词': keywords or None,
        '学科分类': class_names or None,
        '语言': _first_non_empty(data.get('Languages'), '中文'),
        '贡献者': [producer] if producer and producer not in (creators or []) else None,
        '替代标识符': alternative_identifiers or None,
        '关联标识符': related_identifiers,
        '权限': rights,
        '资助者': _first_non_empty(data.get('ProjectName'), data.get('ProjectResource')),
        '版本': _first_non_empty(data.get('Version'), data.get('VersionInfo')),
        '资源链接': resource_url,
        '资源类型': '数据集',
        '数据集基本信息': {
            '标识符': identifier,
            '标题': title_zh,
            '摘要': description,
            '关键词': keywords or None,
            '范围': {
                '时间范围': data_time,
                '空间范围': _first_non_empty(data.get('Area')),
            },
            '语种': _first_non_empty(data.get('Languages'), '中文'),
            '文件内容': file_content,
            '基金项目': _first_non_empty(data.get('ProjectName'), data.get('ProjectCode')),
            '数据量': _first_non_empty(data.get('DataSize')),
            '数据格式': _first_non_empty(data.get('DataFormat')),
            '数据集作者': {
                '作者姓名': creators,
                '工作单位': _first_non_empty(data.get('Unit'), data.get('Organization'), data.get('PropertyRightUnit')),
                '电子邮箱': None,
                '工作贡献': None,
                '作者简介': None,
            },
        },
        '数据集出版信息': {
            '发布日期': publish_date,
            '出版期刊': _first_non_empty(data.get('Resource')),
            '版本信息': _first_non_empty(data.get('VersionInfo'), data.get('Version')),
        },
        '数据集服务信息': {
            '数据集引用格式': citation,
            '数据集共享许可协议': rights,
            '数据集使用声明': _first_non_empty(data.get('DataShareName')),
            '数据集下载地址': download_urls or None,
            '数据集访问地址': resource_url,
        },
        '扩展信息': {
            '英文名称': data.get('EnglishName'),
            '数据来源': data.get('Origin'),
            '科技资源标识': data.get('SciIdentification'),
            '论文DOI': paper_doi,
            '论文链接': data.get('PaperLink'),
            '数据类型': data.get('DataTypeName'),
            '数据记录数': data.get('RecordNO'),
            '数据访问量': data.get('Pv'),
            '数据下载量': data.get('Sv'),
            '数据引用量': data.get('CitationNum'),
            '最新更新日期': update_time,
            '数据创建时间': build_time,
            '联系人': data.get('LinkMan'),
            '电话': data.get('Phone'),
            '地址': data.get('Address'),
            '产权单位': data.get('PropertyRightUnit'),
            '收录证书编号': data.get('Code'),
            '收录证书': _absolute_resource_url(data.get('URL')),
            '数据使用协议链接': data.get('UseLink'),
            '致谢': thanks,
        },
    }

    en: Dict[str, Any] = {
        'Resource Type Classification': 'Dataset',
        'Domain Classification': 'Dataset Metadata',
        'Identifier': identifier,
        'CSTR Identifier': cstr_identifier,
        'Resource Name': title_en,
        'Title': title_en,
        'Creators': creators,
        'Publisher': PUBLISHER_EN,
        'Publication Date': publish_date,
        'Description': _english_text(description),
        'Keywords': english_keywords or None,
        'Discipline Classification': None,
        'Language': 'Chinese',
        'Contributors': None,
        'Alternative Identifiers': alternative_identifiers or None,
        'Related Identifiers': related_identifiers,
        'Rights': rights,
        'Funders': _english_text(data.get('ProjectName')) or data.get('ProjectCode'),
        'Version': _first_non_empty(data.get('Version'), data.get('VersionInfo')),
        'Resource URL': resource_url,
        'ResourceType': 'Dataset',
        'Dataset Basic Information': {
            'Identifier': identifier,
            'Title': title_en,
            'Abstract': _english_text(description),
            'Keywords': english_keywords or None,
            'Coverage': {
                'Time Range': data_time,
                'Spatial Range': _first_non_empty(data.get('Area')),
            },
            'Language': 'Chinese',
            'File Content': file_content,
            'Project/Funder': _english_text(data.get('ProjectName')) or data.get('ProjectCode'),
            'Data Size': _first_non_empty(data.get('DataSize')),
            'Data Format': _first_non_empty(data.get('DataFormat')),
            'Dataset Authors': {
                'Author Name': creators,
                'Affiliation': _english_text(data.get('Unit')) or PUBLISHER_EN,
                'Email': None,
                'Contribution': None,
                'Biography': None,
            },
        },
        'Dataset Publication Information': {
            'Publication Date': publish_date,
            'Journal': _english_text(data.get('Resource')),
            'Version Information': _first_non_empty(data.get('VersionInfo'), data.get('Version')),
        },
        'Dataset Service Information': {
            'Dataset Citation Format': _english_text(citation),
            'Dataset License': rights,
            'Dataset Usage Statement': _english_text(data.get('DataShareName')),
            'Dataset Download URL': download_urls or None,
            'Dataset Access URL': resource_url,
        },
        'Extension Info': {
            'Chinese Title': title_zh,
            'Source': _english_text(data.get('Origin')),
            'Science Resource Identifier': data.get('SciIdentification'),
            'Paper DOI': paper_doi,
            'Paper Link': data.get('PaperLink'),
            'Data Type': _english_text(data.get('DataTypeName')),
            'Record Count': data.get('RecordNO'),
            'Page Views': data.get('Pv'),
            'Download Count': data.get('Sv'),
            'Citation Count': data.get('CitationNum'),
            'Updated At': update_time,
            'Created At': build_time,
            'Contact': _english_text(data.get('LinkMan')),
            'Phone': data.get('Phone'),
            'Address': _english_text(data.get('Address')),
            'Rights Holder': _english_text(data.get('PropertyRightUnit')),
            'Certificate Number': data.get('Code'),
            'Certificate URL': _absolute_resource_url(data.get('URL')),
            'Use Agreement URL': data.get('UseLink'),
            'Acknowledgement': _english_text(thanks),
        },
    }

    return {'zh': zh, 'en': en}


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').strip().lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()
    if normalized_url:
        if _is_nasdc_detail_url(url) or 'agridata.cn/api/databasemanageservice.asmx/getsubjectdbinfobyid' in normalized_url:
            return True
        if 'agridata.cn' not in normalized_url:
            return False
    return bool(
        '国家农业科学数据中心' in combined
        and ('databasename' in combined or '数据基本信息' in combined)
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[MetadataDict]:
    data = _fetch_detail_data(url) if _is_nasdc_detail_url(url) else None
    if not data:
        data = _extract_payload_dict(content or '')
    if not data:
        return None

    return _payload_from_data(data, url, title)
