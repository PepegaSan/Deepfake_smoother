=======================================================================
DEEPFAKE SWAP DETECTOR & AUTO-CUTTER
=======================================================================

This toolkit compares a source video with a deepfake video frame by frame.
It detects where the face swap was successful and where it failed (flicks/glitches).
It automatically generates DaVinci Resolve EDL files (AutoDelete & FullCheck
with Markers) and directly exports the corrected, cut videos using FFmpeg (NVENC).
It can also push the final edit and render job directly to DaVinci Resolve via API.

This toolkit runs out-of-the-box on Windows without needing a Python installation.

**Control Center:** If you use the GUI (`gui.exe` in a release build, or `python gui.py`
from source), you can edit all main options, start the Auto-Watcher, run Compare on two
picked files, open the Flickercheck UI, and edit `watcher_processed.txt` without using
Send To. The sections below still describe `settings.ini` / behaviour in full; the GUI
writes the same keys.

-----------------------------------------------------------------------
0. UI (SCREENSHOT)
-----------------------------------------------------------------------
The repository includes **UI.png** (Control Center, example dark theme). On GitHub the
same image is embedded in **README.md** under “UI”. The screenshot uses placeholder path
fields only — swap it for your own marketing shot if you publish paths.

-----------------------------------------------------------------------
1. FIRST RUN & CONFIGURATION (SETTINGS.INI)
-----------------------------------------------------------------------
You can adjust the tool's behavior without editing any code. Upon first launch,
the "compare.exe" generates a "settings.ini" file in the same folder.
Open it in any text editor to modify these variables: 


A. Language:
* language = en (Set to 'de' for German console and popup texts).


B. Adjusting the Buffer (Flick & No-Face Tolerance):
The script uses a time buffer to decide if a mismatch is just a quick glitch
(which should be cut) or a deliberate scene without a face (which should be kept).
* buffer_seconds = 2.0
  - Increase (e.g., 3.0): The script becomes STRICTER. A scene without a face must last longer (3 seconds) to be kept. Any identical scenes (flicks/errors) shorter than 3 seconds will be aggressively cut out.
  - Decrease (e.g., 0.5): The script becomes MORE FORGIVING. Even short moments
    without a face (or swap errors lasting longer than 0.5 seconds) will be kept
    in the final video.


C. Adjusting Pixel Sensitivity:
If the script fails to detect very subtle swaps or is too sensitive to video
compression noise, you can adjust the pixel difference threshold.
Recommendation: Use the Flickercheck UI (flickercheck_ui.exe in the release build,
or python flickercheck_ui.py from source) to visually determine the perfect values
for your specific footage before entering them here.
* pixel_noise_threshold = 15: This is the noise filter. Increase this if the
  script falsely detects swaps in identical frames due to heavy compression artifacts.
* changed_pixels_threshold = 200: This is the amount of changed pixels needed
  to trigger a "Swap OK" state. Decrease it (e.g., to 50) if the faces are very
  small in the video and the script doesn't detect the swap.


D. Toggling Exports (0 = Off, 1 = On):
You can choose what the script generates by changing the 0 (off) to 1 (on).
* enable_ffmpeg_export = 0 
  Set this to 1 if you want the script to automatically cut and render the final 
  MP4 files via FFmpeg. Leave it at 0 if you only want the EDL files for DaVinci 
  Resolve to save processing time.
* enable_autodelete_edl = 1: Generates standard .edl files to import the cuts
  manually into your editing software.
* enable_fullcheck_edl = 0: Set this to 1 if you also want the script to generate
  "FullCheck" EDLs (which include markers for both the kept and the cut sequences).
* enable_davinci_export = 0: Enables direct API integration to build the timeline
  and render in DaVinci Resolve.


F. FFmpeg Encoder Settings (Hardware Acceleration)

You can customize the video encoder used for FFmpeg exports to significantly speed up processing and reduce file sizes. This is controlled via the `settings.ini` file located in the program directory.

Open `settings.ini` and locate the `[SETTINGS]` section. Change the value for `ffmpeg_encoder =` to one of the following options:

**NVIDIA GPUs:**
* `nvidia_h264` (Default) - Fast processing, high compatibility with all media players.
* `nvidia_hevc` - H.265 codec. Produces smaller files with the same visual quality.
* `nvidia_av1` - The most modern and efficient codec. Extremely small file sizes at high quality. (Highly recommended for RTX 40-series GPUs, e.g., RTX 4090).

**AMD GPUs:**
* `amd_h264` - Standard hardware acceleration for AMD cards.
* `amd_hevc` - H.265 codec for AMD cards (smaller file sizes).

**Fallback (No dedicated GPU):**
* `cpu` - Uses the processor (libx264). High compatibility but significantly slower processing times. 

*Example configuration for maximum efficiency on a modern NVIDIA GPU:*
```ini
[SETTINGS]
enable_ffmpeg_export = 1
ffmpeg_encoder = nvidia_av1
```

**Which video(s) to render** (only when enable_ffmpeg_export = 1):

