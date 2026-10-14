"""Vista oscura de consola DJ, implementada con CustomTkinter."""
from __future__ import annotations

from pathlib import Path
import math
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox

import customtkinter as ctk
import numpy as np


BG = "#090d16"
PANEL = "#111a29"
CYAN = "#00e5ff"
PINK = "#ff3cac"
GREEN = "#53ff9f"
TEXT = "#e8f5ff"


def tiempo(segundos: float) -> str:
    s = max(0, int(segundos))
    return f"{s // 60:02d}:{s % 60:02d}"


class DeckPanel(ctk.CTkFrame):
    """Controles, forma de onda y EQ de un deck."""

    def __init__(self, master, nombre: str, color: str, on_action, on_pitch, on_eq):
        super().__init__(master, fg_color=PANEL, corner_radius=14, border_width=1, border_color="#21344a")
        self.nombre, self.color = nombre, color
        self.on_action, self.on_pitch, self.on_eq = on_action, on_pitch, on_eq
        self.duration = 0.0
        self.title = ctk.CTkLabel(self, text=f"DECK {nombre}  •  SIN PISTA", text_color=color,
                                  font=ctk.CTkFont(size=19, weight="bold"))
        self.title.pack(anchor="w", padx=18, pady=(16, 8))
        self.wave = tk.Canvas(self, height=104, bg="#08111c", highlightthickness=1,
                              highlightbackground="#193448")
        self.wave.pack(fill="x", padx=18, pady=5)
        self.clock = ctk.CTkLabel(self, text="00:00  /  00:00", text_color=TEXT,
                                  font=ctk.CTkFont(family="Consolas", size=17, weight="bold"))
        self.clock.pack(padx=18, pady=(4, 10), anchor="w")
        transport = ctk.CTkFrame(self, fg_color="transparent")
        transport.pack(fill="x", padx=14, pady=3)
        for label, command, color in (("▶ PLAY", "play", color), ("Ⅱ PAUSE", "pause", "#263c52"),
                                      ("■ STOP", "stop", "#263c52")):
            ctk.CTkButton(transport, text=label, fg_color=color if command == "play" else color,
                          hover_color="#2c5269", command=lambda cmd=command: self.on_action(self.nombre, cmd)
                          ).pack(side="left", expand=True, fill="x", padx=4)
        self.pitch_label = ctk.CTkLabel(self, text="PITCH  +0.0%", text_color=color)
        self.pitch_label.pack(anchor="w", padx=18, pady=(10, 0))
        self.pitch = ctk.CTkSlider(self, from_=-12, to=12, number_of_steps=240,
                                   progress_color=color, button_color=color, command=self._pitch)
        self.pitch.set(0)
        self.pitch.pack(fill="x", padx=18, pady=(0, 10))
        eq = ctk.CTkFrame(self, fg_color="transparent")
        eq.pack(fill="x", padx=8, pady=(2, 13))
        self.eq_labels = []
        self.eq_sliders = []
        for index, band in enumerate(("LOW", "MID", "HIGH")):
            cell = ctk.CTkFrame(eq, fg_color="#0b1320", corner_radius=10)
            cell.pack(side="left", expand=True, fill="x", padx=5)
            label = ctk.CTkLabel(cell, text=f"{band}  0 dB", text_color=color,
                                 font=ctk.CTkFont(size=12, weight="bold"))
            label.pack(pady=(8, 0))
            self.eq_labels.append(label)
            slider = ctk.CTkSlider(cell, from_=-12, to=12, orientation="vertical", height=104,
                                   progress_color=color, button_color=color,
                                   command=lambda value, i=index: self._eq(i, value))
            slider.set(0)
            slider.pack(padx=14, pady=8)
            self.eq_sliders.append(slider)

    def _pitch(self, value):
        self.pitch_label.configure(text=f"PITCH  {value:+.1f}%")
        self.on_pitch(self.nombre, value)

    def _eq(self, index, value):
        self.eq_labels[index].configure(text=f"{('LOW','MID','HIGH')[index]}  {value:+.0f} dB")
        self.on_eq(self.nombre, index, value)

    def set_track(self, title: str, duration: float, audio: np.ndarray):
        self.duration = duration
        self.title.configure(text=f"DECK {self.nombre}  •  {title[:42]}")
        self.wave.delete("all")
        width = max(100, self.wave.winfo_width())
        mono = audio.mean(axis=1)
        count = min(width // 3, 400)
        if len(mono) and count:
            bins = np.array_split(mono, count)
            peaks = [float(np.max(np.abs(b))) if len(b) else 0 for b in bins]
            for i, peak in enumerate(peaks):
                x = i * width / count
                h = max(2, peak * 42)
                self.wave.create_line(x, 52-h, x, 52+h, fill=self.color, width=2)
        self.wave.create_line(0, 52, width, 52, fill="#254157")

    def update_clock(self, elapsed: float, duration: float):
        self.clock.configure(text=f"{tiempo(elapsed)}  /  {tiempo(duration)}   −{tiempo(duration-elapsed)}")


class VinylDeckPanel(ctk.CTkFrame):
    """Vista alternativa con un LP animado y transporte para un deck."""

    def __init__(self, master, nombre, color, on_action, on_pitch, on_eq, on_load):
        super().__init__(master, fg_color="#171411", corner_radius=18, border_width=2, border_color="#806342")
        self.nombre, self.color = nombre, color
        self.on_action, self.on_pitch, self.on_eq, self.on_load = on_action, on_pitch, on_eq, on_load
        self.angle = 0.0
        self.playing = False
        self.track_duration = 0.0
        self.title = ctk.CTkLabel(self, text=f"PLATO {nombre}  •  SIN PISTA", text_color=color,
                                  font=ctk.CTkFont(size=18, weight="bold"))
        self.title.pack(anchor="w", padx=18, pady=(15, 3))
        self.canvas = tk.Canvas(self, height=310, bg="#100d0b", highlightthickness=1,
                                highlightbackground="#5a4430")
        self.canvas.pack(fill="both", expand=True, padx=10, pady=(5, 7))
        self.clock = ctk.CTkLabel(self, text="00:00 / 00:00", text_color=TEXT,
                                  font=ctk.CTkFont(family="Consolas", size=16, weight="bold"))
        self.clock.pack(anchor="w", padx=18, pady=4)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=4)
        for label, command in (("▶ PLAY", "play"), ("Ⅱ PAUSE", "pause"), ("■ STOP", "stop")):
            ctk.CTkButton(row, text=label, fg_color=color if command == "play" else "#263c52",
                          hover_color="#2c5269", command=lambda cmd=command: self.on_action(nombre, cmd)
                          ).pack(side="left", expand=True, fill="x", padx=4)
        self.pitch_label = ctk.CTkLabel(self, text="PITCH  +0.0%", text_color=color)
        self.pitch_label.pack(anchor="w", padx=18, pady=(6, 0))
        self.pitch = ctk.CTkSlider(self, from_=-12, to=12, number_of_steps=240,
                                   progress_color=color, button_color=color, command=self._pitch)
        self.pitch.set(0)
        self.pitch.pack(fill="x", padx=18, pady=(0, 8))
        eq = ctk.CTkFrame(self, fg_color="transparent")
        eq.pack(fill="x", padx=10, pady=(0, 8))
        self.eq_sliders = []
        for index, band in enumerate(("LOW", "MID", "HIGH")):
            cell = ctk.CTkFrame(eq, fg_color="#0b1320", corner_radius=8)
            cell.pack(side="left", expand=True, fill="x", padx=4)
            label = ctk.CTkLabel(cell, text=f"{band}  0 dB", text_color=color,
                                 font=ctk.CTkFont(size=11, weight="bold"))
            label.pack(pady=(5, 0))
            slider = ctk.CTkSlider(cell, from_=-12, to=12, orientation="vertical", height=65,
                                   progress_color=color, button_color=color,
                                   command=lambda value, i=index, lab=label:
                                   self._eq(i, value, lab))
            slider.set(0)
            slider.pack(padx=12, pady=4)
            self.eq_sliders.append(slider)
        ctk.CTkButton(self, text=f"CARGAR SELECCIÓN → PLATO {nombre}", fg_color="#1a3345",
                      command=lambda: self.on_load(nombre)).pack(fill="x", padx=18, pady=(0, 14))
        self.canvas.bind("<Configure>", lambda _event: self.draw())

    def _pitch(self, value):
        self.pitch_label.configure(text=f"PITCH  {value:+.1f}%")
        self.on_pitch(self.nombre, value)

    def _eq(self, index, value, label):
        label.configure(text=f"{('LOW','MID','HIGH')[index]}  {value:+.0f} dB")
        self.on_eq(self.nombre, index, value)

    def set_track(self, title, duration):
        self.title.configure(text=f"PLATO {self.nombre}  •  {title[:40]}")
        self.track_duration = duration

    def update_state(self, elapsed, duration, playing):
        self.clock.configure(text=f"{tiempo(elapsed)} / {tiempo(duration)}   −{tiempo(duration-elapsed)}")
        self.playing = playing

    def animate(self):
        if self.playing:
            # 33⅓ rpm: aproximadamente 8 grados por cada 40 ms.
            self.angle = (self.angle + 8) % 360
            self.draw()

    def draw(self):
        canvas = self.canvas
        canvas.delete("all")
        width, height = max(1, canvas.winfo_width()), max(1, canvas.winfo_height())
        radius = max(35, min(width * 0.42, height * 0.45))
        cx, cy = width / 2, height / 2
        canvas.create_oval(cx-radius-11, cy-radius-11, cx+radius+11, cy+radius+11,
                           fill="#30271f", outline="#d0ad7b", width=3)
        canvas.create_oval(cx-radius-5, cy-radius-5, cx+radius+5, cy+radius+5,
                           fill="#1b1d20", outline="#72777a", width=2)
        canvas.create_oval(cx-radius, cy-radius, cx+radius, cy+radius,
                           fill="#090a0c", outline="#92908a", width=2)
        for offset in (0.18, 0.23, 0.29, 0.36, 0.44, 0.53, 0.63, 0.74, 0.84):
            rr = radius * offset
            canvas.create_oval(cx-rr, cy-rr, cx+rr, cy+rr, outline="#30343a", width=1)
        # Marca excéntrica brillante: hace visible la rotación del vinilo.
        theta = math.radians(self.angle - 90)
        mark_r = radius * 0.91
        mx, my = cx + math.cos(theta) * mark_r, cy + math.sin(theta) * mark_r
        canvas.create_oval(mx-5, my-5, mx+5, my+5, fill=self.color, outline="white", width=1)
        label_r = radius * 0.20
        canvas.create_oval(cx-label_r, cy-label_r, cx+label_r, cy+label_r,
                           fill="#bd6236" if self.nombre == "A" else "#b3914d", outline="#f4d37b", width=2)
        canvas.create_oval(cx-4, cy-4, cx+4, cy+4, fill="#111111", outline="#eeeeee")
        canvas.create_text(cx, cy, text="JPDJ", fill="#fff0ce", font=("Segoe UI", 10, "bold"))
        canvas.create_text(cx, cy + label_r + 15, text="33 RPM  /  VINYL", fill="#d5c4a8",
                           font=("Consolas", 8, "bold"))
        # Brazo y cápsula de lectura.
        side = 1 if self.nombre == "A" else -1
        pivot_x, pivot_y = cx + side * radius * 1.24, cy - radius * 0.66
        stylus_x, stylus_y = cx + side * radius * 0.49, cy - radius * 0.43
        canvas.create_line(pivot_x, pivot_y, stylus_x, stylus_y, fill="#171513", width=9, capstyle="round")
        canvas.create_line(pivot_x, pivot_y, stylus_x, stylus_y, fill="#b9b2a7", width=5, capstyle="round")
        canvas.create_line(pivot_x, pivot_y, stylus_x, stylus_y, fill="#e2bd82", width=1)
        canvas.create_oval(pivot_x-12, pivot_y-12, pivot_x+12, pivot_y+12,
                           fill="#78634a", outline="#e5c38e", width=2)
        canvas.create_oval(stylus_x-5, stylus_y-5, stylus_x+5, stylus_y+5,
                           fill=self.color, outline="#fff2d8")


