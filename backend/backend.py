import argparse
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json
import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote, urlsplit, urlunsplit

from cstr_resolver import resolve_cstr, resolve_cstr_landing_page, resolve_cstr_metadata
from doi_resolver import resolve_doi, resolve_doi_landing_page, resolve_doi_metadata
from dynamic_renderer import render_url_content
from extractors.manager import extract_metadata
from llm_api import qwen_chat, LABEL_TRANSLATIONS_EN
from get_id import get_typed_identifiers
from identifier import process_source_code
from upload_rule_extractor import extract_upload_metadata
from metadata_store import (
    clear_conversion_logs,
    get_latest_analysis_history_by_url,
    initialize_metadata_store,
    list_conversion_logs,
    save_analysis_history,
    save_conversion_log,
)


app = Flask(__name__)
CORS(app)

initialize_metadata_store()


FETCH_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/125.0.0.0 Safari/537.36 metadata-extractor/1.0'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

URL_PATTERN = re.compile(r'https?://[^\s<>"\'\)\]\}]+', re.IGNORECASE)
DOI_PATTERN = re.compile(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', re.IGNORECASE)
CSTR_PATTERN = re.compile(r'(?:CSTR\s*[:：]\s*)?([A-Z0-9]{5}\.\d{2}\.[-._;()/:A-Z0-9]+)', re.IGNORECASE)

DYNAMIC_RENDER_DOMAINS = {
    item.strip().lower()
    for item in os.environ.get('METADATA_DYNAMIC_RENDER_DOMAINS', 'ncdc.ac.cn,escience.org.cn,mds.nmdis.org.cn').split(',')
    if item.strip()
}
DYNAMIC_RENDER_MODE = os.environ.get('METADATA_DYNAMIC_RENDER_MODE', 'never').strip().lower()


def _decode_gateway_header(value):
    text = str(value or '').strip()
    if not text:
        return ''
    try:
        return unquote(text)
    except Exception:
        return text


def get_gateway_user():
    return {
        'id': _decode_gateway_header(request.headers.get('X-User-Id', '')),
        'name': _decode_gateway_header(request.headers.get('X-User-Name', '')),
        'email': _decode_gateway_header(request.headers.get('X-User-Email', '')),
    }


def _normalize_url_candidate(value):
    text = str(value or '').strip()
    if not text:
        return ''

    text = text.rstrip('.,;，；、')
    parsed = urlsplit(text)
    if not parsed.scheme or not parsed.netloc:
        return text

    path = parsed.path or ''
    if path not in ('', '/') and path.endswith('/'):
        path = path.rstrip('/')

    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ''))


def _lookup_history_payload(*, source='', url='', text='', user_id=''):
    if source == 'identifier':
        return None

    candidates = []
    seen = set()

    def add_candidate(candidate):
        normalized = _normalize_url_candidate(candidate)
        if normalized and normalized not in seen:
            candidates.append(normalized)
            seen.add(normalized)

    add_candidate(url)
    if source == 'upload' or not url:
        for match in URL_PATTERN.finditer(text or ''):
            add_candidate(match.group(0))

    if source == 'upload' and not candidates:
        return None

    if not candidates:
        return None

    history_record = get_latest_analysis_history_by_url(requested_url=candidates[0], text='', user_id=user_id)
    if not history_record and len(candidates) > 1:
        history_record = get_latest_analysis_history_by_url(
            requested_url='',
            text='\n'.join(candidates[1:]),
            user_id=user_id,
        )

    if not history_record:
        return None

    try:
        result_payload = json.loads(history_record['result_json'])
    except Exception:
        return None

    if not isinstance(result_payload, dict):
        return None

    response_payload = dict(result_payload)
    response_payload['from_history'] = True
    response_payload['history_record_id'] = history_record.get('id')
    response_payload['history_requested_url'] = history_record.get('requested_url')
    response_payload['history_page_title'] = history_record.get('page_title')
    response_payload['history_created_at'] = history_record.get('created_at')
    return response_payload


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'on'}
    return bool(value)


def _strip_cstr_prefixes(value):
    text = str(value or '').strip().strip('.,;，；')
    while re.match(r'^CSTR\s*[:：]\s*', text, flags=re.IGNORECASE):
        text = re.sub(r'^CSTR\s*[:：]\s*', '', text, count=1, flags=re.IGNORECASE).strip()
    return text


def _format_cstr_identifier(value):
    normalized = _normalize_cstr_identifier(value)
    return f'CSTR:{normalized}' if normalized else None


def _normalize_queried_cstr(value):
    return _format_cstr_identifier(value) or ''


def _normalize_cstr_identifier(value):
    match = CSTR_PATTERN.fullmatch(_strip_cstr_prefixes(value))
    return match.group(1) if match else None


def _normalize_doi_identifier(value):
    match = DOI_PATTERN.search(str(value or '').strip().strip('.,;，；'))
    return match.group(0) if match else None


def _normalize_allowed_identifier(value, preferred_type=None):
    type_hint = str(preferred_type or '').strip().upper()
    checks = []
    if type_hint in {'CSTR', 'DOI'}:
        checks.append(type_hint)
    checks.extend(item for item in ('CSTR', 'DOI') if item not in checks)

    for identifier_type in checks:
        if identifier_type == 'CSTR':
            normalized = _normalize_cstr_identifier(value)
        else:
            normalized = _normalize_doi_identifier(value)
        if normalized:
            return {'type': identifier_type, 'identifier': normalized}
    return None


def _format_identifier_display(identifier, language='zh'):
    normalized = _normalize_allowed_identifier(
        identifier.get('identifier') if isinstance(identifier, dict) else identifier,
        preferred_type=identifier.get('type') if isinstance(identifier, dict) else None,
    )
    if not normalized:
        return None
    return f"{normalized['type']}:{normalized['identifier']}"


def _format_identifier_displays(identifier, language='zh'):
    if isinstance(identifier, dict):
        display = _format_identifier_display(identifier, language=language)
        return [display] if display else []

    text = _clean_scalar(identifier)
    if not text:
        return []

    displays = []
    seen = set()
    for identifier_type, pattern in (('DOI', DOI_PATTERN), ('CSTR', CSTR_PATTERN)):
        for match in pattern.finditer(text):
            raw = match.group(1) if identifier_type == 'CSTR' else match.group(0)
            display = _format_identifier_display({'type': identifier_type, 'identifier': raw}, language=language)
            if display and display not in seen:
                seen.add(display)
                displays.append(display)

    if displays:
        return displays

    display = _format_identifier_display(text, language=language)
    return [display] if display else []


def _format_identifier_display_value(value, language='zh'):
    if _is_missing_value(value):
        return None
    if isinstance(value, list):
        formatted = []
        seen = set()
        for item in value:
            for display in _format_identifier_displays(item, language=language):
                if display and display not in seen:
                    seen.add(display)
                    formatted.append(display)
        return formatted or None
    formatted = _format_identifier_displays(value, language=language)
    if len(formatted) > 1:
        return formatted
    return formatted[0] if formatted else None


def _format_cstr_display_value(value, language='zh'):
    if _is_missing_value(value):
        return None
    values = value if isinstance(value, list) else [value]
    formatted = []
    seen = set()
    for item in values:
        text = _clean_scalar(item.get('identifier') if isinstance(item, dict) else item)
        if not text:
            continue
        for match in CSTR_PATTERN.finditer(text):
            display = _format_identifier_display({'type': 'CSTR', 'identifier': match.group(1)}, language=language)
            if display and display not in seen:
                seen.add(display)
                formatted.append(display)
    if not formatted:
        return None
    return formatted if len(formatted) > 1 else formatted[0]


def _normalize_domain_related_identifier_value(value, language='zh'):
    if _is_missing_value(value):
        return None
    related = []
    seen = set()
    for item in _as_list(value):
        relation = None
        candidate = item
        if isinstance(item, dict):
            relation = item.get('relation') or item.get('Relation') or item.get('关系')
            candidate = item.get('identifier') or item.get('value') or item.get('id')
        for display in _format_identifier_displays(candidate, language=language):
            if not display or display in seen:
                continue
            seen.add(display)
            if relation:
                related.append({'relation': relation, 'identifier': display})
            else:
                related.append(display)
    return related or None


def _replace_cstr_identifier_value(key, value, cstr):
    if key in {'标识符', 'Identifier'}:
        language = 'en' if key == 'Identifier' else 'zh'
        return _format_identifier_display({'type': 'CSTR', 'identifier': cstr}, language=language)
    if isinstance(value, dict):
        updated = dict(value)
        updated['type'] = 'CSTR'
        updated['identifier'] = _format_cstr_identifier(cstr)
        return updated
    return _format_cstr_identifier(cstr)


def _format_cstr_value_if_possible(value):
    formatted = _format_cstr_identifier(value)
    return formatted if formatted else value


def _format_cstr_identifiers_in_output(node, cstr_context=False):
    if isinstance(node, list):
        return [_format_cstr_identifiers_in_output(item, cstr_context=cstr_context) for item in node]
    if not isinstance(node, dict):
        return _format_cstr_value_if_possible(node) if cstr_context else node

    item_type = str(node.get('type') or '').strip().upper()
    normalized = {}
    for key, value in node.items():
        key_is_cstr = key in {'CSTR标识符', 'CSTR Identifier', 'cstr_identifier', 'cstrIdentifier'}
        key_is_generic_identifier = key in {'标识符', 'Identifier', 'identifier', 'value'}
        child_cstr_context = key_is_cstr or key_is_generic_identifier or ((cstr_context or item_type == 'CSTR') and key_is_generic_identifier)
        normalized[key] = _format_cstr_identifiers_in_output(value, cstr_context=child_cstr_context)
    return normalized


def _format_unified_cstr_identifiers(metadata):
    if not isinstance(metadata, dict):
        return metadata

    formatted = _format_cstr_identifiers_in_output(metadata)
    core = formatted.get('核心元数据') if isinstance(formatted, dict) else None
    metadatas = core.get('metadatas') if isinstance(core, dict) else None
    if isinstance(metadatas, list):
        for item in metadatas:
            if isinstance(item, dict) and item.get('identifier'):
                item['identifier'] = _format_cstr_value_if_possible(item.get('identifier'))
    return formatted