* ffmpeg_export_target = both — Default. Renders both the source (original) and the deepfake
  as *_AutoCut.mp4 with the same cuts.
* ffmpeg_export_target = source — Only the original/source clip is encoded.
* ffmpeg_export_target = deepfake — Only the deepfake clip is encoded.

Invalid or missing values behave like "both".

* export_avoid_overwrite = 0 (optional, 1 = on): When enabled, FFmpeg and DaVinci do not
  overwrite an existing output file with the same base name. Outputs get a suffix built
  from the compare filter (buffer / noise / pixel), then _2 … _20 if the name is still
  taken. Configure from the Control Center **Export** tab (“Video export files”) or edit
  `settings.ini` directly. Watcher runs use the same setting; generated names still contain
  `_AutoCut` / `_DaVinci_Export` so the watcher ignores them as outputs.

G. Custom Export Folder

By default, all generated files (AutoCut videos, EDLs, DaVinci exports) are saved in the same directory as the source video. If you prefer to collect all exported files in a single, specific location, you can define a custom path in the `settings.ini`.

Open `settings.ini` and locate the `[PATHS]` section. Enter your desired folder path next to `final_export_dir =`.

*Example:*
```ini
[PATHS]
final_export_dir = D:\Video_Exports\AutoCut_Results
```

-----------------------------------------------------------------------
2. DAVINCI RESOLVE API SETUP (IMPORTANT!)
-----------------------------------------------------------------------
If you want to use the automatic DaVinci Resolve timeline creation and rendering
(enable_davinci_export = 1), please read carefully:

* Studio Version Required:
  The external scripting API is exclusively available in DaVinci Resolve Studio
  (the paid version). If your main editor is the DaVinci Resolve Free Version,
  the API connection will be blocked. Users of the Free Version must set
  enable_davinci_export = 0 and use the EDL or FFmpeg export methods instead.

* Creating the "AutoCutPreset":
  Because the DaVinci API overrides bitrate settings when using hardware encoders,
  you must create a specific render preset inside DaVinci Resolve once:
  1. Open DaVinci Resolve Studio and go to the "Deliver" page.
  2. Set your desired export settings (e.g., Format: MP4, Codec: H.265,
     Encoder: NVIDIA, Quality: Restrict to 8000 Kb/s).
  3. Click the three dots top right of the preset list and select
     "Save as New Preset..."
  4. Name it EXACTLY: AutoCutPreset
  5. Click OK. The script will now load this preset automatically for every export.

* API Path:
  If DaVinci Resolve is not installed on your default C: drive, update the
  davinci_api_path inside the [PATHS] section of the settings.ini to match your
  installation directory.

* Render wait limit (inside compare.exe, after Deliver starts):
  In the [SETTINGS] section, `davinci_render_timeout_seconds` controls how long the
  script keeps waiting for DaVinci Resolve to finish the export after the render job
  has started (default: 1800 = 30 minutes). If the export takes longer, compare.exe
  tells Resolve to stop rendering and exits with an error. Set the value to `0` to
  wait without a time limit until the job completes.
  This is separate from the Auto-Watcher's `compare_timeout_seconds` in
  watcher_settings.ini, which limits the entire compare.exe process (analysis,
  FFmpeg, and DaVinci together) when you use watcher.exe.

-----------------------------------------------------------------------
3. CONTROL CENTER (GUI)
-----------------------------------------------------------------------
The **Control Center** (`gui.py` / `gui.exe`) is the usual way to work from source:

* **Watcher & Paths** – Original folder, deepfake (watched) folder, optional export folder;
  language for watcher console; same values as `watcher_settings.ini`.
* **Export** – DaVinci Resolve (API path, timeouts), then **Video export files** (optional
  no-overwrite naming for FFmpeg + DaVinci), EDL toggles, FFmpeg codec and target clips
  (all stored in `settings.ini`).
* **Filter & Ignore** – RegEx / suffix ignores for the watcher, buffer and pixel thresholds.
* **Tools** – Pick two videos and run Compare; launch Flickercheck UI for tuning.
* **Processed Log** – Edit `watcher_processed.txt` for the current deepfake folder safely.

**Appearance:** Light or Dark mode (options / theme control in the GUI) is saved as
`[GUI] ui_theme = light` or `dark` in `settings.ini`. The **Flickercheck** window
(`flickercheck_ui.py`) reads the same key on startup so it matches the Control Center.

Use **Save Settings** at the bottom to write `settings.ini` and `watcher_settings.ini`.

Source tree also includes **theme_palette.py** (shared palette + theme loader for
`gui.py` and `flickercheck_ui.py`).

-----------------------------------------------------------------------
4. AUTO-WATCHER (watcher.py / watcher.exe)
-----------------------------------------------------------------------
The **Watcher** watches **deepfake_dir** for new finished videos, matches each file to an
**original** in **source_dir** (by configurable prefix / RegEx rules), waits until the file
is stable, then runs **compare** with `--auto`. Processed filenames are appended to
**watcher_processed.txt** in the deepfake folder so the same file is not processed in a loop.

