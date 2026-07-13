from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlsplit

import requests


RULE_NAME = 'NMDC'

API_URL = 'https://nmdc.cn/api/services/nmdcweb/api/dataset/metadata'
PUBLISHER_ZH = '国家微生物科学数据中心'
PUBLISHER_EN = 'National Microbiology Data Center'


def _clean_text(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value))
    text = re.sub(r'\s+', ' ', text).strip()
    return text or None


def _strip_cstr_prefix(value: Optional[Any]) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    while re.match(r'^CSTR\s*[:：]\s*', text, flags=re.IGNORECASE):
        text = re.sub(r'^CSTR\s*[:：]\s*', '', text, count=1, flags=re.IGNORECASE).strip()
    return text or None


def _split_terms(value: Optional[Any]) -> Optional[list[str]]:
    text = _clean_text(value)
    if not text:
        return None
    items = [item.strip() for item in re.split(r'[;；,，、]\s*', text) if item.strip()]
    return items or None


def _query_id(url: str) -> Optional[str]:
    query = parse_qs(urlsplit(url or '').query)
    return (query.get('id') or [''])[0] or None


def _load_json_payload(content: str) -> Optional[dict]:
    if not content:
        return None
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _extract_data(payload: Optional[dict]) -> Optional[dict]:
    if not isinstance(payload, dict):
        return None
    data = payload.get('data')
    return data if isinstance(data, dict) else payload


def _fetch_metadata(metadata_id: str) -> Optional[dict]:
    response = requests.get(
        API_URL,
        params={'id': metadata_id},
        headers={
            'User-Agent': 'metadata-extractor/1.0 (+https://localhost)',
            'Accept': 'application/json,text/plain,*/*',
        },
        timeout=12,
    )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and str(payload.get('status')) not in {'0', ''}:
        return None
    return _extract_data(payload)


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').lower()
    if 'nmdc.cn/metadata/detail' in normalized_url and _query_id(url):
        return True
    if 'nmdc.cn/api/services/nmdcweb/api/dataset/metadata' in normalized_url:
        return True
    payload = _load_json_payload(content or '')
    data = _extract_data(payload)
    return isinstance(data, dict) and any(key in data for key in ('chineseName', 'englishName', 'cstr', 'doi'))


