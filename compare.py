import cv2
import sys
import os
import time
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import configparser
import re
import datetime

TEXTS = {
    'en': {
        'first_run_title': "First Run / Erster Start",
        'first_run_msg': "The file 'settings.ini' was created in the program folder.\n\nPlease open this file, adjust the language (en/de), export settings, and API path if needed, then restart the script.\n\n---\n\nDie Datei 'settings.ini' wurde im Programmordner neu erstellt.\n\nBitte öffne diese Datei, passe bei Bedarf die Sprache (en/de), Exporteinstellungen sowie den Pfad zur API an und starte das Skript danach erneut.",
        'file_dialog_source': "1. Select ORIGINAL Video (Source)",
        'file_dialog_df': "2. Select DEEPFAKE Video",
        'confirm_source_title': "Clarify File Assignment",
        'confirm_source_msg': "Is the following file the ORIGINAL video (Source)?\n\n{name}",
        'abort_double_file_title': "Abort",
        'abort_double_file_msg': "The same file was sent twice. Operation aborted.",
        'cache_step1_title': "Step 1",
        'cache_step1_msg': "File cached for AutoCut:\n{name}\n\nPlease right-click the second file -> Send to -> Deepfake AutoCut.",
        'no_files_sendto': "No files passed via Send To. Starting manual file selection...",
        'abort_not_both': "Abort: Not both videos were selected.",
        'press_enter': "\nPress Enter to exit...",
        'unexpected_error': "\nAn unexpected error occurred: {error}",
        'loading_settings': "Loading settings from settings.ini:",
        'set_buffer': "- Buffer: {val} seconds",
        'set_noise': "- Noise Filter: {val}",
        'set_pixel': "- Pixel Tolerance: {val}",
        'set_davinci': "- DaVinci API Export: {val}",
        'set_davinci_timeout': "- DaVinci render time limit: {val}",
        'davinci_timeout_off': "none (wait until DaVinci finishes)",
        'set_ffmpeg': "- FFmpeg Export: {val}",
        'set_ffmpeg_target': "- FFmpeg renders: {val}",
        'ffmpeg_target_both': "source and deepfake",
        'ffmpeg_target_source': "source only",
        'ffmpeg_target_deepfake': "deepfake only",
        'set_fullcheck': "- FullCheck EDL: {val}",
        'on': "On",
        'off': "Off",
        'start_analysis': "\nStarting pixel difference analysis for {frames} frames...",
        'analyzing': "\rAnalyzing: {percent:.1f}% ({current}/{total} frames)",
        'frames_processed': "\n{count} frames processed. Applying filters...",
        'no_diff': "No difference found between the videos.",
        'edl_auto_created': "\nAutoDelete EDL files created:",
        'edl_full_created': "\nFullCheck EDL files created.",
        'all_done': "\nAll operations completed.",
        'manual_res_title': "Manual Resolution Input",
        'manual_res_prompt': "Could not read video resolution.\nPlease enter the resolution manually (e.g., 1920x1080):",
        'manual_res_invalid': "[Info] Invalid input or canceled. Falling back to 1920x1080.",
        'ffmpeg_render': "Rendering {name} via FFmpeg ({codec})...",
        'ffmpeg_progress': "\rProgress: {percent:.1f}% ({frame}/{total} frames)",
        'ffmpeg_error': "\n\n--- FFmpeg Error for {name} ---",
        'ffmpeg_success': "\n-> Successfully created.",
        'davinci_api_missing': "\n[ERROR] DaVinci API (DaVinciResolveScript) not found!",
        'davinci_api_path_searched': "Python explicitly searched in this folder:\n{path}",
        'davinci_api_check_explorer': "Please check in Windows Explorer if this folder and the file 'DaVinciResolveScript.py' actually exist there.",
        'davinci_not_open': "\n[ERROR] DaVinci Resolve Studio must be open before starting this script!",
        'davinci_fallback_skip': "\n[WARN] DaVinci Resolve is not running or the scripting API is unavailable.\nPixel analysis, EDL, and FFmpeg (if enabled) will still run; DaVinci export is skipped.\n",
        'davinci_edl_fallback': "\n[INFO] DaVinci export did not complete; wrote AutoDelete EDL files as fallback (no EDL options were enabled).\n",
        'davinci_export_exception': "\n[WARN] DaVinci export failed: {error}\nWriting AutoDelete EDL as fallback (no EDL options were enabled).\n",
        'davinci_no_project': "\n[ERROR] No open project found in DaVinci Resolve.",
        'davinci_sending_data': "\nSending data via API to DaVinci Resolve Studio...",
        'davinci_import_error': "[ERROR] Could not import {path} into Resolve.",
        'davinci_timeline_error': "[ERROR] Could not create a timeline.",
        'davinci_no_valid_scenes': "No valid scenes found to render.",
        'davinci_preset_warning': "\n[WARNING] Could not find render preset 'AutoCutPreset' in DaVinci!",
        'davinci_preset_fallback': "Rendering will proceed using the last settings used in DaVinci.",
        'davinci_job_created': "Render job for '{name}' created.",
        'davinci_start_render': "Starting hardware rendering in DaVinci Resolve...",
        'davinci_render_running': "-> Rendering in progress! (Progress is now displayed over in the DaVinci Resolve GUI)",
        'davinci_meta_no_resolution': "No resolution in clip metadata.",
        'davinci_meta_parse_error': "[Info] Could not read clip metadata completely: {error}",
        'davinci_render_timeout_exceeded': "DaVinci render exceeded {sec} seconds; export was stopped.",
        'davinci_render_status_failed': "DaVinci render job finished with status: {status}",
        'fps_fallback': "[Info] Could not read a valid FPS from the source video; using 30.",
    },
    'de': {
        'first_run_title': "Erster Start / First Run",
        'first_run_msg': "Die Datei 'settings.ini' wurde im Programmordner neu erstellt.\n\nBitte öffne diese Datei, passe bei Bedarf die Sprache (en/de), Exporteinstellungen sowie den Pfad zur API an und starte das Skript danach erneut.\n\n---\n\nThe file 'settings.ini' was created in the program folder.\n\nPlease open this file, adjust the language (en/de), export settings, and API path if needed, then restart the script.",
        'file_dialog_source': "1. ORIGINAL-Video auswählen (Source)",
        'file_dialog_df': "2. DEEPFAKE-Video auswählen",
        'confirm_source_title': "Dateizuordnung klären",
        'confirm_source_msg': "Ist folgende Datei das ORIGINAL-Video (Source)?\n\n{name}",
        'abort_double_file_title': "Abbruch",
        'abort_double_file_msg': "Die gleiche Datei wurde zweimal gesendet. Vorgang abgebrochen.",
        'cache_step1_title': "Schritt 1",
        'cache_step1_msg': "Datei für AutoCut gemerkt:\n{name}\n\nBitte klicke nun auf die zweite Datei -> Senden an -> Deepfake AutoCut.",
        'no_files_sendto': "Keine Dateien über Senden an übergeben. Starte manuelle Dateiauswahl...",
        'abort_not_both': "Abbruch: Es wurden nicht beide Videos ausgewählt.",
        'press_enter': "\nDrücke Enter zum Beenden...",
        'unexpected_error': "\nEin unerwarteter Fehler ist aufgetreten: {error}",
        'loading_settings': "Lade Einstellungen aus settings.ini:",
        'set_buffer': "- Puffer: {val} Sekunden",
        'set_noise': "- Rausch-Filter: {val}",
        'set_pixel': "- Pixel-Toleranz: {val}",
        'set_davinci': "- DaVinci API Export: {val}",
        'set_davinci_timeout': "- DaVinci Render-Zeitlimit: {val}",
        'davinci_timeout_off': "keins (warten bis DaVinci fertig ist)",
        'set_ffmpeg': "- FFmpeg Export: {val}",
        'set_ffmpeg_target': "- FFmpeg rendert: {val}",
        'ffmpeg_target_both': "Original und Deepfake",
        'ffmpeg_target_source': "nur Original",
        'ffmpeg_target_deepfake': "nur Deepfake",
        'set_fullcheck': "- FullCheck EDL: {val}",
        'on': "An",
        'off': "Aus",
        'start_analysis': "\nStarte Pixel-Differenz-Analyse für {frames} Frames...",
        'analyzing': "\rAnalysiere: {percent:.1f}% ({current}/{total} Frames)",
        'frames_processed': "\n{count} Frames verarbeitet. Wende Filter an...",
        'no_diff': "Kein Unterschied zwischen den Videos gefunden.",
        'edl_auto_created': "\nAutoDelete EDL Dateien erstellt:",
        'edl_full_created': "\nFullCheck EDL Dateien erstellt.",
        'all_done': "\nAlle Vorgänge abgeschlossen.",
        'ffmpeg_render': "Rendere {name} über FFmpeg ({codec})...",
        'ffmpeg_progress': "\rFortschritt: {percent:.1f}% ({frame}/{total} Frames)",
        'ffmpeg_error': "\n\n--- FFmpeg Fehler bei {name} ---",
        'ffmpeg_success': "\n-> Erfolgreich erstellt.",
        'manual_res_title': "Manuelle Auflösungseingabe",
        'manual_res_prompt': "Video-Auflösung konnte nicht ausgelesen werden.\nBitte manuell eingeben (z.B. 1920x1080):",
        'manual_res_invalid': "[Info] Ungültige Eingabe oder abgebrochen. Fallback auf 1920x1080.",
        'davinci_api_missing': "\n[FEHLER] DaVinci API (DaVinciResolveScript) nicht gefunden!",
        'davinci_api_path_searched': "Python hat explizit in diesem Ordner gesucht:\n{path}",
        'davinci_api_check_explorer': "Bitte prüfe im Windows Explorer, ob dieser Ordner und die Datei 'DaVinciResolveScript.py' dort wirklich existieren.",
        'davinci_not_open': "\n[FEHLER] DaVinci Resolve Studio muss geöffnet sein, bevor dieses Skript startet!",
        'davinci_fallback_skip': "\n[WARN] DaVinci Resolve laeuft nicht oder die Scripting-API ist nicht verfuegbar.\nPixel-Analyse, EDL und FFmpeg (falls aktiv) laufen trotzdem; DaVinci-Export wird uebersprungen.\n",
        'davinci_edl_fallback': "\n[INFO] DaVinci-Export nicht erfolgreich; AutoDelete-EDL als Fallback geschrieben (EDL-Optionen waren aus).\n",
        'davinci_export_exception': "\n[WARN] DaVinci-Export fehlgeschlagen: {error}\nAutoDelete-EDL als Fallback (EDL-Optionen waren aus).\n",
        'davinci_no_project': "\n[FEHLER] Kein offenes Projekt in DaVinci Resolve gefunden.",
        'davinci_sending_data': "\nSende Daten über API an DaVinci Resolve Studio...",
        'davinci_import_error': "[FEHLER] Konnte {path} nicht in Resolve importieren.",
        'davinci_timeline_error': "[FEHLER] Konnte keine Timeline erstellen.",
        'davinci_no_valid_scenes': "Keine validen Szenen zum Rendern gefunden.",
        'davinci_preset_warning': "\n[WARNUNG] Konnte Render-Preset 'AutoCutPreset' in DaVinci nicht finden!",
        'davinci_preset_fallback': "Es wird mit den zuletzt in DaVinci genutzten Einstellungen gerendert.",
        'davinci_job_created': "Render-Job für '{name}' erstellt.",
        'davinci_start_render': "Starte Hardware-Rendering in DaVinci Resolve...",
        'davinci_render_running': "-> Rendering läuft! (Der Fortschritt wird dir jetzt drüben in der DaVinci Resolve GUI angezeigt)",
        'davinci_meta_no_resolution': "Keine Auflösung in den Clip-Metadaten.",
        'davinci_meta_parse_error': "[Info] Clip-Metadaten nicht vollständig lesbar: {error}",
        'davinci_render_timeout_exceeded': "DaVinci-Rendering länger als {sec} Sekunden; Export wurde gestoppt.",
        'davinci_render_status_failed': "DaVinci-Render abgeschlossen mit Status: {status}",
        'fps_fallback': "[Info] Keine gültige FPS aus dem Quellvideo lesbar; verwende 30.",
    }
}

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def parse_ffmpeg_export_target(raw):
    v = (raw or "both").strip().lower()
    if v in ("both", "source", "deepfake"):
        return v
    return "both"

