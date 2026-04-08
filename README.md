# Flickchecker

**Deepfake swap detector & auto-cutter** for Windows. Compares a source video with a deepfake frame by frame, finds where the swap holds vs. glitches, and can output **DaVinci Resolve EDLs** (with markers), **FFmpeg** cuts (e.g. NVENC), and optionally drive **DaVinci Resolve Studio** via its scripting API.

Includes a **Control Center** GUI (`gui.py` / `gui.exe`), an **Auto-Watcher** for hands-off folders, and a **Flickercheck** UI to tune pixel thresholds visually.

Pre-built releases can run **without installing Python**; this repository is the **source** tree.

## Documentation

| File | Audience |
|------|----------|
| **[Readme.txt](Readme.txt)** | Full user guide: `settings.ini`, DaVinci setup, Watcher, Send To, troubleshooting |
| **[DEV_README.md](DEV_README.md)** | Developers: venv, `pip install`, running from source |

## Quick start (source)

```bat
pip install -r requirements.txt
copy settings.example.ini settings.ini
copy watcher_settings.example.ini watcher_settings.ini
python gui.py
```

Edit the `.ini` files (or use the GUI **Save Settings**) before processing real jobs.

## Requirements

- Windows (primary target)
- Python 3.x + dependencies in `requirements.txt` when running from source
- Optional: **DaVinci Resolve Studio** for API export; **FFmpeg** / **ffmpeg.exe** for encodes

## License

[GNU General Public License v3.0](LICENSE) — see [LICENSE](LICENSE) for the full text.

Copyright © 2026 the Flickchecker contributors.