**Naming:** Originals must differ within the first **match_prefix_length** characters of the
filename (default 10), because many deepfake tools only embed a short prefix of the source
name in the output. Example: `01_Scene.mp4` vs `02_Scene.mp4` is good; two files both
starting with `Movie_...` can be ambiguous.

**Retry a file:** Remove its exact line from `watcher_processed.txt` and save; the Watcher
will treat it as new on the next scan.

**watcher_settings.ini** (same folder as watcher; GUI writes it from **Watcher & Paths**):

* **[PATHS]** `source_dir`, `deepfake_dir`, `resolve_exe_path` (Resolve.exe – used to **start**
  Resolve if Compare has DaVinci export enabled and Resolve is not running).
* **[SETTINGS]** `language` (en/de), `wait_seconds` (file stability), `compare_timeout_seconds`
  (max duration for **one** Compare subprocess; `0` = no limit), `afk_mode` (if Compare fails:
  `1` = still log as processed to avoid endless retries when unattended; `0` = retry later).
* **[MATCHING]** `ignore_temp_pattern` (RegEx for temp filenames), `match_prefix_length`,
  `ignore_suffix`.

**Timeouts:** `compare_timeout_seconds` (Watcher) caps the **whole** Compare run. Separately,
`davinci_render_timeout_seconds` in **settings.ini** caps only the DaVinci Deliver phase after
render has started (`0` = wait indefinitely). See section 2 above.

**Flickercheck:** The Watcher does not open Flickercheck. Use the GUI **Tools** tab or
run `flickercheck_ui.py` yourself; **Apply thresholds → settings.ini** updates Compare’s pixel
settings.

-----------------------------------------------------------------------
5. SETUP & USAGE (WINDOWS SEND TO)
-----------------------------------------------------------------------
1. Run "Install_SendTo.bat" once to add the tool
   to your Windows "Send to" menu.
2. Select your files using one of the following methods:
   - Method A (Different Folders): Right-click the first video -> Send to ->
     Deepfake AutoCut. A popup will confirm the file is cached. Then go to your
     other folder, right-click the second video -> Send to -> Deepfake AutoCut.
   - Method B (Same Folder): Highlight both videos simultaneously, right-click ->
     Send to -> Deepfake AutoCut.
3. The tool will open a prompt asking you to confirm which of the two files
   is the original source video.
4. The analysis will run, and the outputs will be saved automatically based on
   your settings.ini preferences.

(Alternatively, simply double-click "compare.exe" to select the files via a
graphical menu, or use the Control Center **Tools** tab.)


### Troubleshooting / Common Issues

**1. Watcher processes the same file in an endless loop**
* **Problem:** The tool repeatedly recognizes a finished file as "new" and renders it multiple times. In the log file, the file names are written right next to each other without line breaks.
* **Solution:** Close the tool. Delete the `watcher_processed.txt` file located in your deepfake folder. It was likely corrupted during a previous crash or interruption. Upon the next restart, the script will automatically create a clean, new file.

**2. FFmpeg export aborts immediately or fails**
* **Problem:** An FFmpeg error message appears in the console, and the video is not exported.
* **Solution:** The configured hardware encoder in the `settings.ini` does not match your graphics card. Open the file and check the value at `ffmpeg_encoder =`. Change it to `cpu` for a quick test (this works on any system), or select the exact codec designed for your hardware (e.g., `nvidia_h264` for NVIDIA or `amd_h264` for AMD).

**3. DaVinci Resolve API Error ("DaVinciResolveScript not found")**
* **Problem:** The script aborts with a message stating that the API is missing or no connection could be established.
* **Solution:** 1. DaVinci Resolve **must** be fully launched with a project open before the script is triggered.
  2. Check the `settings.ini` to ensure the path at `davinci_api_path =` is correct for your specific system installation.

**4. The program does not start or crashes instantly**
* **Problem:** The console window flashes briefly and closes immediately, or the script behaves erratically after an update.
* **Solution:** This is frequently caused by outdated, missing, or manually misformatted configuration files. Delete `settings.ini` (and `watcher_settings.ini` if present). Restart the tool afterwards. The files will be completely regenerated with clean default values.

**5. "Unknown" or "Abgeschlossen" error at the end of the DaVinci render**
* **Problem:** The render job in DaVinci finishes successfully, but the Python script throws an error regarding the "Render Status" right at the end.
* **Solution:** This issue generally only occurs with older versions of the script combined with a non-English DaVinci user interface (e.g., German). Ensure you are using the latest version of the `compare.exe`. Alternatively, change the UI language in DaVinci Resolve to English.

Good Luck Have Fun 

-----------------------------------------------------------------------
LICENSE (SOURCE / GITHUB)
-----------------------------------------------------------------------
Copyright (C) 2026 the Flickchecker contributors.

The source code is licensed under the GNU General Public License v3.0.
See the file LICENSE for the full text (https://www.gnu.org/licenses/gpl-3.0).

GitHub shows README.md on the project front page (including the **UI** screenshot).
Full user details stay in this file; developers building from source: see DEV_README.md.
