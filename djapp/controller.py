"""Controlador MVC: conecta eventos de la vista con modelo y audio."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np

from .audio_engine import AudioEngine
from .library import PlaylistLibrary


class DJController:
    def __init__(self, vista):
        self.view = vista
        self.library = PlaylistLibrary()
        self.audio = AudioEngine()
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="JULIOPRODDJ")
        self.jobs = []
        self.selected_track: str | None = None

    def add_tracks(self, rutas: list[str]) -> None:
        nombre = self.view.selected_playlist()
        if not nombre or not rutas:
            return
        self.library.add(nombre, rutas)
        self.view.refresh_tracks(self.library.playlists[nombre])
        self.view.status(f"{len(rutas)} pista(s) añadida(s) a {nombre}")

    def playlist_changed(self, nombre: str) -> None:
        self.view.refresh_tracks(self.library.playlists.get(nombre, []))

    def create_playlist(self, nombre: str) -> None:
        try:
            self.library.create(nombre)
            self.view.refresh_playlists(list(self.library.playlists), nombre)
            self.view.status("Playlist creada")
        except ValueError as exc:
            self.view.error(str(exc))

    def rename_playlist(self, nuevo: str) -> None:
        anterior = self.view.selected_playlist()
        try:
            self.library.rename(anterior, nuevo)
            self.view.refresh_playlists(list(self.library.playlists), nuevo)
            self.view.status("Playlist renombrada")
        except ValueError as exc:
            self.view.error(str(exc))

    def delete_playlist(self) -> None:
        nombre = self.view.selected_playlist()
        try:
            self.library.delete(nombre)
            siguiente = next(iter(self.library.playlists))
            self.view.refresh_playlists(list(self.library.playlists), siguiente)
            self.view.status("Playlist eliminada")
        except ValueError as exc:
            self.view.error(str(exc))

    def load_deck(self, deck: str, ruta: str | None = None) -> None:
        ruta = ruta or self.selected_track
        if not ruta:
            self.view.error("Selecciona una pista o usa Abrir audio.")
            return
        futuro = self.pool.submit(self.audio.load, deck, ruta)
        self.jobs.append((futuro, lambda: self._loaded(deck, ruta)))
        self.view.status(f"Decodificando en Deck {deck}…")

    def _loaded(self, deck: str, ruta: str) -> None:
        modelo = self.audio.decks[deck]
        self.view.deck_loaded(deck, Path(ruta).name, modelo.duration, modelo.audio)
        self.view.status(f"Deck {deck}: pista lista")

    def pump_jobs(self) -> None:
        pendientes = []
        for future, done in self.jobs:
            if future.done():
                try:
                    future.result()
                    done()
                except Exception as exc:
                    self.view.error(f"No se pudo cargar el audio: {exc}")
            else:
                pendientes.append((future, done))
        self.jobs = pendientes

    def start_audio(self) -> None:
        try:
            self.audio.start()
            self.view.status("Salida de audio activa")
        except Exception as exc:
            self.view.error(f"No se pudo iniciar la salida de audio: {exc}")

    def close(self) -> None:
        self.audio.close()
        self.pool.shutdown(wait=False, cancel_futures=True)
