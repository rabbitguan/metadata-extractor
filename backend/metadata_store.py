import hashlib
import json
import sqlite3
from pathlib import Path
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
        return {}

    core = bundle.get(core_key)
    return core if isinstance(core, dict) else {}


def _extract_domain_bundle(result_payload: Dict[str, Any], language_key: str, core_key: str) -> Dict[str, Any]:
    bundle = result_payload.get(language_key)
    if not isinstance(bundle, dict):
        return {}

    domain_bundle: Dict[str, Any] = {}
    for key, value in bundle.items():
        if key == core_key:
            continue
        domain_bundle[key] = value
    return domain_bundle


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

    resource_type_zh = core_zh.get('资源类型')
    resource_type_en = core_en.get('ResourceType')
    domain_classification_zh = core_zh.get('领域判定')
    domain_classification_en = core_en.get('Domain Classification')

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
