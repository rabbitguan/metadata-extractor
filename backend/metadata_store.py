import hashlib
import json
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from typing import Any, Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'metadata_history.sqlite3'


def _connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_metadata_store():
    with _connect() as connection:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requested_url TEXT NOT NULL,
                page_title TEXT,
                page_html TEXT NOT NULL,
                html_sha256 TEXT NOT NULL,
                mode TEXT NOT NULL,
                strategy TEXT,
                resource_type_zh TEXT,
                resource_type_en TEXT,
                domain_classification_zh TEXT,
                domain_classification_en TEXT,
                core_metadata_json TEXT NOT NULL,
                domain_metadata_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_analysis_history_url ON analysis_history(requested_url)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_analysis_history_hash ON analysis_history(html_sha256)')


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def _normalize_url_candidate(value: Any) -> str:
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


def _collect_url_candidates(*values: Any) -> List[str]:
    candidates: List[str] = []
    seen = set()
    for value in values:
        candidate = _normalize_url_candidate(value)
        if candidate and candidate not in seen:
            candidates.append(candidate)
            seen.add(candidate)

    return candidates


def _extract_section_bundle(result_payload: Dict[str, Any], language_key: str, core_key: str) -> Dict[str, Any]:
    section_bundle = result_payload.get(language_key)
    if not isinstance(section_bundle, dict):
        return {}

    if core_key not in section_bundle:
        return section_bundle

    return section_bundle


def _extract_core_bundle(result_payload: Dict[str, Any], language_key: str, core_key: str) -> Dict[str, Any]:
    bundle = result_payload.get(language_key)
    if not isinstance(bundle, dict):
        bundle = result_payload
    if not isinstance(bundle, dict):
        return {}

    core = bundle.get(core_key)
    if not isinstance(core, dict) and core_key == 'Core Metadata':
        core = bundle.get('核心元数据')
    if not isinstance(core, dict) and core_key == '核心元数据':
        core = bundle.get('Core Metadata')
    if isinstance(core, dict) and isinstance(core.get('metadatas'), list) and core['metadatas']:
        first_metadata = core['metadatas'][0]
        return first_metadata if isinstance(first_metadata, dict) else {}
    return core if isinstance(core, dict) else {}


def _extract_domain_bundle(result_payload: Dict[str, Any], language_key: str, core_key: str) -> Dict[str, Any]:
    bundle = result_payload.get(language_key)
    if not isinstance(bundle, dict):
        bundle = result_payload
    if not isinstance(bundle, dict):
        return {}

    domain_bundle: Dict[str, Any] = {}
    for key, value in bundle.items():
        if key in {core_key, '核心元数据', 'Core Metadata'}:
            continue
        domain_bundle[key] = value
    return domain_bundle


def _domain_from_resource_type(resource_type: Any, language: str) -> str:
    value = str(resource_type or '').strip()
    if language == 'en':
        return {
            'Dataset': 'Dataset Metadata',
            'Data Paper': 'Data Paper Metadata',
            'Standard Literature': 'Standard Literature Metadata',
            'Ecological Data': 'Ecological Science Data Metadata',
            'Other': 'Core Metadata',
        }.get(value, 'Core Metadata')

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
    }.get(value, '核心元数据')


def save_analysis_history(
    *,
    requested_url: str,
    page_title: str,
    page_html: str,
    mode: str,
    strategy: str,
    result_payload: Dict[str, Any],
) -> int:
    html_hash = hashlib.sha256((page_html or '').encode('utf-8')).hexdigest()

    core_zh = _extract_core_bundle(result_payload, 'zh', '核心元数据')
    core_en = _extract_core_bundle(result_payload, 'en', 'Core Metadata')
    domain_zh = _extract_domain_bundle(result_payload, 'zh', '核心元数据')
    domain_en = _extract_domain_bundle(result_payload, 'en', 'Core Metadata')

    resource_type_zh = core_zh.get('resource_type') or core_zh.get('资源类型')
    resource_type_en = core_en.get('resource_type') or core_en.get('ResourceType')
    domain_classification_zh = _domain_from_resource_type(resource_type_zh, 'zh')
    domain_classification_en = _domain_from_resource_type(resource_type_en, 'en')

    with _connect() as connection:
        cursor = connection.execute(
            '''
            INSERT INTO analysis_history (
                requested_url,
                page_title,
                page_html,
                html_sha256,
                mode,
                strategy,
                resource_type_zh,
                resource_type_en,
                domain_classification_zh,
                domain_classification_en,
                core_metadata_json,
                domain_metadata_json,
                result_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                requested_url,
                page_title,
                page_html,
                html_hash,
                mode,
                strategy,
                resource_type_zh,
                resource_type_en,
                domain_classification_zh,
                domain_classification_en,
                _json_dumps({'zh': core_zh, 'en': core_en}),
                _json_dumps({'zh': domain_zh, 'en': domain_en}),
                _json_dumps(result_payload),
            ),
        )
        return int(cursor.lastrowid)


def list_analysis_history(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    safe_limit = max(1, min(int(limit or 20), 200))
    safe_offset = max(0, int(offset or 0))

    with _connect() as connection:
        rows = connection.execute(
            '''
            SELECT
                id,
                requested_url,
                page_title,
                html_sha256,
                mode,
                strategy,
                resource_type_zh,
                resource_type_en,
                domain_classification_zh,
                domain_classification_en,
                created_at
            FROM analysis_history
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            ''',
            (safe_limit, safe_offset),
        ).fetchall()

    return [dict(row) for row in rows]


def get_latest_analysis_history_by_url(*, requested_url: str = '', text: str = '') -> Optional[Dict[str, Any]]:
    candidates = _collect_url_candidates(requested_url)

    if text:
        for match in re.finditer(r'https?://[^\s<>"\'\)\]\}]+', text, re.IGNORECASE):
            candidates.extend(_collect_url_candidates(match.group(0)))

    # Preserve order while removing duplicates.
    deduplicated_candidates = []
    seen = set()
    for candidate in candidates:
        if candidate and candidate not in seen:
            deduplicated_candidates.append(candidate)
            seen.add(candidate)

    if not deduplicated_candidates:
        return None

    placeholders = ','.join('?' for _ in deduplicated_candidates)
    with _connect() as connection:
        row = connection.execute(
            f'''
            SELECT
                id,
                requested_url,
                page_title,
                page_html,
                html_sha256,
                mode,
                strategy,
                resource_type_zh,
                resource_type_en,
                domain_classification_zh,
                domain_classification_en,
                core_metadata_json,
                domain_metadata_json,
                result_json,
                created_at
            FROM analysis_history
            WHERE requested_url IN ({placeholders})
            ORDER BY id DESC
            LIMIT 1
            ''',
            deduplicated_candidates,
        ).fetchone()

    return dict(row) if row else None
