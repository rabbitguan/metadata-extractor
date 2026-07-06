from __future__ import annotations

import re
from html import unescape
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup


RULE_NAME = 'PKU Thesis'


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


def _split_keywords(value: Optional[str]) -> list[str]:
    text = _clean_text(value)
    if not text:
        return []
    parts = re.split(r'[;；,，、]\s*', text)
    return [part for part in (_clean_text(item) for item in parts) if part]


def _extract_detail_value(soup: BeautifulSoup, label_names: set[str]) -> Optional[str]:
    for item in soup.select('.paper-detail-list > li'):
        label_el = item.find('label')
        if not label_el:
            continue

        label_text = _clean_text(label_el.get_text(' ', strip=True))
        if not label_text:
            continue

        label_text = label_text.rstrip('：:')
        if label_text not in label_names:
            continue

        value_el = item.find(class_='text')
        if not value_el:
            continue

        value_text = _text_or_none(value_el)
        if value_text:
            return value_text

    return None


def _extract_detail_values(soup: BeautifulSoup, label_names: set[str]) -> list[str]:
    values: list[str] = []
    for item in soup.select('.paper-detail-list > li'):
        label_el = item.find('label')
        if not label_el:
            continue

        label_text = _clean_text(label_el.get_text(' ', strip=True))
        if not label_text:
            continue

        label_text = label_text.rstrip('：:')
        if label_text not in label_names:
            continue

        value_el = item.find(class_='text')
        if not value_el:
            continue

        value_text = _text_or_none(value_el)
        if value_text:
            values.append(value_text)

    return values


def _extract_full_text_url(soup: BeautifulSoup, fallback_url: str) -> Optional[str]:
    for anchor in soup.find_all('a', href=True):
        anchor_text = _clean_text(anchor.get_text(' ', strip=True)) or ''
        href = anchor.get('href') or ''
        if '查看全文' in anchor_text or '全文' in anchor_text or 'full' in href.lower():
            href = href.strip()
            if href.startswith('http://') or href.startswith('https://'):
                return href
            if href.startswith('/'):
                return f'https://thesis.lib.pku.edu.cn{href}'

    return fallback_url or None


def _extract_cstr_identifier(html: str, *extra_values: Optional[str]) -> Optional[str]:
    cstr_pattern = re.compile(r'\b[A-Z0-9]{5}\.\d{2}\.[-._;()/:A-Z0-9]+\b', re.IGNORECASE)
    combined = ' '.join([html, *[value for value in extra_values if value]])
    match = cstr_pattern.search(combined)
    if match:
        return match.group(0)
    return None


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').strip().lower()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()
    return bool(
        'thesis.lib.pku.edu.cn/detail' in normalized_url
        or '学位论文数据库' in combined
        or '中文题名' in combined
        or '外文题名' in combined
        or '论文总页数' in combined
    )


