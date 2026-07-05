from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Dict, Iterable, Optional
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from .base import MetadataDict


RULE_NAME = 'NMDIS Metadata Detail'

PUBLISHER_ZH = '国家海洋科学数据中心'
PUBLISHER_EN = 'National Marine Data Center'

LABELS = [
    '英文名称',
    '数据时间',
    '共享级别',
    '时效性',
    '更新频率',
    '标识符',
    '学科分类',
    '主题分类',
    '所有者',
    '共享方式',
    '关键字',
    '引用方式',
    '数据集摘要',
    '文件数量',
    '数据量',
    '访问量',
    '下载次数',
    '收藏次数',
]

SHARE_LEVELS = {
    '1': '完全公开',
    '2': '有条件共享',
    '3': '不公开',
}

API_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/125.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json,text/plain,*/*',
    'Referer': 'https://mds.nmdis.org.cn/',
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
    query = parse_qs(urlparse(url).query)
    result: Dict[str, str] = {}
    for key, values in query.items():
        for value in values:
            cleaned = _clean_text(unquote(value))
            if cleaned:
                result[key] = cleaned
                break
    return result


def _is_nmdis_detail_url(url: str) -> bool:
    normalized_url = (url or '').strip().lower()
    return 'mds.nmdis.org.cn/pages/dataviewdetail.html' in normalized_url


def _looks_like_static_vue_template(content: str) -> bool:
    return bool(
        '{{pageParams.' in (content or '')
        or '{{ pageParams.' in (content or '')
        or 'v-cloak' in (content or '')
    )


def _fetch_detail_data(url: str) -> Optional[Dict[str, Any]]:
    query = _parse_query(url)
    dataset_id = query.get('dataSetId') or query.get('datasetId')
    if not dataset_id:
        return None

    try:
        response = requests.get(
            'https://mds.nmdis.org.cn/service/sdm/front/directory/getDirectoryDataSetRelation',
            params={'datasetId': dataset_id},
            headers={**API_HEADERS, 'Referer': url or API_HEADERS['Referer']},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as error:
        print(f"[WARNING] NMDIS detail API failed for datasetId={dataset_id}: {error}")
        return None

    data = payload.get('data') if isinstance(payload, dict) else None
    return data if isinstance(data, dict) and data else None


def _extract_cstr(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    match = re.search(r'\bCSTR\s*[:：]\s*([A-Za-z0-9._-]+)', text, flags=re.IGNORECASE)
    if match:
        return f'CSTR:{match.group(1).rstrip(".,;。；")}'
    match = re.search(r'\b\d{5}\.\d{2}\.[A-Za-z0-9._-]+(?:\.[A-Za-z0-9._-]+)*\b', text)
    if match:
        return match.group(0).rstrip('.,;。；')
    return None


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


def _walk_dicts(value: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk_dicts(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_dicts(item)


def _score_dataset_dict(item: Dict[str, Any]) -> int:
    keys = set(item)
    score = 0
    for key in (
        'dataSetName',
        'datasetName',
        'datasetNameEn',
        'datasetIdentifier',
        'datasetKeyword',
        'citationMode',
        'describ',
        'dataTime',
        'shareLevel',
    ):
        if key in keys:
            score += 2
    if 'dataSetId' in keys or 'datasetId' in keys:
        score += 1
    return score


def _extract_payload_dict(content: str) -> Optional[Dict[str, Any]]:
    payload = _load_json_payload(content)
    if payload is None:
        return None

    best: Optional[Dict[str, Any]] = None
    best_score = 0
    for item in _walk_dicts(payload):
        score = _score_dataset_dict(item)
        if score > best_score:
            best = item
            best_score = score

    return best if best_score > 0 else None


def _extract_label_map(soup: BeautifulSoup, plain_text: str) -> Dict[str, str]:
    values: Dict[str, str] = {}

    for label_node in soup.find_all('label'):
        label = _clean_text(label_node.get_text(' ', strip=True))
        if not label:
            continue
        label = label.rstrip('：:').strip()
        if not label:
            continue

        value_node = label_node.find_next_sibling()
        value = _clean_text(value_node.get_text(' ', strip=True)) if value_node else None
        if value and not value.startswith('{{'):
            values[label] = value

    for box in soup.select('.dataset, .baseMsg, .msgAbstract'):
        heading = _clean_text(box.select_one('.myTitle'))
        if heading and '数据集摘要' in heading:
            msg_box = box.select_one('.msgBox')
            value = _clean_text(msg_box.get_text(' ', strip=True)) if msg_box else None
            if value and not value.startswith('{{'):
                values['数据集摘要'] = value

    for label in LABELS:
        if label in values:
            continue
        next_labels = [item for item in LABELS if item != label]
        pattern = rf'{re.escape(label)}\s*[:：]\s*(.*?)\s*(?=(?:{"|".join(re.escape(item) for item in next_labels)})\s*[:：]|$)'
        match = re.search(pattern, plain_text)
        if match:
            value = _clean_text(match.group(1))
            if value and not value.startswith('{{'):
                values[label] = value

    return values


def _extract_title_from_dom(soup: BeautifulSoup, labels: Dict[str, str], fallback_title: str) -> Optional[str]:
    for selector in ('.crumbs div:last-child span', '.crumbs div:last-child a', 'h1', '.title'):
        title = _clean_text(soup.select_one(selector).get_text(' ', strip=True)) if soup.select_one(selector) else None
        if title and not title.startswith('{{') and title not in {'基本信息', '数据集摘要'}:
            return title

    title = _clean_text(soup.title.string if soup.title and soup.title.string else None)
    if title and title != PUBLISHER_ZH:
        return title

    return _clean_text(fallback_title) or labels.get('标识符')


def _share_level_text(value: Optional[Any]) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    return SHARE_LEVELS.get(text, text)


def _format_data_size(value: Optional[Any]) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    if re.search(r'[a-zA-Z\u4e00-\u9fff]', text):
        return text
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
    return f'{size:.0f}{units[index]}' if size >= 10 else f'{size:.1f}{units[index]}'


def _payload_from_data(data: Dict[str, Any], url: str, title: str) -> MetadataDict:
    query = _parse_query(url)
    full_text = json.dumps(data, ensure_ascii=False)

    dataset_id = _first_non_empty(data.get('dataSetId'), data.get('datasetId'), query.get('dataSetId'))
    fallback_title = title if _clean_text(title) != PUBLISHER_ZH else None
    title_zh = _first_non_empty(
        data.get('dataSetName'),
        data.get('datasetName'),
        fallback_title,
        f'{PUBLISHER_ZH}数据集 {dataset_id}' if dataset_id else None,
        '未提取到标题',
    )
    title_en = _english_text(data.get('datasetNameEn')) or title_zh
    abstract = _first_non_empty(data.get('describ'), data.get('description'), data.get('summary'))
    keywords = _unique_list(_split_terms(data.get('datasetKeyword') or data.get('keywords')))
    subject = _first_non_empty(data.get('subjectClass'), data.get('subjectCategory'))
    theme = _first_non_empty(data.get('themeCategory'), data.get('themeClass'))
    owner = _first_non_empty(data.get('owner'), data.get('dataOwner'), PUBLISHER_ZH)
    identifier = _first_non_empty(data.get('datasetIdentifier'), _extract_cstr(full_text), dataset_id)
    cstr_identifier = _extract_cstr(identifier) or _extract_cstr(full_text)
    publish_date = _first_non_empty(data.get('publishTime'), data.get('releaseTime'), data.get('createTime'), data.get('updateTime'))
    data_size = _format_data_size(data.get('dataSize') or data.get('datasetSize'))
    file_number = _first_non_empty(data.get('fileNumber'))
    data_format = _first_non_empty(data.get('dataFormat'), data.get('format'), data.get('dataFormatPath'))
    data_time = _first_non_empty(data.get('dataTime'), data.get('timeRange'))
    share_level = _share_level_text(data.get('shareLevel'))
    sharing_mode = _first_non_empty(data.get('sharingMode'), share_level)
    timeliness = _first_non_empty(data.get('timeliness'))
    update_frequency = _first_non_empty(data.get('updateFrequency'))
    citation = _first_non_empty(data.get('citationMode'))

    resource_url = url or None
    alternative_identifiers = [dataset_id] if dataset_id and dataset_id != identifier else None
    rights = sharing_mode or share_level

    zh: Dict[str, Any] = {
        '资源类型判定': '数据集',
        '领域判定': '数据集元数据',
        '标识符': identifier,
        'CSTR标识符': cstr_identifier,
        '资源名称': title_zh,
        '标题': title_zh,
        '创建者': [owner] if owner else None,
        '发布机构': PUBLISHER_ZH,
        '发布日期': publish_date,
        '描述': abstract,
        '关键词': keywords or None,
        '学科分类': subject,
        '语言': '中文',
        '贡献者': [owner] if owner and owner != PUBLISHER_ZH else None,
        '替代标识符': alternative_identifiers,
        '关联标识符': None,
        '权限': rights,
        '资助者': None,
        '版本': None,
        '资源链接': resource_url,
        '资源类型': '数据集',
        '数据集基本信息': {
            '标识符': identifier,
            '标题': title_zh,
            '摘要': abstract,
            '关键词': keywords or None,
            '范围': {
                '时间范围': data_time,
                '空间范围': None,
            },
            '语种': '中文',
            '文件内容': f'{file_number}个文件' if file_number else None,
            '基金项目': None,
            '数据量': data_size,
            '数据格式': data_format,
            '数据集作者': {
                '作者姓名': [owner] if owner else None,
                '工作单位': PUBLISHER_ZH,
                '电子邮箱': None,
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
            '数据集引用格式': citation,
            '数据集共享许可协议': rights,
            '数据集使用声明': sharing_mode,
            '数据集下载地址': None,
            '数据集访问地址': resource_url,
        },
        '扩展信息': {
            '英文名称': data.get('datasetNameEn'),
            '数据时间': data_time,
            '共享级别': share_level,
            '时效性': timeliness,
            '更新频率': update_frequency,
            '学科分类': subject,
            '主题分类': theme,
            '所有者': owner,
            '共享方式': sharing_mode,
            '文件数量': file_number,
            '数据集ID': dataset_id,
            '提取状态': data.get('_extractionStatus'),
        },
    }

    english_keywords = [_english_text(item) for item in keywords]
    english_keywords = [item for item in english_keywords if item]

    en: Dict[str, Any] = {
        'Resource Type Classification': 'Dataset',
        'Domain Classification': 'Dataset Metadata',
        'Identifier': identifier,
        'CSTR Identifier': cstr_identifier,
        'Resource Name': title_en,
        'Title': title_en,
        'Creators': None,
        'Publisher': PUBLISHER_EN,
        'Publication Date': publish_date,
        'Description': None,
        'Keywords': english_keywords or None,
        'Discipline Classification': None,
        'Language': 'Chinese',
        'Contributors': None,
        'Alternative Identifiers': alternative_identifiers,
        'Related Identifiers': None,
        'Rights': rights,
        'Funders': None,
        'Version': None,
        'Resource URL': resource_url,
        'ResourceType': 'Dataset',
        'Dataset Basic Information': {
            'Identifier': identifier,
            'Title': title_en,
            'Abstract': None,
            'Keywords': english_keywords or None,
            'Coverage': {
                'Time Range': data_time,
                'Spatial Range': None,
            },
            'Language': 'Chinese',
            'File Content': f'{file_number} files' if file_number else None,
            'Project/Funder': None,
            'Data Size': data_size,
            'Data Format': data_format,
            'Dataset Authors': {
                'Author Name': None,
                'Affiliation': PUBLISHER_EN,
                'Email': None,
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
            'Dataset Citation Format': citation,
            'Dataset License': rights,
            'Dataset Usage Statement': None,
            'Dataset Download URL': None,
            'Dataset Access URL': resource_url,
        },
        'Extension Info': {
            'Chinese Title': title_zh,
            'Data Time': data_time,
            'Share Level': share_level,
            'Timeliness': timeliness,
            'Update Frequency': update_frequency,
            'Subject Classification': None,
            'Theme Category': None,
            'Owner': None,
            'Sharing Mode': None,
            'File Count': file_number,
            'Dataset ID': dataset_id,
            'Extraction Status': data.get('_extractionStatus'),
        },
    }

    return {'zh': zh, 'en': en}


def _data_from_static_template(content: str, url: str, title: str) -> Optional[Dict[str, Any]]:
    if not _is_nmdis_detail_url(url) or not _looks_like_static_vue_template(content):
        return None

    query = _parse_query(url)
    dataset_id = query.get('dataSetId') or query.get('datasetId')
    if not dataset_id:
        return None

    return {
        'dataSetId': dataset_id,
        'dataSetName': f'{PUBLISHER_ZH}数据集 {dataset_id}',
        'owner': PUBLISHER_ZH,
        '_extractionStatus': '静态 Vue 模板，需启用动态渲染后补全 pageParams 字段',
    }


def _data_from_dom(content: str, url: str, title: str) -> Optional[Dict[str, Any]]:
    soup = BeautifulSoup(content, 'html.parser')
    plain_text = soup.get_text(' ', strip=True)
    labels = _extract_label_map(soup, plain_text)
    if not labels:
        return None

    query = _parse_query(url)
    title_zh = _extract_title_from_dom(soup, labels, title)
    data: Dict[str, Any] = {
        'dataSetId': query.get('dataSetId'),
        'dataSetName': title_zh,
        'datasetNameEn': labels.get('英文名称'),
        'dataTime': labels.get('数据时间'),
        'shareLevel': labels.get('共享级别'),
        'timeliness': labels.get('时效性'),
        'updateFrequency': labels.get('更新频率'),
        'datasetIdentifier': labels.get('标识符'),
        'subjectClass': labels.get('学科分类'),
        'themeCategory': labels.get('主题分类'),
        'owner': labels.get('所有者'),
        'sharingMode': labels.get('共享方式'),
        'datasetKeyword': labels.get('关键字'),
        'citationMode': labels.get('引用方式'),
        'describ': labels.get('数据集摘要'),
        'fileNumber': labels.get('文件数量'),
        'dataSize': labels.get('数据量'),
    }

    return {key: value for key, value in data.items() if value}


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').strip().lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()

    return bool(
        _is_nmdis_detail_url(url)
        or 'datasetid=' in normalized_url
        and 'nmdis.org.cn' in normalized_url
        or ('国家海洋科学数据中心' in combined and '数据集摘要' in combined)
        or ('datasetIdentifier' in content and 'datasetKeyword' in content)
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[MetadataDict]:
    if not content:
        return None

    data = _fetch_detail_data(url) if _is_nmdis_detail_url(url) else None
    if not data:
        data = _extract_payload_dict(content)
    if not data:
        data = _data_from_dom(content, url, title)
    if not data:
        data = _data_from_static_template(content, url, title)
    if not data:
        return None

    return _payload_from_data(data, url, title)
