"""Modelo persistente de los doce pads de audio."""
from __future__ import annotations

import json
from pathlib import Path

from .library import data_directory


class SamplerStore:
    """Guarda en disco las rutas y nombres de audio asignados a cada pad."""

    PAD_COUNT = 12

    def __init__(self):
        self.file = data_directory() / "sampler.json"
        self.pads: list[dict | None] = [None] * self.PAD_COUNT
        self.gains = [1.0] * self.PAD_COUNT
        self._load()

    def _load(self) -> None:
        if not self.file.exists():
            return
        try:
            raw = json.loads(self.file.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                return
            for index, item in enumerate(raw[:self.PAD_COUNT]):
                if isinstance(item, dict) and item.get("path"):
                    path = str(Path(item["path"]).resolve())
                    self.pads[index] = {
                        "path": path,
                        "title": str(item.get("title") or Path(path).stem),
                    }
                    self.gains[index] = max(0.0, min(2.0, float(item.get("gain", 1.0))))
        except (OSError, ValueError, TypeError):
            self.pads = [None] * self.PAD_COUNT

    def save(self) -> None:
        temporal = self.file.with_suffix(".json.tmp")
        records = [({**item, "gain": self.gains[index]} if item else None)
                   for index, item in enumerate(self.pads)]
        temporal.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        temporal.replace(self.file)

    def assign(self, index: int, path: str) -> dict:
        resolved = str(Path(path).resolve())
        item = {"path": resolved, "title": Path(resolved).stem}
        self.pads[index] = item
        self.save()
        return item

    def clear(self, index: int) -> None:
        self.pads[index] = None
        self.gains[index] = 1.0
        self.save()

    def set_gain(self, index: int, gain: float) -> None:
        self.gains[index] = max(0.0, min(2.0, float(gain)))
        self.save()
