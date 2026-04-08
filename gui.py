import customtkinter as ctk
import configparser
import os
import sys
import subprocess
import threading
import time
from tkinter import filedialog, messagebox

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


class MasterGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AutoCut Control Center")
        self.geometry("980x860")
        self.base_dir = get_base_dir()

        self.settings_file = os.path.join(self.base_dir, 'settings.ini')
        self.watcher_file = os.path.join(self.base_dir, 'watcher_settings.ini')

        self.frame_top = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_top.pack(fill="x", padx=10, pady=5)

        self.switch_theme = ctk.CTkSwitch(self.frame_top, text="Light Mode", command=self.toggle_theme)
        self.switch_theme.pack(side="left", padx=10)

        self.btn_preset = ctk.CTkButton(
            self.frame_top,
            text="⚡ High-End Preset",
            fg_color="#b8860b",
            hover_color="#8b6508",
            command=self.apply_highend_preset
        )
        self.btn_preset.pack(side="right", padx=10)

        self.tabview = ctk.CTkTabview(self, width=930, height=560)
        self.tabview.pack(pady=5, padx=10, fill="both")

        self.tab_main = self.tabview.add("Watcher & Paths")
        self.tab_export = self.tabview.add("Export Methods")
        self.tab_filter = self.tabview.add("Filter & Ignore")
        self.tab_tools = self.tabview.add("Manual & Tools")
        self.tab_processed = self.tabview.add("Processed Log")

        self.build_main_tab()
        self.build_export_tab()
        self.build_filter_tab()
        self.build_tools_tab()
        self.build_processed_tab()

        self.current_process = None

        self.frame_bottom = ctk.CTkFrame(self)
        self.frame_bottom.pack(fill="x", padx=20, pady=10)

        self.btn_save = ctk.CTkButton(
            self.frame_bottom,
            text="💾 Save Settings",
            command=self.save_configs,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.btn_save.pack(side="left", padx=10, pady=10)

        self.status_label = ctk.CTkLabel(self.frame_bottom, text="🔴 Stopped", font=("Arial", 14, "bold"))
        self.status_label.pack(side="left", padx=20)

        self.btn_stop = ctk.CTkButton(
            self.frame_bottom,
            text="⏹ Stop",
            width=60,
            fg_color="red",
            hover_color="darkred",
            state="disabled",
            command=self.stop_active_process
        )
        self.btn_stop.pack(side="right", padx=(5, 10), pady=10)

        self.btn_start = ctk.CTkButton(
            self.frame_bottom,
            text="▶ Start Watcher",
            command=lambda: self.start_process("watcher")
        )
        self.btn_start.pack(side="right", padx=(10, 5), pady=10)

        self.log_visible = True
        self.btn_toggle_log = ctk.CTkButton(
            self,
            text="🔽 Hide Log",
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self.toggle_log
        )
        self.btn_toggle_log.pack(pady=(0, 5))

        self.log_box = ctk.CTkTextbox(self, height=160, state="disabled")
        self.log_box.pack(fill="both", padx=20, pady=(0, 10), expand=True)

        self.load_configs()
        self.toggle_ffmpeg_options()
        self.load_processed_log()

    def toggle_theme(self):
        ctk.set_appearance_mode("Light" if self.switch_theme.get() == 1 else "Dark")

    def toggle_log(self):
        if self.log_visible:
            self.log_box.pack_forget()
            self.btn_toggle_log.configure(text="🔼 Show Log")
            self.geometry("980x650")
        else:
            self.log_box.pack(fill="both", padx=20, pady=(0, 10), expand=True)
            self.btn_toggle_log.configure(text="🔽 Hide Log")
            self.geometry("980x860")
        self.log_visible = not self.log_visible

    def apply_highend_preset(self):
        self.combo_codec.set("nvidia_av1")
        self.var_ffmpeg.set("1")
        self.combo_target.set("both")
        self.var_davinci.set("1")
        self.toggle_ffmpeg_options()
        self.write_log("[INFO] High-End Preset loaded (AV1 Codec, DaVinci active).\n")

    def toggle_ffmpeg_options(self, *args):
        state = "normal" if self.var_ffmpeg.get() == "1" else "disabled"
        self.combo_codec.configure(state=state)
        self.combo_target.configure(state=state)

    def create_path_row(self, parent, label_text, row, is_dir=True):
        ctk.CTkLabel(parent, text=label_text).grid(row=row, column=0, padx=10, pady=10, sticky="w")
        entry = ctk.CTkEntry(parent, width=450)
        entry.grid(row=row, column=1, padx=10, pady=10)
        btn = ctk.CTkButton(parent, text="📁 Browse", width=80, command=lambda: self.browse_path(entry, is_dir))
        btn.grid(row=row, column=2, padx=10, pady=10)
        return entry

    def browse_path(self, entry_widget, is_dir):
        path = filedialog.askdirectory() if is_dir else filedialog.askopenfilename()
        if path:
            entry_widget.delete(0, 'end')
            entry_widget.insert(0, path)
            self.update_processed_log_path_label()

    def build_main_tab(self):
        self.tab_main.columnconfigure(1, weight=1)
        ctk.CTkLabel(self.tab_main, text="Language (Console Output):").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.combo_lang = ctk.CTkOptionMenu(self.tab_main, values=["en", "de"])
        self.combo_lang.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        self.entry_source_dir = self.create_path_row(self.tab_main, "Original Folder (Source):", 1)
        self.entry_df_dir = self.create_path_row(self.tab_main, "Deepfake Folder (Watcher):", 2)
        self.entry_export_dir = self.create_path_row(self.tab_main, "Optional Export Folder:", 3)

    def build_export_tab(self):
        frame_dv = ctk.CTkFrame(self.tab_export)
        frame_dv.pack(fill="x", pady=5, padx=10)

        self.var_davinci = ctk.StringVar(value="0")
        ctk.CTkCheckBox(
            frame_dv,
            text="Enable DaVinci Resolve 20 Studio Export",
            variable=self.var_davinci,
            onvalue="1",
            offvalue="0"
        ).grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="w")

        ctk.CTkLabel(frame_dv, text="DaVinci API Path:").grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")
        self.entry_davinci_api_path = ctk.CTkEntry(frame_dv, width=450)
        self.entry_davinci_api_path.grid(row=1, column=1, padx=10, pady=(0, 10), sticky="w")
        ctk.CTkButton(frame_dv, text="📁 Browse", width=80, command=lambda: self.browse_path(self.entry_davinci_api_path, is_dir=True)).grid(row=1, column=2, padx=10, pady=(0, 10), sticky="w")

        ctk.CTkLabel(frame_dv, text="Resolve.exe Path (optional for auto-start):").grid(row=2, column=0, padx=10, pady=(0, 10), sticky="w")
        self.entry_davinci_exe_path = ctk.CTkEntry(frame_dv, width=450)
        self.entry_davinci_exe_path.grid(row=2, column=1, padx=10, pady=(0, 10), sticky="w")
        ctk.CTkButton(frame_dv, text="📁 Browse", width=80, command=lambda: self.browse_path(self.entry_davinci_exe_path, is_dir=False)).grid(row=2, column=2, padx=10, pady=(0, 10), sticky="w")

        ctk.CTkLabel(frame_dv, text="DaVinci Startup Wait (sec):").grid(row=3, column=0, padx=10, pady=(0, 10), sticky="w")
        self.entry_davinci_startup_wait = ctk.CTkEntry(frame_dv, width=120)
        self.entry_davinci_startup_wait.grid(row=3, column=1, padx=10, pady=(0, 10), sticky="w")

        ctk.CTkLabel(frame_dv, text="DaVinci Render Timeout (sec, 0 = wait forever):").grid(row=4, column=0, padx=10, pady=(0, 10), sticky="w")
        self.entry_davinci_timeout = ctk.CTkEntry(frame_dv, width=120)
        self.entry_davinci_timeout.grid(row=4, column=1, padx=10, pady=(0, 10), sticky="w")

        frame_edl = ctk.CTkFrame(self.tab_export)
        frame_edl.pack(fill="x", pady=5, padx=10)
        self.var_edl_auto = ctk.StringVar(value="1")
        self.var_edl_full = ctk.StringVar(value="0")
        ctk.CTkCheckBox(frame_edl, text="EDL: AutoDelete", variable=self.var_edl_auto, onvalue="1", offvalue="0").pack(side="left", padx=10, pady=10)
        ctk.CTkCheckBox(frame_edl, text="EDL: FullCheck", variable=self.var_edl_full, onvalue="1", offvalue="0").pack(side="left", padx=10, pady=10)

        frame_ff = ctk.CTkFrame(self.tab_export)
        frame_ff.pack(fill="x", pady=5, padx=10)
        self.var_ffmpeg = ctk.StringVar(value="0")
        ctk.CTkCheckBox(
            frame_ff,
            text="Enable FFmpeg Video Export",
            variable=self.var_ffmpeg,
            onvalue="1",
            offvalue="0",
            command=self.toggle_ffmpeg_options
        ).grid(row=0, column=0, padx=10, pady=10, sticky="w")

        ctk.CTkLabel(frame_ff, text="Codec:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.combo_codec = ctk.CTkOptionMenu(frame_ff, values=["nvidia_av1", "nvidia_hevc", "nvidia_h264", "amd_hevc", "amd_h264", "cpu"])
        self.combo_codec.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(frame_ff, text="Target Videos:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.combo_target = ctk.CTkOptionMenu(frame_ff, values=["both", "source", "deepfake"])
        self.combo_target.grid(row=2, column=1, padx=10, pady=5, sticky="w")

    def build_filter_tab(self):
        self.tab_filter.columnconfigure(1, weight=1)

        ctk.CTkLabel(self.tab_filter, text="Watcher ignores files ending with:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entry_ignore_suffix = ctk.CTkEntry(self.tab_filter)
        self.entry_ignore_suffix.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        ctk.CTkLabel(self.tab_filter, text="Watcher ignores pattern (RegEx):").grid(row=1, column=0, padx=10, pady=(10, 0), sticky="w")
        self.entry_ignore_pattern = ctk.CTkEntry(self.tab_filter, width=260)
        self.entry_ignore_pattern.grid(row=1, column=1, padx=10, pady=(10, 0), sticky="w")

        ctk.CTkButton(self.tab_filter, text="?", width=30, command=self.show_regex_info).grid(row=1, column=2, padx=5, pady=(10, 0), sticky="w")
        ctk.CTkLabel(self.tab_filter, text="Tip: Use the top field for simple suffixes. Clear the RegEx field if not needed.", text_color="gray", font=("Arial", 11)).grid(row=2, column=1, padx=10, pady=(0, 10), sticky="w")

        ctk.CTkLabel(self.tab_filter, text="Buffer Seconds:").grid(row=3, column=0, padx=10, pady=10, sticky="nw")
        self.entry_buffer_seconds = ctk.CTkEntry(self.tab_filter, width=120)
        self.entry_buffer_seconds.grid(row=3, column=1, padx=10, pady=10, sticky="w")
        ctk.CTkLabel(
            self.tab_filter,
            text=(
                "Compare: how long the picture must look “no swap” (below your pixel rules) before "
                "that stretch is treated as intentional and kept. Lower = more short flicks/glitches "
                "survive in the edit; higher = stricter. 4–8 s is already quite strict."
            ),
            text_color="gray",
            font=("Arial", 11),
            justify="left",
            wraplength=520,
        ).grid(row=4, column=1, columnspan=2, padx=10, pady=(0, 10), sticky="w")

        ctk.CTkLabel(self.tab_filter, text="Pixel Noise Threshold:").grid(row=5, column=0, padx=10, pady=10, sticky="w")
        self.entry_pixel_noise = ctk.CTkEntry(self.tab_filter, width=120)
        self.entry_pixel_noise.grid(row=5, column=1, padx=10, pady=10, sticky="w")

        ctk.CTkLabel(self.tab_filter, text="Changed Pixels Threshold:").grid(row=6, column=0, padx=10, pady=10, sticky="w")
        self.entry_changed_pixels = ctk.CTkEntry(self.tab_filter, width=120)
        self.entry_changed_pixels.grid(row=6, column=1, padx=10, pady=10, sticky="w")

    def build_tools_tab(self):
        self.tab_tools.columnconfigure(1, weight=1)

        ctk.CTkLabel(self.tab_tools, text="Manual Compare (Replaces 'SendTo')", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="w")
        self.entry_manual_source = self.create_path_row(self.tab_tools, "Original Video (Source):", 1, is_dir=False)
        self.entry_manual_df = self.create_path_row(self.tab_tools, "Deepfake Video:", 2, is_dir=False)

        self.btn_run_compare = ctk.CTkButton(self.tab_tools, text="▶ Run Compare", fg_color="#1f538d", command=lambda: self.start_process("compare"))
        self.btn_run_compare.grid(row=3, column=1, padx=10, pady=10, sticky="w")

        frame_line = ctk.CTkFrame(self.tab_tools, height=2, fg_color="gray")
        frame_line.grid(row=4, column=0, columnspan=3, sticky="ew", padx=10, pady=15)

        ctk.CTkLabel(self.tab_tools, text="Additional Tools", font=("Arial", 14, "bold")).grid(row=5, column=0, columnspan=3, padx=10, pady=(5, 5), sticky="w")
        self.btn_run_analyzer = ctk.CTkButton(self.tab_tools, text="📊 Launch Flickercheck UI", command=self.launch_analyzer, fg_color="#4b0082", hover_color="#300052")
        self.btn_run_analyzer.grid(row=6, column=1, padx=10, pady=10, sticky="w")

    def build_processed_tab(self):
        top = ctk.CTkFrame(self.tab_processed)
        top.pack(fill="x", padx=10, pady=10)

        self.processed_path_label = ctk.CTkLabel(top, text="watcher_processed.txt: -", anchor="w", justify="left")
        self.processed_path_label.pack(fill="x", padx=10, pady=(10, 5))

        btn_row = ctk.CTkFrame(top, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(btn_row, text="🔄 Reload", width=110, command=self.load_processed_log).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="💾 Save", width=110, fg_color="green", hover_color="darkgreen", command=self.save_processed_log).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="🧹 Remove Duplicates", width=150, command=self.deduplicate_processed_log).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="🛠 Fix Corrupted Line", width=150, command=self.fix_corrupted_processed_log).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="📂 Open External", width=120, command=self.open_processed_log_external).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="❌ Clear All", width=110, fg_color="#8b1e1e", hover_color="#5f1212", command=self.clear_processed_log).pack(side="left", padx=5)

        hint = (
            "Here you can safely edit watcher_processed.txt. "
            "One filename per line. Save from the GUI to normalize line endings and reduce loop issues."
        )
        ctk.CTkLabel(self.tab_processed, text=hint, text_color="gray", anchor="w", justify="left").pack(fill="x", padx=20, pady=(0, 8))

        self.processed_text = ctk.CTkTextbox(self.tab_processed, wrap="none")
        self.processed_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def launch_analyzer(self):
        base = self.base_dir
        exe_path = os.path.join(base, "flickercheck_ui.exe")
        py_path = os.path.join(base, "flickercheck_ui.py")
        vid_source = self.entry_manual_source.get()
        vid_df = self.entry_manual_df.get()

        if not os.path.isfile(vid_source) or not os.path.isfile(vid_df):
            self.write_log("\n[ERROR] Please select both valid video files first to run the Flickercheck UI.\n")
            return

        if os.path.isfile(exe_path):
            self.write_log(f"\n[SYSTEM] Launching Flickercheck UI (exe)...\nSource: {vid_source}\nDeepfake: {vid_df}\n")
            subprocess.Popen([exe_path, vid_source, vid_df], cwd=base)
        elif os.path.isfile(py_path):
            self.write_log(f"\n[SYSTEM] Launching Flickercheck UI (Python)...\nSource: {vid_source}\nDeepfake: {vid_df}\n")
            subprocess.Popen([sys.executable, py_path, vid_source, vid_df], cwd=base)
        else:
            self.write_log(
                f"\n[ERROR] Neither flickercheck_ui.exe nor flickercheck_ui.py found in:\n{base}\n"
            )

    def show_regex_info(self):
        msg = (
            "RegEx (Regular Expressions) allow complex filtering rules.\n\n"
            "Explanation of the default pattern:\n"
            "^\\d{6,} = Filename starts with at least 6 digits\n"
            "_(pro|hyb|exp) = Followed by '_pro', '_hyb', or '_exp'\n"
            "(_p)? = Optionally followed by '_p'\n\n"
            "If you don't need this complex filtering, simply clear the text field."
        )
        messagebox.showinfo("RegEx Pattern Info", msg)

    def ensure_compare_defaults(self, config_c):
        if not config_c.has_section('PATHS'):
            config_c.add_section('PATHS')
        if not config_c.has_section('SETTINGS'):
            config_c.add_section('SETTINGS')

        defaults_settings = {
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
            'davinci_render_timeout_seconds': '1800',
            'davinci_startup_wait_seconds': '20'
        }

        defaults_paths = {
            'davinci_api_path': r'C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules',
            'davinci_exe_path': r'C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe',
            'final_export_dir': ''
        }

        changed = False
        for key, value in defaults_settings.items():
            if not config_c.has_option('SETTINGS', key):
                config_c.set('SETTINGS', key, value)
                changed = True
        for key, value in defaults_paths.items():
            if not config_c.has_option('PATHS', key):
                config_c.set('PATHS', key, value)
                changed = True
        return changed

    def load_configs(self):
        config_c = configparser.ConfigParser()
        config_c.read(self.settings_file)

        changed = self.ensure_compare_defaults(config_c)
        if changed:
            with open(self.settings_file, 'w') as f:
                config_c.write(f)

        self.entry_export_dir.insert(0, config_c.get('PATHS', 'final_export_dir', fallback=''))
        self.entry_davinci_api_path.insert(0, config_c.get('PATHS', 'davinci_api_path', fallback=r'C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules'))
        self.entry_davinci_exe_path.insert(0, config_c.get('PATHS', 'davinci_exe_path', fallback=r'C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe'))
        self.entry_davinci_startup_wait.insert(0, config_c.get('SETTINGS', 'davinci_startup_wait_seconds', fallback='20'))
        self.entry_davinci_timeout.insert(0, config_c.get('SETTINGS', 'davinci_render_timeout_seconds', fallback='1800'))
        self.combo_lang.set(config_c.get('SETTINGS', 'language', fallback='en'))
        self.var_davinci.set(config_c.get('SETTINGS', 'enable_davinci_export', fallback='0'))
        self.var_edl_auto.set(config_c.get('SETTINGS', 'enable_autodelete_edl', fallback='1'))
        self.var_edl_full.set(config_c.get('SETTINGS', 'enable_fullcheck_edl', fallback='0'))
        self.var_ffmpeg.set(config_c.get('SETTINGS', 'enable_ffmpeg_export', fallback='0'))
        self.combo_codec.set(config_c.get('SETTINGS', 'ffmpeg_encoder', fallback='nvidia_h264'))
        self.combo_target.set(config_c.get('SETTINGS', 'ffmpeg_export_target', fallback='both'))
        self.entry_buffer_seconds.insert(0, config_c.get('SETTINGS', 'buffer_seconds', fallback='2.0'))
        self.entry_pixel_noise.insert(0, config_c.get('SETTINGS', 'pixel_noise_threshold', fallback='15'))
        self.entry_changed_pixels.insert(0, config_c.get('SETTINGS', 'changed_pixels_threshold', fallback='200'))

        config_w = configparser.ConfigParser()
        config_w.read(self.watcher_file)

        if not config_w.has_section('PATHS'):
            config_w.add_section('PATHS')
        if not config_w.has_section('SETTINGS'):
            config_w.add_section('SETTINGS')
        if not config_w.has_section('MATCHING'):
            config_w.add_section('MATCHING')

        self.entry_source_dir.insert(0, config_w.get('PATHS', 'source_dir', fallback=''))
        self.entry_df_dir.insert(0, config_w.get('PATHS', 'deepfake_dir', fallback=''))
        self.entry_ignore_suffix.insert(0, config_w.get('MATCHING', 'ignore_suffix', fallback='_p'))
        self.entry_ignore_pattern.insert(0, config_w.get('MATCHING', 'ignore_temp_pattern', fallback=r'^\d{6,}_(pro|hyb|exp)(_p)?'))

        self.update_processed_log_path_label()

    def save_configs(self):
        config_c = configparser.ConfigParser()
        if os.path.exists(self.settings_file):
            config_c.read(self.settings_file)
        self.ensure_compare_defaults(config_c)

        config_c.set('PATHS', 'final_export_dir', self.entry_export_dir.get())
        config_c.set('PATHS', 'davinci_api_path', self.entry_davinci_api_path.get())
        config_c.set('PATHS', 'davinci_exe_path', self.entry_davinci_exe_path.get())
        config_c.set('SETTINGS', 'language', self.combo_lang.get())
        config_c.set('SETTINGS', 'enable_davinci_export', self.var_davinci.get())
        config_c.set('SETTINGS', 'enable_autodelete_edl', self.var_edl_auto.get())
        config_c.set('SETTINGS', 'enable_fullcheck_edl', self.var_edl_full.get())
        config_c.set('SETTINGS', 'enable_ffmpeg_export', self.var_ffmpeg.get())
        config_c.set('SETTINGS', 'ffmpeg_encoder', self.combo_codec.get())
        config_c.set('SETTINGS', 'ffmpeg_export_target', self.combo_target.get())
        config_c.set('SETTINGS', 'buffer_seconds', self.entry_buffer_seconds.get())
        config_c.set('SETTINGS', 'pixel_noise_threshold', self.entry_pixel_noise.get())
        config_c.set('SETTINGS', 'changed_pixels_threshold', self.entry_changed_pixels.get())
        config_c.set('SETTINGS', 'davinci_render_timeout_seconds', self.entry_davinci_timeout.get())
        config_c.set('SETTINGS', 'davinci_startup_wait_seconds', self.entry_davinci_startup_wait.get())
        with open(self.settings_file, 'w') as f:
            config_c.write(f)

        config_w = configparser.ConfigParser()
        if os.path.exists(self.watcher_file):
            config_w.read(self.watcher_file)
        if not config_w.has_section('PATHS'):
            config_w.add_section('PATHS')
        if not config_w.has_section('SETTINGS'):
            config_w.add_section('SETTINGS')
        if not config_w.has_section('MATCHING'):
            config_w.add_section('MATCHING')

        config_w.set('PATHS', 'source_dir', self.entry_source_dir.get())
        config_w.set('PATHS', 'deepfake_dir', self.entry_df_dir.get())
        config_w.set('PATHS', 'resolve_exe_path', self.entry_davinci_exe_path.get())
        config_w.set('SETTINGS', 'language', self.combo_lang.get())
        config_w.set('MATCHING', 'ignore_suffix', self.entry_ignore_suffix.get())
        config_w.set('MATCHING', 'ignore_temp_pattern', self.entry_ignore_pattern.get())
        with open(self.watcher_file, 'w') as f:
            config_w.write(f)

        self.update_processed_log_path_label()
        self.write_log("[INFO] Settings saved successfully.\n")

    def get_processed_log_path(self):
        deepfake_dir = self.entry_df_dir.get().strip()
        if not deepfake_dir:
            return None
        return os.path.join(deepfake_dir, 'watcher_processed.txt')

    def update_processed_log_path_label(self):
        path = self.get_processed_log_path()
        if not path:
            self.processed_path_label.configure(text="watcher_processed.txt: no deepfake folder set")
            return
        self.processed_path_label.configure(text=f"watcher_processed.txt: {path}")

    def load_processed_log(self):
        self.update_processed_log_path_label()
        path = self.get_processed_log_path()
        self.processed_text.delete("1.0", "end")

        if not path:
            self.processed_text.insert("1.0", "Set a Deepfake Folder first.\n")
            return

        if not os.path.exists(path):
            self.processed_text.insert("1.0", "")
            self.write_log(f"[INFO] Processed log does not exist yet: {path}\n")
            return

        try:
            with open(path, 'r', encoding='utf-8-sig', errors='replace') as f:
                content = f.read()
            self.processed_text.insert("1.0", content)
            self.write_log(f"[INFO] Loaded processed log: {path}\n")
        except Exception as e:
            self.write_log(f"[ERROR] Could not load processed log: {e}\n")

    def normalize_processed_lines(self, text):
        lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        cleaned = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            cleaned.append(line)
        return cleaned

    def save_processed_log(self):
        path = self.get_processed_log_path()
        if not path:
            self.write_log("[ERROR] No Deepfake Folder set. Cannot save watcher_processed.txt.\n")
            return

        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            text = self.processed_text.get("1.0", "end")
            lines = self.normalize_processed_lines(text)
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                for line in lines:
                    f.write(line + '\n')
            self.processed_text.delete("1.0", "end")
            self.processed_text.insert("1.0", '\n'.join(lines) + ('\n' if lines else ''))
            self.write_log(f"[INFO] Saved processed log safely: {path}\n")
        except Exception as e:
            self.write_log(f"[ERROR] Could not save processed log: {e}\n")

    def deduplicate_processed_log(self):
        text = self.processed_text.get("1.0", "end")
        lines = self.normalize_processed_lines(text)
        unique = []
        seen = set()
        removed = 0
        for line in lines:
            key = line.lower()
            if key in seen:
                removed += 1
                continue
            seen.add(key)
            unique.append(line)

        self.processed_text.delete("1.0", "end")
        self.processed_text.insert("1.0", '\n'.join(unique) + ('\n' if unique else ''))
        self.write_log(f"[INFO] Removed {removed} duplicate entr{'y' if removed == 1 else 'ies'} from watcher_processed.txt editor.\n")

    def fix_corrupted_processed_log(self):
        text = self.processed_text.get("1.0", "end")
        lines = self.normalize_processed_lines(text)
        fixed = []
        repairs = 0
        video_exts = ['.mp4', '.mov', '.avi', '.mkv']

        for line in lines:
            original = line
            split_done = False
            lower = line.lower()
            positions = []
            for ext in video_exts:
                start = 0
                while True:
                    idx = lower.find(ext, start)
                    if idx == -1:
                        break
                    positions.append((idx, idx + len(ext)))
                    start = idx + len(ext)
            positions.sort()

            if len(positions) > 1:
                parts = []
                prev = 0
                for _, end in positions:
                    part = line[prev:end].strip()
                    if part:
                        parts.append(part)
                    prev = end
                if len(parts) > 1:
                    fixed.extend(parts)
                    repairs += 1
                    split_done = True

            if not split_done:
                fixed.append(original)

        self.processed_text.delete("1.0", "end")
        self.processed_text.insert("1.0", '\n'.join(fixed) + ('\n' if fixed else ''))
        self.write_log(f"[INFO] Repaired {repairs} suspicious concatenated line(s) in watcher_processed.txt editor.\n")

    def clear_processed_log(self):
        answer = messagebox.askyesno("Clear watcher_processed.txt", "Do you really want to clear all processed entries?")
        if not answer:
            return
        self.processed_text.delete("1.0", "end")
        self.write_log("[INFO] Processed log editor cleared. Click Save to write the empty file.\n")

    def open_processed_log_external(self):
        path = self.get_processed_log_path()
        if not path:
            self.write_log("[ERROR] No Deepfake Folder set.\n")
            return

        try:
            if not os.path.exists(path):
                with open(path, 'w', encoding='utf-8') as f:
                    f.write('')
            os.startfile(path)
            self.write_log(f"[INFO] Opened processed log externally: {path}\n")
        except Exception as e:
            self.write_log(f"[ERROR] Could not open processed log externally: {e}\n")

    def write_log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert(ctk.END, text)
        self.log_box.see(ctk.END)
        self.log_box.configure(state="disabled")

    def is_davinci_process_running(self):
        try:
            result = subprocess.run(['tasklist'], capture_output=True, text=True, creationflags=0x08000000)
            output = (result.stdout or '').lower()
            return 'resolve.exe' in output or 'davinci resolve' in output
        except Exception:
            return False

    def ensure_davinci_running(self):
        if self.var_davinci.get() != "1":
            return True
        if self.is_davinci_process_running():
            self.write_log("[INFO] DaVinci Resolve is already running.\n")
            return True

        exe_path = self.entry_davinci_exe_path.get().strip()
        if not exe_path:
            self.write_log("[ERROR] DaVinci export is enabled, but no Resolve.exe path is set.\n")
            return False
        if not os.path.isfile(exe_path):
            self.write_log(f"[ERROR] Resolve.exe not found: {exe_path}\n")
            return False

        try:
            wait_seconds = int(float(self.entry_davinci_startup_wait.get().strip() or "20"))
        except Exception:
            wait_seconds = 20

        self.write_log(f"[SYSTEM] DaVinci is not running. Starting Resolve...\n{exe_path}\n")
        try:
            subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
        except Exception as e:
            self.write_log(f"[ERROR] Could not start Resolve.exe: {e}\n")
            return False

        self.write_log(f"[INFO] Waiting {wait_seconds} seconds for DaVinci startup...\n")
        time.sleep(max(0, wait_seconds))

        if self.is_davinci_process_running():
            self.write_log("[INFO] DaVinci Resolve started successfully.\n")
            return True

        self.write_log("[WARNING] Resolve.exe was started, but no running DaVinci process was detected yet. Compare will continue and will do the final API check.\n")
        return True

    def start_process(self, process_type):
        self.save_configs()
        self.btn_start.configure(state="disabled")
        self.btn_run_compare.configure(state="disabled")
        self.btn_stop.configure(state="normal")

        if process_type == "watcher":
            self.status_label.configure(text="🟢 Watcher Active", text_color="lightgreen")
            self.write_log("\n[SYSTEM] Starting Watcher...\n")
            threading.Thread(target=self.run_tool, args=("watcher.exe", []), daemon=True).start()

        elif process_type == "compare":
            vid_source = self.entry_manual_source.get()
            vid_df = self.entry_manual_df.get()

            if not os.path.isfile(vid_source) or not os.path.isfile(vid_df):
                self.write_log("\n[ERROR] Please select both valid video files first.\n")
                self.reset_ui()
                return

            if self.var_davinci.get() == "1":
                self.status_label.configure(text="🔵 Preparing DaVinci", text_color="lightblue")
                if not self.ensure_davinci_running():
                    self.reset_ui()
                    return

            self.status_label.configure(text="🟡 Compare Running", text_color="yellow")
            self.write_log(f"\n[SYSTEM] Starting Manual Compare...\nSource: {vid_source}\nDeepfake: {vid_df}\n")
            threading.Thread(target=self.run_tool, args=("compare.exe", [vid_source, vid_df]), daemon=True).start()

    def run_tool(self, exe_name, args_list):
        """Prefer .exe next to gui; fallback to python *.py (src folder without exes)."""
        base = self.base_dir
        exe_path = os.path.join(base, exe_name)
        py_name = exe_name[:-4] + ".py" if exe_name.lower().endswith(".exe") else exe_name
        py_path = os.path.join(base, py_name)

        if os.path.isfile(exe_path):
            cmd = [exe_path] + args_list
            label = exe_name
        elif os.path.isfile(py_path):
            cmd = [sys.executable, py_path] + args_list
            label = py_name
        else:
            self.after(
                0,
                self.write_log,
                f"\n[ERROR] Could not find {exe_name} or {py_name} in:\n{base}\n",
            )
            self.after(0, self.reset_ui)
            return

        create_no_window = 0x08000000
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=create_no_window,
                cwd=base,
            )
            self.current_process = process
            for line in process.stdout:
                self.after(0, self.write_log, line)
            process.wait()
            self.after(0, self.write_log, f"\n[SYSTEM] {label} stopped.\n")
        except FileNotFoundError:
            self.after(0, self.write_log, f"\n[ERROR] Could not run: {cmd[0]}\n")
        except Exception as e:
            self.after(0, self.write_log, f"\n[ERROR] Process failed: {e}\n")
        finally:
            self.current_process = None
            self.after(0, self.reset_ui)

    def reset_ui(self):
        self.btn_start.configure(state="normal")
        self.btn_run_compare.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.status_label.configure(text="🔴 Stopped", text_color="white")

    def stop_active_process(self):
        if self.current_process:
            self.write_log("\n[SYSTEM] Force stopping process...\n")
            try:
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.current_process.pid)], creationflags=0x08000000)
            except Exception:
                pass


if __name__ == "__main__":
    app = MasterGUI()
    app.mainloop()