def extract(content: str, url: str = '', title: str = '') -> Optional[Dict[str, Any]]:
    data = None
    metadata_id = _query_id(url)
    if metadata_id:
        data = _fetch_metadata(metadata_id)
    if data is None:
        data = _extract_data(_load_json_payload(content or ''))
    if not isinstance(data, dict):
        return None

    title_zh = _clean_text(data.get('chineseName') or data.get('name') or title)
    title_en = _clean_text(data.get('englishName'))
    cstr_identifier = _strip_cstr_prefix(data.get('cstr'))
    doi = _clean_text(data.get('doi'))
    identifier = cstr_identifier or _clean_text(data.get('identifier')) or metadata_id
    keywords_zh = _split_terms(data.get('keyword'))
    keywords_en = _split_terms(data.get('enKeyword'))
    if not keywords_en:
        keywords_en = keywords_zh
    description_zh = _clean_text(data.get('description'))
    description_en = _clean_text(data.get('descriptionEn'))
    resource_url = _clean_text(data.get('link')) or url
    release_time = _clean_text(data.get('releaseTime'))
    create_date = _clean_text(data.get('createDate'))
    organization = _clean_text(data.get('organization')) or PUBLISHER_ZH
    subject = _clean_text(data.get('subject'))
    second_subject = _clean_text(data.get('secondSubject'))
    subjects = [item for item in (subject, second_subject) if item] or None
    file_size = _clean_text(data.get('fileSize') or data.get('downloadSize'))
    data_count = _clean_text(data.get('dataCount'))
    file_count = _clean_text(data.get('fileCount'))
    data_format = None
    download_urls = []
    file_contents = []
    for item in data.get('downloadfiles') or []:
        if not isinstance(item, dict):
            continue
        name = _clean_text(item.get('name'))
        fmt = _clean_text(item.get('format'))
        size = _clean_text(item.get('data_size'))
        count = _clean_text(item.get('data_count'))
        if fmt and fmt not in (data_format or []):
            data_format = [*(data_format or []), fmt]
        file_contents.append(' '.join(part for part in (name, fmt, size, count) if part))
    download_url = _clean_text(data.get('downloadUrl'))
    if download_url:
        download_urls.append(download_url)

    alternative_identifiers = []
    if doi:
        alternative_identifiers.append({'type': 'DOI', 'identifier': doi})
    accession = _clean_text(data.get('identifier'))
    if accession and accession != identifier:
        alternative_identifiers.append({'type': 'Other', 'identifier': accession})

    rights = _clean_text(data.get('license') or data.get('accessRestrictions'))
    funders = None
    if any(data.get(key) for key in ('projectName', 'projectType', 'projectNo')):
        funders = [{
            'name': _clean_text(data.get('projectName')),
            'proj_type': _clean_text(data.get('projectType')),
            'proj_num': _clean_text(data.get('projectNo')),
            'proj_name': _clean_text(data.get('projectName')),
        }]

    creators = [organization] if organization else None
    publisher_zh = organization or PUBLISHER_ZH

    return {
        'zh': {
            '资源类型判定': '数据集',
            '领域判定': '数据集元数据',
            '标题': title_zh,
            'CSTR标识符': cstr_identifier,
            '创建者': creators,
            '发布机构': publisher_zh,
            '发布日期': release_time or create_date,
            '描述': description_zh,
            '关键词': keywords_zh,
            '学科': subjects,
            '语言': 'zh',
            '贡献者': None,
            '替代标识符': alternative_identifiers or None,
            '关联标识符': None,
            '权限': rights,
            '资助者': funders,
            '版本': None,
            '资源链接': [resource_url] if resource_url else None,
            '资源类型': '数据集',
            '数据集基本信息': {
                '标识符': identifier,
                '标题': title_zh,
                '摘要': description_zh,
                '关键词': keywords_zh,
                '范围': {
                    '时间范围': None,
                    '空间范围': None,
                },
                '语种': '中文',
                '文件内容': file_contents or None,
                '基金项目': funders,
                '数据量': file_size or data_count,
                '数据格式': data_format,
                '数据集作者': {
                    '作者姓名': creators,
                    '工作单位': [organization] if organization else None,
                    '电子邮箱': _clean_text(data.get('email')),
                    '工作贡献': None,
                    '作者简介': None,
                },
            },
            '数据集出版信息': {
                '发布日期': release_time,
                '出版期刊': None,
                '版本信息': None,
            },
            '数据集服务信息': {
                '数据集引用格式': None,
                '数据集共享许可协议': rights,
                '数据集使用声明': _clean_text(data.get('process')),
                '数据集下载地址': download_urls or ([resource_url] if resource_url else None),
                '数据论文访问地址': None,
            },
        },
        'en': {
            'Resource Type Classification': 'Dataset',
            'Domain Classification': 'Dataset Metadata',
            'Identifier': cstr_identifier,
            'titles': [{'lang': 'en', 'name': title_en}] if title_en else None,
            'creators': [{'type': 'Organizational', 'affiliation': {'names': [{'lang': 'en', 'name': PUBLISHER_EN}], 'identifiers': None}}],
            'publisher': {'names': [{'lang': 'en', 'name': PUBLISHER_EN}], 'identifiers': None},
            'publish_date': release_time or create_date,
            'descriptions': [{'lang': 'en', 'description': description_en}] if description_en else None,
            'keywords': [{'lang': 'en', 'keyword': keywords_en}] if keywords_en else None,
            'subjects': [{'standard_gbt': subjects, 'standard_oecd': None}] if subjects else None,
            'language': 'zh',
            'contributors': None,
            'alternative_identifiers': alternative_identifiers or None,
            'related_identifiers': None,
            'rights': rights,
            'funders': funders,
            'version': None,
            'urls': [resource_url] if resource_url else None,
            'resource_type': 'Dataset',
        },
    }
