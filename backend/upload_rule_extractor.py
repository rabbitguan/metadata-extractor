from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, Iterable, Optional


DOI_PATTERN = re.compile(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', re.IGNORECASE)
CSTR_PATTERN = re.compile(r'^(?:CSTR\s*[:：]\s*)?([A-Z0-9]{5}\.\d{2}\.[-._;()/:A-Z0-9]+)$', re.IGNORECASE)

DOMAIN_KEY_TRANSLATIONS_ZH = {
    'Dataset Basic Information': '数据集基本信息',
    'Dataset Publication Information': '数据集出版信息',
    'Dataset Service Information': '数据集服务信息',
    'Data Paper Content Information': '数据论文内容信息',
    'Data Paper Publication Information': '数据论文出版信息',
    'Data Paper Service Information': '数据论文服务信息',
    'Title': '标题',
    'Identifier': '标识符',
    'Abstract': '摘要',
    'Keywords': '关键词',
    'Scope': '范围',
    'Time Range': '时间范围',
    'Spatial Range': '空间范围',
    'Language': '语种',
    'File Content': '文件内容',
    'Funding Project': '基金项目',
    'Data Volume': '数据量',
    'Data Format': '数据格式',
    'Dataset Authors': '数据集作者',
    'Data Paper Authors': '数据论文作者',
    'Author Name': '作者姓名',
    'Affiliation': '工作单位',
    'Email': '电子邮箱',
    'Contribution': '工作贡献',
    'Biography': '作者简介',
    'Introduction': '引言',
    'Data Collection and Processing Methods': '数据采集和处理方法',
    'Data Sample Description': '数据样本描述',
    'Data Quality Control and Evaluation': '数据质量控制和评估',
    'Data Use Methods and Recommendations': '数据使用方法和建议',
    'References': '参考文献',
    'Acknowledgements': '致谢',
    'Received Date': '收稿日期',
    'Review Date': '同评日期',
    'Accepted Date': '录用日期',
    'Publication Date': '出版日期',
    'Version Information': '版本信息',
    'Journal': '出版期刊',
    'Dataset Citation': '数据集引用格式',
    'Dataset License': '数据集共享许可协议',
    'Dataset Usage Statement': '数据集使用声明',
    'Dataset Download URL': '数据集下载地址',
    'Dataset Paper URL': '数据论文访问地址',
    'Data Paper Citation': '数据论文引用格式',
    'Data Paper Download URL': '数据论文下载地址',
    'Data Paper License': '数据论文共享许可协议',
    'Dataset Access URL': '数据集访问地址',
    'Resource Name': '资源名称',
    'Resource Identifier': '资源标识符',
    'Subject Classification': '学科分类',
    'Dataset Creators': '数据集创建者',
    'Creation Date': '创建日期',
    'Last Modified Date': '最近修改日期',
    'Use Restrictions': '使用限制',
    'Identification Information': '标识信息',
    'Data Content Information': '数据内容信息',
    'Data Entity': '数据实体',
    'Entity Name': '实体名称',
    'Entity Description': '实体描述',
    'Entity Type': '实体类型',
    'Data Quality and Methods': '数据质量与方法',
    'Data Quality Description': '数据质量描述',
    'Data Generation Method': '数据产生方法',
    'Quality Control Description': '质量控制说明',
    'Data Source': '数据源',
    'Spatial and Temporal Coverage': '空间与时间覆盖范围',
    'Geographic Description': '地理范围描述',
    'West Bounding Longitude': '西部边界经度',
    'East Bounding Longitude': '东部边界经度',
    'South Bounding Latitude': '南部边界纬度',
    'North Bounding Latitude': '北部边界纬度',
    'Start Time': '起始时间',
    'End Time': '结束时间',
    'Project and Funding Information': '项目与资助信息',
    'Project Name': '项目名称',
    'Project Code': '项目代码',
    'Funding Source': '资金来源',
    'Distribution and Citation Information': '分发与引用信息',
    'Dataset Access or Download URL': '数据集访问或下载地址',
    'Record Status': '记录状态',
    'Record Identifier': '记录识别符',
    'Record Date': '记录日期',
    'Standard Number': '标准号',
    'Issuing Agency': '发布机构',
    'Standard Status': '标准状态',
    'Implementation or Trial Date': '实施或试行日期',
    'Confirmation Date': '确认日期',
    'Replaced Standard': '被代替标准',
    'Amendment': '修改件',
    'Supplement': '补充件',
    'Second Standard Number': '第二标准号',
    'Approval Organization': '批准单位',
    'Chinese Standard Name': '中文标准名称',
    'Original Standard Name': '原文标准名称',
    'English Standard Name': '英文标准名称',
    'Issuing Agency Code': '发布机构代码',
    'Chinese Classification for Standards': '中国标准分类号',
    'International Classification for Standards': '国际标准分类号',
    'Effective Region': '有效区域',
    'Abolition Date': '废止日期',
    'Original Classification Number': '原分类号',
    'Drafting Organization': '起草单位',
    'Deadline': '截止日期',
    'Text Language': '正文语种',
    'Publishing Organization': '出版单位',
    'Audit Item': '稽核项',
    'Translation': '译文',
    'Price': '价格',
    'Other Carrier': '其他载体',
    'Chinese Abstract': '中文文摘',
    'English Abstract': '英文文摘',
    'English Subject Terms': '英文主题词',
    'Note': '附注',
    'Document Source': '文献出处',
    'Replacing Standard': '代替标准',
    'Cited Documents': '引用文件',
    'Related Laws': '相关法律',
    'Consistency Degree': '一致性程度',
    'Modified Standard': '被修改件',
    'Supplemented Standard': '被补充件',
    'Chinese Subject Terms': '中文主题词',
    'Chinese Free Terms': '中文自由词',
    'Original Subject Terms': '原文主题词',
    'Call Number': '索取号',
    'Holding Flag': '馆藏标志',
    'Sort Code': '排序码',
    'Standard Type': '标准类型',
    'Document Type': '文献类型',
    'Volume Issue Number': '卷期号',
    'Document Code': '文献代号',
    'Publication Cycle': '出版周期',
    'Publication Place': '出版地',
    'Security Classification': '密级',
    'Proposing Organization': '提出单位',
    'Technical Committee': '归口单位',
    'Country': '国别',
    'Indexing Basis': '标引依据',
    'Update Batch Number': '更新批号',
    'Standard History': '标准历史',
    'Participating Organization': '参建单位',
    'Electronic File Name': '电子文件名称',
}

DOMAIN_KEY_TRANSLATIONS_EN = {value: key for key, value in DOMAIN_KEY_TRANSLATIONS_ZH.items()}
DOMAIN_KEY_TRANSLATIONS_ZH.update({
    'dataset_basic_information': '数据集基本信息',
    'dataset_publication_information': '数据集出版信息',
    'dataset_service_information': '数据集服务信息',
    'data_paper_content_information': '数据论文内容信息',
    'data_paper_publication_information': '数据论文出版信息',
    'data_paper_service_information': '数据论文服务信息',
    'title': '标题',
    'identifier': '标识符',
    'abstract': '摘要',
    'keywords': '关键词',
    'language': '语种',
    'publication_date': '出版日期',
    'version_information': '版本信息',
    'journal': '出版期刊',
    'dataset_download_url': '数据集下载地址',
    'data_paper_download_url': '数据论文下载地址',
    'dataset_access_url': '数据集访问地址',
})
DOMAIN_KEY_TRANSLATIONS_EN.update({
    'dataset_basic_information': 'Dataset Basic Information',
    'dataset_publication_information': 'Dataset Publication Information',
    'dataset_service_information': 'Dataset Service Information',
    'data_paper_content_information': 'Data Paper Content Information',
    'data_paper_publication_information': 'Data Paper Publication Information',
    'data_paper_service_information': 'Data Paper Service Information',
    'title': 'Title',
    'identifier': 'Identifier',
    'abstract': 'Abstract',
    'keywords': 'Keywords',
    'language': 'Language',
    'publication_date': 'Publication Date',
    'version_information': 'Version Information',
    'journal': 'Journal',
    'dataset_download_url': 'Dataset Download URL',
    'data_paper_download_url': 'Data Paper Download URL',
    'dataset_access_url': 'Dataset Access URL',
})


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
    return bool(_normalize_doi_identifier(value))


def _is_cstr(value: Any) -> bool:
    return bool(_normalize_cstr_identifier(value))


def _normalize_cstr_identifier(value: Any) -> Optional[str]:
    match = CSTR_PATTERN.match(str(value or '').strip().strip('.,;，；'))
    return match.group(1) if match else None


def _normalize_doi_identifier(value: Any) -> Optional[str]:
    match = DOI_PATTERN.search(str(value or '').strip().strip('.,;，；'))
    return match.group(0) if match else None


def _normalize_identifier_item(value: Any, preferred_type: Any = None) -> Optional[Dict[str, str]]:
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


def _format_identifier_display(value: Any, language: str = 'zh') -> Optional[str]:
    normalized = _normalize_identifier_item(
        value.get('identifier') if isinstance(value, dict) else value,
        preferred_type=value.get('type') if isinstance(value, dict) else None,
    )
    if not normalized:
        return None
    return f"{normalized['type']}:{normalized['identifier']}"


def _is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ''
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _lower_key_map(data: Dict[str, Any]) -> Dict[str, Any]:
    return {str(key).strip().lower(): value for key, value in data.items()}


def _canonical_key(value: Any) -> str:
    return re.sub(r'[\s_\-]+', '', str(value or '').strip().lower())


def _canonical_key_map(data: Dict[str, Any]) -> Dict[str, Any]:
    return {_canonical_key(key): value for key, value in data.items()}


def _translate_key(key: Any, translations: Dict[str, str]) -> str:
    text = str(key)
    if text in translations:
        return translations[text]
    canonical = _canonical_key(text)
    for source_key, target_key in translations.items():
        if _canonical_key(source_key) == canonical:
            return target_key
    return text


def _translate_keys_recursive(value: Any, translations: Dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {
            _translate_key(key, translations): _translate_keys_recursive(item, translations)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_translate_keys_recursive(item, translations) for item in value]
    return value


def _first(data: Dict[str, Any], *keys: str) -> Any:
    if not isinstance(data, dict):
        return None
    lowered = _lower_key_map(data)
    canonical = _canonical_key_map(data)
    for key in keys:
        if key in data:
            return data.get(key)
        normalized = key.lower()
        if normalized in lowered:
            return lowered.get(normalized)
        canonical_key = _canonical_key(key)
        if canonical_key in canonical:
            return canonical.get(canonical_key)
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
    if isinstance(domain, dict):
        return domain

    for key in (
        '数据集元数据',
        'Dataset Metadata',
        '数据论文元数据',
        'Data Paper Metadata',
        '标准文献元数据',
        'Standard Literature Metadata',
        '生态科学数据元数据',
        'Ecological Science Data Metadata',
        '其他元数据',
        'Other Metadata',
    ):
        domain = _first(payload, key)
        if isinstance(domain, dict):
            return domain

    domain_section_keys = (
        'dataset_basic_information',
        'Dataset Basic Information',
        '数据集基本信息',
        'dataset_publication_information',
        'Dataset Publication Information',
        '数据集出版信息',
        'dataset_service_information',
        'Dataset Service Information',
        '数据集服务信息',
        'data_paper_content_information',
        'Data Paper Content Information',
        '数据论文内容信息',
        'data_paper_publication_information',
        'Data Paper Publication Information',
        '数据论文出版信息',
        'data_paper_service_information',
        'Data Paper Service Information',
        '数据论文服务信息',
        'standard_literature_information',
        'Standard Literature Information',
        '标准文献信息',
        'ecological_identification_information',
        'Identification Information',
        '标识信息',
        'ecological_data_content_information',
        'Data Content Information',
        '数据内容信息',
        'ecological_data_quality_and_methods',
        'Data Quality and Methods',
        '数据质量与方法',
        'ecological_spatial_and_temporal_coverage',
        'Spatial and Temporal Coverage',
        '空间与时间覆盖范围',
        'ecological_project_and_funding_information',
        'Project and Funding Information',
        '项目与资助信息',
        'ecological_distribution_and_citation_information',
        'Distribution and Citation Information',
        '分发与引用信息',
    )
    if any(_first(payload, key) is not None for key in domain_section_keys):
        return payload

    return {}


def _normalize_resource_type(value: Any) -> tuple[str, str, str, str]:
    text = _clean_text(value) or ''
    normalized = text.lower()
    if text in {'数据集'} or normalized in {'dataset', 'data set'}:
        return '数据集', 'Dataset', '数据集元数据', 'Dataset Metadata'
    if text in {'数据论文'} or normalized in {'data_paper', 'data paper', 'paper'}:
        return '数据论文', 'Data Paper', '数据论文元数据', 'Data Paper Metadata'
    if text in {'标准文献'} or normalized in {'standard_literature', 'standard literature', 'standard'}:
        return '标准文献', 'Standard Literature', '标准文献元数据', 'Standard Literature Metadata'
    if text in {'生态科学数据'} or normalized in {'ecological_data', 'ecological data', 'ecological science data'}:
        return '生态科学数据', 'Ecological Data', '生态科学数据元数据', 'Ecological Science Data Metadata'
    return '其他', 'Other', '核心元数据', 'Core Metadata'


def _list_field(data: Dict[str, Any], *keys: str) -> Optional[list]:
    value = _first(data, *keys)
    values = _unique_list(_ensure_list(value))
    return values or None


def _structured_field(data: Dict[str, Any], *keys: str) -> Any:
    value = _first(data, *keys)
    if isinstance(value, (dict, list)):
        return value
    values = _unique_list(_ensure_list(value))
    return values or None


def _structured_scalar_field(data: Dict[str, Any], *keys: str) -> Any:
    value = _first(data, *keys)
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        if value and isinstance(value[0], dict):
            return value[0]
        return _clean_text(value[0]) if value else None
    return _clean_text(value)


def _identifier_candidates(value: Any) -> Iterable[tuple[Any, Any]]:
    for item in _ensure_list(value):
        if isinstance(item, dict):
            yield item.get('identifier') or item.get('value') or item.get('id'), item.get('type')
        else:
            yield item, None


def _normalize_identifier_list(value: Any) -> Optional[list]:
    items = []
    seen = set()
    for candidate, preferred_type in _identifier_candidates(value):
        normalized = _normalize_identifier_item(candidate, preferred_type=preferred_type)
        if not normalized:
            continue
        marker = (normalized['type'], normalized['identifier'].lower())
        if marker in seen:
            continue
        seen.add(marker)
        items.append(normalized)
    return items or None


def _normalize_related_identifier_list(value: Any) -> Optional[list]:
    items = []
    for item in _ensure_list(value):
        if isinstance(item, dict):
            raw_identifier = item.get('identifier')
            if isinstance(raw_identifier, dict):
                identifier = _normalize_identifier_item(
                    raw_identifier.get('identifier') or raw_identifier.get('value') or raw_identifier.get('id'),
                    preferred_type=raw_identifier.get('type'),
                )
            else:
                identifier = _normalize_identifier_item(
                    raw_identifier or item.get('value') or item.get('id'),
                    preferred_type=item.get('type'),
                )
            if identifier:
                items.append({
                    'relation': item.get('relation') or 'Related',
                    'type': identifier['type'],
                    'identifier': identifier,
                })
            continue
        identifier = _normalize_identifier_item(item)
        if identifier:
            items.append({'relation': 'Related', 'type': identifier['type'], 'identifier': identifier})
    return items or None


def _scalar_field(data: Dict[str, Any], *keys: str) -> Optional[str]:
    value = _first(data, *keys)
    if isinstance(value, list):
        return _clean_text(value[0]) if value else None
    return _clean_text(value)


def _extract_identifier_fields(core: Dict[str, Any]) -> tuple[Optional[str], Optional[list]]:
    raw_cstr = _scalar_field(core, 'cstr_identifier', 'cstrIdentifier', 'CSTR标识符', 'identifier', 'Identifier')
    alternative_raw = _structured_field(core, 'alternative_identifiers', 'alternativeIdentifiers', '替代标识符', 'Alternative Identifiers')
    alternative = _normalize_identifier_list(alternative_raw) or []
    doi = _scalar_field(core, 'doi', 'DOI')
    doi_identifier = _normalize_identifier_item(doi, preferred_type='DOI') if doi else None
    if doi_identifier:
        alternative.append(doi_identifier)

    normalized_cstr = _normalize_cstr_identifier(raw_cstr)
    if normalized_cstr:
        cstr_identifier = f'CSTR:{normalized_cstr}'
    else:
        cstr_identifier = None
        identifier = _normalize_identifier_item(raw_cstr)
        if identifier:
            alternative.append(identifier)

    return cstr_identifier, _normalize_identifier_list(alternative)


def _format_domain_identifier(identifier: Optional[str], language: str = 'zh') -> Optional[str]:
    cleaned = _clean_text(identifier)
    if not cleaned:
        return None
    return _format_identifier_display(cleaned, language=language)


def _pick_domain_identifier(cstr_identifier: Optional[str], alternative_identifiers: Optional[list], language: str = 'zh') -> Optional[str]:
    if cstr_identifier:
        return _format_domain_identifier(cstr_identifier, language=language)

    for identifier in alternative_identifiers or []:
        normalized = _normalize_identifier_item(
            identifier.get('identifier') if isinstance(identifier, dict) else identifier,
            preferred_type=identifier.get('type') if isinstance(identifier, dict) else None,
        )
        if normalized and normalized.get('type') == 'CSTR':
            return _format_identifier_display(normalized, language=language)

    for identifier in alternative_identifiers or []:
        normalized = _normalize_identifier_item(
            identifier.get('identifier') if isinstance(identifier, dict) else identifier,
            preferred_type=identifier.get('type') if isinstance(identifier, dict) else None,
        )
        if normalized:
            return _format_identifier_display(normalized, language=language)

    return None


def _fill_missing_identifier(section: Any, key: str, value: Optional[str]) -> Any:
    if not isinstance(section, dict) or not value:
        return section
    if _is_missing_value(section.get(key)):
        section[key] = value
    return section


def _filter_domain_identifiers(value: Any, language: str = 'zh') -> Any:
    if isinstance(value, list):
        return [_filter_domain_identifiers(item, language=language) for item in value]
    if not isinstance(value, dict):
        return value

    filtered = {}
    for key, item in value.items():
        if key in {'标识符', 'Identifier', '资源标识符', 'Resource Identifier'}:
            filtered[key] = _format_identifier_display(item, language=language)
        else:
            filtered[key] = _filter_domain_identifiers(item, language=language)
    return filtered


def _domain_sections(
    domain: Dict[str, Any],
    resource_type_zh: str,
    resource_type_en: str,
    cstr_identifier: Optional[str] = None,
    alternative_identifiers: Optional[list] = None,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    identifier_zh = _pick_domain_identifier(cstr_identifier, alternative_identifiers, language='zh')
    identifier_en = _pick_domain_identifier(cstr_identifier, alternative_identifiers, language='en')

    if resource_type_zh == '数据集':
        scoped_domain = _first(domain, '数据集元数据', 'Dataset Metadata')
        if isinstance(scoped_domain, dict):
            domain = scoped_domain
        basic = _first(domain, 'dataset_basic_information', 'Dataset Basic Information', '数据集基本信息')
        publication = _first(domain, 'dataset_publication_information', 'Dataset Publication Information', '数据集出版信息')
        service = _first(domain, 'dataset_service_information', 'Dataset Service Information', '数据集服务信息')
        basic_zh = _translate_keys_recursive(basic, DOMAIN_KEY_TRANSLATIONS_ZH) if isinstance(basic, dict) else {}
        basic_en = _translate_keys_recursive(basic, DOMAIN_KEY_TRANSLATIONS_EN) if isinstance(basic, dict) else {}
        basic_zh = _filter_domain_identifiers(basic_zh, language='zh')
        basic_en = _filter_domain_identifiers(basic_en, language='en')
        _fill_missing_identifier(basic_zh, '标识符', identifier_zh)
        _fill_missing_identifier(basic_en, 'Identifier', identifier_en)
        return (
            {
                '数据集基本信息': basic_zh,
                '数据集出版信息': _translate_keys_recursive(publication, DOMAIN_KEY_TRANSLATIONS_ZH) if isinstance(publication, dict) else {},
                '数据集服务信息': _translate_keys_recursive(service, DOMAIN_KEY_TRANSLATIONS_ZH) if isinstance(service, dict) else {},
            },
            {
                'Dataset Basic Information': basic_en,
                'Dataset Publication Information': _translate_keys_recursive(publication, DOMAIN_KEY_TRANSLATIONS_EN) if isinstance(publication, dict) else {},
                'Dataset Service Information': _translate_keys_recursive(service, DOMAIN_KEY_TRANSLATIONS_EN) if isinstance(service, dict) else {},
            },
        )

    if resource_type_en == 'Data Paper':
        scoped_domain = _first(domain, '数据论文元数据', 'Data Paper Metadata')
        if isinstance(scoped_domain, dict):
            domain = scoped_domain
        content = _first(domain, 'data_paper_content_information', 'Data Paper Content Information', '数据论文内容信息')
        publication = _first(domain, 'data_paper_publication_information', 'Data Paper Publication Information', '数据论文出版信息')
        service = _first(domain, 'data_paper_service_information', 'Data Paper Service Information', '数据论文服务信息')
        content_zh = _translate_keys_recursive(content, DOMAIN_KEY_TRANSLATIONS_ZH) if isinstance(content, dict) else {}
        content_en = _translate_keys_recursive(content, DOMAIN_KEY_TRANSLATIONS_EN) if isinstance(content, dict) else {}
        content_zh = _filter_domain_identifiers(content_zh, language='zh')
        content_en = _filter_domain_identifiers(content_en, language='en')
        _fill_missing_identifier(content_zh, '标识符', identifier_zh)
        _fill_missing_identifier(content_en, 'Identifier', identifier_en)
        return (
            {
                '数据论文内容信息': content_zh,
                '数据论文出版信息': _translate_keys_recursive(publication, DOMAIN_KEY_TRANSLATIONS_ZH) if isinstance(publication, dict) else {},
                '数据论文服务信息': _translate_keys_recursive(service, DOMAIN_KEY_TRANSLATIONS_ZH) if isinstance(service, dict) else {},
            },
            {
                'Data Paper Content Information': content_en,
                'Data Paper Publication Information': _translate_keys_recursive(publication, DOMAIN_KEY_TRANSLATIONS_EN) if isinstance(publication, dict) else {},
                'Data Paper Service Information': _translate_keys_recursive(service, DOMAIN_KEY_TRANSLATIONS_EN) if isinstance(service, dict) else {},
            },
        )

    if resource_type_en == 'Standard Literature':
        scoped_domain = _first(domain, '标准文献元数据', 'Standard Literature Metadata')
        if isinstance(scoped_domain, dict):
            domain = scoped_domain
        info = _first(domain, 'standard_literature_information', 'Standard Literature Information', '标准文献信息')
        if not isinstance(info, dict):
            info = domain
        info_zh = _translate_keys_recursive(info, DOMAIN_KEY_TRANSLATIONS_ZH) if isinstance(info, dict) else {}
        info_en = _translate_keys_recursive(info, DOMAIN_KEY_TRANSLATIONS_EN) if isinstance(info, dict) else {}
        return (
            {'标准文献信息': _filter_domain_identifiers(info_zh, language='zh')},
            {'Standard Literature Information': _filter_domain_identifiers(info_en, language='en')},
        )

    if resource_type_en == 'Ecological Data':
        scoped_domain = _first(domain, '生态科学数据元数据', 'Ecological Science Data Metadata')
        if isinstance(scoped_domain, dict):
            domain = scoped_domain

        section_pairs = [
            ('标识信息', 'Identification Information', ('ecological_identification_information', 'Identification Information', '标识信息')),
            ('数据内容信息', 'Data Content Information', ('ecological_data_content_information', 'Data Content Information', '数据内容信息')),
            ('数据质量与方法', 'Data Quality and Methods', ('ecological_data_quality_and_methods', 'Data Quality and Methods', '数据质量与方法')),
            ('空间与时间覆盖范围', 'Spatial and Temporal Coverage', ('ecological_spatial_and_temporal_coverage', 'Spatial and Temporal Coverage', '空间与时间覆盖范围')),
            ('项目与资助信息', 'Project and Funding Information', ('ecological_project_and_funding_information', 'Project and Funding Information', '项目与资助信息')),
            ('分发与引用信息', 'Distribution and Citation Information', ('ecological_distribution_and_citation_information', 'Distribution and Citation Information', '分发与引用信息')),
        ]
        zh_sections: Dict[str, Any] = {}
        en_sections: Dict[str, Any] = {}
        for zh_key, en_key, aliases in section_pairs:
            section = _first(domain, *aliases)
            zh_section = _translate_keys_recursive(section, DOMAIN_KEY_TRANSLATIONS_ZH) if isinstance(section, dict) else {}
            en_section = _translate_keys_recursive(section, DOMAIN_KEY_TRANSLATIONS_EN) if isinstance(section, dict) else {}
            zh_sections[zh_key] = _filter_domain_identifiers(zh_section, language='zh')
            en_sections[en_key] = _filter_domain_identifiers(en_section, language='en')
        return zh_sections, en_sections

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

    titles = _structured_field(core, 'title', 'titles', '标题', 'Title') or ([title] if title else None)
    description = _structured_field(core, 'description', 'descriptions', '描述', 'Description', 'abstract', '摘要')
    keywords = _structured_field(core, 'keywords', '关键词', 'Keywords')
    subjects = _structured_field(core, 'subjects', '学科', 'Subjects')
    resource_urls = _structured_field(core, 'resource_url', 'resource_urls', 'urls', '资源链接', 'Resource URL')

    zh: Dict[str, Any] = {
        'titles': titles,
        'identifier': cstr_identifier,
        'creators': _structured_field(core, 'creators', '创建者', 'Creators'),
        'publisher': _structured_scalar_field(core, 'publisher', '发布机构', 'Publisher'),
        'publish_date': _scalar_field(core, 'publication_date', 'publish_date', '发布日期', 'Publication Date'),
        'descriptions': description,
        'keywords': keywords,
        'subjects': subjects,
        'language': _scalar_field(core, 'language', '语言', 'Language'),
        'contributors': _structured_field(core, 'contributors', '贡献者', 'Contributors'),
        'alternative_identifiers': alternative_identifiers,
        'related_identifiers': _normalize_related_identifier_list(_structured_field(core, 'related_identifiers', '关联标识符', 'Related Identifiers')),
        'rights': _structured_field(core, 'rights', '权限', 'Rights'),
        'funders': _structured_field(core, 'funders', '资助者', 'Funders'),
        'version': _scalar_field(core, 'version', '版本', 'Version'),
        'urls': resource_urls,
        'resource_type': resource_type_zh,
        'domain_metadata': domain_zh,
        'extension_info': _scalar_field(payload, 'extension_info', '扩展信息', 'Extension Info'),
    }
    en: Dict[str, Any] = {
        'titles': titles,
        'identifier': cstr_identifier,
        'creators': zh['creators'],
        'publisher': zh['publisher'],
        'publish_date': zh['publish_date'],
        'descriptions': description,
        'keywords': keywords,
        'subjects': subjects,
        'language': zh['language'],
        'contributors': zh['contributors'],
        'alternative_identifiers': alternative_identifiers,
        'related_identifiers': zh['related_identifiers'],
        'rights': zh['rights'],
        'funders': zh['funders'],
        'version': zh['version'],
        'urls': resource_urls,
        'resource_type': resource_type_en,
        'domain_metadata': domain_en,
        'extension_info': zh['extension_info'],
    }

    domain_zh_sections, domain_en_sections = _domain_sections(
        domain,
        resource_type_zh,
        resource_type_en,
        cstr_identifier=cstr_identifier,
        alternative_identifiers=alternative_identifiers,
    )
    zh.update(domain_zh_sections)
    en.update(domain_en_sections)

    return {'zh': zh, 'en': en}
