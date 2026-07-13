from __future__ import annotations

import re
from html import unescape
from typing import Any, Dict, Optional

import requests
from bs4 import BeautifulSoup

from .base import MetadataDict


RULE_NAME = 'NCDC Metadata Detail'
FETCH_HEADERS = {'User-Agent': 'Mozilla/5.0'}
PUBLISHER_ZH = '国家冰川冻土沙漠科学数据中心'
PUBLISHER_EN = 'National Cryosphere Desert Data Center'

TITLE_LABELS = {
    '首页',
    '数据资源',
    '台站数据',
    '数据专题',
    '期刊数据',
    '模型工具',
    '数据汇交',
    '数据汇交指南',
    '科技计划汇交资源',
    '应急响应',
    '全球灾害',
    '科普',
    '综合新闻',
    '平台介绍',
    '详情',
    '数据集摘要',
    '基本信息',
    '引用和标注',
    '许可协议',
    '数据源描述',
    '数据加工方法',
    '数据质量描述',
    '项目支持信息',
    '相关数据',
    '数据文件列表',
    '服务记录',
    'Home',
    'Data resource',
    'Details',
    'Datasets description',
    'Base information',
    'Citations and annotations',
    'license agreement',
    'Relevant data',
    'File list',
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


def _looks_like_url(value: Optional[str]) -> bool:
    return bool(re.match(r'^https?://', str(value or '').strip(), flags=re.IGNORECASE))


def _valid_title(value: Optional[str]) -> Optional[str]:
    text = _clean_text(value)
    if not text or _looks_like_url(text):
        return None
    text = re.split(r'\s+-\s*国家冰川冻土沙漠科学数据中心|\s*\|\s*国家冰川冻土沙漠科学数据中心', text)[0].strip()
    if not text:
        return None
    lowered = text.lower()
    if 'ncdc.ac.cn' in lowered or '国家冰川冻土沙漠科学数据中心' == text:
        return None
    if text in TITLE_LABELS:
        return None
    if len(text) <= 6 and text.endswith('数据'):
        return None
    if re.search(r'\b(CSTR|DOI)\b', text, flags=re.IGNORECASE):
        return None
    if len(text) < 4:
        return None
    return text


def _split_terms(value: Optional[str]) -> list[str]:
    text = _clean_text(value)
    if not text:
        return []
    parts = re.split(r'[;；,，、\|]+', text)
    return [item for item in (_clean_text(part) for part in parts) if item]


def _split_people(value: Optional[str]) -> list[str]:
    text = _clean_text(value)
    if not text:
        return []
    return _unique_list(re.split(r'\s*[,，;；、]\s*', text))


def _unique_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        cleaned = _clean_text(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        unique.append(cleaned)
    return unique


def _has_cjk(value: Optional[str]) -> bool:
    return bool(value and re.search(r'[\u4e00-\u9fff]', value))


def _page_lang(soup: BeautifulSoup) -> Optional[str]:
    html_lang = _clean_text(soup.html.get('lang') if soup.html else None)
    if html_lang:
        lowered = html_lang.lower()
        if lowered.startswith('zh'):
            return 'zh'
        if lowered.startswith('en'):
            return 'en'
    title = _extract_title(soup)
    if _has_cjk(title):
        return 'zh'
    if title:
        return 'en'
    return None


def _fetch_localized_content(url: str, lang: str) -> Optional[str]:
    if not url or 'ncdc.ac.cn/portal/metadata/' not in url.lower():
        return None
    accept_language = 'zh-CN,zh;q=0.9' if lang == 'zh' else 'en-US,en;q=0.9'
    try:
        response = requests.get(
            url,
            headers={**FETCH_HEADERS, 'Accept-Language': accept_language},
            timeout=15,
        )
        response.raise_for_status()
        response.encoding = response.encoding or 'utf-8'
        return response.text
    except Exception:
        return None


def _localized_soups(content: str, url: str) -> tuple[BeautifulSoup, BeautifulSoup]:
    soup = BeautifulSoup(content, 'html.parser')
    lang = _page_lang(soup)
    zh_soup = soup if lang == 'zh' else None
    en_soup = soup if lang == 'en' else None

    if zh_soup is None:
        zh_content = _fetch_localized_content(url, 'zh')
        zh_soup = BeautifulSoup(zh_content, 'html.parser') if zh_content else soup
    if en_soup is None:
        en_content = _fetch_localized_content(url, 'en')
        en_soup = BeautifulSoup(en_content, 'html.parser') if en_content else soup

    return zh_soup, en_soup


def _extract_by_label(soup: BeautifulSoup, labels: list[str]) -> Optional[str]:
    for row in soup.select('.metadata-detail tr'):
        header = _text_or_none(row.find('th'))
        if not header:
            continue
        header = header.rstrip('：:').strip()
        if header not in labels:
            continue

        value_cell = row.find('td')
        if not value_cell:
            continue
        value_text = _text_or_none(value_cell)
        if value_text:
            return value_text

    for row in soup.select('.metadata-detail .row, .metadata-details-wrapper .row'):
        header_node = row.select_one('.t-title')
        if not header_node:
            continue
        header = _text_or_none(header_node)
        if not header:
            continue
        header = header.rstrip('：:').strip()
        if header not in labels:
            continue

        value_node = row.select_one('.t-value')
        if not value_node:
            continue
        value_text = _text_or_none(value_node)
        if value_text:
            return value_text

    return None


def _extract_list_values(soup: BeautifulSoup, labels: list[str]) -> list[str]:
    values: list[str] = []
    for row in soup.select('.metadata-detail tr'):
        header = _text_or_none(row.find('th'))
        if not header:
            continue
        header = header.rstrip('：:').strip()
        if header not in labels:
            continue

        value_cell = row.find('td')
        if not value_cell:
            continue

        anchors = value_cell.find_all('a')
        if anchors:
            for anchor in anchors:
                text = _text_or_none(anchor)
                if text:
                    values.append(text)
            continue

        value_text = _text_or_none(value_cell)
        if value_text:
            values.append(value_text)

    return values


def _extract_sidebar_values(soup: BeautifulSoup, labels: list[str]) -> list[str]:
    values: list[str] = []
    normalized_labels = {label.rstrip('：:').strip().lower() for label in labels}
    for item in soup.select('.list-group-item'):
        heading = _text_or_none(item.select_one('.list-group-item-heading'))
        if not heading or heading.rstrip('：:').strip().lower() not in normalized_labels:
            continue
        anchors = [_text_or_none(anchor) for anchor in item.select('a')]
        anchors = [anchor for anchor in anchors if anchor]
        if anchors:
            values.extend(anchors)
            continue
        text = _text_or_none(item.select_one('.list-group-item-text'))
        if text:
            values.extend(_split_terms(text))
    return _unique_list(values)


def _extract_definition_list_values(soup: BeautifulSoup, labels: list[str]) -> list[str]:
    values: list[str] = []

    for dl in soup.select('dl'):
        terms = dl.find_all('dt')
        definitions = dl.find_all('dd')
        for term, definition in zip(terms, definitions):
            label = _text_or_none(term)
            if not label:
                continue
            label = label.rstrip('：:').strip()
            if label not in labels:
                continue

            anchors = definition.find_all('a')
            if anchors:
                for anchor in anchors:
                    text = _text_or_none(anchor)
                    if text:
                        values.append(text)
                continue

            text = _text_or_none(definition)
            if text:
                values.append(text)

    return values


def _label_matches(value: Optional[str], labels: list[str]) -> bool:
    text = _clean_text(value)
    if not text:
        return False
    return text.rstrip('：:').strip().lower() in {label.rstrip('：:').strip().lower() for label in labels}


def _extract_section_text(soup: BeautifulSoup, title_text: str | list[str]) -> Optional[str]:
    labels = [title_text] if isinstance(title_text, str) else title_text
    for box in soup.select('.info-box'):
        heading = _text_or_none(box.select_one('.title-bar, .title-bar2'))
        if _label_matches(heading, labels):
            block = box.select_one('.info-block')
            if block:
                return _text_or_none(block)
    return None


def _extract_first_paragraph(soup: BeautifulSoup, title_text: str | list[str]) -> Optional[str]:
    labels = [title_text] if isinstance(title_text, str) else title_text
    for box in soup.select('.info-box'):
        heading = _text_or_none(box.select_one('.title-bar, .title-bar2'))
        if _label_matches(heading, labels):
            block = box.select_one('.info-block')
            if not block:
                continue
            paragraph = block.find('p')
            if paragraph:
                return _text_or_none(paragraph)
            return _text_or_none(block)
    return None


def _extract_cstr(text: str) -> Optional[str]:
    if not text:
        return None
    match = re.search(r'cstr\.cn/(?:CSTR:)?([A-Z0-9]{5}\.\d{2}\.[-._;()/:A-Z0-9]+)', text, flags=re.IGNORECASE)
    if match:
        return match.group(1).rstrip('.,;。；')
    match = re.search(r'CSTR:\s*([A-Z0-9]{5}\.\d{2}\.[-._;()/:A-Z0-9]+)', text, flags=re.IGNORECASE)
    if match:
        return match.group(1).rstrip('.,;。；')
    match = re.search(
        r'\b[A-Z0-9]{5}\.\d{2}\.[-._;()/:A-Z0-9]+\b',
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(0).rstrip('.,;。；')
    return None


def _extract_doi(text: str) -> Optional[str]:
    if not text:
        return None
    match = re.search(r'10\.\d{4,9}/[^\s<>"\']+', text)
    if match:
        return match.group(0).rstrip('.,;')
    return None


def _extract_title(soup: BeautifulSoup) -> Optional[str]:
    title = _valid_title(_text_or_none(soup.select_one('.metadata-details-title')))
    if title:
        return title

    title = _valid_title(_extract_by_label(soup, ['中文名称', '英文名称', 'English name', '资源名称', '数据集名称']))
    if title:
        return title

    for selector in ('meta[property="og:title"]', 'meta[name="title"]'):
        node = soup.select_one(selector)
        title = _valid_title(node.get('content') if node else None)
        if title:
            return title

    for selector in ('h1', '.title', '.resource-title'):
        title = _valid_title(_text_or_none(soup.select_one(selector)))
        if title:
            return title

    meta_title = soup.title.string if soup.title and soup.title.string else None
    if meta_title:
        cleaned = _clean_text(meta_title)
        if cleaned:
            title = _valid_title(re.split(r'\s+-\s+|\s+_\s+|\s*\|\s*', cleaned)[0])
            if title:
                return title

    return None


def _extract_title_from_text(text: str) -> Optional[str]:
    if not text:
        return None

    raw_lines = [_clean_text(line) for line in re.split(r'[\r\n]+', text)]
    raw_lines = [line for line in raw_lines if line]

    for line in raw_lines:
        match = re.match(r'^(?:中文名称|资源名称|数据集名称|标题)\s*[:：]?\s*(.+)$', line)
        if match:
            title = _valid_title(match.group(1))
            if title:
                return title

    for line in raw_lines:
        title = _valid_title(line)
        if not title:
            continue
        if any(marker in title for marker in ('摘要', '发布时间', '点击量', '下载量')):
            continue
        if len(title) <= 120 and re.search(r'(数据集|数据|冻土|人口|社会经济|文化|dataset)', title, flags=re.IGNORECASE):
            return title

    match = re.search(r'([^\n。；;]{4,120}(?:数据集|数据|冻土|人口|社会经济|文化|dataset)[^\n。；;]{0,60})', text, flags=re.IGNORECASE)
    if match:
        return _valid_title(match.group(1))

    return None


def _extract_publication_date(soup: BeautifulSoup) -> Optional[str]:
    subtitle = _text_or_none(soup.select_one('.metadata-details-subtitle')) or ''
    match = re.search(r'(\d{4})/(\d{2})/(\d{2})', subtitle)
    if match:
        return f'{match.group(1)}-{match.group(2)}-{match.group(3)}'
    return None


def _extract_reference_citation(soup: BeautifulSoup) -> Optional[str]:
    for item in soup.select('.ref-content .ref-list > li'):
        text = _text_or_none(item)
        if text:
            return text
    return None


def _extract_contact_info(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    contact: Dict[str, Optional[str]] = {
        '联系人': None,
        '服务电话': None,
        '服务邮箱': None,
    }

    for box in soup.select('.panel-body'):
        labels = [
            _text_or_none(dt).rstrip('：:').strip() if _text_or_none(dt) else None
            for dt in box.select('dt')
        ]
        values = [_text_or_none(dd) for dd in box.select('dd')]
        pairs = [(label, value) for label, value in zip(labels, values) if label and value]
        if not pairs:
            continue

        pair_map = {label: value for label, value in pairs}
        if any(key in pair_map for key in ('联系人', '服务电话', '服务邮箱', 'contacts', 'phone', 'mailbox')):
            contact['联系人'] = pair_map.get('联系人') or pair_map.get('contacts')
            contact['服务电话'] = pair_map.get('服务电话') or pair_map.get('phone')
            contact['服务邮箱'] = pair_map.get('服务邮箱') or pair_map.get('mailbox')
            break

    return contact


def _extract_project_support(soup: BeautifulSoup) -> Optional[str]:
    for box in soup.select('.info-box'):
        heading = _text_or_none(box.select_one('.title-bar, .title-bar2'))
        if heading != '项目支持信息':
            continue

        first_row = box.select_one('tbody tr')
        if not first_row:
            continue

        cells = [_text_or_none(cell) for cell in first_row.find_all('td')]
        cells = [cell for cell in cells if cell]
        if len(cells) >= 4:
            project_name = cells[1]
            project_code = cells[2]
            project_type = cells[3]
            return f'{project_name}（{project_code}，{project_type}）'
        if cells:
            return '；'.join(cells)

    return None


def _extract_file_list(soup: BeautifulSoup) -> list[str]:
    for box in soup.select('.meta-tabs .tab-pane#datafiles, .tab-pane#datafiles'):
        file_names: list[str] = []
        for row in box.select('tbody tr'):
            cells = row.find_all('td')
            if len(cells) >= 2:
                file_name = _text_or_none(cells[1])
                if file_name:
                    file_size = _text_or_none(cells[2]) if len(cells) >= 3 else None
                    file_names.append(f'{file_name}（{file_size}）' if file_size else file_name)
        if file_names:
            return file_names
    return []


def _extract_license_text(soup: BeautifulSoup) -> Optional[str]:
    license_block = _extract_section_text(soup, ['许可协议', 'license agreement'])
    if license_block:
        return license_block

    for anchor in soup.select('a[rel~="license"]'):
        text = _text_or_none(anchor)
        if text:
            return text

    return None


def _extract_range(soup: BeautifulSoup) -> Dict[str, Optional[object]]:
    start_date = _extract_by_label(soup, ['采集时间', 'collect time'])
    location = _extract_by_label(soup, ['采集地点', 'collect place'])
    data_size = _extract_by_label(soup, ['数据量', 'data size'])
    data_format = _extract_by_label(soup, ['数据格式', 'data format'])
    resolution = _extract_by_label(soup, ['数据空间分辨率(/米)', 'Data time resolution'])
    projection = _extract_by_label(soup, ['投影', 'Coordinate system'])

    time_range = None
    if start_date:
        match = re.search(r'(\d{4}/\d{2}/\d{2})\s*-\s*(\d{4}/\d{2}/\d{2})', start_date)
        if match:
            time_range = {
                '起始时间': match.group(1).replace('/', '-'),
                '结束时间': match.group(2).replace('/', '-'),
            }
        else:
            time_range = {'起始时间': start_date.replace('/', '-'), '结束时间': None}

    return {
        'time_range': time_range,
        'location': location,
        'data_size': data_size,
        'data_format': data_format,
        'resolution': resolution,
        'projection': projection,
    }


def _extract_citation_authors(citation: Optional[str]) -> list[str]:
    text = _clean_text(citation)
    if not text:
        return []
    author_text = re.split(r'[.。]', text, maxsplit=1)[0]
    if not author_text or _looks_like_url(author_text):
        return []
    return _split_people(author_text)


def _spatial_range(soup: BeautifulSoup, location: Optional[str], lang: str = 'zh') -> Optional[object]:
    text = soup.get_text(' ', strip=True)
    coordinate_patterns = {
        'east': r'(?:东|east)\s*[:：]?\s*([0-9.\-]+)',
        'west': r'(?:西|west)\s*[:：]?\s*([0-9.\-]+)',
        'south': r'(?:南|south)\s*[:：]?\s*([0-9.\-]+)',
        'north': r'(?:北|north)\s*[:：]?\s*([0-9.\-]+)',
    }
    values = {}
    for key, pattern in coordinate_patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        values[key] = _clean_text(match.group(1)) if match else None
    if any(values.values()):
        if lang == 'en':
            return {
                'West Bounding Longitude': values['west'],
                'East Bounding Longitude': values['east'],
                'South Bounding Latitude': values['south'],
                'North Bounding Latitude': values['north'],
            }
        return {
            '西部边界经度': values['west'],
            '东部边界经度': values['east'],
            '南部边界纬度': values['south'],
            '北部边界纬度': values['north'],
        }
    return location


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').strip().lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()

    if 'nmdis.org.cn' in normalized_url or '国家海洋科学数据中心' in combined:
        return False

    return bool(
        'ncdc.ac.cn/portal/metadata/' in normalized_url
        or '国家冰川冻土沙漠科学数据中心' in combined
        or ('数据共享方式' in combined and '国家冰川' in combined)
        or ('数据集摘要' in combined and '国家冰川' in combined)
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[MetadataDict]:
    if not content:
        return None

    zh_soup, en_soup = _localized_soups(content, url)
    zh_text = zh_soup.get_text('\n', strip=True)
    en_text = en_soup.get_text('\n', strip=True)

    title_zh = _first_non_empty(_extract_title(zh_soup), _extract_title_from_text(zh_text), _valid_title(title), '未提取到标题')
    title_en = _first_non_empty(_extract_title(en_soup), _extract_by_label(en_soup, ['英文名称', 'English name']))
    abstract = _extract_first_paragraph(zh_soup, '数据集摘要')
    abstract_en = _extract_first_paragraph(en_soup, ['Datasets description', 'Dataset description'])
    source_description = _extract_first_paragraph(zh_soup, '数据源描述')
    source_description_en = _extract_first_paragraph(en_soup, 'Data source description')
    processing_method = _extract_first_paragraph(zh_soup, '数据加工方法')
    processing_method_en = _extract_first_paragraph(en_soup, 'Data processing method')
    quality_description = _extract_first_paragraph(zh_soup, '数据质量描述')
    quality_description_en = _extract_first_paragraph(en_soup, 'Data quality description')

    publication_date = _extract_publication_date(zh_soup) or _extract_publication_date(en_soup)
    cstr_text = _extract_by_label(zh_soup, ['CSTR']) or _extract_by_label(en_soup, ['CSTR'])
    doi_text = _extract_by_label(zh_soup, ['DOI']) or _extract_by_label(en_soup, ['DOI'])
    reference_citation = _extract_reference_citation(zh_soup)
    reference_citation_en = _extract_reference_citation(en_soup)
    license_text = _extract_license_text(zh_soup) or _extract_license_text(en_soup)
    license_text_en = _extract_license_text(en_soup) or license_text

    data_contributors = _unique_list(_extract_definition_list_values(zh_soup, ['数据贡献者', 'contributors']))
    data_contributors_en = _unique_list(_extract_definition_list_values(en_soup, ['contributors', 'contributors']))
    creators = _unique_list([*_extract_citation_authors(reference_citation), *data_contributors]) or None
    creators_en = _unique_list([*_extract_citation_authors(reference_citation_en), *data_contributors_en]) or creators
    contributors = None
    publisher = PUBLISHER_ZH

    tags = _unique_list([*_extract_list_values(zh_soup, ['主题', '时间', '地点']), *_extract_sidebar_values(zh_soup, ['主题', '时间', '地点'])])
    keywords = _split_terms('；'.join(tags)) if tags else []
    if not keywords:
        keywords = _split_terms(_extract_by_label(zh_soup, ['数据分类', 'Category']))
    tags_en = _unique_list([*_extract_list_values(en_soup, ['Theme', 'Time', 'Place']), *_extract_sidebar_values(en_soup, ['Theme', 'Time', 'Place'])])
    keywords_en = _split_terms('; '.join(tags_en)) if tags_en else []
    if not keywords_en:
        keywords_en = _split_terms(_extract_by_label(en_soup, ['Category']))
    category_zh = _extract_by_label(zh_soup, ['数据分类', 'Category'])
    category_en = _extract_by_label(en_soup, ['Category'])
    discipline_zh = [{'lang': 'zh', 'value': [category_zh]}] if category_zh else None
    discipline_en = [{'lang': 'en', 'value': [category_en]}] if category_en else None

    range_info = _extract_range(zh_soup)
    time_range = range_info['time_range']
    location = range_info['location']
    data_size = range_info['data_size']
    data_format = range_info['data_format']
    resolution = range_info['resolution']
    projection = range_info['projection']
    en_range_info = _extract_range(en_soup)
    time_range_en = en_range_info['time_range'] or time_range
    location_en = en_range_info['location']
    data_size_en = en_range_info['data_size'] or data_size
    data_format_en = en_range_info['data_format'] or data_format
    resolution_en = en_range_info['resolution']
    projection_en = en_range_info['projection']

    spatial_range = _spatial_range(zh_soup, location, 'zh')
    spatial_range_en = _spatial_range(en_soup, location_en, 'en') or spatial_range

    cstr_identifier = _extract_cstr(cstr_text or '') or _extract_cstr(reference_citation or '') or _extract_cstr(reference_citation_en or '') or _extract_cstr(zh_text) or _extract_cstr(en_text)
    doi_identifier = _extract_doi(doi_text or '') or _extract_doi(reference_citation or '') or _extract_doi(reference_citation_en or '') or _extract_doi(zh_text) or _extract_doi(en_text)
    identifier = cstr_identifier or doi_identifier
    alternative_identifiers = [{'type': 'DOI', 'identifier': doi_identifier}] if doi_identifier else None

    funders = _extract_project_support(zh_soup)
    funders_en = _extract_project_support(en_soup) or funders
    contact_info = _extract_contact_info(zh_soup)
    contact_info_en = _extract_contact_info(en_soup)

    data_files = _extract_file_list(zh_soup) or _extract_file_list(en_soup)
    file_content = data_files if data_files else None

    access_url = url or None
    citation_format = reference_citation
    citation_format_en = reference_citation_en or reference_citation
    rights_text = license_text or 'CC BY 4.0'
    rights_text_en = license_text_en or rights_text
    language_nodes = [{'lang': 'zh', 'value': '中文'}, {'lang': 'en', 'value': 'English'}]

    zh: Dict[str, Any] = {
        '资源类型判定': '数据集',
        '领域判定': '数据集元数据',
        '标识符': identifier,
        'CSTR标识符': cstr_identifier,
        '资源名称': title_zh,
        '标题': title_zh,
        '创建者': creators,
        '发布机构': publisher,
        '发布日期': publication_date,
        '描述': abstract,
        '关键词': keywords,
        '学科分类': discipline_zh,
        '语言': language_nodes,
        '贡献者': contributors,
        '替代标识符': alternative_identifiers,
        '关联标识符': None,
        '权限': rights_text,
        '资助者': funders,
        '版本': None,
        '资源链接': access_url,
        '资源类型': '数据集',
        '数据集基本信息': {
            '标识符': identifier,
            '标题': title_zh,
            '摘要': abstract,
            '关键词': keywords,
            '范围': {
                '时间范围': time_range,
                '空间范围': spatial_range,
            },
            '语种': '中文',
            '文件内容': file_content,
            '基金项目': funders,
            '数据量': data_size,
            '数据格式': data_format,
            '数据集作者': {
                '作者姓名': creators,
                '工作单位': publisher,
                '电子邮箱': None,
                '工作贡献': None,
                '作者简介': None,
            },
        },
        '数据集出版信息': {
            '发布日期': publication_date,
            '出版期刊': None,
            '版本信息': None,
        },
        '数据集服务信息': {
            '数据集引用格式': citation_format,
            '数据集共享许可协议': rights_text,
            '数据集使用声明': _extract_by_label(zh_soup, ['数据共享方式', '共享方式']),
            '数据集下载地址': None,
            '数据集访问地址': access_url,
        },
        '扩展信息': {
            '数据源描述': source_description,
            '数据加工方法': processing_method,
            '数据质量描述': quality_description,
            '空间分辨率': resolution,
            '投影': projection,
            '数据分类': category_zh,
            '主题': _extract_list_values(zh_soup, ['主题']) or _extract_sidebar_values(zh_soup, ['主题']),
            '地点': _extract_list_values(zh_soup, ['地点']) or _extract_sidebar_values(zh_soup, ['地点']),
            '数据生产者': creators,
            '联系人': contact_info.get('联系人'),
            '服务电话': contact_info.get('服务电话'),
            '服务邮箱': contact_info.get('服务邮箱'),
        },
    }

    en: Dict[str, Any] = {
        'Resource Type Classification': 'Dataset',
        'Domain Classification': 'Dataset Metadata',
        'Identifier': identifier,
        'CSTR Identifier': cstr_identifier,
        'Resource Name': title_en,
        'Title': title_en,
        'Creators': creators_en,
        'Publisher': PUBLISHER_EN,
        'Publication Date': publication_date,
        'Description': abstract_en,
        'Keywords': keywords_en,
        'Discipline Classification': discipline_en,
        'Language': 'English',
        '语言': language_nodes,
        'Contributors': contributors,
        'Alternative Identifiers': alternative_identifiers,
        'Related Identifiers': None,
        'Rights': rights_text_en,
        'Funders': funders_en,
        'Version': None,
        'Resource URL': access_url,
        'ResourceType': 'Dataset',
        'Dataset Basic Information': {
            'Identifier': identifier,
            'Title': title_en,
            'Abstract': abstract_en,
            'Keywords': keywords_en,
            'Coverage': {
                'Time Range': time_range_en,
                'Spatial Range': spatial_range_en,
            },
            'Language': 'English',
            'File Content': file_content,
            'Project/Funder': funders_en,
            'Data Size': data_size_en,
            'Data Format': data_format_en,
            'Dataset Authors': {
                'Author Name': creators_en,
                'Affiliation': PUBLISHER_EN,
                'Email': None,
                'Contribution': None,
                'Biography': None,
            },
        },
        'Dataset Publication Information': {
            'Publication Date': publication_date,
            'Journal': None,
            'Version Information': None,
        },
        'Dataset Service Information': {
            'Dataset Citation Format': citation_format_en,
            'Dataset License': rights_text_en,
            'Dataset Usage Statement': _extract_by_label(en_soup, ['Share type', 'Data sharing mode']),
            'Dataset Download URL': None,
            'Dataset Access URL': access_url,
        },
        'Extension Info': {
            'Source Description': source_description_en,
            'Processing Method': processing_method_en,
            'Quality Description': quality_description_en,
            'Spatial Resolution': resolution_en,
            'Projection': projection_en,
            'Data Category': category_en,
            'Themes': _extract_list_values(en_soup, ['Theme']) or _extract_sidebar_values(en_soup, ['Theme']),
            'Locations': _extract_list_values(en_soup, ['Place']) or _extract_sidebar_values(en_soup, ['Place']),
            'Data Producer': creators_en,
            'Contact': contact_info_en.get('联系人'),
            'Service Phone': contact_info_en.get('服务电话'),
            'Service Email': contact_info_en.get('服务邮箱'),
        },
    }

    return {'zh': zh, 'en': en}