def load_config():
    base_dir = get_base_dir()
    config_path = os.path.join(base_dir, 'settings.ini')
    config = configparser.ConfigParser()
    
    if not os.path.exists(config_path):
        config['SETTINGS'] = {
            'language': 'en',
            'buffer_seconds': '2.0',
            'pixel_noise_threshold': '15',
            'changed_pixels_threshold': '200',
            'enable_ffmpeg_export': '0',
            'ffmpeg_export_target': 'both',
            'ffmpeg_encoder': 'nvidia_h264',
            'enable_fullcheck_edl': '0',
            'enable_autodelete_edl': '1',
            'enable_davinci_export': '0',
            'davinci_render_timeout_seconds': '1800'
        }
        config['PATHS'] = {
            'davinci_api_path': r'C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules',
            'final_export_dir': ''
        }
        with open(config_path, 'w') as configfile:
            config.write(configfile)
            
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        messagebox.showinfo("First Run / Erster Start", TEXTS['en']['first_run_msg'])
        root.destroy()
        sys.exit(0)
            
    config.read(config_path)

    if not config.has_section('SETTINGS'):
        config.add_section('SETTINGS')
    
    if not config.has_section('PATHS'):
        config.add_section('PATHS')
        
    return {
        'language': config.get('SETTINGS', 'language', fallback='en').lower(),
        'buffer_seconds': config.getfloat('SETTINGS', 'buffer_seconds', fallback=2.0),
        'pixel_noise_threshold': config.getint('SETTINGS', 'pixel_noise_threshold', fallback=15),
        'changed_pixels_threshold': config.getint('SETTINGS', 'changed_pixels_threshold', fallback=200),
        'enable_ffmpeg_export': config.getboolean('SETTINGS', 'enable_ffmpeg_export', fallback=False),
        'ffmpeg_export_target': parse_ffmpeg_export_target(
            config.get('SETTINGS', 'ffmpeg_export_target', fallback='both')
        ),
        'ffmpeg_encoder': config.get('SETTINGS', 'ffmpeg_encoder', fallback='nvidia_h264').lower(),
        'enable_fullcheck_edl': config.getboolean('SETTINGS', 'enable_fullcheck_edl', fallback=False),
        'enable_autodelete_edl': config.getboolean('SETTINGS', 'enable_autodelete_edl', fallback=True),
        'enable_davinci_export': config.getboolean('SETTINGS', 'enable_davinci_export', fallback=False),
        'davinci_render_timeout_seconds': max(
            0,
            config.getint('SETTINGS', 'davinci_render_timeout_seconds', fallback=1800)
        ),
        'davinci_api_path': config.get('PATHS', 'davinci_api_path', fallback=r'C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules'),
        'final_export_dir': config.get('PATHS', 'final_export_dir', fallback='')
    }


