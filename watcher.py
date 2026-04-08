import os
import sys
import time
import subprocess
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import configparser

TEXTS = {
    'en': {
        'saved_title': "Saved Paths Found",
        'saved_msg': "Should the saved folders be used?\n\nOriginals: {s}\nDeepfakes: {d}\n\n(No = Select new folders)",
        'select_prompt': "Please select the two required folders in the pop-up windows...",
        'sel_src': "1. Select ORIGINAL Folder (Source)",
        'sel_df': "2. Select DEEPFAKE Folder (Monitored)",
        'abort': "Aborted.",
        'invalid_paths': "Saved paths invalid or not found. Starting folder selection...\n",
        'saved_declined': "Starting new folder selection (saved paths were not used)...\n",
        'davinci_start': "DaVinci Resolve is not open. Starting program...",
        'davinci_wait': "Waiting 20 seconds for the API to be ready...",
        'davinci_err': "[ERROR] DaVinci Resolve could not be started: {e}",
        'davinci_path': "Please check the path in watcher_settings.ini:\n{path}",
        'err_multi': "[ERROR] Ambiguous: Multiple originals match '{word}'. Skipping. Please rename or move unused originals.",
        'err_compare': "[ERROR] Could not find compare.exe or compare.py in:\n{path}",
        'enter_exit': "Press Enter to exit...",
        'banner': "==================================================\nAuto-Watcher started. Press CTRL+C to exit.\nMonitoring folder: {dir}\nWait time for file release: {wait} seconds\nMax compare run: {ctime}\nAFK mode: {afk}\n==================================================\n",
        'compare_timeout_unlimited': "unlimited (compare_timeout_seconds=0)",
        'ignore': "[IGNORED] {file} - No unique original found.",
        'new_df': "\n[NEW] Complete Deepfake detected: {file}",
        'matched': "-> Matched Original: {src}",
        'done': "[DONE] File processed and left in the same folder.",
        'err_crash': "[ERROR] compare crashed on {file}. Error code: {code}",
        'err_timeout': "[ERROR] compare timed out after {sec}s on {file}",
        'err_abort': "[ERROR] Aborted on {file}: {e}",
        'first_run_skip': "[INFO] First start detected - settings.ini was created. File will NOT be written to watcher_processed.txt.",
        'exit': "\nWatcher is shutting down.",
        'sys_err': "[SYSTEM ERROR] {e}"
    },
    'de': {
        'saved_title': "Gespeicherte Pfade gefunden",
        'saved_msg': "Sollen die gespeicherten Ordner verwendet werden?\n\nOriginale: {s}\nDeepfakes: {d}\n\n(Nein = Neue Ordner auswaehlen)",
        'select_prompt': "Bitte waehle die zwei benoetigten Ordner in den aufpoppenden Fenstern aus...",
        'sel_src': "1. ORIGINAL-Ordner (Source) auswaehlen",
        'sel_df': "2. DEEPFAKE-Ordner (wird ueberwacht) auswaehlen",
        'abort': "Abbruch.",
        'invalid_paths': "Gespeicherte Pfade ungueltig oder nicht gefunden. Starte Ordnerabfrage...\n",
        'saved_declined': "Neue Ordnerauswahl (gespeicherte Pfade werden nicht verwendet)...\n",
        'davinci_start': "DaVinci Resolve ist nicht geoeffnet. Starte Programm...",
        'davinci_wait': "Warte 20 Sekunden, bis die API bereit ist...",
        'davinci_err': "[FEHLER] DaVinci Resolve konnte nicht gestartet werden: {e}",
        'davinci_path': "Bitte pruefe den Pfad in der watcher_settings.ini:\n{path}",
        'err_multi': "[FEHLER] Uneindeutig: Mehrere Originale passen zu '{word}'. Ueberspringe. Bitte Originale eindeutig benennen!",
        'err_compare': "[FEHLER] Weder compare.exe noch compare.py gefunden in:\n{path}",
        'enter_exit': "Druecke Enter zum Beenden...",
        'banner': "==================================================\nAuto-Watcher gestartet. Druecke STRG+C zum Beenden.\nUeberwache Ordner: {dir}\nWartezeit fuer Dateifreigabe: {wait} Sekunden\nMax. Compare-Lauf: {ctime}\nAFK-Modus: {afk}\n==================================================\n",
        'compare_timeout_unlimited': "unbegrenzt (compare_timeout_seconds=0)",
        'ignore': "[IGNORIERT] {file} - Kein eindeutiges Original gefunden.",
        'new_df': "\n[NEU] Komplettes Deepfake erkannt: {file}",
        'matched': "-> Zugeordnetes Original: {src}",
        'done': "[ERLEDIGT] Datei verarbeitet und im selben Ordner belassen.",
        'err_crash': "[FEHLER] compare ist abgestuerzt bei {file}. Fehlercode: {code}",
        'err_timeout': "[FEHLER] compare Zeitueberschreitung nach {sec}s bei {file}",
        'err_abort': "[FEHLER] Abbruch bei {file}: {e}",
        'first_run_skip': "[INFO] Erster Start erkannt - settings.ini wurde erstellt. Datei wird NICHT in watcher_processed.txt geschrieben.",
        'exit': "\nWatcher wird beendet.",
        'sys_err': "[SYSTEMFEHLER] {e}"
    }
}


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resolve_compare_command(base_dir):
    """Release: compare.exe next to watcher. Dev (src): python compare.py."""
    exe_path = os.path.join(base_dir, "compare.exe")
    py_path = os.path.join(base_dir, "compare.py")
    if os.path.isfile(exe_path):
        return [exe_path]
    if os.path.isfile(py_path):
        return [sys.executable, py_path]
    return None


