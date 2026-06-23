from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlsplit, urlunsplit

from cstr_resolver import resolve_cstr
from doi_resolver import resolve_doi
from llm_api import qwen_chat, LABEL_TRANSLATIONS_EN
from get_id import get_typed_identifiers
from identifier import process_source_code
from upload_rule_extractor import extract_upload_metadata
from metadata_store import (
    get_latest_analysis_history_by_url,
    initialize_metadata_store,
    list_analysis_history,
    save_analysis_history,
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


def get_gateway_user():
    return {
        'id': request.headers.get('X-User-Id', ''),
        'name': request.headers.get('X-User-Name', ''),
        'email': request.headers.get('X-User-Email', ''),
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


def _lookup_history_payload(*, source='', url='', text=''):
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

    history_record = get_latest_analysis_history_by_url(requested_url=candidates[0], text='')
    if not history_record and len(candidates) > 1:
        history_record = get_latest_analysis_history_by_url(requested_url='', text='\n'.join(candidates[1:]))

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
    text = str(value or '').strip()
    if re.search(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', text, re.IGNORECASE):
        return 'DOI'
    if re.search(r'\d{5}\.\d{2}\.[-._;()/:A-Z0-9]+', text, re.IGNORECASE):
        return 'CSTR'
    if text.lower().startswith(('http://', 'https://')):
        return 'URL'
    return 'Other'


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
        if 'identifier' in value and 'type' in value:
            return value
        identifier = value.get('identifier') or value.get('value') or value.get('id')
        if identifier:
            return {'type': value.get('type') or _infer_identifier_type(identifier), 'identifier': identifier}
        return value

    text = _clean_scalar(value)
    if not text:
        return None
    return {'type': _infer_identifier_type(text), 'identifier': text}


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
                related.append(item)
                continue
            identifier = _normalize_identifier(item.get('identifier') or item.get('value') or item)
            related.append({
                'relation': item.get('relation') or 'Related',
                'type': item.get('type') or (identifier or {}).get('type') or 'Other',
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
    normalized['alternative_identifiers'] = _normalize_identifier_list(core.get('alternative_identifiers'))
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
            normalized[key] = _normalize_agents(value, lang)
        elif key in {'标识符', 'Identifier'}:
            normalized[key] = _normalize_identifier(value) or value
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
    merged['rights'] = _merge_lists(zh.get('rights'), en.get('rights')) or None
    merged['funders'] = _merge_lists(zh.get('funders'), en.get('funders')) or None
    merged['version'] = _first_non_missing(zh.get('version'), en.get('version'))
    merged['urls'] = _merge_lists(zh.get('urls'), en.get('urls')) or None
    merged['resource_type'] = _standard_resource_type(_first_non_missing(en.get('resource_type'), zh.get('resource_type')))

    return {key: merged.get(key) for key in CORE_FIELD_ALIASES_ZH.keys()}


def _extract_domain_answer(answer, language='zh'):
    if not isinstance(answer, dict):
        return {}

    if language == 'en':
        wrapper_keys = {
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
        wrapper_keys = {'数据集元数据', '数据论文元数据', '标准文献元数据', '生态科学数据元数据'}
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


def fetch_url_content(url):
    response = requests.get(url, headers=FETCH_HEADERS, timeout=15)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    html = response.text or ''
    text, title = _extract_text_from_html(html)
    return {
        'html': html,
        'text': text,
        'title': title,
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


def build_metadata_payload(text, mode, url='', title='', html='', strategy='auto'):
    if strategy == 'upload_rule':
        llm_answer = normalize_llm_answer(extract_upload_metadata(text, title=title))
    else:
        llm_answer = normalize_llm_answer(
            qwen_chat(text, mode, url=url, title=title, raw_html=html, strategy=strategy)
        )
    zh_answer = llm_answer.get('zh')
    en_answer = llm_answer.get('en')
    if not isinstance(zh_answer, dict) and not isinstance(en_answer, dict) and isinstance(llm_answer, dict):
        zh_answer = llm_answer
        en_answer = llm_answer
    if not isinstance(zh_answer, dict) or not isinstance(en_answer, dict):
        raise ValueError('LLM response must be a metadata object or contain zh and en objects')

    # 如果 LLM/规则在英文对象中使用了中文键名，则尝试把这些键名映射为英文。
    # 不再用中文结果补英文值，避免英文视图混入中文内容。
    en_answer = _map_keys_recursive(en_answer, LABEL_TRANSLATIONS_EN)

    # 提取并规范化核心元数据和领域元数据
    zh_core_source = _extract_core_answer(zh_answer, 'zh')
    en_core_source = _extract_core_answer(en_answer, 'en')
    core_zh = _pick_fields(zh_core_source, CORE_FIELD_ALIASES_ZH)
    core_en = _pick_fields(en_core_source, CORE_FIELD_ALIASES_EN)

    domain_zh = _extract_domain_answer(zh_answer, 'zh')
    domain_en = _extract_domain_answer(en_answer, 'en')

    # 将领域判定写回核心层，供前端切换领域表使用
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
    domain_zh = _normalize_domain_metadata_shape(domain_zh, 'zh')
    domain_en = _normalize_domain_metadata_shape(domain_en, 'en')

    core_metadata = _merge_core_language_variants(core_zh, core_en)
    domain_section_zh = _infer_domain_section(core_metadata.get('resource_type'), 'zh')

    merged_answer = {'核心元数据': {'metadatas': [core_metadata]}}
    if domain_zh:
        merged_answer[domain_section_zh] = domain_zh
    elif domain_en:
        merged_answer[domain_section_zh] = domain_en

    if url and html:
        try:
            record_id = save_analysis_history(
                requested_url=url,
                page_title=title,
                page_html=html,
                mode=mode,
                strategy=strategy,
                result_payload=merged_answer,
            )
            print(f"[DB] Saved analysis history record #{record_id}")
        except Exception as error:
            print(f"[DB WARNING] Failed to save analysis history: {error}")

    return merged_answer


def handle_identifier_request(data):
    mode = data.get('mode', 'common')
    items, error_payload = resolve_identifier_content(data)
    if error_payload:
        return jsonify({"status": "error", **error_payload}), 400

    results = []
    for item in items:
        if item.get('status') != 'ok':
            results.append(item)
            continue
        text = item.get('content', '')
        url = item.get('resolved_url', '')
        title = item.get('title', '')
        try:
            print("Asking LLM to process identifier content")
            print(
                f"[Request Debug] strategy=llm, text_len={len(text or '')}, html_len=0, url={url}"
            )
            payload = build_metadata_payload(text, mode, url=url, title=title, html='', strategy='auto')
            results.append({
                'identifier': item.get('identifier'),
                'type': item.get('type'),
                'resolved_url': url,
                'source': item.get('source'),
                'status': 'ok',
                'payload': payload,
                'updated_at': datetime.utcnow().isoformat() + 'Z',
            })
        except (json.JSONDecodeError, ValueError, TypeError) as error:
            print(f"LLM Error: {error}")
            results.append({
                'identifier': item.get('identifier'),
                'type': item.get('type'),
                'resolved_url': url,
                'source': item.get('source'),
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
        if not url:
            return jsonify({"status": "error", "message": "Missing URL"}), 400
        try:
            data = fetch_url_content(url)
            data['url'] = url
        except Exception as error:
            print(f"URL Fetch Error: {error}")
            return jsonify({"status": "error", "message": f"Failed to fetch URL: {error}"}), 400

    if not force_reanalyze:
        history_payload = _lookup_history_payload(
            source=source,
            url=data.get('url', ''),
            text=data.get('text', ''),
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
    print("Asking LLM to process text" if strategy != 'upload_rule' else "Using upload rule extractor")
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
    history_payload = _lookup_history_payload(source='url', url=url, text=text)
    if not history_payload:
        return jsonify({'found': False})

    return jsonify({'found': True, **history_payload})

@app.route('/history', methods=['GET'])
def history():
    limit = request.args.get('limit', 20)
    offset = request.args.get('offset', 0)
    try:
        records = list_analysis_history(limit=limit, offset=offset)
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
    app.run(debug=True, host='127.0.0.1', port=4000, threaded=True)
