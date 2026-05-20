from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import List, Optional

from .base import ExtractorRule, MetadataDict


PACKAGE_DIR = Path(__file__).resolve().parent


def _load_rules() -> List[ExtractorRule]:
    rules: List[ExtractorRule] = []
    package_name = __package__ or 'extractors'

    for module_info in pkgutil.iter_modules([str(PACKAGE_DIR)]):
        if module_info.name in {'base', 'manager', '__init__'}:
            continue

        module = importlib.import_module(f'{package_name}.{module_info.name}')
        rule_name = getattr(module, 'RULE_NAME', module_info.name)
        matches = getattr(module, 'matches', None)
        extract = getattr(module, 'extract', None)

        if callable(matches) and callable(extract):
            rules.append(ExtractorRule(name=rule_name, matches=matches, extract=extract))

    return rules


_RULES = _load_rules()


def list_extractors() -> List[str]:
    return [rule.name for rule in _RULES]


def detect_extractor(url: str, title: str, content: str) -> Optional[ExtractorRule]:
    for rule in _RULES:
        try:
            if rule.matches(url, title, content):
                return rule
        except Exception:
            continue
    return None


def extract_metadata(url: str, title: str, content: str) -> Optional[MetadataDict]:
    rule = detect_extractor(url, title, content)
    if not rule:
        return None

    return rule.extract(content, url, title)
