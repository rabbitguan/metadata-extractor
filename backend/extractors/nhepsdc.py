from __future__ import annotations

import re
from html import unescape
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import MetadataDict


RULE_NAME = 'NHEPSDC Resource Detail'

PUBLISHER_ZH = '国家高能物理科学数据中心'
PUBLISHER_EN = 'National High Energy Physics Scientific Data Center'
CSTR_PATTERN = re.compile(r'\b(?:CSTR\s*[:：]\s*)?([A-Z0-9]{5}\.\d{2}\.[-._;()/:A-Z0-9]+)\b', re.IGNORECASE)
DOI_PATTERN = re.compile(r'\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b')


def _clean_text(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value))
    text = re.sub(r'[\u200b\xa0]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text or None


def _clean_multiline_text(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value))
    text = re.sub(r'[\u200b\xa0]+', ' ', text)
    lines = [_clean_text(line) for line in re.split(r'[\r\n]+', text)]
    return '\n'.join(line for line in lines if line) or None


def _text_or_none(element) -> Optional[str]:
    if not element:
        return None
    if isinstance(element, str):
        return _clean_text(element)
    return _clean_text(element.get_text(' ', strip=True))


def _first_non_empty(*values: Optional[Any]) -> Optional[str]:
    for value in values:
        cleaned = _clean_text(value)
        if cleaned:
            return cleaned
    return None


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


def _split_terms(value: Optional[Any]) -> list[str]:
    text = _clean_text(value)
    if not text:
        return []
    return _unique_list(re.split(r'[;；,，、|]+|\s{2,}', text))


def _rights_description(values: Dict[str, Any]) -> Optional[str]:
    description_parts = []
    for key, value in values.items():
        if key == '许可协议':
            continue
        cleaned = _clean_text(value)
        if cleaned:
            description_parts.append(f'{key}: {cleaned}')
    return '；'.join(description_parts) or None


def _extract_info_rows(soup: BeautifulSoup) -> Dict[str, Any]:
    rows: Dict[str, Any] = {}
    for row in soup.select('.detail-info .info-row'):
        label = _text_or_none(row.select_one('.info-label'))
        if not label:
            continue

        tags = [_text_or_none(item) for item in row.select('.tag')]
        tags = [item for item in tags if item]
        if tags:
            rows[label] = tags
            continue

        value_node = None
        children = [child for child in row.find_all(recursive=False) if getattr(child, 'name', None)]
        for child in children:
            if 'info-label' not in (child.get('class') or []):
                value_node = child
                break
        rows[label] = _text_or_none(value_node or row)
    return rows


def _extract_table_labels(soup: BeautifulSoup) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for label_cell in soup.select('.meta-table td.label'):
        label = _text_or_none(label_cell)
        value_cell = label_cell.find_next_sibling('td')
        if not label or not value_cell:
            continue

        tag_values = [_text_or_none(item) for item in value_cell.select('.field-tag')]
        tag_values = [item for item in tag_values if item]
        value = '；'.join(tag_values) if tag_values else _text_or_none(value_cell)
        if value:
            values[label] = value
    return values


def _extract_markdown_card(soup: BeautifulSoup) -> Optional[str]:
    template = soup.select_one('#defaultMarkdownTemplate')
    if not template:
        return None

    raw = template.string if template.string is not None else template.decode_contents()
    parsed = BeautifulSoup(raw or '', 'html.parser')
    for br in parsed.find_all('br'):
        br.replace_with('\n')
    text = parsed.get_text('\n', strip=True)
    return _clean_multiline_text(text)


def _extract_identifier(info_rows: Dict[str, Any], soup: BeautifulSoup) -> tuple[Optional[str], Optional[str], Optional[str]]:
    raw_identifier = info_rows.get('数据标识')
    if isinstance(raw_identifier, list):
        raw_identifier = raw_identifier[0] if raw_identifier else None
    identifier_text = _clean_text(raw_identifier)

    if not identifier_text:
        anchor = soup.select_one('.info-row a.card-link[href*="CSTR"], .info-row a.card-link[href*="cstr"]')
        identifier_text = _text_or_none(anchor)
        if not identifier_text and anchor and anchor.get('href'):
            identifier_text = _clean_text(anchor.get('href'))

    cstr_match = CSTR_PATTERN.search(identifier_text or '')
    cstr_identifier = cstr_match.group(1) if cstr_match else None
    identifier = cstr_identifier
    identifier_url = None

    anchor = soup.select_one('.info-row a.card-link[href]')
    if anchor and anchor.get('href'):
        identifier_url = _clean_text(anchor.get('href'))

    return identifier, cstr_identifier, identifier_url


def _extract_doi(*values: Optional[Any]) -> Optional[str]:
    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        match = DOI_PATTERN.search(text)
        if match:
            return match.group(0).rstrip('.,;。；')
    return None


def _alternative_identifiers(doi: Optional[str]) -> Optional[list[Dict[str, str]]]:
    return [{'type': 'DOI', 'identifier': doi}] if doi else None