def _apply_queried_cstr_to_payload(payload, queried_cstr):
    cstr = _normalize_cstr_identifier(queried_cstr)
    if not cstr or not isinstance(payload, dict):
        return payload

    def patch_node(node):
        if isinstance(node, list):
            return [patch_node(item) for item in node]
        if not isinstance(node, dict):
            return node

        patched = {}
        for key, value in node.items():
            if key in {'CSTR标识符', '标识符', 'Identifier', 'CSTR Identifier'}:
                patched[key] = _replace_cstr_identifier_value(key, value, cstr)
            else:
                patched[key] = patch_node(value)
        return patched

    def patch_core_section(core):
        if not isinstance(core, dict):
            return
        metadatas = core.get('metadatas')
        if isinstance(metadatas, list):
            for item in metadatas:
                if isinstance(item, dict):
                    item['identifier'] = _format_cstr_identifier(cstr)
        else:
            core['identifier'] = _format_cstr_identifier(cstr)

    patched_payload = patch_node(payload)
    patch_core_section(patched_payload.get('核心元数据'))
    if isinstance(patched_payload.get('zh'), dict):
        patch_core_section(patched_payload['zh'].get('核心元数据'))
    if isinstance(patched_payload.get('en'), dict):
        patch_core_section(patched_payload['en'].get('Core Metadata'))

    return patched_payload


def _looks_like_structured_upload(title='', source='', strategy=''):
    if strategy == 'upload_rule' or source == 'upload':
        return True

    filename = str(title or '').strip().lower()
    return filename.endswith('.json') or filename.endswith('.xml')


def normalize_llm_answer(raw_answer):
    if isinstance(raw_answer, dict):
        return raw_answer

    if isinstance(raw_answer, str):
        return json.loads(raw_answer)

    raise TypeError(f'Unsupported LLM answer type: {type(raw_answer)!r}')


def _first_present_value(answer, *keys):
    if not isinstance(answer, dict):
        return None

    for key in keys:
        if key in answer:
            return answer.get(key)
    return None


def _pick_fields(answer, canonical_alias_map):
    picked = {}
    for canonical_key, aliases in canonical_alias_map.items():
        value = _first_present_value(answer, canonical_key, *aliases)
        picked[canonical_key] = value if value is not None else None
    return picked


def _extract_core_answer(answer, language='zh'):
    if not isinstance(answer, dict):
        return {}

    section_key = 'Core Metadata' if language == 'en' else '核心元数据'
    section = answer.get(section_key)
    if isinstance(section, dict):
        metadatas = section.get('metadatas')
        if isinstance(metadatas, list) and metadatas and isinstance(metadatas[0], dict):
            return metadatas[0]
        return section

    metadatas = answer.get('metadatas')
    if isinstance(metadatas, list) and metadatas and isinstance(metadatas[0], dict):
        return metadatas[0]

    return answer


def _map_keys_recursive(obj, translations):
    """
    递归地将字典中的键名按照 translations 映射，
    保留原有非字典/非列表值结构。用于将 LLM 返回的中文键映射为英文键。
    """
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            mapped_k = translations.get(k, k)
            result[mapped_k] = _map_keys_recursive(v, translations)
        return result
    if isinstance(obj, list):
        return [_map_keys_recursive(i, translations) for i in obj]
    return obj


def _reverse_translation_map(translations):
    return {value: key for key, value in translations.items()}


def _is_missing_value(value):
    if value is None:
        return True
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {'', 'not extracted', '未提取到', 'null'}
    if isinstance(value, list):
        return len(value) == 0
    if isinstance(value, dict):
        return len(value) == 0
    return False


def _merge_missing_values(primary, fallback):
    """
    用 fallback 填充 primary 中缺失的值。primary 优先，fallback 只补空缺。
    """
    if _is_missing_value(primary):
        return fallback

    if isinstance(primary, dict) and isinstance(fallback, dict):
        merged = dict(primary)
        for key, fallback_value in fallback.items():
            if key not in merged:
                merged[key] = fallback_value
                continue

            merged[key] = _merge_missing_values(merged[key], fallback_value)
        return merged

    if isinstance(primary, list) and isinstance(fallback, list):
        return primary if primary else fallback

    return primary


def _is_domain_missing_value(value):
    if _is_missing_value(value):
        return True
    if isinstance(value, list):
        return len(value) == 0 or all(_is_domain_missing_value(item) for item in value)
    if isinstance(value, dict):
        meaningful_values = [
            item
            for key, item in value.items()
            if key not in {'lang', 'type'}
        ]
        return len(meaningful_values) == 0 or all(_is_domain_missing_value(item) for item in meaningful_values)
    return False


def _merge_domain_missing_values(primary, fallback):
    if _is_domain_missing_value(primary):
        return fallback

    if isinstance(primary, dict) and isinstance(fallback, dict):
        merged = dict(primary)
        for key, fallback_value in fallback.items():
            merged[key] = _merge_domain_missing_values(merged.get(key), fallback_value)
        return merged

    if isinstance(primary, list) and isinstance(fallback, list):
        return fallback if _is_domain_missing_value(primary) else primary

    return primary


def _merge_metadata_payload_missing(primary, fallback):
    """
    Merge a secondary metadata payload into a primary payload.
    Primary values win; fallback only fills missing fields.
    """
    if not isinstance(primary, dict):
        return fallback if isinstance(fallback, dict) else primary
    if not isinstance(fallback, dict):
        return primary

    merged = dict(primary)
    for key, fallback_value in fallback.items():
        if key not in merged:
            merged[key] = fallback_value
            continue

        primary_value = merged[key]
        if isinstance(primary_value, dict) and isinstance(fallback_value, dict):
            if isinstance(primary_value.get('metadatas'), list) and isinstance(fallback_value.get('metadatas'), list):
                primary_items = primary_value.get('metadatas') or []
                fallback_items = fallback_value.get('metadatas') or []
                if primary_items and fallback_items and isinstance(primary_items[0], dict) and isinstance(fallback_items[0], dict):
                    next_section = dict(primary_value)
                    next_items = list(primary_items)
                    next_items[0] = _merge_missing_values(next_items[0], fallback_items[0])
                    next_section['metadatas'] = next_items
                    merged[key] = next_section
                    continue
            merged[key] = _merge_metadata_payload_missing(primary_value, fallback_value)
            continue

        merged[key] = _merge_missing_values(primary_value, fallback_value)

    return merged


def _iter_url_values(value):
    if _is_missing_value(value):
        return

    if isinstance(value, str):
        for match in URL_PATTERN.finditer(value):
            yield match.group(0)
        return

    if isinstance(value, list):
        for item in value:
            yield from _iter_url_values(item)
        return

    if isinstance(value, dict):
        for item in value.values():
            yield from _iter_url_values(item)


def _extract_core_resource_urls(payload, current_url=''):
    if not isinstance(payload, dict):
        return []

    candidates = []
    seen = set()
    current_normalized = _normalize_url_candidate(current_url)

    def add_url(candidate):
        normalized = _normalize_url_candidate(candidate)
        if not normalized or normalized == current_normalized or normalized in seen:
            return
        candidates.append(normalized)
        seen.add(normalized)

    zh_core = ((payload.get('zh') or {}).get('核心元数据') or {})
    en_core = ((payload.get('en') or {}).get('Core Metadata') or {})
    merged_core = payload.get('核心元数据') or {}

    for core, field_names in (
        (zh_core, ('资源链接', 'urls')),
        (en_core, ('Resource URL', 'urls')),
        (merged_core, ('资源链接', 'Resource URL', 'urls')),
    ):
        if not isinstance(core, dict):
            continue
        metadatas = core.get('metadatas')
        if isinstance(metadatas, list):
            for item in metadatas:
                if isinstance(item, dict):
                    for field_name in field_names:
                        for url in _iter_url_values(item.get(field_name)):
                            add_url(url)
            continue
        for field_name in field_names:
            for url in _iter_url_values(core.get(field_name)):
                add_url(url)

    return candidates


