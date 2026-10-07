from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CurveRecord:
    entry_id: str
    reference: str | None
    doi: str | None
    material_electrode: str | None
    electrolyte: str | None
    experiment_type: str | None
    units: dict[str, str] = field(default_factory=dict)
    frame: Any = None
    source_path: Path | None = None
    potential_col: str | None = None
    signal_col: str | None = None
    time_col: str | None = None
    signal_kind: str = "unknown"
    raw_metadata: dict[str, Any] = field(default_factory=dict)