def extract(content: str, url: str = '', title: str = '') -> Optional[Dict[str, Any]]:
    if not content:
        return None

    soup = BeautifulSoup(content, 'html.parser')

    title_zh = _text_or_none(soup.select_one('.title-box .title')) or _extract_detail_value(soup, {'中文题名', '题名', '中文标题'}) or (title or None)
    title_en = _extract_detail_value(soup, {'外文题名', '英文题名'})

    abstract_zh = _extract_detail_value(soup, {'中文摘要'})
    abstract_en = _extract_detail_value(soup, {'外文摘要'})

    keywords_zh = _split_keywords(_extract_detail_value(soup, {'中文关键词', '关键词'}))
    keywords_en = _split_keywords(_extract_detail_value(soup, {'外文关键词'}))

    author = _extract_detail_value(soup, {'作者'})
    unit = _extract_detail_value(soup, {'培养单位'})
    department = _extract_detail_value(soup, {'院系'})
    subject_code = _extract_detail_value(soup, {'学科代码'})
    major = _extract_detail_value(soup, {'专业'})
    training_level = _extract_detail_value(soup, {'培养层次'})
    degree = _extract_detail_value(soup, {'学位'})
    student_id = _extract_detail_value(soup, {'学号'})
    defense_date = _extract_detail_value(soup, {'答辩日期'})
    open_date = _extract_detail_value(soup, {'开放日期'})
    language_code = _extract_detail_value(soup, {'论文语种'})
    library_number = _extract_detail_value(soup, {'馆藏号'})
    page_count = _extract_detail_value(soup, {'论文总页数'})
    reference_count = _extract_detail_value(soup, {'参考文献总数'})
    reference_list = _extract_detail_value(soup, {'参考文献列表'})

    authors = [author] if author else []
    contributors = _extract_detail_values(soup, {'导师1姓名', '导师2姓名', '导师3姓名'})
    alternative_identifiers = [f'{library_number}（馆藏号）'] if library_number else []

    title_zh_value = title_zh or title_en or url
    title_en_value = title_en or title_zh or url

    abstract_zh_value = abstract_zh or abstract_en
    abstract_en_value = abstract_en or abstract_zh

    keywords_zh_value = keywords_zh or keywords_en
    keywords_en_value = keywords_en or keywords_zh

    language_value_zh = language_code or None
    language_value_en = 'Chinese' if language_code and language_code.lower() == 'chi' else (language_code or None)

    publication_date = open_date or defense_date
    received_date = defense_date or open_date
    version_info_zh = _extract_detail_value(soup, {'版本信息', '版本'})
    version_info_en = version_info_zh
    publisher = unit or '北京大学'

    full_text_url = _extract_full_text_url(soup, url)
    cstr_identifier = _extract_cstr_identifier(content, title_zh_value, title_en_value, abstract_zh_value, abstract_en_value)

    metadata: Dict[str, Any] = {
        'zh': {
            '资源类型判定': '数据论文',
            '领域判定': '数据论文元数据',
            '标识符': cstr_identifier,
            'CSTR标识符': cstr_identifier,
            '资源名称': title_zh_value,
            '描述': abstract_zh_value,
            '关键词': keywords_zh_value,
            '学科分类': major,
            '主题分类': subject_code,
            '语言': language_value_zh,
            '创建者': authors if authors else None,
            '发布机构': publisher,
            '发布日期': publication_date,
            '贡献者': contributors if contributors else None,
            '替代标识符': alternative_identifiers if alternative_identifiers else None,
            '关联标识符': None,
            '权限': '公开',
            '资助者': None,
            '版本': version_info_zh,
            '资源链接': url,
            '资源类型': '数据论文',
            '数据论文内容信息': {
                '标识符': cstr_identifier,
                '标题': title_zh_value,
                '摘要': abstract_zh_value,
                '关键词': keywords_zh_value,
                '数据论文作者': {
                    '作者姓名': authors if authors else None,
                    '工作单位': unit,
                    '电子邮箱': None,
                    '工作贡献': None,
                    '作者简介': None,
                },
                '数据采集和处理方法': None,
                '引言': None,
                '数据样本描述': None,
                '数据质量控制和评估': None,
                '数据使用方法和建议': None,
                '参考文献': reference_list,
                '致谢': None,
            },
            '数据论文出版信息': {
                '收稿日期': received_date,
                '同评日期': None,
                '录用日期': None,
                '出版日期': publication_date,
                '版本信息': version_info_zh,
                '出版期刊': unit or '北京大学',
            },
            '数据论文服务信息': {
                '数据论文引用格式': None,
                '数据论文下载地址': full_text_url,
                '数据论文共享许可协议': None,
                '数据集访问地址': None,
            },
            '扩展信息': {
                '培养层次': training_level,
                '学位': degree,
                '院系': department,
                '学号': student_id,
                '馆藏号': library_number,
                '论文总页数': page_count,
                '参考文献总数': reference_count,
            },
        },
        'en': {
            'Resource Type Classification': 'Data Paper',
            'Domain Classification': 'Data Paper Metadata',
            'Identifier': cstr_identifier,
            'Title': title_en_value,
            'Description': abstract_en_value,
            'Keywords': keywords_en_value,
            'Discipline Classification': major,
            'Subject Classification': subject_code,
            'Language': language_value_en,
            'Creators': authors if authors else None,
            'Publisher': publisher,
            'Publication Date': publication_date,
            'Contributors': contributors if contributors else None,
            'Alternative Identifiers': alternative_identifiers if alternative_identifiers else None,
            'Related Identifiers': None,
            'Rights': 'Open',
            'Funders': None,
            'Version': version_info_en,
            'Resource URL': url,
            'ResourceType': 'Data Paper',
            'Data Paper Content Information': {
                'Identifier': cstr_identifier,
                'Title': title_en_value,
                'Abstract': abstract_en_value,
                'Keywords': keywords_en_value,
                'Data Paper Authors': {
                    'Author Name': authors if authors else None,
                    'Affiliation': unit,
                    'Email': None,
                    'Contribution': None,
                    'Biography': None,
                },
                'Data Collection and Processing Methods': None,
                'Introduction': None,
                'Data Sample Description': None,
                'Data Quality Control and Evaluation': None,
                'Data Use Methods and Recommendations': None,
                'References': reference_list,
                'Acknowledgements': None,
            },
            'Data Paper Publication Information': {
                'Received Date': received_date,
                'Review Date': None,
                'Accepted Date': None,
                'Publication Date': publication_date,
                'Version Information': version_info_en,
                'Journal': unit or 'Peking University',
            },
            'Data Paper Service Information': {
                'Data Paper Citation Format': None,
                'Data Paper Download URL': full_text_url,
                'Data Paper License': None,
                'Dataset Access URL': None,
            },
            'Extension Info': {
                'Training Level': training_level,
                'Degree': degree,
                'Department': department,
                'Student ID': student_id,
                'Library Number': library_number,
                'Page Count': page_count,
                'Reference Count': reference_count,
            },
        },
    }

    return metadata
