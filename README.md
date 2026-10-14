# JULIOPRODDJ

Reproductor y mezclador de escritorio de dos decks, escrito en Python siguiendo MVC. La biblioteca y el archivo `playlists.json` se guardan en `playlists/`, junto al programa.

## Requisitos

- Python 3.10 o superior
- Un dispositivo de salida de audio reconocido por PortAudio

## Instalación y ejecución

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

En Linux/macOS, crea/activa el entorno virtual con los comandos habituales y ejecuta `python main.py`.

## Paquete para Windows

Los entregables compilados están en `output/`:

- `JULIOPRODDJ-Setup.exe`: instalador por usuario. Se ejecuta en otro PC y crea acceso directo; no requiere Python.
- `JULIOPRODDJ-Portable.zip`: extrae la carpeta `JULIOPRODDJ` en un USB o disco y abre `JULIOPRODDJ.exe` desde ahí; tampoco requiere Python.

Para reconstruirlos en Windows, con las dependencias instaladas, ejecuta `.\build_windows.ps1`. La carpeta `playlists/` se crea junto al ejecutable. Las canciones no se incluyen en estos paquetes y habrá que seleccionarlas desde su ubicación en cada PC.

## Interfaces y datos locales

La cabecera permite elegir entre la consola con waveform y la vista alternativa de dos platos LP animados. Ambas vistas controlan los mismos Deck A/B y la misma salida de audio.

Las playlists y sus metadatos se guardan localmente en `playlists/playlists.json`, dentro de la carpeta del programa; no se utiliza almacenamiento en linea. El archivo conserva rutas locales a las canciones, por lo que mover la aplicacion a otro PC no mueve los audios.

## Controles

- Cargar pistas con **Añadir audio** o elegir una carpeta en el explorador integrado y añadir las canciones seleccionadas.
- Seleccionar una pista de la playlist y usar **Cargar A/B**. Los controles de transporte y EQ son independientes.
- Pitch: 0% es velocidad normal; rango ±12%. Crossfader: izquierda prioriza A, derecha prioriza B.
- Play mezcla ambos decks en tiempo real. Stop vuelve al inicio.

Se admiten WAV y MP3. La salida se mezcla en estéreo a 44.1 kHz. La pista se decodifica en memoria antes de pasar al callback de audio. Para colecciones grandes, carga únicamente las pistas que vas a pinchar: cada pista decodificada ocupa memoria RAM.

## Estructura

```text
reproductor/
├── main.py                 # Arranque
├── requirements.txt
├── README.md
└── djapp/
    ├── __init__.py
    ├── audio_engine.py     # Modelo/motor de audio en tiempo real
    ├── controller.py       # Coordinación MVC y operaciones asíncronas
    ├── library.py          # Modelo de biblioteca y playlists persistentes
    └── view.py             # Vista CustomTkinter
```

El motor usa un único stream PortAudio y mezcla los dos decks en el callback, evitando iniciar hilos de salida competidores. La lectura/decodificación de archivos y persistencia se ejecutan en un executor de fondo; la vista se actualiza en el hilo de Tk.
