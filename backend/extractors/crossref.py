from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Dict, Iterable, Optional


RULE_NAME = 'Crossref'


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value))
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text or None


def _ensure_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _unique_list(values: Iterable[Any]) -> list:
    seen = set()
    result = []
    for item in values:
        if item is None:
            continue
        if isinstance(item, str):
            item = _clean_text(item)
            if not item:
                continue
            key = item
        else:
            key = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


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
                return payload
            except json.JSONDecodeError:
                continue
    return None


def _extract_message(payload: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return None
    message = payload.get('message')
    if isinstance(message, dict):
        return message
    if payload.get('DOI') and (payload.get('title') or payload.get('publisher')):
        return payload
    return None


def _first_text(value: Any) -> Optional[str]:
    for item in _ensure_list(value):
        text = _clean_text(item)
        if text:
            return text
    return None


def _date_from_parts(value: Any) -> Optional[str]:
    if not isinstance(value, dict):
        return None
    date_parts = value.get('date-parts')
    if not isinstance(date_parts, list) or not date_parts:
        return None
    parts = date_parts[0]
    if not isinstance(parts, list) or not parts:
        return None
    try:
        year = str(int(parts[0]))
    except (TypeError, ValueError):
        return None
    if len(parts) >= 3:
        return f'{year}-{int(parts[1]):02d}-{int(parts[2]):02d}'
    if len(parts) >= 2:
        return f'{year}-{int(parts[1]):02d}'
    return year


def _best_date(message: Dict[str, Any]) -> Optional[str]:
    for field in ('published-online', 'published-print', 'published', 'issued', 'created', 'deposited'):
        date_text = _date_from_parts(message.get(field))
        if date_text:
            return date_text
    return None


def _author_name(author: Dict[str, Any]) -> Optional[str]:
    name = _clean_text(author.get('name'))
    if name:
        return name
    given = _clean_text(author.get('given'))
    family = _clean_text(author.get('family'))
    return _clean_text(' '.join(part for part in [given, family] if part))


def _author_affiliations(author: Dict[str, Any]) -> list:
    return _unique_list(
        affiliation.get('name')
        for affiliation in _ensure_list(author.get('affiliation'))
        if isinstance(affiliation, dict)
    )


def _authors(message: Dict[str, Any]) -> tuple[list, list, list]:
    names = []
    affiliations = []
    orcids = []
    for author in _ensure_list(message.get('author')):
        if not isinstance(author, dict):
            continue
        names.append(_author_name(author))
        affiliations.extend(_author_affiliations(author))
        orcid = _clean_text(author.get('ORCID'))
        if orcid:
            orcids.append(orcid)
    return _unique_list(names), _unique_list(affiliations), _unique_list(orcids)


def _container_title(message: Dict[str, Any]) -> Optional[str]:
    return _first_text(message.get('container-title')) or _first_text(message.get('short-container-title'))


def _links(message: Dict[str, Any]) -> list:
    links = [message.get('URL'), message.get('resource', {}).get('primary', {}).get('URL') if isinstance(message.get('resource'), dict) else None]
    for link in _ensure_list(message.get('link')):
        if isinstance(link, dict):
            links.append(link.get('URL'))
    return _unique_list(links)


def _rights(message: Dict[str, Any]) -> list:
    rights = []
    for item in _ensure_list(message.get('license')):
        if not isinstance(item, dict):
            continue
        parts = [item.get('URL'), item.get('content-version'), item.get('delay-in-days')]
        text = _clean_text('; '.join(str(part) for part in parts if part not in (None, '')))
        if text:
            rights.append(text)
    return _unique_list(rights)


def _funders(message: Dict[str, Any]) -> list:
    funders = []
    for funder in _ensure_list(message.get('funder')):
        if not isinstance(funder, dict):
            continue
        name = _clean_text(funder.get('name'))
        awards = _unique_list(funder.get('award'))
        doi = _clean_text(funder.get('DOI') or funder.get('doi'))
        if name or awards or doi:
            parts = [name, f"award: {', '.join(awards)}" if awards else None, f"doi: {doi}" if doi else None]
            funders.append('; '.join(part for part in parts if part))
    return _unique_list(funders)


def _references(message: Dict[str, Any]) -> list:
    refs = []
    for ref in _ensure_list(message.get('reference')):
        if not isinstance(ref, dict):
            continue
        doi = _clean_text(ref.get('DOI') or ref.get('doi'))
        title = _clean_text(ref.get('article-title') or ref.get('volume-title'))
        key = _clean_text(ref.get('key'))
        text = doi or title or key
        if text:
            refs.append(text)
    return _unique_list(refs)


def _alternative_identifiers(message: Dict[str, Any]) -> list:
    values = [message.get('DOI')]
    values.extend(_ensure_list(message.get('ISSN')))
    values.extend(_ensure_list(message.get('ISBN')))
    values.extend(_ensure_list(message.get('archive')))
    return _unique_list(values)


def _resource_type(crossref_type: Optional[str]) -> tuple[str, str, str, str]:
    normalized = (crossref_type or '').lower()
    if normalized == 'dataset':
        return '数据集', 'Dataset', '数据集元数据', 'Dataset Metadata'
    if normalized in {'journal-article', 'proceedings-article', 'posted-content', 'book-chapter', 'book-section'}:
        return '数据论文', 'Data Paper', '数据论文元数据', 'Data Paper Metadata'
    return '其他', 'Other', '核心元数据', 'Core Metadata'


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').lower()
    if 'api.crossref.org/works' in normalized_url:
        return True
    message = _extract_message(_load_json_payload(content or ''))
    return bool(message and message.get('DOI') and (message.get('title') or message.get('publisher')))


def extract(content: str, url: str = '', title: str = '') -> Optional[Dict[str, Any]]:
    message = _extract_message(_load_json_payload(content or ''))
    if not message:
        return None

    doi = _clean_text(message.get('DOI'))
    title_text = _first_text(message.get('title')) or _clean_text(title) or doi or url
    subtitle = _first_text(message.get('subtitle'))
    if subtitle and title_text and subtitle not in title_text:
        title_text = f'{title_text}: {subtitle}'
    abstract = _clean_text(message.get('abstract'))
    publisher = _clean_text(message.get('publisher'))
    publish_date = _best_date(message)
    keywords = _unique_list(message.get('subject'))
    language = _clean_text(message.get('language'))
    authors, affiliations, orcids = _authors(message)
    container = _container_title(message)
    links = _links(message)
    rights = _rights(message)
    funders = _funders(message)
    references = _references(message)
    alternative_identifiers = _alternative_identifiers(message)
    resource_type_zh, resource_type_en, domain_zh, domain_en = _resource_type(_clean_text(message.get('type')))
    primary_url = links[0] if links else url
    primary_right = rights[0] if rights else None

    core_zh = {
        '资源类型判定': resource_type_zh,
        '领域判定': domain_zh,
        '标识符': doi,
        '资源名称': title_text,
        '创建者': authors or None,
        '发布机构': publisher,
        '发布日期': publish_date,
        '描述': abstract,
        '关键词': keywords or None,
        '学科分类': keywords or None,
        '语言': language,
        '替代标识符': alternative_identifiers or None,
        '关联标识符': references or None,
        '权限': rights or None,
        '资助者': funders or None,
        '资源访问地址': primary_url,
        '扩展信息': {
            '来源': 'Crossref',
            '期刊或会议': container,
            '作者 ORCID': orcids or None,
        },
    }
    core_en = {
        'Resource Type Classification': resource_type_en,
        'Domain Classification': domain_en,
        'Identifier': doi,
        'Resource Name': title_text,
        'Creators': authors or None,
        'Publisher': publisher,
        'Publication Date': publish_date,
        'Description': abstract,
        'Keywords': keywords or None,
        'Subject Classification': keywords or None,
        'Language': language,
        'Alternative Identifiers': alternative_identifiers or None,
        'Related Identifiers': references or None,
        'Rights': rights or None,
        'Funders': funders or None,
        'Resource Access URL': primary_url,
        'Extension Info': {
            'Source': 'Crossref',
            'Container Title': container,
            'Author ORCID': orcids or None,
        },
    }

    metadata: Dict[str, Any] = {'zh': core_zh, 'en': core_en}

    if resource_type_en == 'Dataset':
        metadata['zh'].update({
            '数据集基本信息': {
                '标识符': doi,
                '标题': title_text,
                '摘要': abstract,
                '关键词': keywords or None,
                '语种': language,
                '数据集作者': {
                    '作者姓名': authors or None,
                    '工作单位': affiliations or None,
                    '电子邮箱': None,
                    '工作贡献': None,
                    '作者简介': None,
                },
            },
            '数据集出版信息': {
                '发布日期': publish_date,
                '出版期刊': container or publisher,
                '版本信息': None,
            },
            '数据集服务信息': {
                '数据集共享许可协议': primary_right,
                '数据集下载地址': primary_url,
                '数据集引用格式': None,
                '数据集使用声明': None,
                '数据论文访问地址': None,
            },
        })
        metadata['en'].update({
            'Dataset Basic Information': {
                'Identifier': doi,
                'Title': title_text,
                'Abstract': abstract,
                'Keywords': keywords or None,
                'Language': language,
                'Dataset Authors': {
                    'Author Name': authors or None,
                    'Affiliation': affiliations or None,
                    'Email': None,
                    'Contribution': None,
                    'Biography': None,
                },
            },
            'Dataset Publication Information': {
                'Publication Date': publish_date,
                'Journal': container or publisher,
                'Version Information': None,
            },
            'Dataset Service Information': {
                'Dataset License': primary_right,
                'Dataset Download URL': primary_url,
                'Dataset Citation Format': None,
                'Dataset Usage Statement': None,
                'Data Paper Access URL': None,
            },
        })

    if resource_type_en == 'Data Paper':
        metadata['zh'].update({
            '数据论文内容信息': {
                '标识符': doi,
                '标题': title_text,
                '摘要': abstract,
                '关键词': keywords or None,
                '参考文献': references or None,
                '数据论文作者': {
                    '作者姓名': authors or None,
                    '工作单位': affiliations or None,
                    '电子邮箱': None,
                    '工作贡献': None,
                    '作者简介': None,
                },
            },
            '数据论文出版信息': {
                '出版日期': publish_date,
                '出版期刊': container or publisher,
                '版本信息': None,
            },
            '数据论文服务信息': {
                '数据论文下载地址': primary_url,
                '数据论文共享许可协议': primary_right,
                '数据论文引用格式': None,
                '数据集访问地址': None,
            },
        })
        metadata['en'].update({
            'Data Paper Content Information': {
                'Identifier': doi,
                'Title': title_text,
                'Abstract': abstract,
                'Keywords': keywords or None,
                'References': references or None,
                'Data Paper Authors': {
                    'Author Name': authors or None,
                    'Affiliation': affiliations or None,
                    'Email': None,
                    'Contribution': None,
                    'Biography': None,
                },
            },
            'Data Paper Publication Information': {
                'Publication Date': publish_date,
                'Journal': container or publisher,
                'Version Information': None,
            },
            'Data Paper Service Information': {
                'Data Paper Download URL': primary_url,
                'Data Paper License': primary_right,
                'Data Paper Citation Format': None,
                'Dataset Access URL': None,
            },
        })

    return metadata
