# PyInstaller one-file builds

All specs assume you run **PyInstaller from the repository root** (parent of this folder), so imports like `theme_palette` resolve via `pathex`.

## Requirements

```bat
pip install pyinstaller
```

(Optional) your app dependencies from repo root: `pip install -r requirements.txt`

## Build

From repo root:

```bat
packaging\build_all.bat
```

Or individually:

```bat
pyinstaller --noconfirm packaging\gui.spec
pyinstaller --noconfirm packaging\flickercheck.spec
pyinstaller --noconfirm packaging\compare.spec
pyinstaller --noconfirm packaging\watcher.spec
```

Artifacts land in **`dist/`**: `gui.exe`, `flickercheck_ui.exe`, `compare.exe`, `watcher.exe`.

## Notes

- **Windowed** (`console=False`) for all four — no extra console window. For debugging, run `python gui.py` etc. from a terminal instead.
- **`gui.exe`** / **`flickercheck_ui.exe`**: `hiddenimports` includes **`theme_palette`** (shared light/dark colors).
- **`compare.exe`**: does not import `theme_palette`; still built from repo-root `pathex` so local modules are found if you add any later.
- Copy **`theme_palette.py` is not needed next to the exe** — it is bundled. You still need **`settings.ini`**, optional **`ffmpeg.exe`**, and **`DaVinciResolveScript`** path as before.
- UPX is left enabled in the spec; if packaging fails on your machine, set `upx=False` in the spec files.