def _person_agent(name: str) -> Dict[str, Any]:
    return {
        'type': 'Person',
        'person': {
            'names': [{'lang': 'zh', 'name': name}],
            'emails': None,
            'identifiers': None,
            'affiliations': None,
        },
    }


def _organization_agent(name: str, lang: str = 'zh') -> Dict[str, Any]:
    return {
        'type': 'Organize',
        'affiliation': {
            'names': [{'lang': lang, 'name': name}],
            'identifiers': None,
        },
    }


def _extract_file_size(soup: BeautifulSoup) -> Optional[str]:
    for meta_node in soup.select('.file-info .meta'):
        text = _clean_text(meta_node.get_text(' ', strip=True))
        if not text:
            continue
        match = re.search(r'文件大小\s*[:：]\s*([0-9.]+\s*[A-Za-z\u4e00-\u9fff]+)', text)
        if match:
            return _clean_text(match.group(1))
    return None


def _extract_file_format(soup: BeautifulSoup) -> Optional[str]:
    for meta_node in soup.select('.file-info .meta'):
        text = _clean_text(meta_node.get_text(' ', strip=True))
        if not text:
            continue
        match = re.search(r'文件类型\s*[:：]\s*([A-Za-z0-9._+-]+)', text)
        if match:
            return _clean_text(match.group(1))
    for name_node in soup.select('.file-info .name'):
        name = _clean_text(name_node)
        if not name or '.' not in name:
            continue
        suffix = name.rsplit('.', 1)[-1]
        if re.fullmatch(r'[A-Za-z0-9]+', suffix):
            return suffix.lower()
    return None


def _extract_download_urls(soup: BeautifulSoup, base_url: str) -> list[str]:
    return _unique_list(
        urljoin(base_url, href)
        for href in (anchor.get('href') for anchor in soup.select('a.download-link[href]'))
        if href
    )


def _format_byte_size(value: Optional[Any]) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    if not re.fullmatch(r'\d+', text):
        return text
    size = float(text)
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    formatted = f'{size:.2f}'.rstrip('0').rstrip('.')
    return f'{formatted} {units[unit_index]}'


