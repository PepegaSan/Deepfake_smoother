# Flickchecker — source tree

This folder is the **Python source** layout (no bundled `.exe` here unless you build them).

The repository landing page for GitHub is **[README.md](README.md)**.

## Contents

| Item | Purpose |
|------|---------|
| `compare.py`, `watcher.py`, `gui.py`, `flickercheck_ui.py` | Application sources (`flickercheck_ui.py` = visual threshold helper) |
| `Readme.txt` | User documentation (GUI, Watcher, Send To, settings) |
| `LICENSE` | GNU GPL v3.0 |
| `gui.spec` | PyInstaller reference |
| `settings.example.ini`, `watcher_settings.example.ini` | Config templates (no real paths) |
| `requirements.txt` | Python dependencies |
| `run_compare.cmd` | Launch `compare.py` from Explorer / cmd |

## Setup (Windows)

1. **Optional:** virtual environment in this folder  
   `py -3 -m venv .venv`  
   `.venv\Scripts\activate`

2. **Dependencies**  
   `pip install -r requirements.txt`

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