def get_watcher_config():
    config_path = os.path.join(get_base_dir(), 'watcher_settings.ini')
    config = configparser.ConfigParser()

    lang = 'en'
    wait_seconds = 30
    compare_timeout_seconds = 1800
    afk_mode = True
    s_dir = ""
    d_dir = ""
    resolve_exe = r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe"
    ignore_pattern = r'^\d{6,}_(pro|hyb|exp)(_p)?'
    prefix_length = 10
    ignore_suffix = '_p'

    if os.path.exists(config_path):
        config.read(config_path)

    if config.has_section('SETTINGS'):
        lang = config.get('SETTINGS', 'language', fallback='en').lower()
        if lang not in TEXTS:
            lang = 'en'
        wait_seconds = config.getint('SETTINGS', 'wait_seconds', fallback=30)
        compare_timeout_seconds = config.getint(
            'SETTINGS', 'compare_timeout_seconds', fallback=1800
        )
        afk_mode = config.getboolean('SETTINGS', 'afk_mode', fallback=True)

    if config.has_section('PATHS'):
        s_dir = config.get('PATHS', 'source_dir', fallback='')
        d_dir = config.get('PATHS', 'deepfake_dir', fallback='')
        resolve_exe = config.get('PATHS', 'resolve_exe_path', fallback=resolve_exe)

    if config.has_section('MATCHING'):
        ignore_pattern = config.get('MATCHING', 'ignore_temp_pattern', fallback=ignore_pattern)
        prefix_length = config.getint('MATCHING', 'match_prefix_length', fallback=prefix_length)
        ignore_suffix = config.get('MATCHING', 'ignore_suffix', fallback=ignore_suffix)

    if s_dir and d_dir and os.path.exists(s_dir) and os.path.exists(d_dir):
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        use_saved = messagebox.askyesno(
            TEXTS[lang]['saved_title'],
            TEXTS[lang]['saved_msg'].format(s=s_dir, d=d_dir)
        )
        root.destroy()

        if use_saved:
            return (
                s_dir,
                d_dir,
                wait_seconds,
                compare_timeout_seconds,
                resolve_exe,
                lang,
                ignore_pattern,
                prefix_length,
                ignore_suffix,
                afk_mode,
            )
        else:
            print(TEXTS[lang]['saved_declined'])

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    print(TEXTS[lang]['select_prompt'])

    new_s_dir = filedialog.askdirectory(title=TEXTS[lang]['sel_src'])
    if not new_s_dir:
        print(TEXTS[lang]['abort'])
        sys.exit(0)

    new_d_dir = filedialog.askdirectory(title=TEXTS[lang]['sel_df'])
    if not new_d_dir:
        print(TEXTS[lang]['abort'])
        sys.exit(0)

    if not config.has_section('PATHS'):
        config.add_section('PATHS')
    if not config.has_section('SETTINGS'):
        config.add_section('SETTINGS')
    if not config.has_section('MATCHING'):
        config.add_section('MATCHING')

    config['PATHS']['source_dir'] = new_s_dir
    config['PATHS']['deepfake_dir'] = new_d_dir
    config['PATHS']['resolve_exe_path'] = resolve_exe
    config['SETTINGS']['language'] = lang
    config['SETTINGS']['wait_seconds'] = str(wait_seconds)
    config['SETTINGS']['compare_timeout_seconds'] = str(compare_timeout_seconds)
    config['SETTINGS']['afk_mode'] = '1' if afk_mode else '0'
    config['MATCHING']['ignore_temp_pattern'] = ignore_pattern
    config['MATCHING']['match_prefix_length'] = str(prefix_length)
    config['MATCHING']['ignore_suffix'] = ignore_suffix

    with open(config_path, 'w') as configfile:
        config.write(configfile)

    return (
        new_s_dir,
        new_d_dir,
        wait_seconds,
        compare_timeout_seconds,
        resolve_exe,
        lang,
        ignore_pattern,
        prefix_length,
        ignore_suffix,
        afk_mode,
    )


