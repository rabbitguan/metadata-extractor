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
SPECIAL_DETAIL_API_URL = 'https://mds.nmdis.org.cn/service/shsp/front/science/specialsciencetechnology/metadata'
SCIENCE_FILE_BASE_URL = 'https://mds.nmdis.org.cn/science_file'

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
    if text in {'-', '—', '无', '暂无', 'null', 'None'}:
        return None
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


def _identifier_list(*values: Optional[Any]) -> Optional[list[str]]:
    identifiers = _unique_list(value for value in values if _clean_text(value))
    return identifiers or None


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


def _is_nmdis_special_url(url: str) -> bool:
    normalized_url = (url or '').strip().lower()
    return 'mds.nmdis.org.cn/pages/specialdetailx.html' in normalized_url


def _looks_like_static_vue_template(content: str) -> bool:
    return bool(
        '{{pageParams.' in (content or '')
        or '{{ pageParams.' in (content or '')
        or '{{detail.' in (content or '')
        or 'v-cloak' in (content or '')
    )


def _get_json(url: str, params: Optional[Dict[str, str]], referer: str) -> Optional[Dict[str, Any]]:
    headers = {**API_HEADERS, 'Referer': referer or API_HEADERS['Referer']}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException:
        try:
            session = requests.Session()
            session.trust_env = False
            response = session.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
        except requests.RequestException as error:
            print(f'[WARNING] NMDIS API failed for {url}: {error}')
            return None

    response.encoding = response.apparent_encoding or response.encoding or 'utf-8'
    try:
        payload = json.loads(response.text)
    except json.JSONDecodeError as error:
        print(f'[WARNING] NMDIS API JSON decode failed for {url}: {error}')
        return None
    return payload if isinstance(payload, dict) else None


def _fetch_detail_data(url: str) -> Optional[Dict[str, Any]]:
    query = _parse_query(url)
    dataset_id = query.get('dataSetId') or query.get('datasetId')
    if not dataset_id:
        return None

    payload = _get_json(
        'https://mds.nmdis.org.cn/service/sdm/front/directory/getDirectoryDataSetRelation',
        {'datasetId': dataset_id},
        url,
    )
    if not payload:
        return None

    data = payload.get('data') if isinstance(payload, dict) else None
    return data if isinstance(data, dict) and data else None


def _fetch_special_detail_data(url: str) -> Optional[Dict[str, Any]]:
    query = _parse_query(url)
    project_num = query.get('projectNum')
    res_id = query.get('resId')
    if not project_num or not res_id:
        return None

    payload = _get_json(
        SPECIAL_DETAIL_API_URL,
        {'projectNum': project_num, 'resId': res_id},
        url,
    )
    data = payload.get('data') if isinstance(payload, dict) else None
    if not isinstance(data, dict) or not data:
        return None
    data['_nmdisSpecialDetail'] = True
    return data


