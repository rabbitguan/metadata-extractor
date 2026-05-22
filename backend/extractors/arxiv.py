from __future__ import annotations

import re
from html import unescape
from typing import Optional

from .base import MetadataDict
import re as _re


RULE_NAME = 'arXiv'
ARXIV_ABS_PATTERN = re.compile(r'^https?://arxiv\.org/abs/\d{4}\.\d{4,5}(?:v\d+)?/?$', re.IGNORECASE)
ARXIV_INLINE_PATTERN = re.compile(r'arxiv\.org/abs/\d{4}\.\d{4,5}(?:v\d+)?', re.IGNORECASE)


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value))
    text = re.sub(r'\s+', ' ', text).strip()
    return text or None


def _extract_meta_content(html: str, meta_name: str) -> Optional[str]:
    pattern = rf'<meta\s+name=["\']{re.escape(meta_name)}["\']\s+content=["\']([^"\']*)["\']'
    match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return _clean_text(match.group(1))
    return None


def _extract_first_match(html: str, pattern: str, flags=re.IGNORECASE | re.DOTALL) -> Optional[str]:
    match = re.search(pattern, html, flags=flags)
    if match:
        return _clean_text(match.group(1))
    return None


def _extract_arxiv_identifier(url: str, html: str) -> Optional[str]:
    url_match = re.search(r'arxiv\.org/abs/(\d{4}\.\d{4,5})(?:v\d+)?', url, flags=re.IGNORECASE)
    if url_match:
        return url_match.group(1)

    meta_id = _extract_meta_content(html, 'citation_arxiv_id')
    if meta_id:
        return meta_id

    return _extract_first_match(html, r'arXiv:(\d{4}\.\d{4,5})')


def _extract_arxiv_subjects(html: str) -> tuple[Optional[str], Optional[str]]:
    primary = _extract_first_match(html, r'<span class="primary-subject">([^<]+)</span>')
    if not primary:
        return None, None

    if '(' in primary and primary.endswith(')'):
        subject_name, code = primary.rsplit('(', 1)
        return _clean_text(subject_name), code.rstrip(')')
    return _clean_text(primary), None


def _extract_arxiv_version(html: str, url: str) -> Optional[str]:
    match = re.search(r'<strong>\s*\[(v\d+)\]\s*</strong>', html, flags=re.IGNORECASE)
    if match:
        return _clean_text(match.group(1))

    match = re.search(r'/abs/\d{4}\.\d{4,5}(v\d+)', url, flags=re.IGNORECASE)
    if match:
        return _clean_text(match.group(1))

    og_url = _extract_first_match(html, r'<meta\s+property=["\']og:url["\']\s+content=["\']([^"\']+)["\']')
    if og_url:
        match = re.search(r'/abs/\d{4}\.\d{4,5}(v\d+)', og_url, flags=re.IGNORECASE)
        if match:
            return _clean_text(match.group(1))

    return None


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').strip()
    combined = ' '.join([str(title or ''), str(content or '')]).lower()
    return bool(ARXIV_ABS_PATTERN.search(normalized_url) or ARXIV_INLINE_PATTERN.search(normalized_url) or 'arxiv' in combined)