def is_davinci_enabled():
    config_path = os.path.join(get_base_dir(), 'settings.ini')
    config = configparser.ConfigParser()
    if os.path.exists(config_path):
        config.read(config_path)
    if config.has_section('SETTINGS'):
        return config.getboolean('SETTINGS', 'enable_davinci_export', fallback=False)
    return False


def is_resolve_running():
    if sys.platform != 'win32':
        return False
    try:
        kw = {}
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            kw['creationflags'] = subprocess.CREATE_NO_WINDOW
        output = subprocess.check_output(
            ['tasklist', '/FI', 'IMAGENAME eq Resolve.exe', '/FO', 'CSV', '/NH'],
            shell=False,
            **kw,
        ).decode('utf-8', errors='ignore')
        return 'Resolve.exe' in output
    except Exception:
        return False


def start_resolve(resolve_exe_path, lang):
    if not is_resolve_running():
        print(TEXTS[lang]['davinci_start'])
        try:
            os.startfile(resolve_exe_path)
        except Exception as e:
            print(TEXTS[lang]['davinci_err'].format(e=e))
            print(TEXTS[lang]['davinci_path'].format(path=resolve_exe_path))
            return
        print(TEXTS[lang]['davinci_wait'])
        time.sleep(20)


def normalize_name(filename):
    base_name = os.path.splitext(filename)[0].lower()
    return re.sub(r'[^a-z0-9]', '', base_name)


def find_matching_source(df_filename, source_dir, lang, ignore_pattern, prefix_length):
    if ignore_pattern and ignore_pattern.strip() != "":
        if re.match(ignore_pattern, df_filename, re.IGNORECASE):
            return None

    possible_matches = []
    df_norm = normalize_name(df_filename)

    for src_file in os.listdir(source_dir):
        if src_file.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
            src_base = os.path.splitext(src_file)[0]

            if prefix_length > 0:
                prefix_raw = src_base[:prefix_length]
            else:
                prefix_raw = src_base

            prefix_norm = normalize_name(prefix_raw + ".mp4")

            if len(prefix_norm) > 0 and df_norm.startswith(prefix_norm):
                possible_matches.append(src_file)

    if len(possible_matches) == 1:
        return os.path.join(source_dir, possible_matches[0])
    elif len(possible_matches) > 1:
        print(TEXTS[lang]['err_multi'].format(word=df_filename[:15] + "..."))
        return None

    return None


def is_file_stable(filepath, wait_seconds):
    try:
        size1 = os.path.getsize(filepath)
        mtime1 = os.path.getmtime(filepath)

        time.sleep(wait_seconds)

        size2 = os.path.getsize(filepath)
        mtime2 = os.path.getmtime(filepath)

        return size1 == size2 and mtime1 == mtime2
    except OSError:
        return False


def get_processed_files(log_path):
    if not os.path.exists(log_path):
        return set()
    with open(log_path, 'r', encoding='utf-8-sig') as f:
        return set(line.strip().lower() for line in f)


def mark_as_processed(log_path, filename):
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(filename + '\n')


def watcher_compare_outcome(settings_existed_before, settings_exists_after, afk_mode, succeeded):
    """Returns (should_mark_processed, print_first_run_skip)."""
    first_run = not settings_existed_before and settings_exists_after
    if first_run:
        return False, True
    if succeeded:
        return True, False
    return afk_mode, False