def write_settings_pixel_thresholds(base_dir, pixel_noise_threshold=None, changed_pixels_threshold=None):
    """Update only pixel thresholds in settings.ini; other keys unchanged."""
    config_path = os.path.join(base_dir, 'settings.ini')
    if not os.path.exists(config_path):
        return False
    config = configparser.ConfigParser()
    config.read(config_path)
    if not config.has_section('SETTINGS'):
        return False
    if pixel_noise_threshold is not None:
        config.set('SETTINGS', 'pixel_noise_threshold', str(int(pixel_noise_threshold)))
    if changed_pixels_threshold is not None:
        config.set('SETTINGS', 'changed_pixels_threshold', str(int(changed_pixels_threshold)))
    with open(config_path, 'w', encoding='utf-8') as f:
        config.write(f)
    return True


def frame_to_tc(frame, fps_int):
    h = int(frame / (fps_int * 3600))
    m = int((frame / (fps_int * 60)) % 60)
    s = int((frame / fps_int) % 60)
    f = int(frame % fps_int)
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"

def get_segment_style(is_good):
    if is_good:
        return {
            "clip_name": "SWAP_OK",
            "clip_color": "Green",
            "resolve_color": "ResolveColorGreen",
            "marker_text": "SWAP_OK"
        }
    else:
        return {
            "clip_name": "FLICK_ERROR",
            "clip_color": "Red",
            "resolve_color": "ResolveColorRed",
            "marker_text": "FLICK_ERROR"
        }