def _normalize_whitespace(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _clean_scalar(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return None
    text = _normalize_whitespace(value)
    return text or None


def _infer_identifier_type(value):
    normalized = _normalize_allowed_identifier(value)
    return normalized.get('type') if normalized else None


def _language_name_list(value, lang, field='name'):
    if _is_missing_value(value):
        return None

    normalized = []
    for item in _as_list(value):
        if isinstance(item, dict):
            item_lang = item.get('lang') or lang
            item_value = item.get(field) or item.get('name') or item.get('title') or item.get('value')
            if item_value:
                normalized.append({'lang': item_lang, field: item_value})
            elif 'lang' in item and field in item:
                normalized.append(item)
            continue
        text = _clean_scalar(item)
        if text:
            normalized.append({'lang': lang, field: text})

    return normalized or None


def _normalize_identifier(value):
    if isinstance(value, dict):
        identifier = value.get('identifier') or value.get('value') or value.get('id')
        if identifier:
            return _normalize_allowed_identifier(identifier, preferred_type=value.get('type'))
        return None

    text = _clean_scalar(value)
    if not text:
        return None
    return _normalize_allowed_identifier(text)


def _normalize_identifier_list(value):
    if _is_missing_value(value):
        return None
    items = []
    for item in _as_list(value):
        normalized = _normalize_identifier(item)
        if normalized:
            items.append(normalized)
    return items or None


def _normalize_affiliation(value, lang):
    if _is_missing_value(value):
        return None
    if isinstance(value, dict):
        if 'names' in value:
            return value
        name = value.get('name') or value.get('名称') or value.get('工作单位') or value.get('affiliation') or value.get('value')
        identifiers = value.get('identifiers') or value.get('identifier')
        return {
            'names': _language_name_list(name, lang),
            'identifiers': _normalize_identifier_list(identifiers),
        }

    text = _clean_scalar(value)
    if not text:
        return None
    return {
        'names': _language_name_list(text, lang),
        'identifiers': None,
    }


def _normalize_person(value, lang):
    if isinstance(value, dict):
        if 'names' in value:
            return value
        name = (
            value.get('name') or value.get('姓名') or value.get('作者姓名')
            or value.get('creator') or value.get('author') or value.get('value')
        )
        emails = value.get('emails') or value.get('email') or value.get('电子邮箱')
        identifiers = value.get('identifiers') or value.get('identifier')
        affiliations = value.get('affiliations') or value.get('affiliation') or value.get('工作单位')
        return {
            'names': _language_name_list(name, lang),
            'emails': [item for item in (_clean_scalar(i) for i in _as_list(emails)) if item] or None,
            'identifiers': _normalize_identifier_list(identifiers),
            'affiliations': [
                item for item in (_normalize_affiliation(i, lang) for i in _as_list(affiliations)) if item
            ] or None,
        }

    text = _clean_scalar(value)
    if not text:
        return None
    return {
        'names': _language_name_list(text, lang),
        'emails': None,
        'identifiers': None,
        'affiliations': None,
    }


def _normalize_agent(value, lang, contribution_type=None):
    if _is_missing_value(value):
        return None
    if isinstance(value, dict) and ('person' in value or 'affiliation' in value):
        return value

    if isinstance(value, dict):
        agent_type = value.get('type')
        if agent_type in {'Organize', 'Organization', 'Organizational'} or value.get('affiliation'):
            result = {'type': 'Organize', 'affiliation': _normalize_affiliation(value.get('affiliation') or value, lang)}
        else:
            result = {'type': 'Person', 'person': _normalize_person(value, lang)}
    else:
        result = {'type': 'Person', 'person': _normalize_person(value, lang)}

    if contribution_type:
        result['contribution_type'] = contribution_type
    return result


def _normalize_agents(value, lang, contribution_type=None):
    if _is_missing_value(value):
        return None
    if isinstance(value, dict) and 'value' in value:
        value = value.get('value')
    agents = []
    for item in _as_list(value):
        normalized = _normalize_agent(item, lang, contribution_type=contribution_type)
        if normalized:
            agents.append(normalized)
    return agents or None


def _normalize_descriptions(value, lang):
    return _language_name_list(value, lang, field='description')


def _normalize_keywords(value, lang):
    if _is_missing_value(value):
        return None
    if isinstance(value, dict) and 'value' in value:
        value = value.get('value')
    if isinstance(value, list) and value and all(isinstance(item, dict) and 'keyword' in item for item in value):
        return value
    if isinstance(value, dict) and 'keyword' in value:
        return [value]
    keywords = []
    for item in _as_list(value):
        if isinstance(item, dict):
            keyword_value = item.get('keyword') or item.get('keywords') or item.get('value')
            if keyword_value:
                keywords.extend([i for i in _as_list(keyword_value) if _clean_scalar(i)])
            continue
        text = _clean_scalar(item)
        if text:
            keywords.append(text)
    return [{'lang': lang, 'keyword': keywords}] if keywords else None


def _normalize_subjects(value):
    if _is_missing_value(value):
        return None
    if isinstance(value, dict) and 'value' in value:
        value = value.get('value')
    subjects = []
    for item in _as_list(value):
        if isinstance(item, dict):
            subjects.append(item)
            continue
        text = _clean_scalar(item)
        if text:
            subjects.append({'standard_gbt': [text], 'standard_oecd': None})
    return subjects or None


def _normalize_related_identifiers(value):
    if _is_missing_value(value):
        return None
    related = []
    for item in _as_list(value):
        if isinstance(item, dict):
            if isinstance(item.get('identifier'), dict):
                identifier = _normalize_identifier(item.get('identifier'))
                if identifier:
                    related.append({
                        **item,
                        'type': identifier.get('type'),
                        'identifier': identifier,
                    })
                continue
            identifier = _normalize_identifier(item.get('identifier') or item.get('value') or item)
            if identifier:
                related.append({
                    'relation': item.get('relation') or 'Related',
                    'type': identifier.get('type'),
                    'identifier': identifier,
                })
            continue
        identifier = _normalize_identifier(item)
        if identifier:
            related.append({'relation': 'Related', 'type': identifier.get('type'), 'identifier': identifier})
    return related or None


def _normalize_rights(value):
    if _is_missing_value(value):
        return None
    if isinstance(value, dict) and 'value' in value:
        value = value.get('value')
    rights = []
    for item in _as_list(value):
        if isinstance(item, dict):
            rights.append(item)
            continue
        text = _clean_scalar(item)
        if text:
            rights.append({
                'license_type': None,
                'license': None,
                'type': None,
                'description': text,
                'cert_num': None,
            })
    return rights or None


def _normalize_funders(value):
    if _is_missing_value(value):
        return None
    if isinstance(value, dict) and 'value' in value:
        value = value.get('value')
    funders = []
    for item in _as_list(value):
        if isinstance(item, dict):
            funders.append(item)
            continue
        text = _clean_scalar(item)
        if text:
            funders.append({'name': text, 'proj_type': None, 'proj_num': None, 'proj_name': None})
    return funders or None


def _normalize_core_metadata_shape(core, lang):
    if not isinstance(core, dict):
        return core

    normalized = dict(core)
    normalized['titles'] = _language_name_list(core.get('titles'), lang)
    normalized['creators'] = _normalize_agents(core.get('creators'), lang)
    normalized['publisher'] = _normalize_affiliation(core.get('publisher'), lang)
    normalized['descriptions'] = _normalize_descriptions(core.get('descriptions'), lang)
    normalized['keywords'] = _normalize_keywords(core.get('keywords'), lang)
    normalized['subjects'] = _normalize_subjects(core.get('subjects'))
    normalized['contributors'] = _normalize_agents(core.get('contributors'), lang, contribution_type='Other')
    identifier = _normalize_allowed_identifier(core.get('identifier'))
    normalized['identifier'] = f"CSTR:{identifier.get('identifier')}" if identifier and identifier.get('type') == 'CSTR' else None

    alternative_identifiers = _normalize_identifier_list(core.get('alternative_identifiers'))
    if identifier and identifier.get('type') != 'CSTR':
        alternative_identifiers = _merge_lists(alternative_identifiers, [identifier]) or None
    normalized['alternative_identifiers'] = alternative_identifiers
    normalized['related_identifiers'] = _normalize_related_identifiers(core.get('related_identifiers'))
    normalized['rights'] = _normalize_rights(core.get('rights'))
    normalized['funders'] = _normalize_funders(core.get('funders'))
    normalized['urls'] = [item for item in (_clean_scalar(i) for i in _as_list(core.get('urls'))) if item] or None
    return normalized


def _normalize_domain_metadata_shape(obj, lang):
    if isinstance(obj, list):
        return [_normalize_domain_metadata_shape(item, lang) for item in obj]
    if not isinstance(obj, dict):
        return obj

    normalized = {}
    for key, value in obj.items():
        if key in {'数据集作者', '数据论文作者', 'Dataset Authors', 'Data Paper Authors'}:
            normalized[key] = _normalize_domain_metadata_shape(value, lang)
        elif key in {'CSTR标识符', 'CSTR Identifier'}:
            normalized[key] = _format_cstr_display_value(value, language=lang)
        elif key in {'标识符', 'Identifier', '资源标识符', 'Resource Identifier', '替代标识符', 'Alternative Identifiers'}:
            normalized[key] = _format_identifier_display_value(value, language=lang)
        elif key in {'关联标识符', 'Related Identifiers'}:
            normalized[key] = _normalize_domain_related_identifier_value(value, language=lang)
        elif key in {'标题', 'Title'}:
            normalized[key] = _language_name_list(value, lang) or value
        elif key in {'摘要', 'Abstract'}:
            normalized[key] = _normalize_descriptions(value, lang) or value
        elif key in {'关键词', 'Keywords'}:
            normalized[key] = _normalize_keywords(value, lang) or value
        else:
            normalized[key] = _normalize_domain_metadata_shape(value, lang)
    return normalized


def _dedupe_jsonable(items):
    result = []
    seen = set()
    for item in items:
        if _is_missing_value(item):
            continue
        try:
            marker = json.dumps(item, ensure_ascii=False, sort_keys=True)
        except TypeError:
            marker = str(item)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(item)
    return result


def _merge_lists(primary, secondary):
    return _dedupe_jsonable(_as_list(primary) + _as_list(secondary))


def _first_non_missing(*values):
    for value in values:
        if not _is_missing_value(value):
            return value
    return None


def _merge_named_entity(primary, secondary):
    if not isinstance(primary, dict):
        return secondary if isinstance(secondary, dict) else primary
    if not isinstance(secondary, dict):
        return primary

    merged = dict(primary)
    merged['names'] = _merge_lists(primary.get('names'), secondary.get('names')) or None
    merged['identifiers'] = _merge_lists(primary.get('identifiers'), secondary.get('identifiers')) or None

    if 'emails' in primary or 'emails' in secondary:
        merged['emails'] = _merge_lists(primary.get('emails'), secondary.get('emails')) or None
    if 'affiliations' in primary or 'affiliations' in secondary:
        merged['affiliations'] = _merge_named_entity_lists(primary.get('affiliations'), secondary.get('affiliations')) or None

    for key, value in secondary.items():
        if key not in merged or _is_missing_value(merged[key]):
            merged[key] = value
    return merged


def _merge_agent(primary, secondary):
    if not isinstance(primary, dict):
        return secondary if isinstance(secondary, dict) else primary
    if not isinstance(secondary, dict):
        return primary

    merged = dict(primary)
    merged['type'] = _first_non_missing(primary.get('type'), secondary.get('type'))
    if 'person' in primary or 'person' in secondary:
        merged['person'] = _merge_named_entity(primary.get('person'), secondary.get('person'))
    if 'affiliation' in primary or 'affiliation' in secondary:
        merged['affiliation'] = _merge_named_entity(primary.get('affiliation'), secondary.get('affiliation'))
    if 'contribution_type' in primary or 'contribution_type' in secondary:
        merged['contribution_type'] = _first_non_missing(primary.get('contribution_type'), secondary.get('contribution_type'))

    for key, value in secondary.items():
        if key not in merged or _is_missing_value(merged[key]):
            merged[key] = value
    return merged


def _merge_named_entity_lists(primary, secondary):
    primary_list = _as_list(primary) if not _is_missing_value(primary) else []
    secondary_list = _as_list(secondary) if not _is_missing_value(secondary) else []
    merged = []
    for index in range(max(len(primary_list), len(secondary_list))):
        first = primary_list[index] if index < len(primary_list) else None
        second = secondary_list[index] if index < len(secondary_list) else None
        merged.append(_merge_named_entity(first, second) if isinstance(first, dict) or isinstance(second, dict) else _first_non_missing(first, second))
    return _dedupe_jsonable(merged)


def _merge_agent_lists(primary, secondary):
    primary_list = _as_list(primary) if not _is_missing_value(primary) else []
    secondary_list = _as_list(secondary) if not _is_missing_value(secondary) else []
    merged = []
    for index in range(max(len(primary_list), len(secondary_list))):
        first = primary_list[index] if index < len(primary_list) else None
        second = secondary_list[index] if index < len(secondary_list) else None
        merged.append(_merge_agent(first, second) if isinstance(first, dict) or isinstance(second, dict) else _first_non_missing(first, second))
    return _dedupe_jsonable(merged)


def _standard_resource_type(value):
    normalized = str(value or '').strip()
    return {
        '数据集': 'Dataset',
        'Dataset': 'Dataset',
        '数据论文': 'Data Paper',
        'Data Paper': 'Data Paper',
        '标准文献': 'Standard Literature',
        'Standard Literature': 'Standard Literature',
        '生态科学数据': 'Ecological Data',
        'Ecological Data': 'Ecological Data',
        '其他': 'Other',
        'Other': 'Other',
    }.get(normalized, normalized or None)


def _contains_cjk(value):
    return bool(re.search(r'[\u4e00-\u9fff]', str(value or '')))


def _drop_cjk_text_values(value):
    if isinstance(value, str):
        return None if _contains_cjk(value) else value
    if isinstance(value, list):
        items = [item for item in (_drop_cjk_text_values(item) for item in value) if not _is_missing_value(item)]
        return items or None
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key in {'identifier', 'type', 'relation', 'license_type', 'license', 'cert_num', 'proj_num'}:
                result[key] = item
            else:
                filtered = _drop_cjk_text_values(item)
                result[key] = filtered
        return result
    return value


def _merge_core_language_variants(core_zh, core_en):
    zh = core_zh if isinstance(core_zh, dict) else {}
    en = _drop_cjk_text_values(core_en) if isinstance(core_en, dict) else {}
    merged = {}

    for key in ['titles', 'descriptions', 'keywords']:
        merged[key] = _merge_lists(zh.get(key), en.get(key)) or None

    merged['identifier'] = _first_non_missing(zh.get('identifier'), en.get('identifier'))
    merged['creators'] = _merge_agent_lists(zh.get('creators'), en.get('creators')) or None
    merged['publisher'] = _merge_named_entity(zh.get('publisher'), en.get('publisher'))
    merged['publish_date'] = _first_non_missing(zh.get('publish_date'), en.get('publish_date'))
    merged['subjects'] = _merge_lists(zh.get('subjects'), en.get('subjects')) or None
    merged['language'] = _first_non_missing(zh.get('language'), en.get('language'))
    merged['contributors'] = _merge_agent_lists(zh.get('contributors'), en.get('contributors')) or None
    merged['alternative_identifiers'] = _merge_lists(zh.get('alternative_identifiers'), en.get('alternative_identifiers')) or None
    merged['related_identifiers'] = _merge_lists(zh.get('related_identifiers'), en.get('related_identifiers')) or None
    merged['rights'] = _first_non_missing(zh.get('rights'), en.get('rights'))
    merged['funders'] = _merge_lists(zh.get('funders'), en.get('funders')) or None
    merged['version'] = _first_non_missing(zh.get('version'), en.get('version'))
    merged['urls'] = _merge_lists(zh.get('urls'), en.get('urls')) or None
    merged['resource_type'] = _standard_resource_type(_first_non_missing(en.get('resource_type'), zh.get('resource_type')))

    return {key: merged.get(key) for key in CORE_FIELD_ALIASES_ZH.keys()}


LABEL_TRANSLATIONS_ZH = {value: key for key, value in LABEL_TRANSLATIONS_EN.items()}

DOMAIN_WRAPPER_KEYS_ZH = {
    '领域元数据',
    '数据集元数据',
    '数据论文元数据',
    '标准文献元数据',
    '生态科学数据元数据',
}

DOMAIN_WRAPPER_KEYS_EN = {
    'Domain Metadata',
    'Dataset Metadata',
    'Data Paper Metadata',
    'Standard Literature Metadata',
    'Ecological Science Data Metadata',
}

DOMAIN_FIELD_KEYS_ZH = {
    '数据论文内容信息',
    '数据论文出版信息',
    '数据论文服务信息',
    '数据集基本信息',
    '数据集出版信息',
    '数据集服务信息',
    '标准文献信息',
    '标准文献内容信息',
    '标准文献出版信息',
    '标准文献服务信息',
    '生态科学数据基本信息',
    '生态科学数据出版信息',
    '生态科学数据服务信息',
}

DOMAIN_FIELD_KEYS_EN = {
    'Data Paper Content Information',
    'Data Paper Publication Information',
    'Data Paper Service Information',
    'Dataset Basic Information',
    'Dataset Publication Information',
    'Dataset Service Information',
    'Standard Literature Information',
    'Standard Literature Content Information',
    'Standard Literature Publication Information',
    'Standard Literature Service Information',
    'Ecological Science Data Basic Information',
    'Ecological Science Data Publication Information',
    'Ecological Science Data Service Information',
}

EXTRA_METADATA_EXCLUDE_KEYS_ZH = {
    '核心元数据',
    '领域判定',
    *DOMAIN_WRAPPER_KEYS_ZH,
    *DOMAIN_FIELD_KEYS_ZH,
}

EXTRA_METADATA_EXCLUDE_KEYS_EN = {
    'Core Metadata',
    'Domain Classification',
    *DOMAIN_WRAPPER_KEYS_EN,
    *DOMAIN_FIELD_KEYS_EN,
}


def _map_key_to_zh(key):
    return LABEL_TRANSLATIONS_ZH.get(str(key), str(key))


def _map_keys_to_zh_recursive(obj):
    return _map_keys_recursive(obj, LABEL_TRANSLATIONS_ZH)


def _is_lang_object(value):
    return isinstance(value, dict) and isinstance(value.get('lang'), str)


def _is_lang_list(value):
    return isinstance(value, list) and value and all(_is_lang_object(item) for item in value)


def _json_equal(left, right):
    try:
        return json.dumps(left, ensure_ascii=False, sort_keys=True) == json.dumps(right, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return left == right


def _language_item(language, value):
    if _is_lang_object(value):
        return value
    return {'lang': language, 'value': value}


def _merge_lang_lists(primary, secondary):
    items = []
    for value in _as_list(primary) + _as_list(secondary):
        if _is_missing_value(value):
            continue
        if _is_lang_list(value):
            items.extend(value)
        elif _is_lang_object(value):
            items.append(value)
    return _dedupe_jsonable(items)


TIME_RANGE_KEYS = {'起始时间', '结束时间', 'Start Time', 'End Time'}


def _is_time_range_node(value):
    if not isinstance(value, dict) or not value:
        return False
    keys = {str(key) for key in value.keys()}
    return bool(keys & TIME_RANGE_KEYS) and keys <= TIME_RANGE_KEYS


def _time_range_scalar(value):
    if _is_lang_object(value):
        return value.get('value')
    if _is_lang_list(value):
        for item in value:
            if not _is_domain_missing_value(item.get('value')):
                return item.get('value')
        return None
    return value


def _merge_time_range_nodes(zh_value, en_value):
    merged = {}
    en_by_zh_key = {
        _map_key_to_zh(key): value
        for key, value in (en_value or {}).items()
    } if isinstance(en_value, dict) else {}

    for key in ('起始时间', '结束时间'):
        value = None
        if isinstance(zh_value, dict):
            value = zh_value.get(key)
        if _is_domain_missing_value(value):
            value = en_by_zh_key.get(key)
        value = _time_range_scalar(value)
        if not _is_domain_missing_value(value):
            merged[key] = value

    return merged or None


def _merge_language_nodes(zh_value, en_value):
    if _is_time_range_node(zh_value) or _is_time_range_node(en_value):
        return _merge_time_range_nodes(zh_value, en_value)

    zh_missing = _is_domain_missing_value(zh_value)
    en_missing = _is_domain_missing_value(en_value)
    if zh_missing and en_missing:
        return None
    if zh_missing:
        if isinstance(en_value, dict) and not _is_lang_object(en_value):
            return {
                _map_key_to_zh(key): _merge_language_nodes(None, value)
                for key, value in en_value.items()
                if not _is_domain_missing_value(value)
            }
        return en_value if _is_lang_list(en_value) else [_language_item('en', en_value)]
    if en_missing:
        if isinstance(zh_value, dict) and not _is_lang_object(zh_value):
            return {
                _map_key_to_zh(key): _merge_language_nodes(value, None)
                for key, value in zh_value.items()
                if not _is_domain_missing_value(value)
            }
        return zh_value if _is_lang_list(zh_value) else [_language_item('zh', zh_value)]

    if isinstance(zh_value, dict) and isinstance(en_value, dict) and not _is_lang_object(zh_value) and not _is_lang_object(en_value):
        en_by_zh_key = {_map_key_to_zh(key): value for key, value in en_value.items()}
        keys = []
        for key in list(zh_value.keys()) + list(en_by_zh_key.keys()):
            zh_key = _map_key_to_zh(key)
            if zh_key not in keys:
                keys.append(zh_key)

        merged = {}
        for key in keys:
            value = _merge_language_nodes(zh_value.get(key), en_by_zh_key.get(key))
            if not _is_domain_missing_value(value):
                merged[key] = value
        return merged

    if _is_lang_list(zh_value) or _is_lang_list(en_value):
        merged = _merge_lang_lists(zh_value, en_value)
        return merged or None

    if _json_equal(zh_value, en_value):
        return zh_value

    return _dedupe_jsonable([
        _language_item('zh', zh_value),
        _language_item('en', en_value),
    ])


def _extra_answer_fields(answer, language='zh'):
    if not isinstance(answer, dict):
        return {}

    exclude = EXTRA_METADATA_EXCLUDE_KEYS_EN if language == 'en' else EXTRA_METADATA_EXCLUDE_KEYS_ZH
    result = {}
    for key, value in answer.items():
        if key in exclude or key in {'zh', 'en'}:
            continue
        result[key] = value
    return result


def _core_with_extra_fields(core_metadata, zh_source, en_source):
    merged = dict(core_metadata)
    known_keys = set(CORE_FIELD_ALIASES_ZH.keys())
    known_aliases = set()
    for aliases in CORE_FIELD_ALIASES_ZH.values():
        known_aliases.update(aliases)
    for aliases in CORE_FIELD_ALIASES_EN.values():
        known_aliases.update(aliases)

    zh_extra = {
        key: value
        for key, value in (zh_source or {}).items()
        if key not in known_keys and key not in known_aliases and key not in EXTRA_METADATA_EXCLUDE_KEYS_ZH
    }
    en_extra = {
        _map_key_to_zh(key): value
        for key, value in (en_source or {}).items()
        if key not in known_keys and key not in known_aliases and key not in EXTRA_METADATA_EXCLUDE_KEYS_EN
    }
    extra = _merge_language_nodes(zh_extra, en_extra)
    if isinstance(extra, dict):
        merged.update(extra)
    return merged


def _section_as_metadatas(section):
    if isinstance(section, dict) and isinstance(section.get('metadatas'), list):
        return section
    if isinstance(section, dict):
        return {'metadatas': [section]}
    return {'metadatas': [{}]}


def _domain_type_from_answer(answer, core_data):
    domain_root = answer.get('领域元数据') or answer.get('Domain Metadata')
    if isinstance(domain_root, dict) and isinstance(domain_root.get('metadata_type'), str):
        return normalize_domain_type(domain_root.get('metadata_type'))

    for key in (*DOMAIN_WRAPPER_KEYS_ZH, *DOMAIN_WRAPPER_KEYS_EN):
        if key in {'领域元数据', 'Domain Metadata'}:
            continue
        if isinstance(answer.get(key), dict):
            return normalize_domain_type(key)

    resource_type = _first_present_value(
        core_data,
        'resource_type',
        '资源类型',
        '资源类型判定',
        'ResourceType',
        'Resource Type Classification',
    )
    return _infer_domain_section(resource_type, 'zh')


def normalize_domain_type(value):
    text = str(value or '').strip()
    return {
        'Domain Metadata': '领域元数据',
        'Dataset Metadata': '数据集元数据',
        'Data Paper Metadata': '数据论文元数据',
        'Standard Literature Metadata': '标准文献元数据',
        'Ecological Science Data Metadata': '生态科学数据元数据',
        'Core Metadata': '核心元数据',
    }.get(text, text or '领域元数据')


def _build_already_unified_metadata(answer):
    core_section = answer.get('核心元数据') or answer.get('Core Metadata')
    core_section = _section_as_metadatas(core_section)
    core_items = core_section.get('metadatas') or []
    core_data = core_items[0] if core_items and isinstance(core_items[0], dict) else {}
    domain_type = _domain_type_from_answer(answer, core_data)

    domain_root = answer.get('领域元数据') or answer.get('Domain Metadata')
    if isinstance(domain_root, dict):
        domain_items = domain_root.get('metadatas')
        if isinstance(domain_items, list):
            domain_data = domain_items[0] if domain_items and isinstance(domain_items[0], dict) else {}
        else:
            domain_data = {
                key: value
                for key, value in domain_root.items()
                if key not in {'metadata_type', 'metadatas'}
            }
    else:
        domain_data = {}
        specific_domain = answer.get(domain_type)
        if isinstance(specific_domain, dict):
            specific_items = specific_domain.get('metadatas')
            domain_data = specific_items[0] if isinstance(specific_items, list) and specific_items and isinstance(specific_items[0], dict) else specific_domain
        else:
            extracted = _extract_domain_answer(answer, 'zh')
            if isinstance(extracted, dict):
                domain_data = extracted

    return _format_unified_cstr_identifiers({
        '核心元数据': core_section,
        '领域元数据': {
            'metadata_type': domain_type,
            'metadatas': [domain_data if isinstance(domain_data, dict) else {}],
        },
    })


def _build_unified_metadata(answer):
    if not isinstance(answer, dict):
        raise ValueError('LLM response must be a metadata object')

    raw_zh_answer = answer.get('zh') if isinstance(answer.get('zh'), dict) else None
    raw_en_answer = answer.get('en') if isinstance(answer.get('en'), dict) else None
    has_bilingual_wrappers = raw_zh_answer is not None or raw_en_answer is not None

    if not has_bilingual_wrappers:
        return _build_already_unified_metadata(answer)

    zh_answer = raw_zh_answer if raw_zh_answer is not None else answer
    en_answer = raw_en_answer if raw_en_answer is not None else answer
    en_answer = _map_keys_recursive(en_answer, LABEL_TRANSLATIONS_EN)

    zh_core_source = _extract_core_answer(zh_answer, 'zh')
    en_core_source = _extract_core_answer(en_answer, 'en')
    core_zh = _pick_fields(zh_core_source, CORE_FIELD_ALIASES_ZH)
    core_en = _pick_fields(en_core_source, CORE_FIELD_ALIASES_EN)

    resource_type_zh = _first_present_value(zh_core_source, 'resource_type', '资源类型', '资源类型判定')
    resource_type_en = _first_present_value(en_core_source, 'resource_type', 'ResourceType', 'Resource Type Classification')
    domain_class_zh = _first_present_value(zh_answer, '领域判定')
    domain_class_en = _first_present_value(en_answer, 'Domain Classification')

    if not core_zh.get('resource_type'):
        core_zh['resource_type'] = resource_type_zh or _resource_type_from_domain(domain_class_zh, 'zh')
    if not core_en.get('resource_type'):
        core_en['resource_type'] = resource_type_en or _resource_type_from_domain(domain_class_en, 'en')

    core_zh = _normalize_core_metadata_shape(core_zh, 'zh')
    core_en = _normalize_core_metadata_shape(core_en, 'en')
    core_metadata = _merge_core_language_variants(core_zh, core_en)
    if has_bilingual_wrappers:
        core_metadata = _core_with_extra_fields(core_metadata, zh_core_source, en_core_source)

    domain_section_zh = _infer_domain_section(core_metadata.get('resource_type'), 'zh')
    metadata = {
        '核心元数据': {'metadatas': [core_metadata]},
        '领域元数据': {
            'metadata_type': domain_section_zh,
            'metadatas': [{}],
        },
    }

    domain_zh = _normalize_domain_metadata_shape(_extract_domain_answer(zh_answer, 'zh'), 'zh')
    domain_en = _normalize_domain_metadata_shape(_extract_domain_answer(en_answer, 'en'), 'en')
    domain_en = _map_keys_to_zh_recursive(domain_en)
    domain_unified = _merge_language_nodes(domain_zh, domain_en)
    if isinstance(domain_unified, dict) and domain_unified and domain_section_zh != '核心元数据':
        metadata['领域元数据']['metadatas'][0] = domain_unified

    if not has_bilingual_wrappers:
        for key, value in answer.items():
            if key in {'zh', 'en'}:
                continue
            zh_key = _map_key_to_zh(key)
            if zh_key not in metadata and zh_key not in DOMAIN_FIELD_KEYS_ZH and zh_key not in DOMAIN_WRAPPER_KEYS_ZH:
                metadata['领域元数据']['metadatas'][0][zh_key] = value
        if domain_section_zh != '核心元数据' and not metadata['领域元数据']['metadatas'][0]:
            domain_direct = _extract_domain_answer(answer, 'zh')
            if domain_direct:
                metadata['领域元数据']['metadatas'][0] = _normalize_domain_metadata_shape(domain_direct, 'zh')
    else:
        zh_extra = _extra_answer_fields(zh_answer, 'zh')
        en_extra = _map_keys_to_zh_recursive(_extra_answer_fields(en_answer, 'en'))
        extra = _merge_language_nodes(zh_extra, en_extra)
        if isinstance(extra, dict):
            metadata['领域元数据']['metadatas'][0].update({
                key: value for key, value in extra.items()
                if key not in metadata['领域元数据']['metadatas'][0]
            })

    return _format_unified_cstr_identifiers(metadata)


def _extract_domain_answer(answer, language='zh'):
    if not isinstance(answer, dict):
        return {}

    if language == 'en':
        wrapper_keys = {
            'Domain Metadata',
            'Dataset Metadata',
            'Data Paper Metadata',
            'Standard Literature Metadata',
            'Ecological Science Data Metadata',
        }
        field_keys = {
            'Data Paper Content Information',
            'Data Paper Publication Information',
            'Data Paper Service Information',
            'Dataset Basic Information',
            'Dataset Publication Information',
            'Dataset Service Information',
            'Standard Literature Information',
            'Standard Literature Content Information',
            'Standard Literature Publication Information',
            'Standard Literature Service Information',
            'Ecological Science Data Basic Information',
            'Ecological Science Data Publication Information',
            'Ecological Science Data Service Information',
        }
    else:
        wrapper_keys = {'领域元数据', '数据集元数据', '数据论文元数据', '标准文献元数据', '生态科学数据元数据'}
        field_keys = {
            '数据论文内容信息',
            '数据论文出版信息',
            '数据论文服务信息',
            '数据集基本信息',
            '数据集出版信息',
            '数据集服务信息',
            '标准文献信息',
            '标准文献内容信息',
            '标准文献出版信息',
            '标准文献服务信息',
            '生态科学数据基本信息',
            '生态科学数据出版信息',
            '生态科学数据服务信息',
        }

    for key in wrapper_keys:
        section = answer.get(key)
        if isinstance(section, dict):
            metadatas = section.get('metadatas')
            if isinstance(metadatas, list) and metadatas and isinstance(metadatas[0], dict):
                return metadatas[0]
            return section

    return {key: value for key, value in answer.items() if key in field_keys}


def _extract_text_from_html(html):
    if not html:
        return '', ''

    soup = BeautifulSoup(html, 'html.parser')
    title = ''
    if soup.title and soup.title.string:
        title = _normalize_whitespace(soup.title.string)

    meta_description = ''
    meta_tag = soup.find('meta', attrs={'name': 'description'})
    if meta_tag and meta_tag.get('content'):
        meta_description = _normalize_whitespace(meta_tag.get('content'))
    if not meta_description:
        og_tag = soup.find('meta', attrs={'property': 'og:description'})
        if og_tag and og_tag.get('content'):
            meta_description = _normalize_whitespace(og_tag.get('content'))

    body_text = _normalize_whitespace(soup.get_text(' ', strip=True))
    chunks = [chunk for chunk in [title, meta_description, body_text] if chunk]
    return '\n'.join(chunks), title


def _html_looks_client_rendered(html='', text='', title=''):
    lowered_html = str(html or '').lower()
    lowered_title = str(title or '').strip().lower()
    normalized_text = _normalize_whitespace(text)
    if len(normalized_text) < 600 and any(marker in lowered_html for marker in ('id="app"', 'id="root"', '__next', 'data-reactroot')):
        return True
    if lowered_title in {'', 'loading', '加载中', '请稍候', 'just a moment...'}:
        return True
    if len(normalized_text) < 200 and lowered_html.count('<script') >= 5:
        return True
    return False


def _should_dynamic_render(url='', html='', text='', title='', dynamic_render='auto'):
    requested = str(dynamic_render if dynamic_render is not None else 'auto').strip().lower()
    if requested in {'0', 'false', 'no', 'off', 'never', 'disabled'}:
        return False
    if requested in {'1', 'true', 'yes', 'on', 'always', 'force'}:
        return True
    if DYNAMIC_RENDER_MODE in {'never', 'off', 'disabled'}:
        return False
    if DYNAMIC_RENDER_MODE in {'always', 'force'}:
        return True

    normalized_url = str(url or '').lower()
    if any(domain in normalized_url for domain in DYNAMIC_RENDER_DOMAINS):
        return True
    return _html_looks_client_rendered(html=html, text=text, title=title)


def _declared_response_encoding(response):
    headers = getattr(response, 'headers', None)
    content_type = headers.get('content-type', '') if hasattr(headers, 'get') else ''
    match = re.search(r'charset=["\']?([^;"\']+)', str(content_type or ''), flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()

    raw_head = getattr(response, 'content', b'')[:4096]
    for pattern in (
        br'<meta[^>]+charset=["\']?([^"\' >]+)',
        br'<\?xml[^>]+encoding=["\']([^"\']+)',
    ):
        match = re.search(pattern, raw_head, flags=re.IGNORECASE)
        if match:
            return match.group(1).decode('ascii', errors='ignore').strip()
    return None


def _select_response_encoding(response):
    declared = _declared_response_encoding(response)
    if declared:
        return declared

    current = getattr(response, 'encoding', None)
    if current and str(current).lower() not in {'iso-8859-1'}:
        return current

    return getattr(response, 'apparent_encoding', None) or current or 'utf-8'


def fetch_url_content(url, dynamic_render='auto'):
    response = requests.get(url, headers=FETCH_HEADERS, timeout=15)
    response.raise_for_status()
    response.encoding = _select_response_encoding(response)
    html = response.text or ''
    text, title = _extract_text_from_html(html)
    render_method = 'static'

    if _should_dynamic_render(url=url, html=html, text=text, title=title, dynamic_render=dynamic_render):
        try:
            settle_ms = 5000 if 'mds.nmdis.org.cn' in str(url or '').lower() else 800
            rendered = render_url_content(url, headers=FETCH_HEADERS, settle_ms=settle_ms)
            rendered_html = rendered.get('html') or ''
            rendered_text, rendered_title = _extract_text_from_html(rendered_html)
            if len(rendered_text or '') >= len(text or '') or _html_looks_client_rendered(html=html, text=text, title=title):
                html = rendered_html
                text = rendered_text
                title = rendered_title or rendered.get('title') or title
                render_method = 'dynamic'
        except Exception as error:
            print(f"[Dynamic Render Warning] Falling back to static fetch for {url}: {error}")

    return {
        'html': html,
        'text': text,
        'title': title,
        'render_method': render_method,
    }

CORE_FIELD_ALIASES_ZH = {
    'titles': ['标题', '资源名称', 'Title', 'Resource Name', 'title'],
    'identifier': ['CSTR标识符', '标识符', 'Identifier', 'CSTR Identifier'],
    'creators': ['创建者', '作者', '作者姓名', 'Creators', 'Authors', 'Author Name', 'Data Paper Authors', 'Dataset Authors'],
    'publisher': ['发布机构', 'Publisher', '出版机构', '出版单位', '期刊', 'Journal'],
    'publish_date': ['发布日期', '生成日期', '出版日期', 'Publication Date', 'Received Date', 'Year', '年份', 'publication_date'],
    'descriptions': ['描述', '摘要', 'Description', 'Abstract'],
    'keywords': ['关键词', 'Keywords', 'MeSH'],
    'subjects': ['学科', '学科分类', 'Subjects', 'Discipline Classification', 'Subject Classification'],
    'language': ['语言', '语种', 'Language'],
    'contributors': ['贡献者', 'Contributors'],
    'alternative_identifiers': ['替代标识符', 'Alternative Identifiers', 'DOI', 'PMID'],
    'related_identifiers': ['关联标识符', 'Related Identifiers'],
    'rights': ['权限', '资源使用许可', 'Rights', 'Usage License'],
    'funders': ['资助者', '基金项目', 'Funders', 'Funding Project'],
    'version': ['版本', '版本信息', 'Version', 'Version Information'],
    'urls': ['资源链接', '资源访问地址', '数据论文下载地址', 'Resource URL', 'Resource Access URL', 'Dataset Download URL', 'Data Paper Download URL'],
    'resource_type': ['资源类型', '资源类型判定', 'ResourceType', 'Resource Type Classification'],
}


CORE_FIELD_ALIASES_EN = {
    'titles': ['Title', 'titles', 'Resource Name', 'title', '标题'],
    'identifier': ['Identifier', 'identifier', 'CSTR Identifier', 'CSTR标识符', '标识符'],
    'creators': ['Creators', 'creators', 'Authors', 'Author Name', 'Data Paper Authors', 'Dataset Authors', '创建者'],
    'publisher': ['Publisher', 'publisher', 'Journal', '发布机构', '出版机构', '出版单位', '期刊'],
    'publish_date': ['Publication Date', 'publish_date', 'Generated Date', 'Received Date', 'Year', '出版日期', '发布日期', 'publication_date'],
    'descriptions': ['Description', 'descriptions', 'Abstract', '摘要', '描述'],
    'keywords': ['Keywords', 'keywords', 'MeSH', '关键词'],
    'subjects': ['Subjects', 'subjects', 'Discipline Classification', 'Subject Classification', '学科'],
    'language': ['Language', 'language', '语种', '语言'],
    'contributors': ['Contributors', 'contributors', '贡献者'],
    'alternative_identifiers': ['Alternative Identifiers', 'alternative_identifiers', 'DOI', 'PMID', '替代标识符'],
    'related_identifiers': ['Related Identifiers', 'related_identifiers', '关联标识符'],
    'rights': ['Rights', 'rights', 'Usage License', '资源使用许可'],
    'funders': ['Funders', 'funders', 'Funding Project', '资助者'],
    'version': ['Version', 'version', 'Version Information', '版本'],
    'urls': ['Resource URL', 'urls', 'Resource Access URL', 'Dataset Download URL', 'Data Paper Download URL', '资源链接'],
    'resource_type': ['ResourceType', 'resource_type', 'Resource Type Classification', '资源类型'],
}


def _infer_domain_section(resource_type_value, language='zh'):
    resource = str(resource_type_value or '').strip()
    if not resource:
        return '核心元数据' if language == 'zh' else 'Core Metadata'

    if language == 'en':
        return {
            'Dataset': 'Dataset Metadata',
            'Data Paper': 'Data Paper Metadata',
            'Standard Literature': 'Standard Literature Metadata',
            'Ecological Data': 'Ecological Science Data Metadata',
            'Other': 'Core Metadata',
            'Core Metadata': 'Core Metadata',
        }.get(resource, 'Core Metadata')

    return {
        '数据集': '数据集元数据',
        'Dataset': '数据集元数据',
        '数据论文': '数据论文元数据',
        'Data Paper': '数据论文元数据',
        '标准文献': '标准文献元数据',
        'Standard Literature': '标准文献元数据',
        '生态科学数据': '生态科学数据元数据',
        'Ecological Data': '生态科学数据元数据',
        '其他': '核心元数据',
        'Other': '核心元数据',
        '核心元数据': '核心元数据',
    }.get(resource, '核心元数据')


def _resource_type_from_domain(domain_value, language='zh'):
    domain = str(domain_value or '').strip()
    if not domain:
        return '其他' if language == 'zh' else 'Other'

    if language == 'en':
        return {
            'Dataset Metadata': 'Dataset',
            'Data Paper Metadata': 'Data Paper',
            'Standard Literature Metadata': 'Standard Literature',
            'Ecological Science Data Metadata': 'Ecological Data',
            'Core Metadata': 'Other',
        }.get(domain, 'Other')

    return {
        '数据集元数据': '数据集',
        '数据论文元数据': '数据论文',
        '标准文献元数据': '标准文献',
        '生态科学数据元数据': '生态科学数据',
        '核心元数据': '其他',
    }.get(domain, '其他')


def build_metadata_payload(text, mode, url='', title='', html='', strategy='auto', persist_history=True):
    if strategy == 'upload_rule':
        llm_answer = normalize_llm_answer(extract_upload_metadata(text, title=title))
    else:
        llm_answer = normalize_llm_answer(
            qwen_chat(text, mode, url=url, title=title, raw_html=html, strategy=strategy)
        )
    merged_answer = _build_unified_metadata(llm_answer)

    if persist_history and url and html:
        try:
            record_id = save_analysis_history(
                requested_url=url,
                page_title=title,
                page_html=html,
                mode=mode,
                strategy=strategy,
                result_payload=merged_answer,
                user_id=get_gateway_user().get('id', ''),
            )
            print(f"[DB] Saved analysis history record #{record_id}")
        except Exception as error:
            print(f"[DB WARNING] Failed to save analysis history: {error}")

    return merged_answer


def build_rule_metadata_payload(text, mode, url='', title='', html=''):
    rule_content = html or text
    print(f"[Extractor Debug] url={url}, title={title}, content_len={len(rule_content or '')}")
    website_result = extract_metadata(url=url, title=title, content=rule_content)
    if website_result is None:
        raise ValueError('rule_not_matched')
    return _build_unified_metadata(normalize_llm_answer(website_result))


def build_url_metadata_payload(url, mode, strategy='auto'):
    data = fetch_url_content(url, dynamic_render='auto')
    if strategy == 'rule':
        return build_rule_metadata_payload(
            data.get('text', ''),
            mode,
            url=url,
            title=data.get('title', ''),
            html=data.get('html', ''),
        )
    return build_metadata_payload(
        data.get('text', ''),
        mode,
        url=url,
        title=data.get('title', ''),
        html=data.get('html', ''),
        strategy=strategy,
        persist_history=False,
    )


def supplement_payload_from_resource_url(payload, mode, current_url=''):
    for url in _extract_core_resource_urls(payload, current_url=current_url)[:1]:
        try:
            print(f"[Supplemental] Fetching resource URL {url} (dynamic_render={DYNAMIC_RENDER_MODE})")
            fallback_payload = build_url_metadata_payload(url, mode, strategy='rule')
            return _merge_metadata_payload_missing(payload, fallback_payload), {
                'source': 'resource_url',
                'url': url,
                'status': 'ok',
            }
        except Exception as error:
            print(f"[WARNING] Failed to supplement metadata from resource URL {url}: {error}")
            return payload, {
                'source': 'resource_url',
                'url': url,
                'status': 'error',
                'message': str(error),
            }

    return payload, None


def _resolve_identifier_landing_page(identifier_type, identifier):
    if identifier_type == 'doi':
        return resolve_doi_landing_page(identifier, clean_html=process_source_code)
    if identifier_type == 'cstr':
        return resolve_cstr_landing_page(identifier, clean_html=process_source_code)
    raise ValueError(f'Unsupported identifier type: {identifier_type}')


def _metadata_source_for_identifier(identifier_type, identifier):
    if identifier_type == 'doi':
        return 'doi', resolve_doi_metadata(identifier)
    if identifier_type == 'cstr':
        return 'cstr', resolve_cstr_metadata(identifier, clean_html=process_source_code)
    raise ValueError(f'Unsupported identifier type: {identifier_type}')


def _extract_identifiers_from_source(content='', payload=None):
    chunks = [str(content or '')]
    if payload is not None:
        try:
            chunks.append(json.dumps(payload, ensure_ascii=False))
        except Exception:
            pass

    identifiers = []
    seen = set()
    for item in get_typed_identifiers('\n'.join(chunks), include_patent=False):
        if item.get('type') not in {'doi', 'cstr'}:
            continue
        normalized = _normalize_allowed_identifier(item.get('id'), preferred_type=item.get('type'))
        if not normalized:
            continue
        normalized_type = normalized['type'].lower()
        key = (normalized_type, normalized['identifier'].lower())
        if key in seen:
            continue
        seen.add(key)
        identifiers.append({'type': normalized_type, 'identifier': normalized['identifier']})
    return identifiers


def _build_payload_from_identifier_source(source_item, mode):
    resolved = source_item.get('resolved') or {}
    content = resolved.get('content') or ''
    url = resolved.get('url') or ''
    title = resolved.get('title') or ''
    payload = build_rule_metadata_payload(content, mode, url=url, title=title, html='')

    supplemental_results = []
    if source_item.get('priority') in {'cstr', 'doi'}:
        for supplemental in resolved.get('supplemental_urls') or []:
            supplemental_url = supplemental.get('url') if isinstance(supplemental, dict) else str(supplemental or '')
            if not supplemental_url:
                continue
            try:
                print(
                    f"[Supplemental] Fetching {supplemental_url} "
                    f"(dynamic_render={DYNAMIC_RENDER_MODE})"
                )
                supplemental_page = fetch_url_content(supplemental_url, dynamic_render='auto')
                supplemental_payload = build_rule_metadata_payload(
                    supplemental_page.get('text', ''),
                    mode,
                    url=supplemental_url,
                    title=supplemental_page.get('title', ''),
                    html=supplemental_page.get('html', ''),
                )
                payload = _merge_metadata_payload_missing(payload, supplemental_payload)
                supplemental_results.append({
                    'source': supplemental.get('source') if isinstance(supplemental, dict) else 'supplemental',
                    'url': supplemental_url,
                    'status': 'ok',
                    'priority': source_item.get('priority'),
                    'render_method': supplemental_page.get('render_method'),
                })
            except Exception as supplemental_error:
                print(f"[WARNING] Supplemental metadata failed for {supplemental_url}: {supplemental_error}")
                supplemental_results.append({
                    'source': supplemental.get('source') if isinstance(supplemental, dict) else 'supplemental',
                    'url': supplemental_url,
                    'status': 'error',
                    'priority': source_item.get('priority'),
                    'message': str(supplemental_error),
                })

    if source_item.get('priority') == 'web':
        payload, resource_result = supplement_payload_from_resource_url(payload, mode, current_url=url)
        if resource_result:
            resource_result['priority'] = 'web'
            supplemental_results.append(resource_result)

    return payload, supplemental_results


def _collect_identifier_sources(identifier_type, identifier, mode):
    sources = []
    source_results = []
    seen_metadata_identifiers = {(identifier_type, str(identifier or '').lower())}

    def add_resolved_source(priority, source_type, source_identifier, resolver):
        try:
            resolved = resolver(source_type, source_identifier)
            content = resolved.get('content')
            if not content:
                raise ValueError('Resolved page has no readable content')
            source_item = {
                'priority': priority,
                'type': source_type,
                'identifier': source_identifier,
                'resolved': resolved,
            }
            sources.append(source_item)
            source_results.append({
                'priority': priority,
                'type': source_type,
                'identifier': source_identifier,
                'source': resolved.get('source', source_type),
                'url': resolved.get('url'),
                'status': 'resolved',
            })
            return source_item
        except Exception as error:
            print(f"[WARNING] Failed to resolve {priority} source for {source_type.upper()} {source_identifier}: {error}")
            source_results.append({
                'priority': priority,
                'type': source_type,
                'identifier': source_identifier,
                'status': 'error',
                'message': str(error),
            })
            return None

    add_resolved_source('web', identifier_type, identifier, _resolve_identifier_landing_page)
    try:
        own_priority, own_resolved = _metadata_source_for_identifier(identifier_type, identifier)
        own_source = add_resolved_source(own_priority, identifier_type, identifier, lambda *_: own_resolved)
    except Exception as error:
        own_source = None
        print(f"[WARNING] Failed to resolve metadata source for {identifier_type.upper()} {identifier}: {error}")
        source_results.append({
            'priority': identifier_type,
            'type': identifier_type,
            'identifier': identifier,
            'status': 'error',
            'message': str(error),
        })

    if own_source:
        for related in _extract_identifiers_from_source(
            content=(own_source.get('resolved') or {}).get('content', ''),
        ):
            related_type = related.get('type')
            if related_type == identifier_type:
                continue
            related_identifier = related.get('identifier')
            key = (related_type, str(related_identifier or '').lower())
            if key in seen_metadata_identifiers:
                continue
            seen_metadata_identifiers.add(key)
            try:
                related_priority, related_resolved = _metadata_source_for_identifier(related_type, related_identifier)
                add_resolved_source(related_priority, related_type, related_identifier, lambda *_: related_resolved)
            except Exception as error:
                print(f"[WARNING] Failed to resolve related metadata source for {related_type.upper()} {related_identifier}: {error}")
                source_results.append({
                    'priority': related_type,
                    'type': related_type,
                    'identifier': related_identifier,
                    'status': 'error',
                    'message': str(error),
                })

    return sources, source_results


def _merge_identifier_source_payloads(sources, mode):
    payloads_by_priority = {'web': [], 'cstr': [], 'doi': []}
    source_results = []
    supplemental_results = []

    for source_item in sources:
        resolved = source_item.get('resolved') or {}
        try:
            payload, source_supplemental = _build_payload_from_identifier_source(source_item, mode)
            payloads_by_priority.setdefault(source_item.get('priority'), []).append(payload)
            supplemental_results.extend(source_supplemental)
            source_results.append({
                'priority': source_item.get('priority'),
                'type': source_item.get('type'),
                'identifier': source_item.get('identifier'),
                'source': resolved.get('source', source_item.get('type')),
                'url': resolved.get('url'),
                'status': 'ok',
            })
        except Exception as error:
            print(
                f"[WARNING] Metadata extraction failed for "
                f"{source_item.get('priority')} {source_item.get('type')} {source_item.get('identifier')}: {error}"
            )
            source_results.append({
                'priority': source_item.get('priority'),
                'type': source_item.get('type'),
                'identifier': source_item.get('identifier'),
                'source': resolved.get('source', source_item.get('type')),
                'url': resolved.get('url'),
                'status': 'error',
                'message': str(error),
            })

    merged_payload = None
    for priority in ('web', 'cstr', 'doi'):
        for payload in payloads_by_priority.get(priority) or []:
            if merged_payload is None:
                merged_payload = payload
            else:
                merged_payload = _merge_metadata_payload_missing(merged_payload, payload)

    return merged_payload, source_results, supplemental_results


def handle_identifier_request(data):
    mode = data.get('mode', 'common')
    identifiers = extract_doi_cstr_identifiers(collect_identifier_text(data))
    if not identifiers:
        error_payload = {'message': 'No DOI or CSTR identifier found'}
    else:
        error_payload = None
    if error_payload:
        return jsonify({"status": "error", **error_payload}), 400

    results = []
    for item in identifiers:
        identifier_type = item['type']
        identifier = item['id']
        try:
            print(f"Processing identifier sources for {identifier_type.upper()} {identifier}")
            sources, resolve_results = _collect_identifier_sources(identifier_type, identifier, mode)
            payload, source_results, supplemental_results = _merge_identifier_source_payloads(sources, mode)

            if payload is None:
                raise ValueError('No metadata payload generated')

            if identifier_type == 'cstr':
                payload = _apply_queried_cstr_to_payload(payload, identifier)

            results.append({
                'identifier': _normalize_queried_cstr(identifier) if identifier_type == 'cstr' else identifier,
                'type': identifier_type,
                'resolved_url': next(
                    (
                        result.get('url')
                        for result in source_results
                        if result.get('priority') == 'web' and result.get('status') == 'ok'
                    ),
                    next((result.get('url') for result in source_results if result.get('status') == 'ok'), ''),
                ),
                'source': 'merged',
                'status': 'ok',
                'payload': payload,
                'source_results': resolve_results + source_results,
                'supplemental_sources': supplemental_results,
                'updated_at': datetime.utcnow().isoformat() + 'Z',
            })
        except (json.JSONDecodeError, ValueError, TypeError) as error:
            print(f"LLM Error: {error}")
            results.append({
                'identifier': _normalize_queried_cstr(identifier) if identifier_type == 'cstr' else identifier,
                'type': identifier_type,
                'resolved_url': '',
                'source': 'merged',
                'status': 'error',
                'message': 'Invalid bilingual JSON format from LLM',
                'updated_at': datetime.utcnow().isoformat() + 'Z',
            })

    return jsonify({'items': results})


def handle_register_request(data):
    source = data.get('source', 'text')
    mode = data.get('mode', 'common')
    strategy = data.get('strategy', 'auto')
    force_reanalyze = _parse_bool(data.get('force_reanalyze', False))

    if source == 'url':
        url = str(data.get('url') or '').strip()
        dynamic_render = data.get('dynamic_render', data.get('render', 'auto'))
        if not url:
            return jsonify({"status": "error", "message": "Missing URL"}), 400
        if not force_reanalyze:
            history_payload = _lookup_history_payload(
                source=source,
                url=url,
                text='',
                user_id=get_gateway_user().get('id', ''),
            )
            if history_payload:
                return jsonify(history_payload)
        try:
            data = fetch_url_content(url, dynamic_render=dynamic_render)
            data['url'] = url
        except Exception as error:
            print(f"URL Fetch Error: {error}")
            return jsonify({"status": "error", "message": f"Failed to fetch URL: {error}"}), 400

    if not force_reanalyze:
        history_payload = _lookup_history_payload(
            source=source,
            url=data.get('url', ''),
            text=data.get('text', ''),
            user_id=get_gateway_user().get('id', ''),
        )
        if history_payload:
            return jsonify(history_payload)

    text = data.get('text', '')
    html = data.get('html', '')
    url = data.get('url', '')
    title = data.get('title', '')
    if not str(text or '').strip() and source in {'text', 'web', 'upload'}:
        return jsonify({"status": "error", "message": "Missing text"}), 400
    if _looks_like_structured_upload(title=title, source=source, strategy=strategy):
        strategy = 'upload_rule'
    print("Processing text" if strategy != 'upload_rule' else "Using upload rule extractor")
    print(
        f"[Request Debug] strategy={strategy}, text_len={len(text or '')}, html_len={len(html or '')}, url={url}"
    )

    try:
        merged_answer = build_metadata_payload(text, mode, url=url, title=title, html=html, strategy=strategy)
    except (json.JSONDecodeError, ValueError, TypeError) as error:
        print(f"LLM Error: {error}")
        if strategy == 'upload_rule':
            return jsonify({"status": "error", "message": str(error)}), 400
        return jsonify({"status": "error", "message": "Invalid bilingual JSON format from LLM"}), 400
    except Exception as error:
        print(f"Processing Error: {error}")
        return jsonify({"status": "error", "message": f"Failed to process text: {error}"}), 500

    print("Processing complete")
    print("Merged answer:", json.dumps(merged_answer, ensure_ascii=False, indent=2))
    return jsonify(merged_answer)


@app.route('/query', methods=['POST'])
def query():
    print("Received query request")
    data = request.get_json() or {}
    return handle_identifier_request(data)


@app.route('/register', methods=['POST'])
def register():
    print("Received register request")
    data = request.get_json() or {}
    return handle_register_request(data)


@app.route('/history/lookup', methods=['GET'])
def history_lookup():
    url = request.args.get('url', '')
    text = request.args.get('text', '')
    history_payload = _lookup_history_payload(
        source='url',
        url=url,
        text=text,
        user_id=get_gateway_user().get('id', ''),
    )
    if not history_payload:
        return jsonify({'found': False})

    return jsonify({'found': True, **history_payload})

@app.route('/history', methods=['GET', 'POST', 'DELETE'])
def history():
    user_id = get_gateway_user().get('id', '')
    if request.method == 'POST':
        data = request.get_json() or {}
        payload = data.get('payload')
        if not isinstance(payload, dict):
            return jsonify({'status': 'error', 'message': 'Missing payload'}), 400
        try:
            record_id = save_conversion_log(
                user_id=user_id,
                source=data.get('source', ''),
                mode=data.get('mode', ''),
                strategy=data.get('strategy', ''),
                title=data.get('title', ''),
                requested_url=data.get('url', ''),
                identifier_input=data.get('identifierInput', ''),
                input_preview=data.get('inputPreview', ''),
                result_payload=payload,
            )
        except Exception as error:
            return jsonify({'status': 'error', 'message': f'Failed to save history: {error}'}), 500
        return jsonify({'status': 'ok', 'id': record_id})

    if request.method == 'DELETE':
        try:
            deleted = clear_conversion_logs(user_id=user_id)
        except Exception as error:
            return jsonify({'status': 'error', 'message': f'Failed to clear history: {error}'}), 500
        return jsonify({'status': 'ok', 'deleted': deleted})

    limit = request.args.get('limit', 20)
    offset = request.args.get('offset', 0)
    try:
        records = list_conversion_logs(user_id=user_id, limit=limit, offset=offset)
    except Exception as error:
        return jsonify({'status': 'error', 'message': f'Failed to load history: {error}'}), 500

    try:
        parsed_limit = int(limit or 20)
    except Exception:
        parsed_limit = 20

    try:
        parsed_offset = int(offset or 0)
    except Exception:
        parsed_offset = 0

    return jsonify({'records': records, 'limit': parsed_limit, 'offset': parsed_offset})


@app.route('/user', methods=['GET'])
def user():
    return jsonify({'user': get_gateway_user()})


def collect_identifier_text(data):
    raw_identifiers = data.get('identifiers')
    if isinstance(raw_identifiers, list):
        chunks = [str(item) for item in raw_identifiers if item is not None]
        return '\n'.join(chunks)
    if raw_identifiers is not None:
        return str(raw_identifiers)
    return str(data.get('text') or data.get('html') or '')


def extract_doi_cstr_identifiers(text):
    return [
        item
        for item in get_typed_identifiers(text, include_patent=False)
        if item['type'] in ('doi', 'cstr')
    ]


def resolve_identifier_item(identifier_type, identifier):
    if identifier_type == 'doi':
        return resolve_doi(identifier, clean_html=process_source_code)
    if identifier_type == 'cstr':
        return resolve_cstr(identifier, clean_html=process_source_code)
    raise ValueError(f'Unsupported identifier type: {identifier_type}')


def resolve_identifier_content(data):
    identifier_text = collect_identifier_text(data)
    identifiers = extract_doi_cstr_identifiers(identifier_text)
    if not identifiers:
        return None, {'message': 'No DOI or CSTR identifier found'}

    items = []
    for item in identifiers:
        identifier_type = item['type']
        identifier = item['id']
        try:
            resolved = resolve_identifier_item(identifier_type, identifier)
            content = resolved.get('content')
            resolved_url = resolved.get('url')
            source = resolved.get('source', identifier_type)
            if not content:
                raise ValueError('Resolved page has no readable content')

            items.append({
                'identifier': identifier,
                'type': identifier_type,
                'resolved_url': resolved_url,
                'source': source,
                'content': content,
                'supplemental_urls': resolved.get('supplemental_urls') or [],
                'status': 'ok',
            })
        except Exception as error:
            print(f"[WARNING] Failed to resolve {identifier_type.upper()} {identifier}: {error}")
            items.append({
                'identifier': identifier,
                'type': identifier_type,
                'status': 'error',
                'message': str(error),
            })

    if all(item.get('status') != 'ok' for item in items):
        return None, {
            'message': 'Failed to resolve any DOI or CSTR identifier',
            'errors': [
                {
                    'identifier': item.get('identifier'),
                    'type': item.get('type'),
                    'message': item.get('message'),
                }
                for item in items
                if item.get('status') != 'ok'
            ],
        }

    return items, None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run metadata extractor backend.')
    parser.add_argument('--host', default='127.0.0.1', help='Flask bind host, default: 127.0.0.1')
    parser.add_argument('--port', type=int, default=4000, help='Flask bind port, default: 4000')
    parser.add_argument(
        '-d',
        action='store_true',
        help='Enable browser dynamic rendering for URL fetches.',
    )
    args = parser.parse_args()

    if args.d:
        DYNAMIC_RENDER_MODE = 'auto'

    print(
        f"[Startup] dynamic_render={DYNAMIC_RENDER_MODE}, "
        f"dynamic_render_domains={','.join(sorted(DYNAMIC_RENDER_DOMAINS)) or '(none)'}"
    )
    app.run(debug=True, host=args.host, port=args.port, threaded=True)
