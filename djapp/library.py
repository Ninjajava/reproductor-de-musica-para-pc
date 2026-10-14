"""Modelo de biblioteca y persistencia relativa al directorio de la aplicación."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from mutagen import File as AudioTags


def data_directory() -> Path:
    """Carpeta persistente junto al programa (también al ejecutar versión congelada)."""
    base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
    target = base / "playlists"
    target.mkdir(parents=True, exist_ok=True)
    return target


class PlaylistLibrary:
    """Gestiona playlists y rutas de audio guardadas en playlists.json."""

    def __init__(self):
        self.directory = data_directory()
        self.file = self.directory / "playlists.json"
        self.playlists: dict[str, list[dict]] = {"Mi música": []}
        self._load()

    def _load(self) -> None:
        if self.file.exists():
            try:
                raw = json.loads(self.file.read_text(encoding="utf-8"))
                self.playlists = {str(k): [self._record(item) for item in v] for k, v in raw.items()}
            except (OSError, ValueError, TypeError):
                self.playlists = {"Mi música": []}
        if not self.playlists:
            self.playlists = {"Mi música": []}

    def save(self) -> None:
        temporal = self.file.with_suffix(".json.tmp")
        temporal.write_text(json.dumps(self.playlists, ensure_ascii=False, indent=2), encoding="utf-8")
        temporal.replace(self.file)

    @staticmethod
    def _record(item) -> dict:
        """Migra las playlists anteriores que solo almacenaban rutas."""
        if isinstance(item, dict):
            return {"path": str(item.get("path", "")), "title": str(item.get("title", "")),
                    "artist": str(item.get("artist", "")), "duration": float(item.get("duration", 0))}
        path = str(item)
        return {"path": path, "title": Path(path).stem, "artist": "", "duration": 0.0}

    def create(self, nombre: str) -> None:
        nombre = nombre.strip()
        if not nombre or nombre in self.playlists:
            raise ValueError("Escribe un nombre nuevo para la playlist.")
        self.playlists[nombre] = []
        self.save()

    def rename(self, anterior: str, nuevo: str) -> None:
        nuevo = nuevo.strip()
        if anterior not in self.playlists or not nuevo or (nuevo != anterior and nuevo in self.playlists):
            raise ValueError("El nombre está vacío o ya existe.")
        self.playlists[nuevo] = self.playlists.pop(anterior)
        self.save()

    def delete(self, nombre: str) -> None:
        if len(self.playlists) <= 1:
            raise ValueError("Debe quedar al menos una playlist.")
        self.playlists.pop(nombre)
        self.save()

    def add(self, nombre: str, rutas: list[str]) -> None:
        actuales = self.playlists[nombre]
        for ruta in rutas:
            p = str(Path(ruta).resolve())
            ya_guardados = {cancion["path"] for cancion in actuales}
            if Path(p).suffix.lower() in {".wav", ".mp3"} and p not in ya_guardados:
                title, artist, duration = Path(p).stem, "", 0.0
                try:
                    tags = AudioTags(p)
                    if tags:
                        def tag_text(primary: str, simple: str, default: str) -> str:
                            value = tags.get(primary)
                            if value is None:
                                value = tags.get(simple, default)
                            if isinstance(value, (list, tuple)):
                                value = value[0] if value else default
                            return str(value)
                        title = tag_text("TIT2", "title", title)
                        artist = tag_text("TPE1", "artist", "")
                        duration = float(getattr(tags.info, "length", 0.0))
                except Exception:
                    pass
                actuales.append({"path": p, "title": title, "artist": artist, "duration": duration})
        self.save()
