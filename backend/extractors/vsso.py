from __future__ import annotations

import re
from html import unescape
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from .base import MetadataDict


RULE_NAME = 'VSSO Metadata Detail'
BASE_URL = 'https://vsso.nssdc.ac.cn'
API_URL = f'{BASE_URL}/nssdc/coreMetadata/getDetail'
API_HEADERS = {
    'User-Agent': 'metadata-extractor/1.0 (+https://localhost)',
    'Accept': 'application/json,text/plain,*/*',
    'Referer': f'{BASE_URL}/nssdc_zh/html/vssoinfo.html',
}


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value))
    text = re.sub(r'\s+', ' ', text).strip()
    return text or None


def _text_or_none(element) -> Optional[str]:
    if not element:
        return None
    if isinstance(element, str):
        return _clean_text(element)
    return _clean_text(element.get_text(' ', strip=True))


def _first_non_empty(*values: Optional[str]) -> Optional[str]:
    for value in values:
        text = _clean_text(value)
        if text:
            return text
    return None


def _strip_label_value(value: Optional[str]) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    if re.fullmatch(r'[\u4e00-\u9fffA-Za-z\s/（）()]+[:：]', text):
        return None
    return re.sub(r'^[\u4e00-\u9fffA-Za-z\s/（）()]+[:：]\s*', '', text).strip() or None


def _split_terms(value: Optional[str]) -> list[str]:
    text = _clean_text(value)
    if not text:
        return []
    parts = re.split(r'[;；,，、\|\s]+', text)
    return [item for item in (_clean_text(part) for part in parts) if item]


def _extract_id_text(soup: BeautifulSoup, element_id: str) -> Optional[str]:
    element = soup.select_one(f'#{element_id}')
    if not element:
        return None

    value = element.get('value') if hasattr(element, 'get') else None
    if value:
        return _clean_text(value)

    return _strip_label_value(_text_or_none(element))


def _extract_link_id(url: str, html: str = '') -> Optional[str]:
    parsed = urlparse(url or '')
    if parsed.query:
        query = parse_qs(parsed.query)
        for key in ('linkId', 'id'):
            if query.get(key):
                return _clean_text(query[key][0])
        if re.fullmatch(r'\d+', parsed.query):
            return parsed.query

    match = re.search(r'vssoinfo\.html\?(\d+)', url or html)
    if match:
        return match.group(1)
    return None


