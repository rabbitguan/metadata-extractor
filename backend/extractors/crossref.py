from __future__ import annotations

import re
from html import unescape
from typing import Optional

from .base import MetadataDict


RULE_NAME = 'Crossref'


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value))
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text or None


def _parse_crossref_lines(content: str) -> dict[str, str]:
    fields = {}
    for line in str(content or '').splitlines():
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        key = key.strip()
        value = _clean_text(value)
        if key and value:
            fields[key] = value
    return fields


def _first_date(*values: Optional[str]) -> Optional[str]:
    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        match = re.search(r'\b(\d{4})(?:[-/](\d{1,2}))?(?:[-/](\d{1,2}))?\b', text)
        if not match:
            continue
        parts = [match.group(1)]
        if match.group(2):
            parts.append(match.group(2).zfill(2))
        if match.group(3):
            parts.append(match.group(3).zfill(2))
        return '-'.join(parts)
    return None


def _split_subjects(value: Optional[str]) -> Optional[list[str]]:
    text = _clean_text(value)
    if not text:
        return None
    items = [item.strip() for item in re.split(r';|,', text) if item.strip()]
    return items or None


def _creator_items(value: Optional[str]) -> Optional[list[dict]]:
    text = _clean_text(value)
    if not text:
        return None
    return [
        {
            'type': 'Person',
            'person': {
                'names': [{'lang': 'en', 'name': text}],
                'emails': None,
                'identifiers': None,
                'affiliations': None,
            },
        }
    ]


def matches(url: str, title: str, content: str) -> bool:
    return 'Metadata Source: Crossref' in str(content or '')


def extract(content: str, url: str, title: str) -> Optional[MetadataDict]:
    fields = _parse_crossref_lines(content)
    doi = _clean_text(fields.get('DOI'))
    resolved_url = _clean_text(fields.get('URL')) or url
    title_text = _clean_text(fields.get('title') or title)
    abstract = _clean_text(fields.get('abstract'))
    subjects = _split_subjects(fields.get('subject'))
    publish_date = _first_date(
        fields.get('published-print'),
        fields.get('published-online'),
        fields.get('issued'),
    )
    publisher = _clean_text(fields.get('publisher'))
    resource_type = _clean_text(fields.get('type')) or 'Data Paper'
    alternative_identifiers = [{'type': 'DOI', 'identifier': doi}] if doi else None
    urls = [item for item in (resolved_url, f'https://doi.org/{doi}' if doi else None) if item]

    return {
        'zh': {
            '资源类型判定': resource_type,
            '领域判定': '核心元数据',
            '资源名称': title_text or doi or resolved_url,
            '描述': abstract,
            '关键词': subjects,
            '生成日期': publish_date,
            '资源访问地址': urls,
            '替代标识符': alternative_identifiers,
            '提供方信息': publisher,
        },
        'en': {
            'Resource Type Classification': resource_type,
            'Domain Classification': 'Core Metadata',
            'titles': [{'lang': 'en', 'name': title_text or doi or resolved_url}],
            'creators': _creator_items(fields.get('author')),
            'publisher': {'names': [{'lang': 'en', 'name': publisher}], 'identifiers': None} if publisher else None,
            'publish_date': publish_date,
            'descriptions': [{'lang': 'en', 'description': abstract}] if abstract else None,
            'keywords': [{'lang': 'en', 'keyword': subjects}] if subjects else None,
            'subjects': [{'standard_gbt': None, 'standard_oecd': subjects}] if subjects else None,
            'language': 'en',
            'alternative_identifiers': alternative_identifiers,
            'urls': urls,
            'resource_type': resource_type,
        },
    }