def write_edl(output_path, all_seqs, fps_int, video_path, auto_remove):
    clip_name = os.path.basename(video_path)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("TITLE: GPU Check EDL\n")
        f.write("FCM: NON-DROP FRAME\n\n")

        event_num = 1
        record_time_frames = 0

        for start_frame, end_frame, is_good in all_seqs:
            if auto_remove and not is_good:
                continue

            duration = end_frame - start_frame
            if duration <= 0:
                continue

            src_tc_in = frame_to_tc(start_frame, fps_int)
            src_tc_out = frame_to_tc(end_frame, fps_int)

            if auto_remove:
                rec_tc_in = frame_to_tc(record_time_frames, fps_int)
                record_time_frames += duration
                rec_tc_out = frame_to_tc(record_time_frames, fps_int)
            else:
                rec_tc_in = src_tc_in
                rec_tc_out = src_tc_out

            style = get_segment_style(is_good)

            f.write(f"{event_num:03d} AX AA/V C        {src_tc_in} {src_tc_out} {rec_tc_in} {rec_tc_out}\n")
            f.write(f"* FROM CLIP NAME: {clip_name}\n")
            f.write(f"* CLIP NAME: {style['clip_name']}\n")
            f.write(f"* CLIP COLOR: {style['clip_color']}\n")
            f.write(f"* {style['marker_text']}\n")
            f.write(f" |C:{style['resolve_color']} |M:{style['marker_text']} |D:1\n\n")

            event_num += 1