def extract(content: str, url: str, title: str) -> Optional[MetadataDict]:
    html = content or ''
    arxiv_id = _extract_arxiv_identifier(url, html)
    title_text = (
        _extract_meta_content(html, 'citation_title')
        or _extract_first_match(html, r'<h1 class="title[^>]*>\s*<span class="descriptor">Title:</span>(.*?)</h1>')
        or title
    )
    abstract_text = _extract_meta_content(html, 'citation_abstract') or _extract_first_match(
        html,
        r'<blockquote class="abstract[^>]*>\s*<span class="descriptor">Abstract:</span>(.*?)</blockquote>',
    )
    authors = re.findall(r'<meta\s+name=["\']citation_author["\']\s+content=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    if not authors:
        authors = re.findall(r'<div class="authors">.*?<a[^>]*>([^<]+)</a>', html, flags=re.IGNORECASE | re.DOTALL)
    authors = [_clean_text(author) for author in authors if _clean_text(author)]
    subject_name, subject_code = _extract_arxiv_subjects(html)
    version_info = _extract_arxiv_version(html, url)
    submitted_date = _extract_meta_content(html, 'citation_date') or _extract_first_match(html, r'\[Submitted on\s+([^\]]+)\]')
    publication_date = _clean_text(submitted_date)
    doi = _extract_first_match(html, r'<a[^>]+id="arxiv-doi-link"[^>]*>(https://doi\.org/[^<]+)</a>')
    pdf_url = _extract_meta_content(html, 'citation_pdf_url') or (f'https://arxiv.org/pdf/{arxiv_id}' if arxiv_id else None)
    license_url = _extract_first_match(html, r'<div class="abs-license">.*?<a[^>]+href="([^"]+)"', flags=re.IGNORECASE | re.DOTALL)
    journal_ref = _extract_meta_content(html, 'citation_journal_title')
    keywords = [item for item in [subject_name, subject_code] if item]
    primary_identifier = arxiv_id or url
    alternative_identifiers = [doi] if doi else []
    # 验证并提取 CSTR 标识符（格式示例: 12345.12.123456.123456）
    cstr_pattern = _re.compile(r'\d{5}\.\d{2}\.\d{6}\.\d{6}')
    combined_for_cstr = ' '.join(filter(None, [primary_identifier, ' '.join(alternative_identifiers), title_text or '', abstract_text or '', html]))
    cstr_match = cstr_pattern.search(combined_for_cstr)
    cstr_id = cstr_match.group(0) if cstr_match else None

    metadata = {
        'zh': {
            '资源类型判定': '数据论文',
            '领域判定': '数据论文元数据',
            '标识符': primary_identifier,
            'CSTR标识符': cstr_id,
            '资源名称': _clean_text(title_text) or arxiv_id or url,
            '描述': _clean_text(abstract_text),
            '关键词': keywords,
            '生成日期': publication_date,
            '注册日期': None,
            '最新发布日期': None,
            '学科分类': _clean_text(subject_name),
            '主题分类': _clean_text(subject_code),
            '知识产权类别': None,
            '资源使用许可': _clean_text(license_url),
            '资源访问地址': url,
            '替代标识符': alternative_identifiers,
            '共享方式': None,
            '提供方信息': None,
            '服务方信息': None,
            '数据论文内容信息': {
                '标识符': primary_identifier,
                '标题': _clean_text(title_text) or arxiv_id or url,
                '摘要': _clean_text(abstract_text),
                '关键词': keywords,
                '数据论文作者': {
                    '作者姓名': authors if authors else None,
                    '工作单位': None,
                    '电子邮箱': None,
                    '工作贡献': None,
                    '作者简介': None,
                },
                '数据采集和处理方法': None,
            },
            '数据论文出版信息': {
                '收稿日期': publication_date,
                '同评日期': None,
                '录用日期': None,
                '出版期刊': journal_ref,
            },
            '数据论文服务信息': {
                '数据论文下载地址': pdf_url,
                '数据论文共享许可协议': _clean_text(license_url),
            },
            '扩展信息': '',
        },
        'en': {
            'Resource Type Classification': 'Data Paper',
            'Domain Classification': 'Data Paper Metadata',
            'Identifier': primary_identifier,
            'Resource Name': _clean_text(title_text) or arxiv_id or url,
            'Description': _clean_text(abstract_text),
            'Keywords': keywords,
            'Generation Date': publication_date,
            'Registration Date': None,
            'Latest Release Date': None,
            'Discipline Classification': _clean_text(subject_name),
            'Subject Classification': _clean_text(subject_code),
            'Intellectual Property Type': None,
            'Usage License': _clean_text(license_url),
            'Resource Access URL': url,
            'Alternative Identifiers': alternative_identifiers,
            'Sharing Details': None,
            'Provider Information': None,
            'Service Provider Information': None,
            'Data Paper Content Information': {
                'Identifier': primary_identifier,
                'Title': _clean_text(title_text) or arxiv_id or url,
                'Abstract': _clean_text(abstract_text),
                'Keywords': keywords,
                'Data Paper Authors': {
                    'Author Name': authors if authors else None,
                    'Affiliation': None,
                    'Email': None,
                    'Contribution': None,
                    'Biography': None,
                },
                'Data Collection and Processing Methods': None,
            },
            'Data Paper Publication Information': {
                'Received Date': publication_date,
                'Review Date': None,
                'Accepted Date': None,
                'Journal': journal_ref,
            },
            'Data Paper Service Information': {
                'Data Paper Download URL': pdf_url,
                'Data Paper License': _clean_text(license_url),
            },
            'Extension Info': '',
        },
    }

    return metadata