def main():
    (
        SOURCE_DIR,
        DEEPFAKE_DIR,
        WAIT_SECONDS,
        COMPARE_TIMEOUT_SECONDS,
        RESOLVE_EXE_PATH,
        lang,
        IGNORE_PATTERN,
        PREFIX_LENGTH,
        IGNORE_SUFFIX,
        AFK_MODE,
    ) = get_watcher_config()
    compare_run_timeout = (
        None if COMPARE_TIMEOUT_SECONDS <= 0 else COMPARE_TIMEOUT_SECONDS
    )
    LOG_PATH = os.path.join(DEEPFAKE_DIR, 'watcher_processed.txt')
    base_dir = get_base_dir()
    compare_cmd = resolve_compare_command(base_dir)

    if not compare_cmd:
        print(TEXTS[lang]['err_compare'].format(path=base_dir))
        input(TEXTS[lang]['enter_exit'])
        sys.exit(1)

    afk_label = ("AN" if AFK_MODE else "AUS") if lang == 'de' else ("ON" if AFK_MODE else "OFF")
    ctime_label = (
        TEXTS[lang]['compare_timeout_unlimited']
        if compare_run_timeout is None
        else f"{compare_run_timeout}s"
    )
    print(TEXTS[lang]['banner'].format(
        dir=DEEPFAKE_DIR,
        wait=WAIT_SECONDS,
        ctime=ctime_label,
        afk=afk_label,
    ))

    missing_source_warned = set()

    while True:
        try:
            processed = get_processed_files(LOG_PATH)

            for filename in os.listdir(DEEPFAKE_DIR):
                if filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):

                    if "_DaVinci_Export" in filename or "_AutoCut" in filename:
                        continue

                    if IGNORE_SUFFIX and os.path.splitext(filename)[0].lower().endswith(IGNORE_SUFFIX.lower()):
                        continue

                    if filename.strip().lower() in processed:
                        continue

                    source_path = find_matching_source(filename, SOURCE_DIR, lang, IGNORE_PATTERN, PREFIX_LENGTH)

                    if not source_path:
                        is_ignored_temp = False
                        if IGNORE_PATTERN and IGNORE_PATTERN.strip() != "":
                            if re.match(IGNORE_PATTERN, filename, re.IGNORECASE):
                                is_ignored_temp = True

                        if not is_ignored_temp:
                            if filename not in missing_source_warned:
                                print(TEXTS[lang]['ignore'].format(file=filename))
                                missing_source_warned.add(filename)
                        continue

                    fake_path = os.path.join(DEEPFAKE_DIR, filename)
                    if not is_file_stable(fake_path, WAIT_SECONDS):
                        continue

                    print(TEXTS[lang]['new_df'].format(file=filename))
                    print(TEXTS[lang]['matched'].format(src=os.path.basename(source_path)))

                    if is_davinci_enabled():
                        start_resolve(RESOLVE_EXE_PATH, lang)

                    settings_path = os.path.join(get_base_dir(), 'settings.ini')
                    settings_existed_before = os.path.exists(settings_path)
                    should_mark_processed = False

                    try:
                        subprocess.run(
                            compare_cmd + [source_path, fake_path, "--auto"],
                            check=True,
                            timeout=compare_run_timeout,
                        )
                        print(TEXTS[lang]['done'])
                        settings_after = os.path.exists(settings_path)
                        mark, first_run_msg = watcher_compare_outcome(
                            settings_existed_before, settings_after, AFK_MODE, True
                        )
                        should_mark_processed = mark
                        if first_run_msg:
                            print(TEXTS[lang]['first_run_skip'])

                    except subprocess.CalledProcessError as e:
                        print(TEXTS[lang]['err_crash'].format(file=filename, code=e.returncode))
                        settings_after = os.path.exists(settings_path)
                        mark, _ = watcher_compare_outcome(
                            settings_existed_before, settings_after, AFK_MODE, False
                        )
                        should_mark_processed = mark

                    except subprocess.TimeoutExpired as e:
                        print(TEXTS[lang]['err_timeout'].format(file=filename, sec=int(e.timeout)))
                        settings_after = os.path.exists(settings_path)
                        mark, _ = watcher_compare_outcome(
                            settings_existed_before, settings_after, AFK_MODE, False
                        )
                        should_mark_processed = mark

                    except Exception as e:
                        print(TEXTS[lang]['err_abort'].format(file=filename, e=e))
                        settings_after = os.path.exists(settings_path)
                        mark, _ = watcher_compare_outcome(
                            settings_existed_before, settings_after, AFK_MODE, False
                        )
                        should_mark_processed = mark

                    finally:
                        if should_mark_processed:
                            mark_as_processed(LOG_PATH, filename)

            for i in range(5, 0, -1):
                msg = f"\r[Aktiv] Warte auf neue Dateien... Scan in {i}s " if lang == 'de' else f"\r[Active] Waiting for new files... Scan in {i}s "
                sys.stdout.write(msg)
                sys.stdout.flush()
                time.sleep(1)

            sys.stdout.write("\r" + " " * 70 + "\r")

        except KeyboardInterrupt:
            print(TEXTS[lang]['exit'])
            break
        except Exception as e:
            print(TEXTS[lang]['sys_err'].format(e=e))
            time.sleep(5)


if __name__ == "__main__":
    main()