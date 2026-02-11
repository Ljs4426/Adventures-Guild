from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


class FormulaManager:
    def __init__(self, path: str = "formulas.json") -> None:
        self._path = Path(path)
        self._cache: Dict[str, Dict[str, str]] = {}

    def _load(self) -> None:
        if self._cache:
            return
        if not self._path.exists():
            self._cache = {}
            return
        # Load once and keep it in memory.
        self._cache = json.loads(self._path.read_text(encoding="utf-8"))

    def get_sheet_formulas(self, sheet_name: str) -> Dict[str, str]:
        self._load()
        return self._cache.get(sheet_name, {})

    def render(self, template: str, row: int) -> str:
        return template.replace("{row}", str(row))