def export_video_ffmpeg(video_path, output_path, all_seqs, fps_float, total_frames, ffmpeg_exe, lang, encoder_setting):
    good_seqs = [seq for seq in all_seqs if seq[2]]
    if not good_seqs:
        return

    filter_path = output_path + "_filter.txt"
    with open(filter_path, 'w', encoding='utf-8') as f:
        concat_inputs = []
        for i, (start, end, _) in enumerate(good_seqs):
            start_sec = start / fps_float
            end_sec = end / fps_float
            
            f.write(f"[0:v]trim=start={start_sec:.5f}:end={end_sec:.5f},setpts=PTS-STARTPTS[v{i}];\n")
            f.write(f"[0:a]atrim=start={start_sec:.5f}:end={end_sec:.5f},asetpts=PTS-STARTPTS[a{i}];\n")
            
            concat_inputs.append(f"[v{i}][a{i}]")

        f.write(f"{''.join(concat_inputs)}concat=n={len(good_seqs)}:v=1:a=1[outv][outa]\n")

    print(TEXTS[lang]['ffmpeg_render'].format(name=os.path.basename(output_path), codec=encoder_setting))
    encoder_params = {
        'cpu': ["-c:v", "libx264", "-preset", "fast", "-crf", "18"],
        'nvidia_h264': ["-c:v", "h264_nvenc", "-preset", "p6", "-cq", "18"],
        'nvidia_hevc': ["-c:v", "hevc_nvenc", "-preset", "p6", "-cq", "18"],
        'nvidia_av1': ["-c:v", "av1_nvenc", "-preset", "p6", "-cq", "18"],
        'amd_h264': ["-c:v", "h264_amf", "-rc", "cqp", "-qp_p", "18", "-qp_i", "18"],
        'amd_hevc': ["-c:v", "hevc_amf", "-rc", "cqp", "-qp_p", "18", "-qp_i", "18"]
    }
    
    # Fallback auf nvidia_h264, falls eine ungueltige Eingabe gemacht wird
    selected_params = encoder_params.get(encoder_setting, encoder_params['nvidia_h264'])

    cmd = [
        ffmpeg_exe, "-y",
        "-i", video_path,
        "-filter_complex_script", filter_path,
        "-map", "[outv]",
        "-map", "[outa]"
    ] + selected_params + [
        "-c:a", "aac", "-b:a", "256k",
        output_path
    ]
    
    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True, encoding='utf-8', errors='replace')
    
    frame_pattern = re.compile(r"frame=\s*(\d+)")
    last_lines = []
    
    for line in process.stderr:
        last_lines.append(line.strip())
        if len(last_lines) > 15:
            last_lines.pop(0)
            
        match = frame_pattern.search(line)
        if match and total_frames > 0:
            frame = int(match.group(1))
            percent = (frame / total_frames) * 100
            sys.stdout.write(TEXTS[lang]['ffmpeg_progress'].format(percent=percent, frame=frame, total=total_frames))
            sys.stdout.flush()
            
    process.wait()
    
    if process.returncode != 0:
        print(TEXTS[lang]['ffmpeg_error'].format(name=os.path.basename(video_path)))
        for line in last_lines:
            print(line)
        print("---------------------------------\n")
    else:
        print(TEXTS[lang]['ffmpeg_success'])
        
    if os.path.exists(filter_path):
        try:
            os.remove(filter_path)
        except Exception:
            pass

def export_via_davinci(
    deepfake_video,
    source_video,
    all_seqs,
    davinci_api_path,
    lang,
    final_export_dir,
    davinci_render_timeout_seconds,
):
    """Returns True if render completed successfully, False otherwise."""

    if davinci_api_path not in sys.path:
        sys.path.append(davinci_api_path)

    try:
        import DaVinciResolveScript as dvr_script
    except ImportError:
        print(TEXTS[lang]['davinci_api_missing'])
        print(TEXTS[lang]['davinci_api_path_searched'].format(path=davinci_api_path))
        print(TEXTS[lang]['davinci_api_check_explorer'])
        return False

    resolve = dvr_script.scriptapp("Resolve")
    if not resolve:
        print(TEXTS[lang]['davinci_not_open'])
        return False

    projectManager = resolve.GetProjectManager()
    project = projectManager.GetCurrentProject()
    if not project:
        print(TEXTS[lang]['davinci_no_project'])
        return False

    mediaPool = project.GetMediaPool()

    print(TEXTS[lang]['davinci_sending_data'])

    # Pause so Windows can release file locks from OpenCV before Resolve imports the clip
    time.sleep(2)
    
    # 2. Pfad für die DaVinci-API erzwingen (Forward-Slashes verhindern Lesefehler)
    abs_video_path = os.path.abspath(deepfake_video).replace('\\', '/')
    
    imported_items = mediaPool.ImportMedia([abs_video_path])
    
    if not imported_items:
        print(TEXTS[lang]['davinci_import_error'].format(path=abs_video_path))
        return False

    df_item = imported_items[0]

    clip_props = df_item.GetClipProperty() or {}
    res = clip_props.get('Resolution', '')
    fps_val = clip_props.get('FPS', '60')

    try:
        if not res:
            raise ValueError(TEXTS[lang]['davinci_meta_no_resolution'])

        width, height = [int(x) for x in str(res).lower().replace(' ', '').split('x', 1)]

        project.SetSetting('timelineResolutionWidth', str(width))
        project.SetSetting('timelineResolutionHeight', str(height))
        project.SetSetting('timelineFrameRate', str(fps_val))
    except Exception as e:
        print(TEXTS[lang]['davinci_meta_parse_error'].format(error=e))
        
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        try:
            user_res = simpledialog.askstring(
                TEXTS[lang]['manual_res_title'],
                TEXTS[lang]['manual_res_prompt'],
                initialvalue="1920x1080"
            )
        finally:
            root.destroy()

        if user_res:
            try:
                width, height = [int(x) for x in user_res.lower().replace(' ', '').split('x', 1)]
                project.SetSetting('timelineResolutionWidth', str(width))
                project.SetSetting('timelineResolutionHeight', str(height))
            except Exception:
                print(TEXTS[lang]['manual_res_invalid'])
                width, height = 1920, 1080
        else:
            print(TEXTS[lang]['manual_res_invalid'])
            width, height = 1920, 1080
    
    base_name = os.path.splitext(os.path.basename(deepfake_video))[0]
    timestamp = datetime.datetime.now().strftime("%H%M%S")
    timeline_name = f"AutoCut_{base_name}_{timestamp}"
    timeline = mediaPool.CreateEmptyTimeline(timeline_name)
    
    if not timeline:
        print(TEXTS[lang]['davinci_timeline_error'])
        return False

    clips_to_append = []
    for start_frame, end_frame, is_good in all_seqs:
        if is_good:
            duration = end_frame - start_frame
            if duration > 0:
                clips_to_append.append({
                    "mediaPoolItem": df_item,
                    "startFrame": int(start_frame),
                    "endFrame": int(end_frame)
                })
    
    if clips_to_append:
        mediaPool.AppendToTimeline(clips_to_append)
    else:
        print(TEXTS[lang]['davinci_no_valid_scenes'])
        return False

    if final_export_dir and os.path.exists(final_export_dir):
        target_dir = final_export_dir
    else:
        target_dir = os.path.dirname(abs_video_path)

    project.SetCurrentTimeline(timeline)
    project.DeleteAllRenderJobs()
    
    if not project.LoadRenderPreset("AutoCutPreset"):
        print(TEXTS[lang]['davinci_preset_warning'])
        print(TEXTS[lang]['davinci_preset_fallback'])
    
    project.SetRenderSettings({
        "SelectAllFrames": True,
        "TargetDir": target_dir,
        "CustomName": f"{base_name}_DaVinci_Export",
        "ResolutionWidth": width,
        "ResolutionHeight": height
    })
    
    project.AddRenderJob()
    print(TEXTS[lang]['davinci_job_created'].format(name=f"{base_name}_DaVinci_Export"))
    print(TEXTS[lang]['davinci_start_render'])
    project.StartRendering()
    print(TEXTS[lang]['davinci_render_running'])

    # Wait until DaVinci finishes; optional time limit (settings.ini davinci_render_timeout_seconds, 0 = no limit)
    start_time = time.time()

    while project.IsRenderingInProgress():
        time.sleep(5)
        if (
            davinci_render_timeout_seconds > 0
            and (time.time() - start_time) > davinci_render_timeout_seconds
        ):
            project.StopRendering()
            time.sleep(2)
            raise Exception(
                TEXTS[lang]['davinci_render_timeout_exceeded'].format(
                    sec=davinci_render_timeout_seconds
                )
            )

    render_jobs = project.GetRenderJobList()
    if not render_jobs:
        return False

    job_id = render_jobs[-1].get("JobId")
    if not job_id:
        return False

    status_dict = project.GetRenderJobStatus(job_id)
    status = status_dict.get("JobStatus", "Unknown") if status_dict else "Unknown"

    if status not in ["Complete", "Abgeschlossen"]:
        raise Exception(
            TEXTS[lang]['davinci_render_status_failed'].format(status=status)
        )

    return True