def _fetch_detail_data(url: str, html: str = '') -> Dict[str, Any]:
    link_id = _extract_link_id(url, html)
    if not link_id:
        return {}
    try:
        response = requests.get(API_URL, params={'linkId': link_id}, headers=API_HEADERS, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except Exception as error:
        print(f'[WARNING] VSSO detail API failed for linkId={link_id}: {error}')
        return {}
    if not isinstance(payload, dict) or payload.get('code') not in (0, None):
        return {}
    data = payload.get('coreMetadataDatasetInfo')
    return data if isinstance(data, dict) else {}


def _data_value(data: Dict[str, Any], key: str, fallback: Optional[str] = None) -> Optional[str]:
    value = data.get(key) if isinstance(data, dict) else None
    return _first_non_empty(value, fallback)


def _extract_leading_text(element) -> Optional[str]:
    if not element:
        return None

    parts: list[str] = []
    for child in element.children:
        if getattr(child, 'name', None) == 'br':
            break
        if isinstance(child, str):
            parts.append(child)
        else:
            parts.append(child.get_text(' ', strip=True))

    return _clean_text(' '.join(parts))


def _extract_main_description(soup: BeautifulSoup) -> Optional[str]:
    element = soup.select_one('#descriptionContentCh')
    if not element:
        return None

    text = _extract_leading_text(element)
    if text:
        return text

    return _text_or_none(element)


def _extract_identifier(soup: BeautifulSoup, html: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    cstr_text = _extract_id_text(soup, 'cstr')
    doi_text = _extract_id_text(soup, 'doi')
    hidden_doi = _extract_id_text(soup, 'hidden_doi')

    cstr_identifier = _extract_cstr_identifier(cstr_text)

    doi_value = _first_non_empty(doi_text, hidden_doi)
    identifier = cstr_identifier or doi_value or _first_non_empty(cstr_text, doi_value)

    if not identifier:
        identifier = _extract_cstr_identifier(html)

    return identifier, cstr_identifier, doi_value


def _extract_cstr_identifier(*values: Optional[str]) -> Optional[str]:
    pattern = re.compile(r'(?:CSTR\s*[:：]\s*)?(\d{5}\.\d{2}\.[-._;()/:A-Z0-9]+)', re.IGNORECASE)
    for value in values:
        match = pattern.search(str(value or ''))
        if match:
            return match.group(1).strip().strip('.,;，；')
    return None


def _extract_dataset_link(html: str) -> Optional[str]:
    match = re.search(r'getDataResource\("([^"]+)"\)', html)
    if match:
        return _clean_text(match.group(1))
    return None


def _extract_time_range(text: Optional[str]) -> Optional[Dict[str, Optional[str]]]:
    cleaned = _clean_text(text)
    if not cleaned:
        return None

    match = re.search(
        r'(\d{4}-\d{2}-\d{2})\s*(?:TO|to|至|到|—|-|–)\s*(\d{4}-\d{2}-\d{2})',
        cleaned,
        flags=re.IGNORECASE,
    )
    if match:
        return {'起始时间': match.group(1), '结束时间': match.group(2)}

    return {'起始时间': cleaned, '结束时间': None}


def _time_range_from_data(data: Dict[str, Any], fallback_text: Optional[str]) -> Optional[Dict[str, Optional[str]]]:
    begin = _clean_text(data.get('timeSpanBegin')) if isinstance(data, dict) else None
    end = _clean_text(data.get('timeSpanEnd')) if isinstance(data, dict) else None
    if begin or end:
        return {'起始时间': begin, '结束时间': end}
    return _extract_time_range(fallback_text)


def _extract_citation_format(soup: BeautifulSoup) -> Optional[str]:
    citation = _text_or_none(soup.select_one('#chineseQuotation'))
    if citation:
        return citation
    return None


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').strip().lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()

    return bool(
        'vsso.nssdc.ac.cn/nssdc_zh/html/vssoinfo.html' in normalized_url
        or 'page-vssoinfo' in combined
        or 'virtual space science observatory' in combined
        or '空间科学虚拟观测台' in combined
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[MetadataDict]:
    if not content:
        return None

    soup = BeautifulSoup(content, 'html.parser')
    html = content
    data = _fetch_detail_data(url, html)

    title_zh = _first_non_empty(_data_value(data, 'dataNameCh'), _extract_id_text(soup, 'dataNameCh'), title, _text_or_none(soup.title), url)
    title_en = _first_non_empty(_data_value(data, 'dataNameEn'), _extract_id_text(soup, 'dataNameEn'), title_zh, title)

    description = _first_non_empty(_data_value(data, 'desCh'), _extract_main_description(soup))
    description_en = _first_non_empty(_data_value(data, 'desEn'), description)
    keywords_zh = _split_terms(_data_value(data, 'keywordCh', _extract_id_text(soup, 'keywordCh')))
    keywords_en = _split_terms(_data_value(data, 'keywordEn')) or keywords_zh

    release_date = _data_value(data, 'releaseDate', _extract_id_text(soup, 'releaseDate'))
    version = _data_value(data, 'versionNum', _extract_id_text(soup, 'versionNum')) or _data_value(data, 'nowVersion', _extract_id_text(soup, 'nowVersion'))
    dataset_size = _data_value(data, 'datasetTotalSize', _extract_id_text(soup, 'datasetTotalSize'))
    time_range_text = _extract_id_text(soup, 'scopeServices')
    time_range = _time_range_from_data(data, time_range_text)

    sharing_method = _data_value(data, 'shareMathod', _extract_id_text(soup, 'shareMathod'))
    sharing_scope = _data_value(data, 'shareScope', _extract_id_text(soup, 'shareScope'))
    sharing_plan = _data_value(data, 'sharePlan', _extract_id_text(soup, 'sharingPlan'))
    application_procedure = _data_value(data, 'applicationProcedure', _extract_id_text(soup, 'applicationProcedure'))
    protection_period = _data_value(data, 'period', _extract_id_text(soup, 'protectionPeriod')) or _data_value(data, 'periodEnd')

    source_project = _data_value(data, 'sourceProjectCh', _extract_id_text(soup, 'sourceProjectChT'))
    source_project_en = _data_value(data, 'sourceProjectEn', source_project)
    instrument = _data_value(data, 'instrumentCh', _extract_id_text(soup, 'instrumentChT'))
    instrument_en = _data_value(data, 'instrumentEn', instrument)
    observatory = _data_value(data, 'observatoryCh', _extract_id_text(soup, 'observatoryChT'))
    observatory_en = _data_value(data, 'observatoryEn', observatory)

    producer = _data_value(data, 'dataProducerCh', _extract_id_text(soup, 'dataProducerChT'))
    producer_en = _data_value(data, 'dataProducerEn', producer)
    producer_tel = _data_value(data, 'dataProducerTel', _extract_id_text(soup, 'dataProducerTelT'))
    producer_email = _data_value(data, 'dataProducerEmail', _extract_id_text(soup, 'dataProducerEmailT'))

    license_text = _data_value(data, 'license', _extract_id_text(soup, 'sharingProtocol')) or 'CC BY 4.0'
    license_url = None
    license_anchor = soup.select_one('#sharingProtocol a[href]')
    if license_anchor and license_anchor.get('href'):
        license_url = _clean_text(license_anchor.get('href'))

    citation_format = _extract_citation_format(soup)
    download_url = _data_value(data, 'url', _extract_dataset_link(html))

    identifier, cstr_identifier, doi_identifier = _extract_identifier(soup, html)
    cstr_identifier = _extract_cstr_identifier(_data_value(data, 'cstr'), cstr_identifier)
    doi_identifier = _data_value(data, 'doi', doi_identifier)
    identifier = cstr_identifier or doi_identifier or identifier
    resource_url = url or download_url

    creators = [producer] if producer else None
    alternative_identifiers = [item for item in [doi_identifier] if item]

    subject_classification = _data_value(data, 'subjectCategory') or '空间科学'
    topic_classification = _data_value(data, 'themCategory') or '行星磁层与波粒相互作用'

    file_formats = ['sts', 'mat', 'cdf', 'txt']
    file_content = [
        'MAVEN MAG 磁场数据',
        'MAVEN STATIC 离子通量数据',
        'Juno WAVES 波动数据',
        'Juno MAG 背景磁场数据',
        'Cassini RPWS 波数据',
        'Cassini MAG 背景磁场数据',
        'Cassini CAPS 电子通量数据',
    ]

    zh: Dict[str, Any] = {
        '资源类型判定': '数据集',
        '领域判定': '数据集元数据',
        '标识符': identifier,
        'CSTR标识符': cstr_identifier,
        '资源名称': title_zh,
        '标题': title_zh,
        '创建者': creators,
        '发布机构': '国家空间科学数据中心',
        '发布日期': release_date,
        '描述': description,
        '关键词': keywords_zh,
        '学科分类': subject_classification,
        '语言': '中文',
        '贡献者': [observatory] if observatory else None,
        '替代标识符': alternative_identifiers if alternative_identifiers else None,
        '关联标识符': None,
        '权限': {
            '共享途径': sharing_method,
            '开放范围': sharing_scope,
            '开放状态': sharing_plan,
            '申请流程': application_procedure,
            '保护期说明': protection_period,
            '共享许可协议': license_text,
        },
        '资助者': None,
        '版本': version,
        '资源链接': resource_url,
        '资源类型': '数据集',
        '数据集基本信息': {
            '标识符': identifier,
            '标题': title_zh,
            '摘要': description,
            '关键词': keywords_zh,
            '范围': {
                '时间范围': time_range,
                '空间范围': None,
            },
            '语种': '中文',
            '文件内容': file_content,
            '基金项目': source_project,
            '数据量': dataset_size,
            '数据格式': file_formats,
            '数据集作者': {
                '作者姓名': creators,
                '工作单位': '武汉大学电子信息学院磁层空间天气实验室' if producer else None,
                '电子邮箱': producer_email,
                '工作贡献': '数据集生产、整理与发布' if producer else None,
                '作者简介': None,
            },
        },
        '数据集出版信息': {
            '发布日期': release_date,
            '出版期刊': None,
            '版本信息': version,
        },
        '数据集服务信息': {
            '数据集引用格式': citation_format,
            '数据集共享许可协议': license_text,
            '数据集使用声明': application_procedure,
            '数据集下载地址': download_url,
            '数据集访问地址': resource_url,
        },
        '扩展信息': {
            '共享途径': sharing_method,
            '开放范围': sharing_scope,
            '开放状态': sharing_plan,
            '保护期说明': protection_period,
            '数据生产者': producer,
            '联系电话': producer_tel,
            '电子邮箱': producer_email,
            '观测平台': observatory,
            '观测设备': instrument,
            '许可链接': license_url,
            '主题分类': topic_classification,
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
        'Publisher': 'National Space Science Data Center',
        'Publication Date': release_date,
        'Description': description_en,
        'Keywords': keywords_en,
        'Discipline Classification': subject_classification,
        'Language': 'Chinese',
        'Contributors': [observatory_en] if observatory_en else None,
        'Alternative Identifiers': alternative_identifiers if alternative_identifiers else None,
        'Related Identifiers': None,
        'Rights': {
            'Sharing Method': sharing_method,
            'Sharing Scope': sharing_scope,
            'Sharing Status': sharing_plan,
            'Application Procedure': application_procedure,
            'Protection Period': protection_period,
            'License': license_text,
        },
        'Funders': None,
        'Version': version,
        'Resource URL': resource_url,
        'ResourceType': 'Dataset',
        'Dataset Basic Information': {
            'Identifier': identifier,
            'Title': title_en,
            'Abstract': description_en,
            'Keywords': keywords_en,
            'Coverage': {
                'Time Range': time_range,
                'Spatial Range': None,
            },
            'Language': 'Chinese',
            'File Content': file_content,
            'Project/Funder': source_project_en,
            'Data Size': dataset_size,
            'Data Format': file_formats,
            'Dataset Authors': {
                'Author Name': [producer_en] if producer_en else None,
                'Affiliation': 'Magnetospheric Space Weather Laboratory, School of Electronic Information, Wuhan University' if producer else None,
                'Email': producer_email,
                'Contribution': 'Dataset production, curation, and release' if producer else None,
                'Biography': None,
            },
        },
        'Dataset Publication Information': {
            'Publication Date': release_date,
            'Journal': None,
            'Version Information': version,
        },
        'Dataset Service Information': {
            'Dataset Citation Format': citation_format,
            'Dataset License': license_text,
            'Dataset Usage Statement': application_procedure,
            'Dataset Download URL': download_url,
            'Dataset Access URL': resource_url,
        },
        'Extension Info': {
            'Sharing Method': sharing_method,
            'Sharing Scope': sharing_scope,
            'Sharing Status': sharing_plan,
            'Protection Period': protection_period,
            'Data Producer': producer,
            'Telephone': producer_tel,
            'Email': producer_email,
            'Observatory': observatory,
            'Instrument': instrument_en,
            'License URL': license_url,
            'Topic Classification': topic_classification,
        },
    }

    return {'zh': zh, 'en': en}
