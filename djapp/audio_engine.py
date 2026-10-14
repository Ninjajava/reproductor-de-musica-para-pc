"""Motor de audio: dos decks se mezclan en un único callback PortAudio."""
from __future__ import annotations

import numpy as np
import sounddevice as sd
import miniaudio
import queue
from scipy.signal import butter, sosfilt

RATE = 44100


class Deck:
    """Estado de un deck. La posición se expresa en frames de la pista."""

    def __init__(self, nombre: str):
        self.nombre = nombre
        self.audio: np.ndarray | None = None
        self.ruta: str | None = None
        self.position = 0.0
        self.playing = False
        self.pitch = 0.0
        self.level = 1.0
        self.gains = [0.0, 0.0, 0.0]
        self.duration = 0.0
        self._states = [np.zeros((1, 2, 2)), np.zeros((1, 2, 2))]
        self._sos = [butter(2, 250, fs=RATE, btype="lowpass", output="sos"),
                     butter(2, 4000, fs=RATE, btype="lowpass", output="sos")]

    def load(self, ruta: str, audio: np.ndarray) -> None:
        self.audio = audio
        self.ruta = ruta
        self.duration = len(audio) / RATE
        self.position = 0.0
        self.playing = False
        self._states = [np.zeros((1, 2, 2)), np.zeros((1, 2, 2))]

    def render(self, frames: int) -> np.ndarray:
        """Renderiza un bloque; llamado exclusivamente por el hilo de audio."""
        pista = self.audio
        if not self.playing or pista is None:
            return np.zeros((frames, 2), dtype=np.float32)
        step = 1.0 + float(self.pitch) / 100.0
        indices = self.position + step * np.arange(frames, dtype=np.float64)
        valid = indices < len(pista)
        bloque = np.zeros((frames, 2), dtype=np.float32)
        if valid.any():
            # Interpolación lineal para pitch variable sin cambiar la duración del dispositivo.
            base = indices[valid]
            left = base.astype(np.int64)
            right = np.minimum(left + 1, len(pista) - 1)
            frac = (base - left)[:, None]
            bloque[valid] = pista[left] * (1.0 - frac) + pista[right] * frac
        self.position += frames * step
        if self.position >= len(pista):
            self.position = float(len(pista))
            self.playing = False
        low, self._states[0] = sosfilt(self._sos[0], bloque, axis=0, zi=self._states[0])
        low_mid, self._states[1] = sosfilt(self._sos[1], bloque, axis=0, zi=self._states[1])
        high, mid = bloque - low_mid, low_mid - low
        lg, mg, hg = (10.0 ** (float(g) / 20.0) for g in self.gains)
        return low * lg + mid * mg + high * hg

    @property
    def elapsed(self) -> float:
        return min(self.position / RATE, self.duration)


class AudioEngine:
    """Salida compartida y mezclador estéreo en tiempo real."""

    def __init__(self):
        self.decks = {"A": Deck("A"), "B": Deck("B")}
        self.crossfader = 0.5
        self.master = 1.0
        self._stream: sd.OutputStream | None = None
        self.samples: list[np.ndarray | None] = [None] * 12
        self._sample_triggers: queue.SimpleQueue[tuple[str, int]] = queue.SimpleQueue()
        self._active_samples: dict[int, list] = {}
        self.sample_progress = [0.0] * 12
        self.sample_gains = [1.0] * 12

    @staticmethod
    def decode(ruta: str) -> np.ndarray:
        """Decodifica WAV/MP3 desde bytes, sin depender del nombre o encoding de la ruta."""
        with open(ruta, "rb") as archivo:
            data = archivo.read()
        decoded = miniaudio.decode(data, miniaudio.SampleFormat.FLOAT32, 2, RATE)
        return np.asarray(decoded.samples, dtype=np.float32).reshape(-1, 2).copy()

    def load(self, deck: str, ruta: str) -> None:
        self.decks[deck].load(ruta, self.decode(ruta))

    def set_sample(self, index: int, audio: np.ndarray) -> None:
        self.samples[index] = audio
        self._sample_triggers.put(("replace", index))

    def clear_sample(self, index: int) -> None:
        self.samples[index] = None
        self._sample_triggers.put(("replace", index))

    def trigger_sample(self, index: int) -> bool:
        if self.samples[index] is None:
            return False
        self._sample_triggers.put(("toggle", index))
        return True

    def start(self) -> None:
        if self._stream is not None:
            return

        def callback(outdata, frames, _time, _status):
            a, b = self.decks["A"].render(frames), self.decks["B"].render(frames)
            x = float(self.crossfader)
            mix = (a * float(self.decks["A"].level) * np.cos(x * np.pi / 2)
                   + b * float(self.decks["B"].level) * np.sin(x * np.pi / 2))
            while True:
                try:
                    command, index = self._sample_triggers.get_nowait()
                except queue.Empty:
                    break
                if command == "replace":
                    self._active_samples.pop(index, None)
                    self.sample_progress[index] = 0.0
                elif index in self._active_samples:
                    del self._active_samples[index]
                    self.sample_progress[index] = 0.0
                else:
                    audio = self.samples[index]
                    if audio is not None:
                        self._active_samples[index] = [audio, 0]
            finished = []
            for index, (audio, position) in self._active_samples.items():
                count = min(frames, len(audio) - position)
                if count > 0:
                    mix[:count] += audio[position:position + count] * float(self.sample_gains[index])
                    position += count
                if position < len(audio):
                    self._active_samples[index][1] = position
                    self.sample_progress[index] = position / len(audio)
                else:
                    finished.append(index)
            for index in finished:
                del self._active_samples[index]
                self.sample_progress[index] = 0.0
            np.clip(mix * float(self.master), -1.0, 1.0, out=mix)
            outdata[:] = mix

        self._stream = sd.OutputStream(samplerate=RATE, channels=2, dtype="float32",
                                       blocksize=512, callback=callback, latency="low")
        self._stream.start()

    def close(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
