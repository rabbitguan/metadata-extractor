from __future__ import annotations

import re
from html import unescape
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup

from .base import MetadataDict


RULE_NAME = 'NCDC Metadata Detail'


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


def _split_terms(value: Optional[str]) -> list[str]:
    text = _clean_text(value)
    if not text:
        return []
    parts = re.split(r'[;；,，、\|\s]+', text)
    return [item for item in (_clean_text(part) for part in parts) if item]


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


def _extract_section_text(soup: BeautifulSoup, title_text: str) -> Optional[str]:
    for box in soup.select('.info-box'):
        heading = _text_or_none(box.select_one('.title-bar, .title-bar2'))
        if heading and heading.strip() == title_text:
            block = box.select_one('.info-block')
            if block:
                return _text_or_none(block)
    return None


def _extract_first_paragraph(soup: BeautifulSoup, title_text: str) -> Optional[str]:
    for box in soup.select('.info-box'):
        heading = _text_or_none(box.select_one('.title-bar, .title-bar2'))
        if heading and heading.strip() == title_text:
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
    match = re.search(r'CSTR:\s*([A-Za-z0-9._-]+)', text, flags=re.IGNORECASE)
    if match:
        return match.group(1).rstrip('.,;。；')
    match = re.search(r'\b\d{5}\.\d{2}\.\d{2}\.\d{2}\.\d{5}-V\d+\b|\b\d{5}\.\d{2}\.\d{6}\.\d{6}\b', text)
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
    title = _text_or_none(soup.select_one('.metadata-details-title'))
    if title:
        return title

    meta_title = soup.title.string if soup.title and soup.title.string else None
    if meta_title:
        cleaned = _clean_text(meta_title)
        if cleaned:
            return cleaned.split(' - ')[0].strip()

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
        if '联系人' in pair_map or '服务电话' in pair_map or '服务邮箱' in pair_map:
            contact['联系人'] = pair_map.get('联系人')
            contact['服务电话'] = pair_map.get('服务电话')
            contact['服务邮箱'] = pair_map.get('服务邮箱')
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
                    file_names.append(file_name)
        if file_names:
            return file_names
    return []


def _extract_license_text(soup: BeautifulSoup) -> Optional[str]:
    license_block = _extract_section_text(soup, '许可协议')
    if license_block:
        return license_block

    for anchor in soup.select('a[rel~="license"]'):
        text = _text_or_none(anchor)
        if text:
            return text

    return None


