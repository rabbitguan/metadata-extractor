from __future__ import annotations

import re
from html import unescape
from typing import Any, Dict, Iterable, Optional

from bs4 import BeautifulSoup

from .base import MetadataDict


RULE_NAME = 'NHEPSDC Resource Detail'

PUBLISHER_ZH = '国家高能物理科学数据中心'
PUBLISHER_EN = 'National High Energy Physics Scientific Data Center'
CSTR_PATTERN = re.compile(r'\b(?:CSTR:)?(\d{5}\.\d{2}\.[A-Za-z0-9][A-Za-z0-9._-]*(?:\.[A-Za-z0-9][A-Za-z0-9._-]*)+)\b')


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
    summary = _first_non_empty(info_rows.get('摘要'), _extract_markdown_card(soup))
    card_text = _extract_markdown_card(soup)
    description = _first_non_empty(summary, card_text)
    subject = _first_non_empty(info_rows.get('学科分类'), table_values.get('研究领域'))
    source_org = _clean_text(info_rows.get('来源机构'))

    identifier, cstr_identifier, identifier_url = _extract_identifier(info_rows, soup)
    resource_url = url or identifier_url

    sharing_method = table_values.get('共享途径')
    sharing_scope = table_values.get('共享范围')
    access_right = table_values.get('访问权限')
    license_text = table_values.get('许可协议')
    access_note = table_values.get('访问说明')
    other_note = table_values.get('其他')

    creator_name_zh = source_org or PUBLISHER_ZH
    creators = [creator_name_zh]
    rights = {
        '共享途径': sharing_method,
        '共享范围': sharing_scope,
        '访问权限': access_right,
        '许可协议': license_text,
        '访问说明': access_note,
        '其他': other_note,
    }
    rights = {key: value for key, value in rights.items() if value}

    core_zh: Dict[str, Any] = {
        'titles': [{'lang': 'zh', 'name': title_zh}] if title_zh else None,
        'identifier': cstr_identifier or identifier,
        'creators': [{
            'type': 'Organize',
            'affiliation': {
                'names': [{'lang': 'zh', 'name': creator_name_zh}],
                'identifiers': None,
            },
        }],
        'publisher': {
            'names': [
                {'lang': 'zh', 'name': PUBLISHER_ZH},
                {'lang': 'en', 'name': PUBLISHER_EN},
            ],
            'identifiers': None,
        },
        'publish_date': None,
        'descriptions': [{'lang': 'zh', 'description': description}] if description else None,
        'keywords': [{'lang': 'zh', 'keyword': keywords}] if keywords else None,
        'subjects': [{'standard_gbt': [subject], 'standard_oecd': None}] if subject else None,
        'language': 'zh',
        'contributors': [{
            'type': 'Organize',
            'contribution_type': 'HostingInstitution',
            'affiliation': {
                'names': [{'lang': 'zh', 'name': PUBLISHER_ZH}],
                'identifiers': None,
            },
        }],
        'alternative_identifiers': None,
        'related_identifiers': None,
        'rights': [{
            'license_type': None,
            'license': license_text,
            'type': access_right,
            'description': '；'.join(f'{key}: {value}' for key, value in rights.items()) if rights else None,
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
            '数据量': None,
            '数据格式': None,
            '数据集作者': {
                '作者姓名': creators,
                '工作单位': source_org or PUBLISHER_ZH,
                '电子邮箱': None,
                '工作贡献': '数据集建设、发布与服务',
                '作者简介': None,
            },
        },
        '数据集出版信息': {
            '发布日期': None,
            '出版期刊': None,
            '版本信息': None,
        },
        '数据集服务信息': {
            '数据集引用格式': None,
            '数据集共享许可协议': license_text,
            '数据集使用声明': access_note or access_right,
            '数据集下载地址': None,
            '数据论文访问地址': resource_url,
        },
    }

    core_en: Dict[str, Any] = {
        'titles': None,
        'identifier': cstr_identifier or identifier,
        'creators': [{
            'type': 'Organize',
            'affiliation': {
                'names': [{'lang': 'en', 'name': PUBLISHER_EN}],
                'identifiers': None,
            },
        }],
        'publisher': {
            'names': [{'lang': 'en', 'name': PUBLISHER_EN}],
            'identifiers': None,
        },
        'publish_date': None,
        'descriptions': None,
        'keywords': None,
        'subjects': None,
        'language': 'zh',
        'contributors': [{
            'type': 'Organize',
            'contribution_type': 'HostingInstitution',
            'affiliation': {
                'names': [{'lang': 'en', 'name': PUBLISHER_EN}],
                'identifiers': None,
            },
        }],
        'alternative_identifiers': None,
        'related_identifiers': None,
        'rights': [{
            'license_type': None,
            'license': license_text,
            'type': access_right,
            'description': '；'.join(f'{key}: {value}' for key, value in rights.items()) if rights else None,
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
            'Data Size': None,
            'Data Format': None,
            'Dataset Authors': {
                'Author Name': creators,
                'Affiliation': creator_name_zh,
                'Email': None,
                'Contribution': 'Dataset construction, publication, and service',
                'Biography': None,
            },
        },
        'Dataset Publication Information': {
            'Publication Date': None,
            'Journal': None,
            'Version Information': None,
        },
        'Dataset Service Information': {
            'Dataset Citation Format': None,
            'Dataset License': license_text,
            'Dataset Usage Statement': access_note or access_right,
            'Dataset Download URL': None,
            'Dataset Paper URL': resource_url,
        },
    }

    return {'zh': zh, 'en': en}
