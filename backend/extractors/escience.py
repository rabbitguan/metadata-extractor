from __future__ import annotations

import re
from html import unescape
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup


RULE_NAME = 'eScience Metadata Detail'

FIELD_LABELS = [
    '资源名称（中文）',
    'Resource Name (Foreign Language)',
    '标识符',
    'CSTR标识符',
    '学科分类',
    '主题分类',
    '关键词',
    '描述',
    '资源介绍',
    '资源简介',
    '资源生成日期',
    '最近发布日期',
    '资源信息链接发布地址',
    '共享方式',
    '共享途径',
    '共享范围',
    '申请流程',
    '服务机构名称',
    '服务机构通信地址',
    '服务机构邮政编码',
    '服务机构联系电话',
    '服务机构电子信箱',
    '所属平台',
]

API_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json,text/plain,*/*',
    'Referer': 'https://www.escience.org.cn/',
}


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value))
    text = re.sub(r'\s+', ' ', text).strip()
    return text or None


def _has_cjk(value: Optional[str]) -> bool:
    return bool(re.search(r'[\u4e00-\u9fff]', str(value or '')))


def _english_text(value: Optional[str]) -> Optional[str]:
    cleaned = _clean_text(value)
    if not cleaned or _has_cjk(cleaned):
        return None
    return cleaned


def _english_terms(values: Optional[list[str]]) -> Optional[list[str]]:
    terms = [_english_text(value) for value in (values or [])]
    return [term for term in terms if term] or None


def _extract_query_identifiers(url: str) -> tuple[Optional[str], Optional[str]]:
    if not url:
        return None, None

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query_id = None
    query_cstr = None

    for key in ('id',):
        values = query.get(key)
        if not values:
            continue
        for value in values:
            normalized = _clean_text(unquote(value))
            if normalized:
                query_id = normalized
                break
        if query_id:
            break

    for key in ('cstrId',):
        values = query.get(key)
        if not values:
            continue
        for value in values:
            normalized = _clean_text(unquote(value))
            if normalized:
                query_cstr = normalized
                break
        if query_cstr:
            break

    return query_id, query_cstr


def _fetch_detail_data(url: str) -> Optional[Dict[str, Any]]:
    query_id, query_cstr = _extract_query_identifiers(url)
    candidates = [query_id, query_cstr]
    seen = set()

    for cstr_id in candidates:
        cstr_id = _clean_text(cstr_id)
        if not cstr_id or cstr_id in seen:
            continue
        seen.add(cstr_id)
        try:
            response = requests.get(
                'https://api.escience.org.cn/metadata/metadata/search/detail',
                params={'cstrId': cstr_id},
                headers=API_HEADERS,
                timeout=12,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as error:
            print(f"[WARNING] eScience detail API failed for {cstr_id}: {error}")
            continue

        data = payload.get('data') if isinstance(payload, dict) else None
        if isinstance(data, dict) and data:
            return data

    return None


def _extract_first_url(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    match = re.search(r'https?://[^\s<>"]+', text)
    if not match:
        return None
    url_value = match.group(0).rstrip('.,;，。；)）')
    return _clean_text(url_value)


def _label_pattern(label: str) -> str:
    parts = label.strip().split()
    if not parts:
        return re.escape(label)
    return r'\s*'.join(re.escape(part) for part in parts)


def _extract_by_label(text: str, label: str, labels: list[str]) -> Optional[str]:
    if not text:
        return None
    current = _label_pattern(label)
    next_patterns = [_label_pattern(item) for item in labels if item != label]
    if not next_patterns:
        return None

    pattern = rf'{current}\s*[:：]?\s*(.*?)\s*(?=(?:{"|".join(next_patterns)})\s*[:：]?|$)'
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None

    value = _clean_text(match.group(1))
    if not value:
        return None
    value = re.sub(r'^(：|:)', '', value).strip()
    return value or None


def _extract_cstr_identifier(text: str, url: str, query_cstr: Optional[str], query_id: Optional[str]) -> Optional[str]:
    labeled_pattern = re.compile(r'\bCSTR\s*[:：]\s*([A-Za-z0-9._-]+)\b', flags=re.IGNORECASE)
    strict_pattern = re.compile(r'\b\d{5}\.\d{2}\.[A-Za-z0-9._-]+\b')

    for source in (query_cstr or '', text or '', query_id or '', url or ''):
        if not source:
            continue

        labeled = labeled_pattern.search(source)
        if labeled:
            return f'CSTR:{labeled.group(1)}'

        strict = strict_pattern.search(source)
        if strict:
            return strict.group(0)

    return _normalize_cstr_candidate(query_cstr) or _normalize_cstr_candidate(query_id)


def _normalize_cstr_candidate(value: Optional[str]) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None

    labeled = re.search(r'\bCSTR\s*[:：]\s*([A-Za-z0-9._-]+)\b', text, flags=re.IGNORECASE)
    if labeled:
        return f'CSTR:{labeled.group(1)}'

    hash_split = re.match(r'^[0-9a-fA-F]{32}:(.+)$', text)
    if hash_split:
        return _clean_text(hash_split.group(1))

    # Accept compact CSTR-like IDs (e.g., 15937.11.LncBook6) when no explicit prefix is present.
    if re.fullmatch(r'[A-Za-z0-9._-]{6,}', text) and '.' in text:
        return text

    return None


def _split_terms(value: Optional[str]) -> list[str]:
    text = _clean_text(value)
    if not text:
        return []
    parts = re.split(r'[;；,，、\|\s]+', text)
    return [item for item in (_clean_text(part) for part in parts) if item]


def _extract_title(text: str, fallback_title: str) -> Optional[str]:
    title = _extract_by_label(text, '资源名称（中文）', FIELD_LABELS)
    if title:
        return _strip_inline_identifier_noise(title)

    title = _extract_by_label(
        text,
        '资源详情',
        ['资源详情', '快速访问', '所属平台', '资源介绍', '资源生成日期', '基本 信息', '资源名称（中文）'],
    )
    if title:
        title = re.sub(r'^[^\u4e00-\u9fa5A-Za-z0-9]+', '', title)
        return _strip_inline_identifier_noise(title)

    if fallback_title:
        return _strip_inline_identifier_noise(fallback_title)

    return None


def _extract_description(text: str) -> Optional[str]:
    description = _extract_by_label(text, '描述', FIELD_LABELS)
    if description:
        return description

    description = _extract_by_label(text, '资源介绍', FIELD_LABELS)
    if description:
        return description

    alt = _extract_by_label(text, '资源简介', FIELD_LABELS)
    return alt


def _strip_inline_identifier_noise(value: Optional[str]) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None

    cleaned = re.split(
        r'\s+(?:CSTR标识符|标识符|CSTR\s+Identifier|Identifier)\s*[:：]?\s*',
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return _clean_text(cleaned) or text


def _list_from_api(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item for item in (_clean_text(item) for item in value) if item]
    return _split_terms(_clean_text(value))


def _payload_from_api(data: Dict[str, Any], url: str) -> Dict[str, Any]:
    title_text = _clean_text(data.get('title'))
    title_en = _clean_text(data.get('titleEn'))
    cstr_identifier = _normalize_cstr_candidate(data.get('cstrId'))
    identifier = data.get('id') or cstr_identifier or url
    keywords = _list_from_api(data.get('keywordsArr') or data.get('keywords'))
    subject_terms = _list_from_api(data.get('subjectArr') or data.get('subject'))
    theme_terms = _list_from_api(data.get('themeArr') or data.get('theme'))
    theme_value = ' '.join(theme_terms) if theme_terms else None
    description = _clean_text(data.get('descr'))
    generated_date = _clean_text(data.get('generateDateStr') or data.get('generateDate'))
    latest_release_date = _clean_text(data.get('utime'))
    resource_url = _clean_text(data.get('link')) or url
    service_org = _clean_text(data.get('serviceOrg') or data.get('serviceOrgAggr') or data.get('orgName'))
    platform_name = _clean_text(data.get('orgName') or data.get('orgNameAggr'))
    service_address = _clean_text(data.get('serviceOrgAddr'))
    service_postal = _clean_text(data.get('serviceOrgPostCode'))
    service_phone = _clean_text(data.get('serviceOrgPhone'))
    service_email = _clean_text(data.get('serviceOrgEmail'))
    sharing_channel = _clean_text(data.get('sharePathway'))
    sharing_scope = _clean_text(data.get('shareScope'))
    application_process = _clean_text(data.get('applicationProcess'))
    subject_value = ' '.join(subject_terms) if subject_terms else platform_name

    zh_payload: Dict[str, Any] = {
        '资源类型判定': '数据集',
        '领域判定': '数据集元数据',
        '标识符': identifier,
        'CSTR标识符': cstr_identifier,
        '资源名称': title_text,
        '标题': title_text,
        '创建者': [service_org] if service_org else None,
        '发布机构': service_org or platform_name,
        '发布日期': latest_release_date or generated_date,
        '描述': description,
        '关键词': keywords or None,
        '生成日期': generated_date,
        '注册日期': _clean_text(data.get('ctime')),
        '最新发布日期': latest_release_date,
        '学科分类': subject_value,
        '学科': subject_value,
        '主题分类': theme_value,
        '知识产权类别': None,
        '资源使用许可': None,
        '资源访问地址': resource_url,
        '共享方式': {
            '共享途径': sharing_channel,
            '共享范围': sharing_scope,
            '申请流程': application_process,
        },
        '提供方信息': None,
        '服务方信息': {
            '服务方名称': service_org,
            '服务方详细地址': service_address,
            '服务方邮政编码': service_postal,
            '服务方联系电话': service_phone,
            '服务方电子邮箱': service_email,
        },
        '数据集基本信息': {
            '标识符': identifier,
            '标题': title_text,
            '资源名称': title_text,
            '摘要': description,
            '描述': description,
            '关键词': keywords or None,
            '学科分类': subject_terms if subject_terms else None,
            '主题分类': theme_value,
            '资源名称（外文）': title_en,
        },
        '数据集出版信息': {
            '生成日期': generated_date,
            '注册日期': _clean_text(data.get('ctime')),
            '最新发布日期': latest_release_date,
        },
        '数据集服务信息': {
            '资源访问地址': resource_url,
            '共享途径': sharing_channel,
            '共享范围': sharing_scope,
            '申请流程': application_process,
        },
        '扩展信息': {
            '所属平台': platform_name,
            '资源名称（外文）': title_en,
        },
    }

    english_title = _english_text(title_en)
    english_keywords = _english_terms(keywords)
    en_payload: Dict[str, Any] = {
        'Resource Type Classification': 'Dataset',
        'Domain Classification': 'Dataset Metadata',
        'Identifier': cstr_identifier or identifier,
        'CSTR Identifier': cstr_identifier,
        'titles': [{'lang': 'en', 'name': english_title}] if english_title else None,
        'creators': None,
        'publisher': None,
        'publish_date': latest_release_date or generated_date,
        'descriptions': None,
        'keywords': [{'lang': 'en', 'keyword': english_keywords}] if english_keywords else None,
        'subjects': None,
        'language': None,
        'contributors': None,
        'alternative_identifiers': None,
        'related_identifiers': None,
        'rights': None,
        'funders': None,
        'version': None,
        'urls': [resource_url] if resource_url else None,
        'resource_type': 'Dataset',
        'Resource Name': english_title,
        'Title': english_title,
        'Creators': None,
        'Publisher': None,
        'Publication Date': latest_release_date or generated_date,
        'Description': None,
        'Keywords': english_keywords,
        'Generation Date': generated_date,
        'Registration Date': _clean_text(data.get('ctime')),
        'Latest Release Date': latest_release_date,
        'Discipline Classification': None,
        'Subject Classification': None,
        'Intellectual Property Type': None,
        'Usage License': None,
        'Resource Access URL': resource_url,
        'Sharing Details': {
            'Sharing Channel': None,
            'Sharing Scope': None,
            'Application Process': None,
        },
        'Provider Information': None,
        'Service Provider Information': {
            'Service Provider Name': None,
            'Service Provider Address': None,
            'Service Provider Postal Code': service_postal,
            'Service Provider Phone': service_phone,
            'Service Provider Email': service_email,
        },
        'Dataset Basic Information': {
            'Identifier': cstr_identifier or identifier,
            'Resource Name': english_title,
            'Description': None,
            'Keywords': english_keywords,
            'Discipline Classification': None,
            'Subject Classification': None,
            'Resource Name (Foreign Language)': english_title,
        },
        'Dataset Publication Information': {
            'Generation Date': generated_date,
            'Registration Date': _clean_text(data.get('ctime')),
            'Latest Release Date': latest_release_date,
        },
        'Dataset Service Information': {
            'Resource Access URL': resource_url,
            'Sharing Channel': None,
            'Sharing Scope': None,
            'Application Process': None,
        },
        'Extension Info': {
            'Platform': None,
            'Resource Name (Foreign Language)': english_title,
        },
    }

    return {
        'zh': zh_payload,
        'en': en_payload,
    }


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').lower().strip()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()

    return bool(
        'escience.org.cn/metadata/detail' in normalized_url
        or ('escience.org.cn' in normalized_url and 'metadata/detail' in normalized_url)
        or ('中国科技资源共享网' in combined and '资源详情' in combined)
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[Dict[str, Any]]:
    if not content:
        return None

    if 'escience.org.cn' in (url or '').lower() and 'metadata/detail' in (url or '').lower():
        api_data = _fetch_detail_data(url)
        if api_data:
            return _payload_from_api(api_data, url)

    soup = BeautifulSoup(content, 'html.parser')
    plain_text = _clean_text(soup.get_text(' ', strip=True)) or _clean_text(content) or ''

    title_text = _extract_title(plain_text, title)
    description = _extract_description(plain_text)

    generated_date = _extract_by_label(plain_text, '资源生成日期', FIELD_LABELS)
    latest_release_date = _extract_by_label(plain_text, '最近发布日期', FIELD_LABELS)
    info_url_text = _extract_by_label(plain_text, '资源信息链接发布地址', FIELD_LABELS)

    sharing_channel = _extract_by_label(plain_text, '共享途径', FIELD_LABELS)
    sharing_scope = _extract_by_label(plain_text, '共享范围', FIELD_LABELS)
    application_process = _extract_by_label(plain_text, '申请流程', FIELD_LABELS)

    service_org = _extract_by_label(plain_text, '服务机构名称', FIELD_LABELS)
    service_address = _extract_by_label(plain_text, '服务机构通信地址', FIELD_LABELS)
    service_postal = _extract_by_label(plain_text, '服务机构邮政编码', FIELD_LABELS)
    service_phone = _extract_by_label(plain_text, '服务机构联系电话', FIELD_LABELS)
    service_email = _extract_by_label(plain_text, '服务机构电子信箱', FIELD_LABELS)

    platform_name = _extract_by_label(
        plain_text,
        '所属平台',
        ['所属平台', '资源介绍', '资源生成日期', '基本 信息', '资源名称（中文）'],
    )

    subject_terms = _split_terms(_extract_by_label(plain_text, '学科分类', FIELD_LABELS))
    theme_value = _extract_by_label(plain_text, '主题分类', FIELD_LABELS)
    keywords = _split_terms(_extract_by_label(plain_text, '关键词', FIELD_LABELS))
    title_en = _strip_inline_identifier_noise(
        _extract_by_label(plain_text, 'Resource Name (Foreign Language)', FIELD_LABELS)
    )

    query_id, query_cstr = _extract_query_identifiers(url)
    identifier = query_id or query_cstr or title_text or url
    cstr_identifier = _extract_cstr_identifier(plain_text, url, query_cstr, query_id)
    identifier_en = cstr_identifier or identifier

    if not title_text:
        title_text = identifier

    resource_url = _extract_first_url(info_url_text) or _extract_first_url(plain_text) or url
    publish_date = latest_release_date or generated_date
    creators = [service_org] if service_org else None
    publisher = service_org or platform_name
    subject_value = ' '.join(subject_terms) if subject_terms else platform_name

    zh_payload: Dict[str, Any] = {
        '资源类型判定': '数据集',
        '领域判定': '数据集元数据',
        '标识符': identifier,
        'CSTR标识符': cstr_identifier,
        '资源名称': title_text,
        '标题': title_text,
        '创建者': creators,
        '发布机构': publisher,
        '发布日期': publish_date,
        '描述': description,
        '关键词': keywords,
        '生成日期': generated_date,
        '注册日期': None,
        '最新发布日期': latest_release_date,
        '学科分类': subject_value,
        '学科': subject_value,
        '主题分类': theme_value,
        '知识产权类别': None,
        '资源使用许可': None,
        '资源访问地址': resource_url,
        '共享方式': {
            '共享途径': sharing_channel,
            '共享范围': sharing_scope,
            '申请流程': application_process,
        },
        '提供方信息': None,
        '服务方信息': {
            '服务方名称': service_org,
            '服务方详细地址': service_address,
            '服务方邮政编码': service_postal,
            '服务方联系电话': service_phone,
            '服务方电子邮箱': service_email,
        },
        '数据集基本信息': {
            '标识符': identifier,
            '标题': title_text,
            '资源名称': title_text,
            '摘要': description,
            '描述': description,
            '关键词': keywords,
            '学科分类': subject_terms if subject_terms else None,
            '主题分类': theme_value,
            '资源名称（外文）': title_en,
        },
        '数据集出版信息': {
            '生成日期': generated_date,
            '注册日期': None,
            '最新发布日期': latest_release_date,
        },
        '数据集服务信息': {
            '资源访问地址': resource_url,
            '共享途径': sharing_channel,
            '共享范围': sharing_scope,
            '申请流程': application_process,
        },
        '扩展信息': {
            '所属平台': platform_name,
            '资源名称（外文）': title_en,
        },
    }

    english_title = _english_text(title_en)
    english_keywords = _english_terms(keywords)
    en_payload: Dict[str, Any] = {
        'Resource Type Classification': 'Dataset',
        'Domain Classification': 'Dataset Metadata',
        'Identifier': identifier_en,
        'CSTR Identifier': cstr_identifier,
        'titles': [{'lang': 'en', 'name': english_title}] if english_title else None,
        'creators': None,
        'publisher': None,
        'publish_date': publish_date,
        'descriptions': None,
        'keywords': [{'lang': 'en', 'keyword': english_keywords}] if english_keywords else None,
        'subjects': None,
        'language': None,
        'contributors': None,
        'alternative_identifiers': None,
        'related_identifiers': None,
        'rights': None,
        'funders': None,
        'version': None,
        'urls': [resource_url] if resource_url else None,
        'resource_type': 'Dataset',
        'Resource Name': english_title,
        'Title': english_title,
        'Creators': None,
        'Publisher': None,
        'Publication Date': publish_date,
        'Description': None,
        'Keywords': english_keywords,
        'Generation Date': generated_date,
        'Registration Date': None,
        'Latest Release Date': latest_release_date,
        'Discipline Classification': None,
        'Subject Classification': None,
        'Intellectual Property Type': None,
        'Usage License': None,
        'Resource Access URL': resource_url,
        'Sharing Details': {
            'Sharing Channel': None,
            'Sharing Scope': None,
            'Application Process': None,
        },
        'Provider Information': None,
        'Service Provider Information': {
            'Service Provider Name': None,
            'Service Provider Address': None,
            'Service Provider Postal Code': service_postal,
            'Service Provider Phone': service_phone,
            'Service Provider Email': service_email,
        },
        'Dataset Basic Information': {
            'Identifier': identifier_en,
            'Resource Name': english_title,
            'Description': None,
            'Keywords': english_keywords,
            'Discipline Classification': None,
            'Subject Classification': None,
            'Resource Name (Foreign Language)': english_title,
        },
        'Dataset Publication Information': {
            'Generation Date': generated_date,
            'Registration Date': None,
            'Latest Release Date': latest_release_date,
        },
        'Dataset Service Information': {
            'Resource Access URL': resource_url,
            'Sharing Channel': None,
            'Sharing Scope': None,
            'Application Process': None,
        },
        'Extension Info': {
            'Platform': None,
            'Resource Name (Foreign Language)': english_title,
        },
    }

    return {
        'zh': zh_payload,
        'en': en_payload,
    }