def _extract_range(soup: BeautifulSoup) -> Dict[str, Optional[object]]:
    start_date = _extract_by_label(soup, ['采集时间'])
    location = _extract_by_label(soup, ['采集地点'])
    data_size = _extract_by_label(soup, ['数据量'])
    data_format = _extract_by_label(soup, ['数据格式'])
    resolution = _extract_by_label(soup, ['数据空间分辨率(/米)'])
    projection = _extract_by_label(soup, ['投影'])

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


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').strip().lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()

    return bool(
        'ncdc.ac.cn/portal/metadata/' in normalized_url
        or '国家冰川冻土沙漠科学数据中心' in combined
        or '数据共享方式' in combined
        or '数据集摘要' in combined
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[MetadataDict]:
    if not content:
        return None

    soup = BeautifulSoup(content, 'html.parser')

    title_zh = _first_non_empty(_extract_title(soup), title, url)
    title_en = _first_non_empty(title_zh, title)
    abstract = _extract_first_paragraph(soup, '数据集摘要')
    source_description = _extract_first_paragraph(soup, '数据源描述')
    processing_method = _extract_first_paragraph(soup, '数据加工方法')
    quality_description = _extract_first_paragraph(soup, '数据质量描述')

    publication_date = _extract_publication_date(soup)
    cstr_text = _extract_by_label(soup, ['CSTR'])
    doi_text = _extract_by_label(soup, ['DOI'])
    reference_citation = _extract_reference_citation(soup)
    license_text = _extract_license_text(soup)

    contributors = _unique_list(_extract_definition_list_values(soup, ['数据贡献者']))
    creators = None
    publisher = '国家冰川冻土沙漠科学数据中心'

    tags = _extract_list_values(soup, ['主题', '时间', '地点'])
    keywords = _split_terms('；'.join(tags)) if tags else []
    if not keywords:
        keywords = _split_terms(_extract_by_label(soup, ['数据分类']))

    range_info = _extract_range(soup)
    time_range = range_info['time_range']
    location = range_info['location']
    data_size = range_info['data_size']
    data_format = range_info['data_format']
    resolution = range_info['resolution']
    projection = range_info['projection']

    spatial_range = None
    if location or any([soup.find(string=re.compile(r'东:')), soup.find(string=re.compile(r'西:')), soup.find(string=re.compile(r'南:')), soup.find(string=re.compile(r'北:'))]):
        east = _clean_text(re.search(r'东:\s*([0-9.\-]+)', soup.get_text(' ', strip=True)).group(1)) if re.search(r'东:\s*([0-9.\-]+)', soup.get_text(' ', strip=True)) else None
        west = _clean_text(re.search(r'西:\s*([0-9.\-]+)', soup.get_text(' ', strip=True)).group(1)) if re.search(r'西:\s*([0-9.\-]+)', soup.get_text(' ', strip=True)) else None
        south = _clean_text(re.search(r'南:\s*([0-9.\-]+)', soup.get_text(' ', strip=True)).group(1)) if re.search(r'南:\s*([0-9.\-]+)', soup.get_text(' ', strip=True)) else None
        north = _clean_text(re.search(r'北:\s*([0-9.\-]+)', soup.get_text(' ', strip=True)).group(1)) if re.search(r'北:\s*([0-9.\-]+)', soup.get_text(' ', strip=True)) else None
        spatial_range = {
            '地理范围描述': location,
            '西部边界经度': west,
            '东部边界经度': east,
            '南部边界纬度': south,
            '北部边界纬度': north,
        }

    cstr_identifier = _extract_cstr(cstr_text or '') or _extract_cstr(reference_citation or '')
    doi_identifier = _extract_doi(doi_text or '') or _extract_doi(reference_citation or '')
    identifier = cstr_identifier or doi_identifier or title_zh
    alternative_identifiers = [item for item in [doi_identifier, cstr_identifier] if item]

    funders = _extract_project_support(soup)
    contact_info = _extract_contact_info(soup)

    data_files = _extract_file_list(soup)
    file_content = data_files if data_files else None

    access_url = url or None
    citation_format = reference_citation
    rights_text = license_text or 'CC BY 4.0'

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
        '学科分类': _first_non_empty(*keywords) or '荒漠化',
        '语言': '中文',
        '贡献者': contributors if contributors else None,
        '替代标识符': alternative_identifiers if alternative_identifiers else None,
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
            '数据集使用声明': _extract_by_label(soup, ['数据共享方式']),
            '数据集下载地址': None,
            '数据集访问地址': access_url,
        },
        '扩展信息': {
            '数据源描述': source_description,
            '数据加工方法': processing_method,
            '数据质量描述': quality_description,
            '空间分辨率': resolution,
            '投影': projection,
            '数据分类': _extract_by_label(soup, ['数据分类']),
            '主题': _extract_list_values(soup, ['主题']),
            '地点': _extract_list_values(soup, ['地点']),
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
        'Creators': creators,
        'Publisher': 'National Cryosphere Desert Data Center',
        'Publication Date': publication_date,
        'Description': abstract,
        'Keywords': keywords,
        'Discipline Classification': _first_non_empty(*keywords) or 'Desertification',
        'Language': 'Chinese',
        'Contributors': contributors if contributors else None,
        'Alternative Identifiers': alternative_identifiers if alternative_identifiers else None,
        'Related Identifiers': None,
        'Rights': rights_text,
        'Funders': funders,
        'Version': None,
        'Resource URL': access_url,
        'ResourceType': 'Dataset',
        'Dataset Basic Information': {
            'Identifier': identifier,
            'Title': title_en,
            'Abstract': abstract,
            'Keywords': keywords,
            'Coverage': {
                'Time Range': time_range,
                'Spatial Range': spatial_range,
            },
            'Language': 'Chinese',
            'File Content': file_content,
            'Project/Funder': funders,
            'Data Size': data_size,
            'Data Format': data_format,
            'Dataset Authors': {
                'Author Name': creators,
                'Affiliation': publisher,
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
            'Dataset Citation Format': citation_format,
            'Dataset License': rights_text,
            'Dataset Usage Statement': _extract_by_label(soup, ['数据共享方式']),
            'Dataset Download URL': None,
            'Dataset Access URL': access_url,
        },
        'Extension Info': {
            'Source Description': source_description,
            'Processing Method': processing_method,
            'Quality Description': quality_description,
            'Spatial Resolution': resolution,
            'Projection': projection,
            'Data Category': _extract_by_label(soup, ['数据分类']),
            'Themes': _extract_list_values(soup, ['主题']),
            'Locations': _extract_list_values(soup, ['地点']),
            'Data Producer': creators,
            'Contact': contact_info.get('联系人'),
            'Service Phone': contact_info.get('服务电话'),
            'Service Email': contact_info.get('服务邮箱'),
        },
    }

    return {'zh': zh, 'en': en}