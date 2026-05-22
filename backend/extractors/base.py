from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional


MetadataDict = Dict[str, object]


@dataclass(frozen=True)
class ExtractorRule:
    name: str
    matches: Callable[[str, str, str], bool]
    extract: Callable[[str, str, str], Optional[MetadataDict]]
