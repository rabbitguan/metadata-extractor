from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, Iterable, Optional


DOI_PATTERN = re.compile(r'\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b', re.IGNORECASE)
CSTR_PATTERN = re.compile(r'^\d{5}\.\d{2}\.[-._;()/:A-Z0-9]+$', re.IGNORECASE)


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = re.sub(r'\s+', ' ', str(value)).strip()
    return text or None


def _ensure_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _unique_list(values: Iterable[Any]) -> list:
    result = []
    seen = set()
    for value in values:
        cleaned = _clean_text(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def _is_doi(value: Any) -> bool:
    return bool(DOI_PATTERN.search(str(value or '').strip()))


def _is_cstr(value: Any) -> bool:
    return bool(CSTR_PATTERN.match(str(value or '').strip()))


def _lower_key_map(data: Dict[str, Any]) -> Dict[str, Any]:
    return {str(key).strip().lower(): value for key, value in data.items()}


def _first(data: Dict[str, Any], *keys: str) -> Any:
    if not isinstance(data, dict):
        return None
    lowered = _lower_key_map(data)
    for key in keys:
        if key in data:
            return data.get(key)
        normalized = key.lower()
        if normalized in lowered:
            return lowered.get(normalized)
    return None


def _xml_element_to_dict(element: ET.Element) -> Any:
    children = list(element)
    if not children:
        return (element.text or '').strip()

    result: Dict[str, Any] = {}
    for child in children:
        key = child.tag.split('}', 1)[-1]
        value = _xml_element_to_dict(child)
        if key in result:
            if not isinstance(result[key], list):
                result[key] = [result[key]]
            result[key].append(value)
        else:
            result[key] = value
    result.update(element.attrib)
    return result


def _parse_path(path: str) -> list[str]:
    normalized = re.sub(r'\[\d+\]', '', str(path or '').strip())
    return [part for part in normalized.split('.') if part]


def _assign_flattened_value(target: Dict[str, Any], path: str, value: str) -> None:
    parts = _parse_path(path)
    if not parts:
        return

    current = target
    for part in parts[:-1]:
        next_value = current.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            current[part] = next_value
        current = next_value

    leaf = parts[-1]
    cleaned = _clean_text(value)
    if not cleaned:
        return

    existing = current.get(leaf)
    if existing is None:
        current[leaf] = cleaned
        return
    if isinstance(existing, list):
        existing.append(cleaned)
        return
    current[leaf] = [existing, cleaned]


def _load_flattened_payload(raw: str) -> Optional[Dict[str, Any]]:
    payload: Dict[str, Any] = {}
    matched = False

    for line in str(raw or '').splitlines():
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        key = key.strip()
        if not key:
            continue
        _assign_flattened_value(payload, key, value)
        matched = True

    return payload if matched and payload else None


def _load_payload(text: str) -> Dict[str, Any]:
    raw = str(text or '').strip()
    if not raw:
        raise ValueError('Uploaded file is empty')

    if raw.startswith('<'):
        root = ET.fromstring(raw)
        payload = _xml_element_to_dict(root)
        if isinstance(payload, dict):
            return payload
        raise ValueError('XML root must contain structured metadata fields')

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        flattened_payload = _load_flattened_payload(raw)
        if flattened_payload is not None:
            return flattened_payload
        raise ValueError(f'Invalid JSON upload: {error}') from error
    if isinstance(payload, list):
        if len(payload) != 1:
            raise ValueError('Uploaded JSON array must contain exactly one resource object')
        payload = payload[0]
    if not isinstance(payload, dict):
        raise ValueError('Uploaded JSON must be an object')
    return payload


def _extract_core(payload: Dict[str, Any]) -> Dict[str, Any]:
    core = _first(payload, 'core', 'core_metadata', '核心元数据', 'Core Metadata')
    if isinstance(core, dict):
        return core
    return payload


def _extract_domain(payload: Dict[str, Any]) -> Dict[str, Any]:
    domain = _first(payload, 'domain', 'domain_metadata', '领域元数据', 'Domain Metadata')
    return domain if isinstance(domain, dict) else {}


def _normalize_resource_type(value: Any) -> tuple[str, str, str, str]:
    text = _clean_text(value) or ''
    normalized = text.lower()
    if text in {'数据集'} or normalized in {'dataset', 'data set'}:
        return '数据集', 'Dataset', '数据集元数据', 'Dataset Metadata'
    if text in {'数据论文'} or normalized in {'data_paper', 'data paper', 'paper'}:
        return '数据论文', 'Data Paper', '数据论文元数据', 'Data Paper Metadata'
    return '其他', 'Other', '核心元数据', 'Core Metadata'


def _list_field(data: Dict[str, Any], *keys: str) -> Optional[list]:
    value = _first(data, *keys)
    values = _unique_list(_ensure_list(value))
    return values or None


def _scalar_field(data: Dict[str, Any], *keys: str) -> Optional[str]:
    value = _first(data, *keys)
    if isinstance(value, list):
        return _clean_text(value[0]) if value else None
    return _clean_text(value)


def _extract_identifier_fields(core: Dict[str, Any]) -> tuple[Optional[str], Optional[list]]:
    raw_cstr = _scalar_field(core, 'cstr_identifier', 'cstrIdentifier', 'CSTR标识符', 'identifier', 'Identifier')
    alternative = _list_field(core, 'alternative_identifiers', 'alternativeIdentifiers', '替代标识符', 'Alternative Identifiers') or []
    doi = _scalar_field(core, 'doi', 'DOI')
    if doi:
        alternative.append(doi)

    if raw_cstr and _is_cstr(raw_cstr):
        cstr_identifier = raw_cstr
    else:
        cstr_identifier = None
        if raw_cstr and (_is_doi(raw_cstr) or raw_cstr not in alternative):
            alternative.append(raw_cstr)

    return cstr_identifier, (_unique_list(alternative) or None)


def _domain_sections(domain: Dict[str, Any], resource_type_zh: str, resource_type_en: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
    if resource_type_zh == '数据集':
        basic = _first(domain, 'dataset_basic_information', 'Dataset Basic Information', '数据集基本信息')
        publication = _first(domain, 'dataset_publication_information', 'Dataset Publication Information', '数据集出版信息')
        service = _first(domain, 'dataset_service_information', 'Dataset Service Information', '数据集服务信息')
        return (
            {
                '数据集基本信息': basic if isinstance(basic, dict) else {},
                '数据集出版信息': publication if isinstance(publication, dict) else {},
                '数据集服务信息': service if isinstance(service, dict) else {},
            },
            {
                'Dataset Basic Information': basic if isinstance(basic, dict) else {},
                'Dataset Publication Information': publication if isinstance(publication, dict) else {},
                'Dataset Service Information': service if isinstance(service, dict) else {},
            },
        )

    if resource_type_en == 'Data Paper':
        content = _first(domain, 'data_paper_content_information', 'Data Paper Content Information', '数据论文内容信息')
        publication = _first(domain, 'data_paper_publication_information', 'Data Paper Publication Information', '数据论文出版信息')
        service = _first(domain, 'data_paper_service_information', 'Data Paper Service Information', '数据论文服务信息')
        return (
            {
                '数据论文内容信息': content if isinstance(content, dict) else {},
                '数据论文出版信息': publication if isinstance(publication, dict) else {},
                '数据论文服务信息': service if isinstance(service, dict) else {},
            },
            {
                'Data Paper Content Information': content if isinstance(content, dict) else {},
                'Data Paper Publication Information': publication if isinstance(publication, dict) else {},
                'Data Paper Service Information': service if isinstance(service, dict) else {},
            },
        )

    return {}, {}


def extract_upload_metadata(text: str, title: str = '') -> Dict[str, Any]:
    payload = _load_payload(text)
    core = _extract_core(payload)
    domain = _extract_domain(payload)

    resource_type_zh, resource_type_en, domain_zh, domain_en = _normalize_resource_type(
        _first(payload, 'resource_type', 'resourceType', '资源类型', 'ResourceType')
        or _first(core, 'resource_type', 'resourceType', '资源类型', 'ResourceType')
    )
    cstr_identifier, alternative_identifiers = _extract_identifier_fields(core)

    titles = _list_field(core, 'title', 'titles', '标题', 'Title') or ([title] if title else None)
    description = _list_field(core, 'description', 'descriptions', '描述', 'Description', 'abstract', '摘要')
    keywords = _list_field(core, 'keywords', '关键词', 'Keywords')
    subjects = _list_field(core, 'subjects', '学科', 'Subjects')
    resource_urls = _list_field(core, 'resource_url', 'resource_urls', 'urls', '资源链接', 'Resource URL')

    zh: Dict[str, Any] = {
        '标题': titles,
        'CSTR标识符': cstr_identifier,
        '创建者': _list_field(core, 'creators', '创建者', 'Creators'),
        '发布机构': _scalar_field(core, 'publisher', '发布机构', 'Publisher'),
        '发布日期': _scalar_field(core, 'publication_date', 'publish_date', '发布日期', 'Publication Date'),
        '描述': description,
        '关键词': keywords,
        '学科': subjects,
        '语言': _scalar_field(core, 'language', '语言', 'Language'),
        '贡献者': _list_field(core, 'contributors', '贡献者', 'Contributors'),
        '替代标识符': alternative_identifiers,
        '关联标识符': _list_field(core, 'related_identifiers', '关联标识符', 'Related Identifiers'),
        '权限': _scalar_field(core, 'rights', '权限', 'Rights'),
        '资助者': _list_field(core, 'funders', '资助者', 'Funders'),
        '版本': _scalar_field(core, 'version', '版本', 'Version'),
        '资源链接': resource_urls,
        '资源类型': resource_type_zh,
        '领域判定': domain_zh,
        '扩展信息': _scalar_field(payload, 'extension_info', '扩展信息', 'Extension Info'),
    }
    en: Dict[str, Any] = {
        'Title': titles,
        'Identifier': cstr_identifier,
        'Creators': zh['创建者'],
        'Publisher': zh['发布机构'],
        'Publication Date': zh['发布日期'],
        'Description': description,
        'Keywords': keywords,
        'Subjects': subjects,
        'Language': zh['语言'],
        'Contributors': zh['贡献者'],
        'Alternative Identifiers': alternative_identifiers,
        'Related Identifiers': zh['关联标识符'],
        'Rights': zh['权限'],
        'Funders': zh['资助者'],
        'Version': zh['版本'],
        'Resource URL': resource_urls,
        'ResourceType': resource_type_en,
        'Domain Classification': domain_en,
        'Extension Info': zh['扩展信息'],
    }

    domain_zh_sections, domain_en_sections = _domain_sections(domain, resource_type_zh, resource_type_en)
    zh.update(domain_zh_sections)
    en.update(domain_en_sections)

    return {'zh': zh, 'en': en}