def main(source_video, deepfake_video, settings):
    lang = (settings.get('language', 'en') or 'en')
    if isinstance(lang, str):
        lang = lang.lower()
    if lang not in TEXTS:
        lang = 'en'
        
    base_dir = get_base_dir()
    local_ffmpeg = os.path.join(base_dir, "ffmpeg.exe")
    ffmpeg_exe = local_ffmpeg if os.path.exists(local_ffmpeg) else "ffmpeg"
    
    buffer_seconds = settings['buffer_seconds']
    noise_thresh = settings['pixel_noise_threshold']
    pixel_thresh = settings['changed_pixels_threshold']
    enable_ffmpeg = settings['enable_ffmpeg_export']
    ffmpeg_export_target = settings['ffmpeg_export_target']
    ffmpeg_encoder = settings['ffmpeg_encoder']
    enable_fullcheck = settings['enable_fullcheck_edl']
    enable_autodelete_edl = settings['enable_autodelete_edl']
    enable_davinci = settings['enable_davinci_export']
    davinci_api_path = settings['davinci_api_path']
    final_export_dir = settings.get('final_export_dir', '')
    davinci_render_timeout_seconds = settings.get('davinci_render_timeout_seconds', 1800)

    run_davinci_export = False
    if enable_davinci:
        if davinci_api_path not in sys.path:
            sys.path.append(davinci_api_path)
        try:
            import DaVinciResolveScript as dvr_script
            resolve = dvr_script.scriptapp("Resolve")
            if resolve:
                run_davinci_export = True
            else:
                print(TEXTS[lang]['davinci_fallback_skip'])
        except ImportError:
            print(TEXTS[lang]['davinci_api_missing'])
            print(TEXTS[lang]['davinci_api_path_searched'].format(path=davinci_api_path))
            print(TEXTS[lang]['davinci_api_check_explorer'])
            print(TEXTS[lang]['davinci_fallback_skip'])

    cap_src = cv2.VideoCapture(source_video)
    cap_df = cv2.VideoCapture(deepfake_video)
    
    fps_float = float(cap_src.get(cv2.CAP_PROP_FPS))
    if not fps_float or fps_float <= 0:
        print(TEXTS[lang]['fps_fallback'])
        fps_float = 30.0
    fps_int = max(1, int(round(fps_float)))
    buffer_frames = int(fps_float * buffer_seconds)
    total_frames = int(cap_src.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(TEXTS[lang]['loading_settings'])
    print(TEXTS[lang]['set_buffer'].format(val=buffer_seconds))
    print(TEXTS[lang]['set_noise'].format(val=noise_thresh))
    print(TEXTS[lang]['set_pixel'].format(val=pixel_thresh))
    print(TEXTS[lang]['set_davinci'].format(val=TEXTS[lang]['on'] if enable_davinci else TEXTS[lang]['off']))
    if enable_davinci and run_davinci_export:
        _dto = davinci_render_timeout_seconds
        _tout = TEXTS[lang]['davinci_timeout_off'] if _dto == 0 else f"{_dto}s"
        print(TEXTS[lang]['set_davinci_timeout'].format(val=_tout))
    print(TEXTS[lang]['set_ffmpeg'].format(val=TEXTS[lang]['on'] if enable_ffmpeg else TEXTS[lang]['off']))
    if enable_ffmpeg:
        print(TEXTS[lang]['set_ffmpeg_target'].format(
            val=TEXTS[lang][f'ffmpeg_target_{ffmpeg_export_target}']
        ))
    print(TEXTS[lang]['set_fullcheck'].format(val=TEXTS[lang]['on'] if enable_fullcheck else TEXTS[lang]['off']))
    
    print(TEXTS[lang]['start_analysis'].format(frames=total_frames))
    
    raw_diff = []
    actual_frame_count = 0
    
    for _ in range(total_frames):
        ret_s, frame_s = cap_src.read()
        ret_d, frame_d = cap_df.read()
        
        if not ret_s or not ret_d:
            break
            
        gray_s = cv2.cvtColor(frame_s, cv2.COLOR_BGR2GRAY)
        gray_d = cv2.cvtColor(frame_d, cv2.COLOR_BGR2GRAY)
        
        diff = cv2.absdiff(gray_s, gray_d)
        _, thresh = cv2.threshold(diff, noise_thresh, 255, cv2.THRESH_BINARY)
        changed_pixels = cv2.countNonZero(thresh)
        
        has_diff = changed_pixels > pixel_thresh
        raw_diff.append(has_diff)
        actual_frame_count += 1

        if total_frames > 0 and (actual_frame_count % 30 == 0 or actual_frame_count == total_frames):
            percent = (actual_frame_count / total_frames) * 100
            sys.stdout.write(TEXTS[lang]['analyzing'].format(percent=percent, current=actual_frame_count, total=total_frames))
            sys.stdout.flush()

    cap_src.release()
    cap_df.release()

    print(TEXTS[lang]['frames_processed'].format(count=actual_frame_count))
    
    keep_frames = []
    false_streak = 0
    
    for i in range(len(raw_diff)):
        if raw_diff[i]:
            keep_frames.append(i)
            false_streak = 0
        else:
            false_streak += 1
            if false_streak >= buffer_frames:
                keep_frames.append(i)
                if false_streak == buffer_frames:
                    for j in range(1, buffer_frames):
                        keep_frames.append(i - j)

    keep_frames_set = set(keep_frames)
    
    if not keep_frames_set:
        print(TEXTS[lang]['no_diff'])
        return

    all_seqs = []
    if actual_frame_count > 0:
        current_state = 0 in keep_frames_set
        start_frame = 0
        for i in range(1, actual_frame_count):
            state = i in keep_frames_set
            if state != current_state:
                all_seqs.append((start_frame, i, current_state))
                start_frame = i
                current_state = state
        all_seqs.append((start_frame, actual_frame_count, current_state))

    base_src_full = os.path.splitext(source_video)[0]
    base_df_full = os.path.splitext(deepfake_video)[0]
    
    if final_export_dir and os.path.exists(final_export_dir):
        path_src_base = os.path.join(final_export_dir, os.path.basename(base_src_full))
        path_df_base = os.path.join(final_export_dir, os.path.basename(base_df_full))
    else:
        path_src_base = base_src_full
        path_df_base = base_df_full

    if enable_autodelete_edl:
        edl_src_auto = f"{path_src_base}_SOURCE_AutoDelete.edl"
        edl_df_auto = f"{path_df_base}_DEEPFAKE_AutoDelete.edl"
        write_edl(edl_src_auto, all_seqs, fps_int, source_video, auto_remove=True)
        write_edl(edl_df_auto, all_seqs, fps_int, deepfake_video, auto_remove=True)
        print(TEXTS[lang]['edl_auto_created'])
        print(f"- {os.path.basename(edl_src_auto)}")
        print(f"- {os.path.basename(edl_df_auto)}")
        
    if enable_fullcheck:
        edl_src_full = f"{path_src_base}_SOURCE_FullCheck.edl"
        edl_df_full = f"{path_df_base}_DEEPFAKE_FullCheck.edl"
        write_edl(edl_src_full, all_seqs, fps_int, source_video, auto_remove=False)
        write_edl(edl_df_full, all_seqs, fps_int, deepfake_video, auto_remove=False)
        print(TEXTS[lang]['edl_full_created'])
    
    if enable_ffmpeg:
        vid_src_auto = f"{path_src_base}_AutoCut.mp4"
        vid_df_auto = f"{path_df_base}_AutoCut.mp4"
        if ffmpeg_export_target in ("both", "source"):
            export_video_ffmpeg(source_video, vid_src_auto, all_seqs, fps_float, total_frames, ffmpeg_exe, lang, ffmpeg_encoder)
        if ffmpeg_export_target in ("both", "deepfake"):
            export_video_ffmpeg(deepfake_video, vid_df_auto, all_seqs, fps_float, total_frames, ffmpeg_exe, lang, ffmpeg_encoder)

    davinci_ok = True
    if enable_davinci:
        if run_davinci_export:
            try:
                davinci_ok = export_via_davinci(
                    deepfake_video,
                    source_video,
                    all_seqs,
                    davinci_api_path,
                    lang,
                    final_export_dir,
                    davinci_render_timeout_seconds,
                )
            except Exception as ex:
                print(TEXTS[lang]['davinci_export_exception'].format(error=ex))
                davinci_ok = False
        else:
            davinci_ok = False

    if (
        enable_davinci
        and not enable_autodelete_edl
        and not enable_fullcheck
        and not davinci_ok
    ):
        edl_fb_src = f"{path_src_base}_SOURCE_AutoDelete.edl"
        edl_fb_df = f"{path_df_base}_DEEPFAKE_AutoDelete.edl"
        write_edl(edl_fb_src, all_seqs, fps_int, source_video, auto_remove=True)
        write_edl(edl_fb_df, all_seqs, fps_int, deepfake_video, auto_remove=True)
        print(TEXTS[lang]['davinci_edl_fallback'])
        print(f"- {os.path.basename(edl_fb_src)}")
        print(f"- {os.path.basename(edl_fb_df)}")

    print(TEXTS[lang]['all_done'])

def get_files_via_gui(lang):
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    
    source = filedialog.askopenfilename(title=TEXTS[lang]['file_dialog_source'], filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv")])
    if not source:
        root.destroy()
        return None, None
        
    deepfake = filedialog.askopenfilename(title=TEXTS[lang]['file_dialog_df'], filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv")])
    root.destroy()
    if not deepfake:
        return None, None
        
    return source, deepfake

def confirm_source(file1, file2, lang):
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    
    name1 = os.path.basename(file1)
    answer = messagebox.askyesno(TEXTS[lang]['confirm_source_title'], TEXTS[lang]['confirm_source_msg'].format(name=name1))
    root.destroy()
    if answer:
        return file1, file2
    else:
        return file2, file1

if __name__ == "__main__":
    settings = load_config()
    lang = settings.get('language', 'en').lower()
    if lang not in TEXTS:
        lang = 'en'
        
    source_video = None
    deepfake_video = None

    if len(sys.argv) == 4 and sys.argv[3] == "--auto":
        source_video = sys.argv[1]
        deepfake_video = sys.argv[2]

    elif len(sys.argv) == 3:
        source_video, deepfake_video = confirm_source(sys.argv[1], sys.argv[2], lang)
        
    elif len(sys.argv) == 2:
        cache_file = os.path.join(get_base_dir(), "autocut_cache.txt")
        current_file = sys.argv[1]

        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_file = f.read().strip()
            
            os.remove(cache_file)

            if cached_file == current_file:
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                messagebox.showinfo(TEXTS[lang]['abort_double_file_title'], TEXTS[lang]['abort_double_file_msg'])
                root.destroy()
                sys.exit(0)

            source_video, deepfake_video = confirm_source(cached_file, current_file, lang)
        else:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(current_file)
            
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            messagebox.showinfo(TEXTS[lang]['cache_step1_title'], TEXTS[lang]['cache_step1_msg'].format(name=os.path.basename(current_file)))
            root.destroy()
            sys.exit(0)
            
    else:
        print(TEXTS[lang]['no_files_sendto'])
        source_video, deepfake_video = get_files_via_gui(lang)

    if not source_video or not deepfake_video:
        print(TEXTS[lang]['abort_not_both'])
        input(TEXTS[lang]['press_enter'])
        sys.exit(1)
        
    is_auto_mode = (len(sys.argv) == 4 and sys.argv[3] == "--auto")

    try:
        main(source_video, deepfake_video, settings)
    except Exception as e:
        print(TEXTS[lang]['unexpected_error'].format(error=e))
        # Im Fehlerfall auch bei Auto-Mode kurz warten, damit man die Fehlermeldung lesen kann
        if is_auto_mode:
            time.sleep(10)
        sys.exit(1)
        
    if not is_auto_mode:
        input(TEXTS[lang]['press_enter'])