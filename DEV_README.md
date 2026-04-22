# Flickchecker — source tree

This folder is the **Python source** layout (no bundled `.exe` here unless you build them).

The repository landing page for GitHub is **[README.md](README.md)**.

## Contents

| Item | Purpose |
|------|---------|
| `compare.py`, `watcher.py`, `gui.py`, `flickercheck_ui.py` | Application sources (`flickercheck_ui.py` = visual threshold helper) |
| `theme_palette.py` | Shared `PALETTE_LIGHT` / `PALETTE_DARK` and `load_ui_theme_is_light()` for GUI + Flickercheck |
| `UI.png` | Screenshot for docs (README “UI” section); replace with your own if paths must stay private |
| `Readme.txt` | User documentation (GUI, Watcher, Send To, settings) |
| `LICENSE` | GNU GPL v3.0 |
| `packaging/*.spec`, `packaging/build_all.bat` | PyInstaller **one-file** specs (windowed); run from repo root — see [packaging/README.md](packaging/README.md) |
| `settings.example.ini`, `watcher_settings.example.ini` | Config templates (no real paths) |
| `requirements.txt` | Runtime Python dependencies (incl. **customtkinter**, **tkinterdnd2** for GUI Tools DnD, OpenCV / NumPy / Pillow) |
| `packaging/requirements-build.txt` | **PyInstaller** only — for `packaging/build_all.bat` |
| `run_compare.cmd` | Launch `compare.py` from Explorer / cmd |

## Setup (Windows)

1. **Optional:** virtual environment in this folder  
   `py -3 -m venv .venv`  
   `.venv\Scripts\activate`

2. **Dependencies**  
   `pip install -r requirements.txt`  
   (Python **3.10+** recommended on Windows for prebuilt wheels.)

3. **Config (once)**  
   `copy settings.example.ini settings.ini`  
   `copy watcher_settings.example.ini watcher_settings.ini`  
   Edit paths/options in those files, or use the **Control Center** GUI.

## Running

- **`python gui.py`** — Control Center: settings, Watcher, manual Compare, processed log. Uses `watcher.exe` / `compare.exe` if present next to the scripts; otherwise `python watcher.py` / `python compare.py`.

- **`python compare.py`** or **`run_compare.cmd`** — Same CLI as `compare.exe` (e.g. Send To pointing at the script).

- **`python watcher.py`** — Watches the deepfake folder; runs `compare.exe` or `python compare.py` from the same directory.

## Notes

`compare.py` looks for `ffmpeg.exe` next to the script; for development, `ffmpeg` on `PATH` is enough.

The **`packaging/gui.spec`** and **`packaging/flickercheck.spec`** files already list `hiddenimports=['theme_palette']` for one-file `gui.exe` / `flickercheck_ui.exe`.