class DJView(ctk.CTk):
    """Ventana principal y capa de presentación MVC."""

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("JULIOPRODDJ  •  DJ MIXER")
        self.geometry("1500x940")
        self.minsize(1160, 760)
        self.configure(fg_color=BG)
        self.controller = None
        self.track_paths: list[str] = []
        self.folder_paths: list[str] = []
        self.selected_path: str | None = None
        self.mode_var = tk.StringVar(value="Consola")
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(100, self._tick)
        self.after(40, self._animate_vinyls)

    def set_controller(self, controller):
        self.controller = controller
        self.refresh_playlists(list(controller.library.playlists), next(iter(controller.library.playlists)))
        self.path_label.configure(text=f"BIBLIOTECA  •  {controller.library.directory}")

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(18, 10))
        ctk.CTkLabel(header, text="JULIOPRODDJ", text_color=CYAN,
                     font=ctk.CTkFont(size=27, weight="bold")).pack(side="left")
        ctk.CTkLabel(header, text="DUAL DECK  /  LIVE MIX ENGINE", text_color="#879db2",
                     font=ctk.CTkFont(family="Consolas", size=13)).pack(side="left", padx=18, pady=(7,0))
        ctk.CTkLabel(header, text="INTERFAZ", text_color="#879db2").pack(side="right", padx=(8, 4))
        self.mode_menu = ctk.CTkOptionMenu(header, variable=self.mode_var,
                                           values=["Consola", "Vinilos LP"], width=135,
                                           command=self._change_mode)
        self.mode_menu.pack(side="right", padx=(0, 10))
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=18, pady=8)
        body.grid_columnconfigure(0, weight=0, minsize=300)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        side = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=14, width=300)
        side.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        side.grid_propagate(False)
        ctk.CTkLabel(side, text="LIBRARY / PLAYLISTS", text_color=CYAN,
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=15, pady=(15,8))
        self.playlist_var = tk.StringVar(value="Mi música")
        self.playlist_menu = ctk.CTkOptionMenu(side, variable=self.playlist_var, values=["Mi música"],
                                                command=self._playlist_changed)
        self.playlist_menu.pack(fill="x", padx=14, pady=4)
        actions = ctk.CTkFrame(side, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=4)
        for text, fn in (("＋", self._create_playlist), ("✎", self._rename_playlist), ("−", self._delete_playlist)):
            ctk.CTkButton(actions, text=text, width=60, command=fn).pack(side="left", expand=True, padx=3)
        self.track_list = tk.Listbox(side, bg="#08111c", fg=TEXT, selectbackground="#0b7890",
                                     selectforeground="white", relief="flat", highlightthickness=1,
                                     highlightbackground="#20374b", font=("Segoe UI", 10), activestyle="none")
        self.track_list.pack(fill="both", expand=True, padx=14, pady=(8, 5))
        self.track_list.bind("<<ListboxSelect>>", self._select_track)
        ctk.CTkLabel(side, text="EXPLORADOR DE ARCHIVOS", text_color=CYAN,
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=15, pady=(6, 3))
        self.folder_label = ctk.CTkLabel(side, text="Elige una carpeta para explorar", text_color="#7f97ad",
                                         wraplength=270, anchor="w", font=ctk.CTkFont(size=10))
        self.folder_label.pack(fill="x", padx=15, pady=2)
        self.file_list = tk.Listbox(side, height=7, bg="#08111c", fg=TEXT, selectbackground="#0b7890",
                                    selectforeground="white", relief="flat", highlightthickness=1,
                                    highlightbackground="#20374b", font=("Segoe UI", 10), activestyle="none")
        self.file_list.pack(fill="x", padx=14, pady=5)
        self.file_list.bind("<Double-Button-1>", lambda _e: self._add_explorer_selection())
        load_row = ctk.CTkFrame(side, fg_color="transparent")
        load_row.pack(fill="x", padx=10, pady=(0,7))
        ctk.CTkButton(load_row, text="＋ Añadir audio", command=self._browse_audio).pack(fill="x", padx=4, pady=3)
        ctk.CTkButton(load_row, text="📁 Explorar carpeta", fg_color="#20344b",
                      command=self._browse_folder).pack(fill="x", padx=4, pady=3)
        ctk.CTkButton(load_row, text="Añadir selección del explorador", fg_color="#20344b",
                      command=self._add_explorer_selection).pack(fill="x", padx=4, pady=3)
        self.path_label = ctk.CTkLabel(side, text="", text_color="#7f97ad", wraplength=270,
                                       font=ctk.CTkFont(size=10))
        self.path_label.pack(fill="x", padx=14, pady=(2,10))

        mixer = ctk.CTkFrame(body, fg_color="transparent")
        mixer.grid(row=0, column=1, sticky="nsew")
        self._standard_mixer = mixer
        mixer.grid_columnconfigure((0, 1), weight=1, uniform="deck")
        mixer.grid_rowconfigure(0, weight=1)
        self.decks = {}
        for col, name, color in ((0, "A", CYAN), (1, "B", PINK)):
            panel = DeckPanel(mixer, name, color, self._transport, self._set_pitch, self._set_eq)
            panel.grid(row=0, column=col, sticky="nsew", padx=7, pady=4)
            self.decks[name] = panel
            ctk.CTkButton(panel, text=f"CARGAR SELECCIÓN → DECK {name}", fg_color="#1a3345",
                          command=lambda n=name: self._load_selected(n)).pack(fill="x", padx=18, pady=(0,14))

        self.vinyl_mixer = ctk.CTkFrame(body, fg_color="transparent")
        self.vinyl_mixer.grid(row=0, column=1, sticky="nsew")
        self.vinyl_mixer.grid_columnconfigure((0, 2), weight=5, uniform="vinyl_deck")
        self.vinyl_mixer.grid_columnconfigure(1, weight=1, minsize=170)
        self.vinyl_mixer.grid_rowconfigure(0, weight=1)
        self.vinyl_decks = {}
        for col, name, color in ((0, "A", CYAN), (2, "B", PINK)):
            panel = VinylDeckPanel(self.vinyl_mixer, name, color, self._transport,
                                   self._set_pitch, self._set_eq, self._load_selected)
            panel.grid(row=0, column=col, sticky="nsew", padx=7, pady=4)
            self.vinyl_decks[name] = panel
        self._build_vinyl_mixer()
        self.vinyl_mixer.grid_remove()

        bottom = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12)
        bottom.pack(fill="x", padx=25, pady=(0,8))
        ctk.CTkLabel(bottom, text="A", text_color=CYAN, width=30).pack(side="left", padx=(20,2))
        self.cross = ctk.CTkSlider(bottom, from_=0, to=1, progress_color=CYAN, button_color=TEXT,
                                   command=self._crossfade)
        self.cross.set(0.5)
        self.cross.pack(side="left", fill="x", expand=True, padx=12, pady=10)
        ctk.CTkLabel(bottom, text="CROSSFADER", text_color=TEXT,
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=8)
        ctk.CTkLabel(bottom, text="B", text_color=PINK, width=30).pack(side="left", padx=(2,15))
        self.master_slider = ctk.CTkSlider(bottom, from_=0, to=1, width=150, command=self._master)
        self.master_slider.set(.85)
        self.master_slider.pack(side="right", padx=(0,20), pady=10)
        ctk.CTkLabel(bottom, text="MASTER", text_color="#96a9b8").pack(side="right", padx=3)
        self.status_label = ctk.CTkLabel(self, text="Listo", text_color="#87a2b6", anchor="w")
        self.status_label.pack(fill="x", padx=27, pady=(0,10))

    def selected_playlist(self):
        return self.playlist_var.get()

    def refresh_playlists(self, names, selected):
        self.playlist_menu.configure(values=names or ["Mi música"])
        self.playlist_var.set(selected)
        if self.controller:
            self.refresh_tracks(self.controller.library.playlists.get(selected, []))

    def refresh_tracks(self, paths):
        self.track_paths = [item["path"] if isinstance(item, dict) else item for item in paths]
        self.track_list.delete(0, tk.END)
        for item, path in zip(paths, self.track_paths):
            title = item.get("title", Path(path).name) if isinstance(item, dict) else Path(path).name
            artist = item.get("artist", "") if isinstance(item, dict) else ""
            self.track_list.insert(tk.END, f"{title}  —  {artist}" if artist else title)
        self.selected_path = None

    def _playlist_changed(self, name):
        if self.controller:
            self.controller.playlist_changed(name)

    def _select_track(self, _event=None):
        picked = self.track_list.curselection()
        self.selected_path = self.track_paths[picked[0]] if picked else None
        if self.controller:
            self.controller.selected_track = self.selected_path

    def _browse_audio(self):
        files = filedialog.askopenfilenames(title="Añadir audio", filetypes=[("Audio", "*.mp3 *.wav")])
        if files:
            self.controller.add_tracks(list(files))

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Explorar carpeta de música")
        if not folder:
            return
        files = sorted(str(p) for p in Path(folder).iterdir() if p.is_file() and p.suffix.lower() in {".mp3", ".wav"})
        self.folder_paths = files
        self.folder_label.configure(text=folder)
        self.file_list.delete(0, tk.END)
        for path in files:
            self.file_list.insert(tk.END, Path(path).name)
        if not files:
            self.error("No se encontraron archivos MP3 o WAV en esa carpeta.")
        else:
            self.status(f"{len(files)} archivos disponibles en el explorador")

    def _add_explorer_selection(self):
        picked = self.file_list.curselection()
        if picked:
            self.controller.add_tracks([self.folder_paths[i] for i in picked])

    def _load_selected(self, deck):
        self.controller.load_deck(deck, self.selected_path)

    def _change_mode(self, mode):
        if mode == "Vinilos LP":
            self.decks_frame_show(False)
            self.vinyl_mixer.grid()
            for name, panel in self.vinyl_decks.items():
                model = self.controller.audio.decks[name]
                panel.pitch.set(model.pitch)
                for slider, gain in zip(panel.eq_sliders, model.gains):
                    slider.set(gain)
                self.level_sliders[name].set(model.level)
        else:
            self.vinyl_mixer.grid_remove()
            self.decks_frame_show(True)
            for name, panel in self.decks.items():
                model = self.controller.audio.decks[name]
                panel.pitch.set(model.pitch)
                for slider, gain in zip(panel.eq_sliders, model.gains):
                    slider.set(gain)

    def _build_vinyl_mixer(self):
        center = ctk.CTkFrame(self.vinyl_mixer, fg_color="#191511", corner_radius=15,
                              border_width=2, border_color="#8b6a43", width=170)
        center.grid(row=0, column=1, sticky="nsew", padx=3, pady=4)
        center.grid_propagate(False)
        ctk.CTkLabel(center, text="JULIOPRODDJ", text_color="#ffe0aa",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(15, 0))
        ctk.CTkLabel(center, text="DUAL CHANNEL MIXER", text_color="#9c8668",
                     font=ctk.CTkFont(family="Consolas", size=9)).pack(pady=(2, 8))
        self.mix_meter = tk.Canvas(center, height=38, bg="#080a0a", highlightthickness=1,
                                   highlightbackground="#51412e")
        self.mix_meter.pack(fill="x", padx=12, pady=5)
        levels = ctk.CTkFrame(center, fg_color="transparent")
        levels.pack(fill="both", expand=True, padx=8, pady=4)
        self.level_sliders = {}
        for name, color in (("A", CYAN), ("B", PINK)):
            channel = ctk.CTkFrame(levels, fg_color="#100f0e", corner_radius=9)
            channel.pack(side="left", expand=True, fill="both", padx=3)
            ctk.CTkLabel(channel, text=name, text_color=color,
                         font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(8, 0))
            slider = ctk.CTkSlider(channel, from_=0, to=1.2, orientation="vertical", height=155,
                                   progress_color=color, button_color=color,
                                   command=lambda value, deck=name: self._set_level(deck, value))
            slider.set(1.0)
            slider.pack(padx=9, pady=8, fill="y", expand=True)
            ctk.CTkLabel(channel, text="LEVEL", text_color="#9c927f",
                         font=ctk.CTkFont(size=9)).pack(pady=(0, 8))
            self.level_sliders[name] = slider
        ctk.CTkLabel(center, text="A  ◇  B", text_color="#d8c49f",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(3, 14))

    def decks_frame_show(self, show):
        if show:
            self._standard_mixer.grid()
        else:
            self._standard_mixer.grid_remove()

    def _transport(self, nombre, accion):
        if accion == "play":
            self.controller.start_audio()
            self.controller.audio.decks[nombre].playing = True
        elif accion == "pause":
            self.controller.audio.decks[nombre].playing = False
        else:
            modelo = self.controller.audio.decks[nombre]
            modelo.playing = False
            modelo.position = 0.0

    def _set_pitch(self, nombre, value):
        if self.controller:
            self.controller.audio.decks[nombre].pitch = float(value)

    def _set_eq(self, nombre, index, value):
        if self.controller:
            self.controller.audio.decks[nombre].gains[index] = float(value)

    def _set_level(self, nombre, value):
        if self.controller:
            self.controller.audio.decks[nombre].level = float(value)

    def _crossfade(self, value):
        if self.controller:
            self.controller.audio.crossfader = float(value)

    def _master(self, value):
        if self.controller:
            self.controller.audio.master = float(value)

    def _create_playlist(self):
        nombre = simpledialog.askstring("Nueva playlist", "Nombre de la playlist:", parent=self)
        if nombre:
            self.controller.create_playlist(nombre)

    def _rename_playlist(self):
        anterior = self.selected_playlist()
        nuevo = simpledialog.askstring("Renombrar playlist", "Nuevo nombre:", initialvalue=anterior, parent=self)
        if nuevo:
            self.controller.rename_playlist(nuevo)

    def _delete_playlist(self):
        if messagebox.askyesno("Eliminar playlist", f"¿Eliminar '{self.selected_playlist()}'?", parent=self):
            self.controller.delete_playlist()

    def deck_loaded(self, nombre, title, duration, audio):
        self.decks[nombre].set_track(title, duration, audio)
        self.vinyl_decks[nombre].set_track(title, duration)

    def status(self, text):
        self.status_label.configure(text=text)

    def error(self, text):
        self.status(text)
        messagebox.showerror("JULIOPRODDJ", text, parent=self)

    def _tick(self):
        if self.controller:
            self.controller.pump_jobs()
            for name, deck in self.controller.audio.decks.items():
                self.decks[name].update_clock(deck.elapsed, deck.duration)
                self.vinyl_decks[name].update_state(deck.elapsed, deck.duration, deck.playing)
        self.after(100, self._tick)

    def _animate_vinyls(self):
        for panel in self.vinyl_decks.values():
            panel.animate()
        self._draw_mix_meter()
        self.after(40, self._animate_vinyls)

    def _draw_mix_meter(self):
        if not self.controller:
            return
        canvas = self.mix_meter
        canvas.delete("all")
        width, height = max(100, canvas.winfo_width()), max(30, canvas.winfo_height())
        palette = ("#38d978", "#74ed65", "#c9e34d", "#ffaf45", "#f35d52")
        for channel_index, name in enumerate(("A", "B")):
            deck = self.controller.audio.decks[name]
            x0 = 8 + channel_index * (width / 2)
            canvas.create_text(x0, 8, text=name, fill=CYAN if name == "A" else PINK,
                               anchor="w", font=("Consolas", 8, "bold"))
            lit = min(5, int(deck.level * 5)) if deck.playing else 0
            for index in range(5):
                x = x0 + 19 + index * 13
                fill = palette[index] if index < lit else "#292b29"
                canvas.create_rectangle(x, 5, x + 9, height - 5, fill=fill, outline="")

    def _close(self):
        if self.controller:
            self.controller.close()
        self.destroy()