def _data_amount(soup: BeautifulSoup, table_values: Dict[str, str]) -> Optional[str]:
    size = _first_non_empty(
        _extract_file_size(soup),
        _format_byte_size(table_values.get('总大小（字节）')),
    )
    file_count = _clean_text(table_values.get('文件数量'))
    parts = [size, f'{file_count}个文件' if file_count else None]
    return '；'.join(_unique_list(parts)) or None


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').strip().lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()
    return bool(
        'nhepsdc.cn/resource/' in normalized_url
        or (
            '国家高能物理科学数据中心' in combined
            and 'data-particulars-page' in combined
            and 'detail-title' in combined
        )
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[MetadataDict]:
    if not content:
        return None

    soup = BeautifulSoup(content, 'html.parser')
    info_rows = _extract_info_rows(soup)
    table_values = _extract_table_labels(soup)

    title_zh = _first_non_empty(_text_or_none(soup.select_one('.detail-title')), title, url)
    keywords = info_rows.get('关键词') if isinstance(info_rows.get('关键词'), list) else _split_terms(info_rows.get('关键词'))
    card_text = _extract_markdown_card(soup)
    summary = _first_non_empty(info_rows.get('摘要'), card_text)
    description = _first_non_empty(summary, card_text)
    subject = _first_non_empty(info_rows.get('学科分类'), table_values.get('研究领域'))
    source_org = _clean_text(info_rows.get('来源机构'))

    identifier, cstr_identifier, identifier_url = _extract_identifier(info_rows, soup)
    identifier_text = ' '.join(_text_or_none(anchor) or '' for anchor in soup.select('.info-row a.card-link'))
    doi = _extract_doi(info_rows.get('数据标识'), identifier_text, card_text)
    resource_url = url or identifier_url
    publish_date = _first_non_empty(table_values.get('提交时间'), table_values.get('共享发布时间'), table_values.get('最后更新日期'))
    submitter_name = _first_non_empty(
        table_values.get('汇交人姓名（中文）'),
        table_values.get('资源贡献者（中文）'),
        table_values.get('资源贡献者'),
    )
    submitter_email = _first_non_empty(table_values.get('汇交人电子邮箱'))
    submitter_affiliation = _first_non_empty(table_values.get('汇交人所在任职机构'))
    creator_name = _first_non_empty(submitter_name, table_values.get('资源贡献者（中文）'), table_values.get('资源贡献者'))
    creator_agent_zh = (
        _person_agent(creator_name)
        if creator_name
        else _organization_agent(source_org or PUBLISHER_ZH, 'zh')
    )
    creator_agent_en = (
        _person_agent(creator_name)
        if creator_name
        else _organization_agent(PUBLISHER_EN, 'en')
    )
    data_amount = _data_amount(soup, table_values)
    data_format = _first_non_empty(table_values.get('文件格式'), table_values.get('数据格式'), _extract_file_format(soup))
    download_urls = _extract_download_urls(soup, resource_url or url)

    sharing_method = table_values.get('共享途径')
    sharing_scope = table_values.get('共享范围')
    access_right = table_values.get('访问权限')
    license_text = table_values.get('许可协议')
    access_note = table_values.get('访问说明')
    other_note = table_values.get('其他')

    dataset_author_names = [creator_name] if creator_name else [source_org or PUBLISHER_ZH]
    rights = {
        '共享途径': sharing_method,
        '共享范围': sharing_scope,
        '访问权限': access_right,
        '许可协议': license_text,
        '访问说明': access_note,
        '其他': other_note,
    }
    rights = {key: value for key, value in rights.items() if value}
    rights_description = _rights_description(rights)

    core_zh: Dict[str, Any] = {
        'titles': [{'lang': 'zh', 'name': title_zh}] if title_zh else None,
        'identifier': cstr_identifier or identifier,
        'creators': [creator_agent_zh],
        'publisher': {
            'names': [
                {'lang': 'zh', 'name': PUBLISHER_ZH},
                {'lang': 'en', 'name': PUBLISHER_EN},
            ],
            'identifiers': None,
        },
        'publish_date': publish_date,
        'descriptions': [{'lang': 'zh', 'description': description}] if description else None,
        'keywords': [{'lang': 'zh', 'keyword': keywords}] if keywords else None,
        'subjects': [{'standard_gbt': [subject], 'standard_oecd': None}] if subject else None,
        'language': 'zh',
        'contributors': None,
        'alternative_identifiers': _alternative_identifiers(doi),
        'related_identifiers': None,
        'rights': [{
            'license_type': None,
            'license': license_text,
            'type': None,
            'description': rights_description,
            'cert_num': None,
        }] if (rights or license_text or access_right) else None,
        'funders': None,
        'version': None,
        'urls': [resource_url] if resource_url else None,
        'resource_type': 'Dataset',
    }
    zh: Dict[str, Any] = {
        '核心元数据': {'metadatas': [core_zh]},
        '数据集基本信息': {
            '标识符': identifier,
            '标题': title_zh,
            '摘要': description,
            '关键词': keywords or None,
            '范围': {
                '时间范围': None,
                '空间范围': None,
            },
            '语种': '中文',
            '文件内容': card_text,
            '基金项目': None,
            '数据量': data_amount,
            '数据格式': data_format,
            '数据集作者': {
                '作者姓名': dataset_author_names,
                '工作单位': submitter_affiliation or source_org or PUBLISHER_ZH,
                '电子邮箱': submitter_email,
                '工作贡献': '数据集建设、发布与服务',
                '作者简介': None,
            },
        },
        '数据集出版信息': {
            '发布日期': publish_date,
            '出版期刊': None,
            '版本信息': None,
        },
        '数据集服务信息': {
            '数据集引用格式': None,
            '数据集共享许可协议': license_text,
            '数据集使用声明': access_note or access_right,
            '数据集下载地址': '；'.join(download_urls) if download_urls else None,
            '数据论文访问地址': resource_url,
        },
    }

    core_en: Dict[str, Any] = {
        'titles': None,
        'identifier': cstr_identifier or identifier,
        'creators': [creator_agent_en],
        'publisher': {
            'names': [{'lang': 'en', 'name': PUBLISHER_EN}],
            'identifiers': None,
        },
        'publish_date': publish_date,
        'descriptions': None,
        'keywords': None,
        'subjects': None,
        'language': 'zh',
        'contributors': None,
        'alternative_identifiers': _alternative_identifiers(doi),
        'related_identifiers': None,
        'rights': [{
            'license_type': None,
            'license': license_text,
            'type': None,
            'description': rights_description,
            'cert_num': None,
        }] if (rights or license_text or access_right) else None,
        'funders': None,
        'version': None,
        'urls': [resource_url] if resource_url else None,
        'resource_type': 'Dataset',
    }
    en: Dict[str, Any] = {
        'Core Metadata': {'metadatas': [core_en]},
        'Dataset Basic Information': {
            'Identifier': identifier,
            'Title': title_zh,
            'Abstract': description,
            'Keywords': keywords or None,
            'Coverage': {
                'Time Range': None,
                'Spatial Range': None,
            },
            'Language': 'Chinese',
            'File Content': card_text,
            'Project/Funder': None,
            'Data Size': data_amount,
            'Data Format': data_format,
            'Dataset Authors': {
                'Author Name': dataset_author_names,
                'Affiliation': submitter_affiliation or source_org or PUBLISHER_ZH,
                'Email': submitter_email,
                'Contribution': 'Dataset construction, publication, and service',
                'Biography': None,
            },
        },
        'Dataset Publication Information': {
            'Publication Date': publish_date,
            'Journal': None,
            'Version Information': None,
        },
        'Dataset Service Information': {
            'Dataset Citation Format': None,
            'Dataset License': license_text,
            'Dataset Usage Statement': access_note or access_right,
            'Dataset Download URL': '；'.join(download_urls) if download_urls else None,
            'Dataset Paper URL': resource_url,
        },
    }

    return {'zh': zh, 'en': en}
