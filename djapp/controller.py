"""Controlador MVC: conecta eventos de la vista con modelo y audio."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np

from .audio_engine import AudioEngine
from .library import PlaylistLibrary
from .sampler import SamplerStore


class DJController:
    def __init__(self, vista):
        self.view = vista
        self.library = PlaylistLibrary()
        self.sampler = SamplerStore()
        self.audio = AudioEngine()
        self.audio.sample_gains = self.sampler.gains.copy()
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="JULIOPRODDJ")
        self.jobs = []
        self.selected_track: str | None = None
        for index, item in enumerate(self.sampler.pads):
            if item and Path(item["path"]).is_file():
                self.load_sample(index, item["path"], persist=False)
            elif item:
                self.view.sample_assigned(index, f"{item['title']} (no encontrado)")

    def load_sample(self, index: int, ruta: str, persist: bool = True) -> None:
        if Path(ruta).suffix.lower() != ".mp3":
            self.view.error("Los pads aceptan archivos MP3.")
            return
        future = self.pool.submit(self.audio.decode, ruta)
        def loaded():
            self.audio.set_sample(index, future.result())
            item = self.sampler.assign(index, ruta) if persist else self.sampler.pads[index]
            self.view.sample_assigned(index, item["title"] if item else Path(ruta).stem)
            self.view.status(f"Pad F{index + 1}: {Path(ruta).name} listo")
        self.jobs.append((future, loaded,
                          "El archivo termina en .mp3, pero su contenido no se pudo decodificar. "
                          "Comprueba que sea un MP3 válido, completo y no esté dañado; el nombre no influye."))
        self.view.status(f"Decodificando MP3 para F{index + 1}…")

    def clear_sample(self, index: int) -> None:
        self.audio.clear_sample(index)
        self.audio.sample_gains[index] = 1.0
        self.sampler.clear(index)
        self.view.sample_cleared(index)
        self.view.status(f"Pad F{index + 1} vacío")

    def set_sample_gain(self, index: int, value: float) -> None:
        self.audio.sample_gains[index] = float(value)
        self.sampler.set_gain(index, value)

    def trigger_sample(self, index: int) -> None:
        if not self.audio.trigger_sample(index):
            self.view.status(f"Asigna un MP3 al pad F{index + 1}")
            return
        self.start_audio()

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
        self.jobs.append((futuro, lambda: self._loaded(deck, ruta),
                          "No se pudo decodificar el audio. Comprueba que sea un MP3 o WAV válido y accesible."))
        self.view.status(f"Decodificando en Deck {deck}…")

    def _loaded(self, deck: str, ruta: str) -> None:
        modelo = self.audio.decks[deck]
        self.view.deck_loaded(deck, Path(ruta).name, modelo.duration, modelo.audio)
        self.view.status(f"Deck {deck}: pista lista")

    def pump_jobs(self) -> None:
        pendientes = []
        for future, done, error_message in self.jobs:
            if future.done():
                try:
                    future.result()
                    done()
                except Exception as exc:
                    self.view.error(f"{error_message}\n\nDetalle del decodificador: {exc}")
            else:
                pendientes.append((future, done, error_message))
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