def _extract_cstr(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    match = re.search(r'\bCSTR\s*[:：]\s*([A-Z0-9]{5}\.\d{2}\.[-._;()/:A-Z0-9]+)', text, flags=re.IGNORECASE)
    if match:
        return f'CSTR:{match.group(1).rstrip(".,;。；")}'
    match = re.search(r'\b[A-Z0-9]{5}\.\d{2}\.[-._;()/:A-Z0-9]+\b', text, flags=re.IGNORECASE)
    if match:
        return match.group(0).rstrip('.,;。；')
    return None


def _extract_doi(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    match = re.search(r'\bDOI\s*[:：]\s*(10\.\S+)', text, flags=re.IGNORECASE)
    if not match:
        match = re.search(r'\b(10\.\d{4,9}/\S+)', text, flags=re.IGNORECASE)
    return match.group(1).rstrip('.,;。；') if match else None


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
        'chName',
        'resDesc',
        'keyWord',
        'resTimeCoverage',
        'resGeogCoverage',
    ):
        if key in keys:
            score += 2
    if 'dataSetId' in keys or 'datasetId' in keys or 'resId' in keys:
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


def _file_list(data: Dict[str, Any]) -> list[Dict[str, Any]]:
    files = data.get('fileList')
    return [item for item in files if isinstance(item, dict)] if isinstance(files, list) else []


def _join_file_urls(data: Dict[str, Any], *types: str) -> Optional[str]:
    wanted = {item.lower() for item in types if item}
    urls: list[str] = []
    for item in _file_list(data):
        file_type = _clean_text(item.get('type'))
        if wanted and (file_type or '').lower() not in wanted:
            continue
        path = _clean_text(item.get('path'))
        if not path:
            continue
        if path.startswith(('http://', 'https://')):
            urls.append(path)
        else:
            urls.append(f'{SCIENCE_FILE_BASE_URL}{path if path.startswith("/") else "/" + path}')
    return '; '.join(_unique_list(urls)) or None


def _file_count(data: Dict[str, Any]) -> Optional[str]:
    file_number = _first_non_empty(data.get('fileNumber'))
    if file_number:
        return file_number
    files = [item for item in _file_list(data) if (item.get('type') or '').lower() != 'thumbnail']
    return str(len(files)) if files else None


def _agent_list(*values: Optional[Any]) -> Optional[list[str]]:
    agents = _unique_list(value for value in values if _clean_text(value))
    return agents or None


def _payload_from_data(data: Dict[str, Any], url: str, title: str) -> MetadataDict:
    query = _parse_query(url)
    full_text = json.dumps(data, ensure_ascii=False)

    is_special_detail = bool(data.get('_nmdisSpecialDetail'))
    dataset_id = _first_non_empty(
        data.get('dataSetId'),
        data.get('datasetId'),
        data.get('resId'),
        query.get('dataSetId'),
        query.get('resId'),
    )
    project_num = _first_non_empty(data.get('projectNum'), data.get('sourceProjectNum'), query.get('projectNum'))
    fallback_title = title if _clean_text(title) != PUBLISHER_ZH else None
    title_zh = _first_non_empty(
        data.get('dataSetName'),
        data.get('datasetName'),
        data.get('chName'),
        query.get('name'),
        fallback_title,
        f'{PUBLISHER_ZH}数据集 {dataset_id}' if dataset_id else None,
        '未提取到标题',
    )
    title_en = _english_text(data.get('datasetNameEn')) or _english_text(data.get('enName')) or title_zh
    abstract = _first_non_empty(data.get('describ'), data.get('description'), data.get('summary'), data.get('resDesc'))
    keywords = _unique_list(_split_terms(data.get('datasetKeyword') or data.get('keywords') or data.get('keyWord')))
    subject = _first_non_empty(data.get('subjectClass'), data.get('subjectCategory'), data.get('disClass'))
    theme = _first_non_empty(data.get('themeCategory'), data.get('themeClass'), data.get('subClass'))
    owner = _first_non_empty(data.get('owner'), data.get('dataOwner'), data.get('sourcePartUnit'), data.get('sourceProjectUnit'), PUBLISHER_ZH)
    creator_name = _first_non_empty(data.get('sourcePartPerson'), data.get('sourceProjectPerson'), owner)
    if not is_special_detail and owner:
        creator_name = owner
    contributor_names = _agent_list(data.get('metadataPerson'), data.get('sourceProjectPerson'))
    if contributor_names and creator_name:
        contributor_names = [item for item in contributor_names if item != creator_name] or None
    doi_identifier = _extract_doi(full_text)
    identifier = _first_non_empty(data.get('datasetIdentifier'), data.get('metadataIdentifier'), doi_identifier, _extract_cstr(full_text), dataset_id)
    cstr_identifier = _extract_cstr(identifier) or _extract_cstr(full_text)
    domain_identifiers = _identifier_list(_extract_doi(identifier) or doi_identifier, cstr_identifier) or _identifier_list(identifier)
    publish_date = _first_non_empty(
        data.get('publishTime'),
        data.get('releaseTime'),
        data.get('createTime'),
        data.get('updateTime'),
        data.get('latestRevTime'),
        data.get('metadataUpdateTime'),
    )
    data_size = _format_data_size(data.get('dataSize') or data.get('datasetSize') or data.get('resSize'))
    file_number = _file_count(data)
    data_format = _first_non_empty(data.get('dataFormat'), data.get('format'), data.get('dataFormatPath'), data.get('resFormat'))
    data_time = _first_non_empty(data.get('dataTime'), data.get('timeRange'), data.get('resTimeCoverage'))
    spatial_range = _first_non_empty(data.get('spatialRange'), data.get('geoRange'), data.get('resGeogCoverage'))
    share_level = _share_level_text(data.get('shareLevel'))
    sharing_mode = _first_non_empty(data.get('sharingMode'), data.get('shareModel'), share_level)
    timeliness = _first_non_empty(data.get('timeliness'))
    update_frequency = _first_non_empty(data.get('updateFrequency'))
    citation = _first_non_empty(data.get('citationMode'))
    resource_type = _first_non_empty(data.get('resType'), '数据集')
    download_url = _join_file_urls(data, 'Document') or _first_non_empty(data.get('onlineLink'))
    author_affiliation = _first_non_empty(data.get('sourcePartUnit'), data.get('sourceProjectUnit'), owner)
    author_email = _first_non_empty(data.get('sourcePartEmail'), data.get('metadataEmail'))

    resource_url = url or None
    alternative_identifiers = _unique_list([item for item in (dataset_id, project_num) if item and item != identifier]) or None
    rights = sharing_mode or share_level

    zh: Dict[str, Any] = {
        '资源类型判定': resource_type,
        '领域判定': '数据集元数据',
        '标识符': identifier,
        'CSTR标识符': cstr_identifier,
        '资源名称': title_zh,
        '标题': title_zh,
        '创建者': [creator_name] if creator_name else None,
        '发布机构': PUBLISHER_ZH,
        '发布日期': publish_date,
        '描述': abstract,
        '关键词': keywords or None,
        '学科分类': subject,
        '语言': '中文',
        '贡献者': contributor_names,
        '替代标识符': alternative_identifiers,
        '关联标识符': None,
        '权限': rights,
        '资助者': None,
        '版本': None,
        '资源链接': resource_url,
        '资源类型': resource_type,
        '数据集基本信息': {
            '标识符': domain_identifiers or identifier,
            '标题': title_zh,
            '摘要': abstract,
            '关键词': keywords or None,
            '范围': {
                '时间范围': data_time,
                '空间范围': spatial_range,
            },
            '语种': '中文',
            '文件内容': f'{file_number}个文件' if file_number else None,
            '基金项目': _first_non_empty(data.get('sourceProjectName')),
            '数据量': data_size,
            '数据格式': data_format,
            '数据集作者': {
                '作者姓名': [creator_name] if creator_name else None,
                '工作单位': author_affiliation,
                '电子邮箱': author_email,
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
            '数据集下载地址': download_url,
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
            '项目编号': project_num,
            '元数据编写人': data.get('metadataPerson'),
            '提取状态': data.get('_extractionStatus'),
        },
    }

    english_keywords = [_english_text(item) for item in keywords]
    english_keywords = [item for item in english_keywords if item]

    en: Dict[str, Any] = {
        'Resource Type Classification': resource_type,
        'Domain Classification': 'Dataset Metadata',
        'Identifier': identifier,
        'CSTR Identifier': cstr_identifier,
        'Resource Name': title_en,
        'Title': title_en,
        'Creators': [creator_name] if creator_name and not _has_cjk(creator_name) else None,
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
        'ResourceType': resource_type,
        'Dataset Basic Information': {
            'Identifier': domain_identifiers or identifier,
            'Title': title_en,
            'Abstract': None,
            'Keywords': english_keywords or None,
            'Coverage': {
                'Time Range': data_time,
                'Spatial Range': spatial_range,
            },
            'Language': 'Chinese',
            'File Content': f'{file_number} files' if file_number else None,
            'Project/Funder': _english_text(data.get('sourceProjectName')) or data.get('sourceProjectName'),
            'Data Size': data_size,
            'Data Format': data_format,
            'Dataset Authors': {
                'Author Name': [creator_name] if creator_name and not _has_cjk(creator_name) else None,
                'Affiliation': _english_text(author_affiliation),
                'Email': author_email,
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
            'Dataset Download URL': download_url,
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
    if not (_is_nmdis_detail_url(url) or _is_nmdis_special_url(url)) or not _looks_like_static_vue_template(content):
        return None

    query = _parse_query(url)
    dataset_id = query.get('dataSetId') or query.get('datasetId') or query.get('resId')
    if not dataset_id:
        return None

    data = {
        'dataSetId': dataset_id,
        'dataSetName': query.get('name') or f'{PUBLISHER_ZH}数据集 {dataset_id}',
        'owner': PUBLISHER_ZH,
        '_extractionStatus': '静态 Vue 模板，需启用动态渲染后补全 pageParams 字段',
    }
    if _is_nmdis_special_url(url):
        data.update({
            'resId': dataset_id,
            'projectNum': query.get('projectNum'),
            'chName': query.get('name'),
            '_nmdisSpecialDetail': True,
            '_extractionStatus': '静态 Vue 模板，需调用专题科技资源接口补全 detail 字段',
        })
    return data


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
        or _is_nmdis_special_url(url)
        or 'datasetid=' in normalized_url
        and 'nmdis.org.cn' in normalized_url
        or ('resid=' in normalized_url and 'projectnum=' in normalized_url and 'nmdis.org.cn' in normalized_url)
        or ('国家海洋科学数据中心' in combined and '数据集摘要' in combined)
        or ('datasetIdentifier' in content and 'datasetKeyword' in content)
        or ('specialsciencetechnology/metadata' in content or '{{detail.' in content)
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[MetadataDict]:
    if not content:
        return None

    data = _fetch_detail_data(url) if _is_nmdis_detail_url(url) else None
    if not data and _is_nmdis_special_url(url):
        data = _fetch_special_detail_data(url)
    if not data:
        data = _extract_payload_dict(content)
    if not data:
        data = _data_from_dom(content, url, title)
    if not data:
        data = _data_from_static_template(content, url, title)
    if not data:
        return None

    return _payload_from_data(data, url, title)
