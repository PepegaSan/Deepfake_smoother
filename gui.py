import customtkinter as ctk
import configparser
import os
import sys
import tkinter as tk
import subprocess
import threading
import time
from tkinter import filedialog, messagebox

from theme_palette import PALETTE_DARK, PALETTE_LIGHT, load_ui_theme_is_light

ctk.set_default_color_theme("blue")

BTN_RADIUS = 10
BTN_HEIGHT = 40
BTN_HEIGHT_BAR = 42
BTN_HEIGHT_COMPACT = 36
FONT_BTN = ("Segoe UI Black", 10)
FONT_APP_TITLE = ("Segoe UI Black", 18)  # same face as buttons; larger for top bar
FONT_BTN_NAV = ("Segoe UI Semibold", 10)
FONT_UI = ("Segoe UI", 13)
FONT_UI_SM = ("Segoe UI", 11)
FONT_SECTION = ("Segoe UI Semibold", 15)
FONT_HINT = ("Segoe UI", 11)


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


class MasterGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.base_dir = get_base_dir()
        self.settings_file = os.path.join(self.base_dir, "settings.ini")
        self.watcher_file = os.path.join(self.base_dir, "watcher_settings.ini")

        self._tkdnd_ready = False
        try:
            from tkinterdnd2 import TkinterDnD

            TkinterDnD._require(self)
            self._tkdnd_ready = True
        except Exception:
            pass

        self._manual_compare_zone_parts = []
        # Manual compare paths: must use StringVar — CTkEntry.get() can lie while _placeholder_text_active is True.
        self._var_manual_source = tk.StringVar(value="")
        self._var_manual_df = tk.StringVar(value="")

        # DaVinci paths / timeouts (UI lives in gear ⚙ options; values always in memory for save/compare)
        self._var_davinci_api_path = tk.StringVar(value="")
        self._var_davinci_exe_path = tk.StringVar(value="")
        self._var_davinci_startup_wait = tk.StringVar(value="20")
        self._var_davinci_render_timeout = tk.StringVar(value="1800")
        self._options_davinci_section_built = False
        self._davinci_option_entries = []
        self._opt_davinci_folded = True
        self._btn_opt_davinci_fold = None
        self._frame_opt_davinci_body = None

        self._theme_is_light = load_ui_theme_is_light(self.settings_file)
        self._pal = dict(PALETTE_LIGHT if self._theme_is_light else PALETTE_DARK)
        ctk.set_appearance_mode("Light" if self._theme_is_light else "Dark")

        self._nav_key = "main"
        self._section_shells = []
        self._muted_labels = []
        self._browse_buttons = []
        self._options_win = None
        self._options_syncing = False

        self.title("AutoCut Control Center")
        # Log panel: fixed height at bottom; window grows downward only (no stealing space from body).
        self._geom_compact = "1140x720"
        self._log_panel_text_h = 160
        self._log_window_extra = self._log_panel_text_h + 28  # textbox + bottom pady + border/chrome
        w0, h0 = 1140, 720
        self._geom_with_log = f"{w0}x{h0 + self._log_window_extra}"
        self.geometry(self._geom_with_log)
        self.minsize(920, 640)
        self.configure(fg_color=self._pal["bg"])

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # —— Top bar ——
        self.frame_top = ctk.CTkFrame(self, fg_color=self._pal["panel"], corner_radius=0, height=56)
        self.frame_top.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.frame_top.grid_columnconfigure(1, weight=1)
        self.frame_top.grid_propagate(False)

        self.lbl_app_title = ctk.CTkLabel(
            self.frame_top, text="AutoCut Control Center", font=FONT_APP_TITLE, text_color=self._pal["text"],
        )
        self.lbl_app_title.grid(row=0, column=0, padx=(20, 12), pady=12, sticky="w")

        self.btn_options = ctk.CTkButton(
            self.frame_top,
            text="⚙",
            command=self._toggle_options_popup,
            **self._gear_button_kw(),
        )
        self.btn_options.grid(row=0, column=2, padx=(8, 20), pady=8, sticky="e")

        # —— Body: sidebar + content ——
        self.frame_body = ctk.CTkFrame(self, fg_color=self._pal["bg"])
        self.frame_body.grid(row=1, column=0, sticky="nsew", padx=14, pady=(10, 6))
        self.frame_body.grid_columnconfigure(1, weight=1)
        self.frame_body.grid_rowconfigure(0, weight=1)

        self.frame_sidebar = ctk.CTkFrame(
            self.frame_body, width=216, fg_color=self._pal["panel"], corner_radius=14, border_width=1, border_color=self._pal["border"],
        )
        self.frame_sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 12), pady=0)
        self.frame_sidebar.grid_propagate(False)

        self.frame_content = ctk.CTkFrame(
            self.frame_body, fg_color=self._pal["panel"], corner_radius=14, border_width=1, border_color=self._pal["border"],
        )
        self.frame_content.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.frame_content.grid_rowconfigure(0, weight=1)
        self.frame_content.grid_columnconfigure(0, weight=1)

        self.content_scroll = ctk.CTkScrollableFrame(
            self.frame_content,
            fg_color=self._pal["panel"],
            corner_radius=0,
            scrollbar_fg_color=self._pal["panel_elev"],
            scrollbar_button_color=self._pal["border"],
            scrollbar_button_hover_color=self._pal["cyan_dim"],
        )
        self.content_scroll.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.content_scroll.grid_columnconfigure(0, weight=1)

        self.panel_main = ctk.CTkFrame(self.content_scroll, fg_color=self._pal["panel"])
        self.panel_export = ctk.CTkFrame(self.content_scroll, fg_color=self._pal["panel"])
        self.panel_filter = ctk.CTkFrame(self.content_scroll, fg_color=self._pal["panel"])
        self.panel_tools = ctk.CTkFrame(self.content_scroll, fg_color=self._pal["panel"])
        self.panel_processed = ctk.CTkFrame(self.content_scroll, fg_color=self._pal["panel"])
        self.panels = {
            "main": self.panel_main,
            "export": self.panel_export,
            "filter": self.panel_filter,
            "tools": self.panel_tools,
            "processed": self.panel_processed,
        }
        self.nav_buttons = {}

        nav_items = [
            ("WATCHER", "main"),
            ("TOOLS", "tools"),
            ("FILTER", "filter"),
            ("EXPORT", "export"),
            ("WATCHER LOGS", "processed"),
        ]
        for text, key in nav_items:
            self.nav_buttons[key] = self._nav_button(text, key)

        self.build_main_tab()
        self.build_export_tab()
        self.build_filter_tab()
        self.build_tools_tab()
        self.build_processed_tab()

        self.select_panel("main")

        self.current_process = None

        # —— Bottom action bar ——
        self.frame_bottom = ctk.CTkFrame(
            self, fg_color=self._pal["panel"], corner_radius=12, border_width=1, border_color=self._pal["border"],
        )
        self.frame_bottom.grid(row=2, column=0, sticky="ew", padx=14, pady=(4, 6))

        self.btn_save = ctk.CTkButton(
            self.frame_bottom,
            text="💾 SAVE SETTINGS",
            command=self.save_configs,
            **self._button_kw("success", height=BTN_HEIGHT_BAR),
        )
        self.btn_save.pack(side="left", padx=12, pady=12)

        self.status_label = ctk.CTkLabel(
            self.frame_bottom, text="🔴 Stopped", font=("Segoe UI Semibold", 14), text_color=self._pal["text"],
        )
        self.status_label.pack(side="left", padx=16)

        self.btn_stop = ctk.CTkButton(
            self.frame_bottom,
            text="⏹ STOP",
            width=100,
            state="disabled",
            command=self.stop_active_process,
            **self._button_kw("stop", height=BTN_HEIGHT_BAR),
        )
        self.btn_stop.pack(side="right", padx=(6, 12), pady=12)

        self.btn_start = ctk.CTkButton(
            self.frame_bottom,
            text="▶ START WATCHER",
            width=200,
            command=lambda: self.start_process("watcher"),
            **self._button_kw("primary_emphasis", height=BTN_HEIGHT_BAR),
        )
        self.btn_start.pack(side="right", padx=(12, 6), pady=12)

        self.log_visible = True
        self.var_hide_log = ctk.StringVar(value="0")

        self.log_box = ctk.CTkTextbox(
            self,
            height=self._log_panel_text_h,
            state="disabled",
            font=("Consolas", 12),
            fg_color=self._pal["panel_elev"],
            border_color=self._pal["border"],
            text_color=self._pal["text"],
        )
        self.log_box.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 12))
        self.grid_rowconfigure(3, weight=0)

        self.load_configs()
        self.toggle_ffmpeg_options()
        self.load_processed_log()

    def _entry_kw(self):
        return dict(
            height=36,
            corner_radius=8,
            border_width=1,
            fg_color=self._pal["panel_elev"],
            border_color=self._pal["border"],
            text_color=self._pal["text"],
            font=FONT_UI,
            placeholder_text_color=self._pal["muted"],
        )

    def _set_manual_video_entry(self, path_var: tk.StringVar, entry, raw):
        """Set manual-compare path via StringVar (reliable); keep CTkEntry placeholder state consistent."""
        s = "" if raw is None else str(raw).strip()
        if s:
            s = self._recover_nt_path_if_mojibake(s)
        ph_deact = getattr(entry, "_deactivate_placeholder", None)
        if callable(ph_deact):
            try:
                ph_deact()
            except Exception:
                pass
        path_var.set(s)
        if s:
            try:
                setattr(entry, "_placeholder_text_active", False)
            except Exception:
                pass
        else:
            ph = entry.cget("placeholder_text")
            if ph:
                entry.configure(placeholder_text=ph)

    @staticmethod
    def _manual_video_entry_nonempty(entry) -> bool:
        sv = getattr(entry, "_manual_path_var", None)
        if sv is not None:
            return bool(sv.get().strip())
        return bool(MasterGUI._ctk_entry_actual_text(entry))

    @staticmethod
    def _ctk_entry_actual_text(entry) -> str:
        """
        CTkEntry.get() returns '' while _placeholder_text_active is True, even if the inner tk.Entry
        already holds the real path (stale flag after load / focus). Read the inner widget when needed.
        """
        try:
            active = getattr(entry, "_placeholder_text_active", False)
            inner = entry._entry
            raw = inner.get()
        except Exception:
            return (entry.get() or "").strip()
        if not active:
            return (entry.get() or "").strip()
        ph = ""
        try:
            ph = entry.cget("placeholder_text") or ""
        except Exception:
            pass
        if ph and raw == ph:
            return ""
        return (raw or "").strip()

    @staticmethod
    def _apply_entry_value(entry, raw):
        """Fill a CTkEntry from disk. CTkEntry.insert('') disables placeholder until focus; empty must re-arm placeholder."""
        s = "" if raw is None else str(raw)
        stripped = s.strip()
        if stripped:
            stripped = MasterGUI._recover_nt_path_if_mojibake(stripped)
        ph_deact = getattr(entry, "_deactivate_placeholder", None)
        if callable(ph_deact):
            try:
                ph_deact()
            except Exception:
                pass
        entry.delete(0, "end")
        if stripped:
            entry.insert(0, stripped)
            try:
                setattr(entry, "_placeholder_text_active", False)
            except Exception:
                pass
        else:
            ph = entry.cget("placeholder_text")
            if ph:
                entry.configure(placeholder_text=ph)

    def _option_kw(self):
        return dict(
            height=34,
            corner_radius=8,
            fg_color=self._pal["panel_elev"],
            button_color=self._pal["cyan_dim"],
            button_hover_color=self._pal["cyan"],
            font=FONT_UI_SM,
            text_color=self._pal["text"],
            dropdown_fg_color=self._pal["panel"],
            dropdown_hover_color=self._pal["panel_elev"],
            dropdown_text_color=self._pal["text"],
        )

    def _button_kw(self, variant="ghost", *, height=BTN_HEIGHT, font=None, width=None):
        """Sticker-style buttons: thick dark rim + bold caps text; colors unchanged by variant."""
        font = font or FONT_BTN
        kw = dict(
            corner_radius=BTN_RADIUS,
            font=font,
            height=height,
            border_width=2,
            border_color=self._pal["btn_rim"],
        )
        if width is not None:
            kw["width"] = width
        if variant == "ghost":
            kw.update(
                fg_color=self._pal["panel_elev"],
                hover_color=self._pal["border"],
                text_color=self._pal["text"],
            )
        elif variant == "ghost_muted":
            kw.update(
                fg_color=self._pal["panel_elev"],
                hover_color=self._pal["border"],
                text_color=self._pal["muted"],
            )
        elif variant == "primary":
            kw.update(
                fg_color=self._pal["cyan_dim"],
                hover_color=self._pal["cyan"],
                text_color=self._pal["text"],
                border_color=self._pal["primary_border"],
            )
        elif variant == "primary_emphasis":
            kw.update(
                fg_color=self._pal["cyan_dim"],
                hover_color=self._pal["cyan"],
                text_color=self._pal["text"],
                border_color=self._pal["primary_border"],
                font=("Segoe UI Black", 11),
            )
        elif variant == "success":
            kw.update(
                fg_color="#1b5e20",
                hover_color="#2e7d32",
                text_color="#f0f0f8",
                border_color="#041208",
            )
        elif variant == "stop":
            kw.update(
                fg_color=self._pal["stop"],
                hover_color="#b71c1c",
                text_color="#ffffff",
                border_color="#1a0505",
                font=("Segoe UI Black", 11),
            )
        elif variant == "gold":
            kw.update(
                fg_color=self._pal["gold_dim"],
                hover_color=self._pal["gold"],
                text_color=self._pal["text"],
                border_color="#1f1804",
            )
        elif variant == "purple":
            kw.update(
                fg_color="#4b0082",
                hover_color="#6a0dad",
                text_color="#f0f0f8",
                border_color="#12001f",
            )
        elif variant == "danger_soft":
            kw.update(
                fg_color="#8b1e1e",
                hover_color="#5f1212",
                text_color="#f0f0f8",
                border_color="#140404",
            )
        elif variant == "icon_sq":
            kw.update(
                fg_color=self._pal["panel_elev"],
                hover_color=self._pal["border"],
                text_color=self._pal["text"],
                width=40,
                height=40,
                corner_radius=10,
                font=("Segoe UI Black", 12),
            )
        elif variant == "nav_idle":
            kw.update(
                fg_color=self._pal["panel_elev"],
                hover_color=self._pal["border"],
                text_color=self._pal["muted"],
                font=FONT_BTN_NAV,
            )
        elif variant == "nav_active":
            kw.update(
                fg_color=self._pal["cyan_dim"],
                hover_color=self._pal["cyan"],
                text_color=self._pal["text"],
                border_color=self._pal["cyan"],
                font=("Segoe UI Black", 10),
            )
        return kw

    def _gear_button_kw(self):
        kw = self._button_kw("ghost", height=40)
        kw["width"] = 44
        kw["font"] = ("Segoe UI Semibold", 20)
        return kw

    def _muted_label(self, parent, **kwargs):
        lb = ctk.CTkLabel(parent, text_color=self._pal["muted"], **kwargs)
        self._muted_labels.append(lb)
        return lb

    def _section_card(self, parent, title):
        outer = ctk.CTkFrame(
            parent,
            fg_color=self._pal["panel_elev"],
            corner_radius=12,
            border_width=1,
            border_color=self._pal["border"],
        )
        outer.pack(fill="x", pady=(0, 14), padx=2)
        hdr = ctk.CTkLabel(outer, text=title, font=FONT_SECTION, text_color=self._pal["text"], anchor="w")
        hdr.pack(fill="x", padx=14, pady=(12, 8))
        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=(0, 12))
        self._section_shells.append((outer, hdr))
        return inner

    def _nav_button(self, text, key):
        btn = ctk.CTkButton(
            self.frame_sidebar,
            text=text,
            anchor="w",
            command=lambda k=key: self.select_panel(k),
            **self._button_kw("nav_idle", height=44),
        )
        btn.pack(fill="x", padx=10, pady=5)
        return btn

    def select_panel(self, key):
        self._nav_key = key
        for k, fr in self.panels.items():
            fr.pack_forget()
        self.panels[key].pack(fill="both", expand=True, padx=4, pady=4)
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(**self._button_kw("nav_active", height=44))
            else:
                btn.configure(**self._button_kw("nav_idle", height=44))

    def _apply_theme_mode(self):
        ctk.set_appearance_mode("Light" if self._theme_is_light else "Dark")
        self._pal = dict(PALETTE_LIGHT if self._theme_is_light else PALETTE_DARK)
        self._apply_ui_palette()
        self._persist_ui_theme_to_settings()

    def _persist_ui_theme_to_settings(self):
        """Store ui_theme in settings.ini so Light/Dark survives restart."""
        config_c = configparser.ConfigParser()
        if os.path.exists(self.settings_file):
            config_c.read(self.settings_file)
        self.ensure_compare_defaults(config_c)
        if not config_c.has_section("GUI"):
            config_c.add_section("GUI")
        config_c.set("GUI", "ui_theme", "light" if self._theme_is_light else "dark")
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                config_c.write(f)
        except OSError:
            pass

    def _on_theme_segment(self, value):
        light = value == "Light"
        if light == self._theme_is_light:
            return
        self._theme_is_light = light
        self._apply_theme_mode()

    def _close_options_popup(self):
        if self._options_win is not None:
            try:
                self._options_win.destroy()
            except Exception:
                pass
            self._options_win = None
        self._options_davinci_section_built = False
        self._davinci_option_entries = []
        self._btn_opt_davinci_fold = None
        self._frame_opt_davinci_body = None

    def _toggle_options_davinci_fold(self):
        self._opt_davinci_folded = not self._opt_davinci_folded
        if self._opt_davinci_folded:
            self._frame_opt_davinci_body.pack_forget()
            self._btn_opt_davinci_fold.configure(text="▶ DaVinci Resolve — paths & timeouts")
        else:
            self._frame_opt_davinci_body.pack(fill="x", padx=10, pady=(0, 8))
            self._btn_opt_davinci_fold.configure(text="▼ DaVinci Resolve — paths & timeouts")

    def _build_options_davinci_section(self, parent):
        """Paths + timeouts once per options window (rebuilt after popup close)."""
        if self._options_davinci_section_built:
            return
        self._options_davinci_section_built = True
        self._davinci_option_entries = []

        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="x", padx=4, pady=(4, 0))

        self._btn_opt_davinci_fold = ctk.CTkButton(
            wrap,
            text="▶ DaVinci Resolve — paths & timeouts",
            anchor="w",
            command=self._toggle_options_davinci_fold,
            font=FONT_UI_SM,
            fg_color=self._pal["panel_elev"],
            hover_color=self._pal["border"],
            text_color=self._pal["text"],
            border_width=1,
            border_color=self._pal["border"],
            height=36,
            corner_radius=8,
        )
        self._btn_opt_davinci_fold.pack(fill="x", padx=4, pady=4)

        self._frame_opt_davinci_body = ctk.CTkFrame(parent, fg_color="transparent")
        self._opt_davinci_folded = True

        body = self._frame_opt_davinci_body
        self._davinci_option_entries.append(
            self.create_path_row(
                body,
                "DaVinci API path (Scripting Modules)…",
                True,
                self._var_davinci_api_path,
                track_browse=False,
            )
        )
        self._davinci_option_entries.append(
            self.create_path_row(
                body,
                "Resolve.exe path (optional, auto-start)…",
                False,
                self._var_davinci_exe_path,
                track_browse=False,
            )
        )

        row_wait = ctk.CTkFrame(body, fg_color="transparent")
        row_wait.pack(fill="x", pady=4)
        row_wait.columnconfigure(0, weight=1)
        row_wait.columnconfigure(1, weight=1)
        self.entry_davinci_startup_wait = ctk.CTkEntry(
            row_wait,
            textvariable=self._var_davinci_startup_wait,
            placeholder_text="DaVinci startup wait (seconds)…",
            **self._entry_kw(),
        )
        self.entry_davinci_startup_wait.grid(row=0, column=0, sticky="ew", padx=(4, 6))
        self.entry_davinci_timeout = ctk.CTkEntry(
            row_wait,
            textvariable=self._var_davinci_render_timeout,
            placeholder_text="DaVinci render timeout (seconds, 0 = forever)…",
            **self._entry_kw(),
        )
        self.entry_davinci_timeout.grid(row=0, column=1, sticky="ew", padx=(6, 4))
        self._davinci_option_entries.extend((self.entry_davinci_startup_wait, self.entry_davinci_timeout))

    def _toggle_options_popup(self):
        if self._options_win is not None:
            try:
                if self._options_win.winfo_exists():
                    self._close_options_popup()
                    return
            except Exception:
                self._options_win = None

        win = ctk.CTkToplevel(self)
        self._options_win = win
        win.title("Options")
        p = self._pal
        win.configure(fg_color=p["bg"])
        win.resizable(False, False)
        win.transient(self)
        win.protocol("WM_DELETE_WINDOW", self._close_options_popup)

        outer = ctk.CTkFrame(win, fg_color=p["bg"], corner_radius=0)
        outer.pack(fill="both", expand=True)
        frm = ctk.CTkFrame(
            outer,
            fg_color=p["panel"],
            corner_radius=12,
            border_width=1,
            border_color=p["border"],
        )
        frm.pack(fill="both", expand=True, padx=10, pady=10)

        scroll = ctk.CTkScrollableFrame(
            frm,
            fg_color="transparent",
            height=400,
            scrollbar_button_color=p["border"],
            scrollbar_button_hover_color=p["cyan_dim"],
        )
        scroll.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        ctk.CTkLabel(scroll, text="APPEARANCE", font=FONT_UI_SM, text_color=p["muted"], anchor="w").pack(
            fill="x", padx=6, pady=(4, 4),
        )
        seg = ctk.CTkSegmentedButton(
            scroll,
            values=["Dark", "Light"],
            command=self._on_theme_segment,
            font=FONT_UI_SM,
            fg_color=p["panel_elev"],
            selected_color=p["cyan_dim"],
            selected_hover_color=p["cyan"],
            unselected_color=p["panel_elev"],
            unselected_hover_color=p["border"],
            text_color=p["text"],
        )
        seg.pack(fill="x", padx=6, pady=(0, 10))
        seg.set("Light" if self._theme_is_light else "Dark")

        ctk.CTkCheckBox(
            scroll,
            text="Hide console log",
            variable=self.var_hide_log,
            onvalue="1",
            offvalue="0",
            command=self._on_hide_log_checkbox,
            font=FONT_UI_SM,
            text_color=p["text"],
            fg_color=p["cyan_dim"],
            hover_color=p["cyan"],
            border_color=p["border"],
        ).pack(anchor="w", padx=6, pady=(4, 8))

        self._options_syncing = True
        try:
            self.var_hide_log.set("1" if not self.log_visible else "0")
        finally:
            self._options_syncing = False

        self._build_options_davinci_section(scroll)

        ctk.CTkButton(
            frm,
            text="RESET SETTINGS",
            command=self._options_reset_clicked,
            **self._button_kw("success", height=BTN_HEIGHT),
        ).pack(fill="x", padx=14, pady=(0, 12))

        win.update_idletasks()
        bw = self.btn_options.winfo_width() or 44
        bx = self.btn_options.winfo_rootx()
        by = self.btn_options.winfo_rooty()
        ww, wh = 420, 520
        win.geometry(f"{ww}x{wh}+{bx + bw - ww}+{by + self.btn_options.winfo_height() + 8}")

    def _options_reset_clicked(self):
        self.apply_reset_settings()
        self._close_options_popup()

    def set_log_panel_visible(self, visible: bool):
        if visible == self.log_visible:
            return
        if visible:
            self.log_box.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 12))
            self.geometry(self._geom_with_log)
            self.grid_rowconfigure(3, weight=0)
        else:
            self.log_box.grid_remove()
            self.geometry(self._geom_compact)
            self.grid_rowconfigure(3, weight=0)
        self.log_visible = visible
        self._options_syncing = True
        try:
            self.var_hide_log.set("1" if not visible else "0")
        finally:
            self._options_syncing = False

    def _on_hide_log_checkbox(self):
        if self._options_syncing:
            return
        hide = self.var_hide_log.get() == "1"
        self.set_log_panel_visible(not hide)

    def _apply_ui_palette(self):
        """Re-apply self._pal to all explicitly themed widgets (entries, chrome, nav, etc.)."""
        p = self._pal
        self.configure(fg_color=p["bg"])
        self.frame_top.configure(fg_color=p["panel"])
        self.lbl_app_title.configure(text_color=p["text"])
        self.btn_options.configure(**self._gear_button_kw())
        self.frame_body.configure(fg_color=p["bg"])
        self.frame_sidebar.configure(fg_color=p["panel"], border_color=p["border"])
        self.frame_content.configure(fg_color=p["panel"], border_color=p["border"])
        self.content_scroll.configure(
            fg_color=p["panel"],
            scrollbar_fg_color=p["panel_elev"],
            scrollbar_button_color=p["border"],
            scrollbar_button_hover_color=p["cyan_dim"],
        )
        for pan in self.panels.values():
            pan.configure(fg_color=p["panel"])
        self.frame_bottom.configure(fg_color=p["panel"], border_color=p["border"])
        self.status_label.configure(text_color=p["text"])
        self.log_box.configure(fg_color=p["panel_elev"], border_color=p["border"], text_color=p["text"])
        self.btn_save.configure(**self._button_kw("success", height=BTN_HEIGHT_BAR))
        self.btn_stop.configure(**self._button_kw("stop", height=BTN_HEIGHT_BAR))
        self.btn_start.configure(**self._button_kw("primary_emphasis", height=BTN_HEIGHT_BAR))

        for k, btn in self.nav_buttons.items():
            btn.configure(**self._button_kw("nav_active" if k == self._nav_key else "nav_idle", height=44))

        for outer, hdr in self._section_shells:
            outer.configure(fg_color=p["panel_elev"], border_color=p["border"])
            hdr.configure(text_color=p["text"])

        for lb in self._muted_labels:
            lb.configure(text_color=p["muted"])

        for e in self._all_entries():
            e.configure(**self._entry_kw())
            ph = e.cget("placeholder_text")
            if ph:
                e.configure(placeholder_text=ph)

        for ob in (self.combo_lang, self.combo_codec, self.combo_target):
            ob.configure(**self._option_kw())

        cb_kw = dict(
            fg_color=p["cyan_dim"],
            hover_color=p["cyan"],
            text_color=p["text"],
            border_color=p["border"],
        )
        self.cb_afk_watcher.configure(**cb_kw)
        self.cb_davinci_export.configure(**cb_kw)
        self.cb_edl_auto.configure(**cb_kw)
        self.cb_edl_full.configure(**cb_kw)
        self.cb_ffmpeg_export.configure(**cb_kw)
        self.cb_export_unique.configure(**cb_kw)

        for b in self._browse_buttons:
            b.configure(**self._button_kw("ghost", height=BTN_HEIGHT_COMPACT))

        for e in getattr(self, "_davinci_option_entries", ()) or ():
            try:
                e.configure(**self._entry_kw())
                ph = e.cget("placeholder_text")
                if ph:
                    e.configure(placeholder_text=ph)
            except Exception:
                pass
        btn_fold = getattr(self, "_btn_opt_davinci_fold", None)
        if btn_fold is not None:
            try:
                btn_fold.configure(
                    fg_color=p["panel_elev"],
                    hover_color=p["border"],
                    text_color=p["text"],
                    border_color=p["border"],
                )
            except Exception:
                pass

        self.btn_run_compare.configure(**self._button_kw("primary_emphasis", height=44))
        self.btn_run_analyzer.configure(**self._button_kw("primary_emphasis", height=44))
        self.sep_tools.configure(fg_color=p["border"])

        self.btn_proc_reload.configure(**self._button_kw("ghost", height=BTN_HEIGHT_COMPACT))
        self.btn_proc_save.configure(**self._button_kw("success", height=BTN_HEIGHT_COMPACT))
        self.btn_proc_dedupe.configure(**self._button_kw("ghost", height=BTN_HEIGHT_COMPACT))
        self.btn_proc_fixln.configure(**self._button_kw("ghost", height=BTN_HEIGHT_COMPACT))
        self.btn_proc_open.configure(**self._button_kw("ghost", height=BTN_HEIGHT_COMPACT))
        self.btn_proc_clear.configure(**self._button_kw("danger_soft", height=BTN_HEIGHT_COMPACT))
        self.btn_regex_help.configure(**self._button_kw("icon_sq"))

        self.processed_text.configure(fg_color=p["panel_elev"], border_color=p["border"], text_color=p["text"])

        for part in self._manual_compare_zone_parts:
            try:
                part["outer"].configure(fg_color=p["panel_elev"], border_color=p["cyan_dim"])
                part["icon"].configure(text_color=p["cyan"])
                part["head"].configure(text_color=p["text"])
                part["sub"].configure(text_color=p["muted"])
            except Exception:
                pass

        st = self.status_label.cget("text")
        if st.startswith("🔴"):
            self.status_label.configure(text_color=p["text"])
        elif st.startswith("🔵"):
            self.status_label.configure(text_color=p["cyan"])

    def _all_entries(self):
        return (
            self.entry_source_dir,
            self.entry_df_dir,
            self.entry_export_dir,
            self.entry_wait_seconds,
            self.entry_watcher_compare_timeout,
            self.entry_match_prefix,
            self.entry_ignore_suffix,
            self.entry_ignore_pattern,
            self.entry_buffer_seconds,
            self.entry_pixel_noise,
            self.entry_changed_pixels,
            self.entry_manual_source,
            self.entry_manual_df,
        )

    def apply_reset_settings(self):
        """Reset all Control Center fields to the same defaults as a first run (missing INI keys / built-in fallbacks)."""
        api = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"
        resolve = r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe"
        pat = r"^\d{6,}_(pro|hyb|exp)(_p)?"

        self._apply_entry_value(self.entry_export_dir, "")
        self._var_davinci_api_path.set(api)
        self._var_davinci_exe_path.set(resolve)
        self._var_davinci_startup_wait.set("20")
        self._var_davinci_render_timeout.set("1800")
        self.combo_lang.set("en")
        self.var_davinci.set("0")
        self.var_edl_auto.set("1")
        self.var_edl_full.set("0")
        self.var_ffmpeg.set("0")
        self.var_export_unique.set("0")
        self.combo_codec.set("nvidia_h264")
        self.combo_target.set("both")
        self._apply_entry_value(self.entry_buffer_seconds, "2.0")
        self._apply_entry_value(self.entry_pixel_noise, "15")
        self._apply_entry_value(self.entry_changed_pixels, "200")
        self._set_manual_video_entry(self._var_manual_source, self.entry_manual_source, "")
        self._set_manual_video_entry(self._var_manual_df, self.entry_manual_df, "")

        self._apply_entry_value(self.entry_source_dir, "")
        self._apply_entry_value(self.entry_df_dir, "")
        self._apply_entry_value(self.entry_wait_seconds, "30")
        self._apply_entry_value(self.entry_watcher_compare_timeout, "1800")
        self._apply_entry_value(self.entry_match_prefix, "10")
        self.var_afk_watcher.set("1")
        self._apply_entry_value(self.entry_ignore_suffix, "_p")
        self._apply_entry_value(self.entry_ignore_pattern, pat)

        self.toggle_ffmpeg_options()
        self.load_processed_log()
        self._theme_is_light = False
        self._apply_theme_mode()
        self.write_log(
            "[INFO] Reset settings applied (first-start defaults in the UI; theme saved. "
            "Use Save for watcher paths and any remaining settings.ini / watcher_settings.ini fields.)\n"
        )

    def toggle_ffmpeg_options(self, *args):
        state = "normal" if self.var_ffmpeg.get() == "1" else "disabled"
        self.combo_codec.configure(state=state)
        self.combo_target.configure(state=state)

    def create_path_row(self, parent, placeholder, is_dir=True, strvar=None, track_browse=True):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=6)
        row.columnconfigure(0, weight=1)
        kw = dict(self._entry_kw())
        if strvar is not None:
            kw["textvariable"] = strvar
        entry = ctk.CTkEntry(row, placeholder_text=placeholder, **kw)
        entry.grid(row=0, column=0, sticky="ew", padx=(4, 8))
        btn = ctk.CTkButton(
            row,
            text="BROWSE",
            width=100,
            command=lambda e=entry, d=is_dir, sv=strvar: self.browse_path(e, d, sv),
            **self._button_kw("ghost", height=BTN_HEIGHT_COMPACT),
        )
        btn.grid(row=0, column=1, padx=(0, 4))
        if track_browse:
            self._browse_buttons.append(btn)
        return entry

    _MANUAL_VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v")

    @staticmethod
    def _try_mojibake_decode_step(cur: str):
        """One UTF-8-as-wrong-codepage reversal (common Tcl/DnD mojibake on Windows)."""
        for enc in ("latin-1", "cp1252"):
            try:
                nxt = os.path.normpath(cur.encode(enc).decode("utf-8"))
            except (UnicodeDecodeError, UnicodeEncodeError):
                continue
            if nxt != cur:
                return nxt
        return None

    @staticmethod
    def _recover_nt_path_if_mojibake(p: str) -> str:
        """
        Tcl / shell / INI can expose UTF-8 paths as Latin-1 code points ('fÃ¼r' for 'für').
        Apply the usual reversal repeatedly (multi-layer mojibake) until a real file is found
        or decoding no longer changes the string.
        """
        p = (p or "").strip().strip('"')
        if not p:
            return ""
        if os.name != "nt":
            return os.path.normpath(p)
        cur = os.path.normpath(p)
        for _ in range(16):
            if os.path.isfile(cur):
                return cur
            nxt = MasterGUI._try_mojibake_decode_step(cur)
            if nxt is None:
                break
            cur = nxt
        return cur

    @staticmethod
    def _best_stored_manual_path(raw: str, prev: str) -> str:
        """
        Prefer a path that exists on disk. Avoid overwriting a good INI value with a non-file
        widget string (e.g. multi-layer mojibake from the entry after a bad round-trip).
        """
        raw = MasterGUI._recover_nt_path_if_mojibake((raw or "").strip())
        prev = MasterGUI._recover_nt_path_if_mojibake((prev or "").strip())
        if raw and os.path.isfile(raw):
            return raw
        if prev and os.path.isfile(prev):
            return prev
        return raw or prev or ""

    @staticmethod
    def _normalize_shell_path(raw):
        if raw is None:
            return ""
        if isinstance(raw, bytes):
            raw = raw.decode(sys.getfilesystemencoding() or "utf-8", errors="replace")
        p = str(raw).strip().strip('"')
        p = os.path.normpath(p)
        return MasterGUI._recover_nt_path_if_mojibake(p)

    def _browse_manual_video(self, entry_widget):
        path = filedialog.askopenfilename(
            parent=self,
            title="Select video",
            filetypes=[
                ("Video files", "*.mp4 *.mov *.avi *.mkv *.webm *.m4v"),
                ("All files", "*.*"),
            ],
        )
        if path:
            sv = getattr(entry_widget, "_manual_path_var", None)
            if sv is not None:
                self._set_manual_video_entry(sv, entry_widget, path)
            else:
                self._apply_entry_value(entry_widget, path)

    def _manual_video_entry_click(self, event, entry_widget):
        """Empty path: single-click opens picker. Non-empty: normal click to edit text; use double-click to replace."""
        if self._manual_video_entry_nonempty(entry_widget):
            return
        self.after(1, lambda: self._browse_manual_video(entry_widget))
        return "break"

    def _manual_video_entry_dblbrowse(self, event, entry_widget):
        """Path already set: double-click path field to pick another file (cancel keeps current path)."""
        self.after(1, lambda: self._browse_manual_video(entry_widget))
        return "break"

    def _manual_video_zone_click(self, entry_widget):
        """Click on drop-zone chrome: always open file picker; cancel leaves paths unchanged."""
        self.after(1, lambda: self._browse_manual_video(entry_widget))

    def _first_matching_video_path_from_tkdnd(self, data):
        """Parse tkdnd <<Drop>> data (brace-separated paths on Windows) and return first video file."""
        if not data:
            return None
        try:
            paths = self.tk.splitlist(data)
        except tk.TclError:
            paths = [str(data).strip()]
        for raw in paths:
            p = self._normalize_shell_path(raw)
            if not p:
                continue
            low = p.lower()
            if os.path.isfile(p) and any(low.endswith(ext) for ext in self._MANUAL_VIDEO_EXTS):
                return p
        return None

    def create_manual_video_drop_row(self, parent, headline, subtitle, path_var: tk.StringVar):
        """
        Prominent drag-and-drop target + path field (no separate Browse button).
        Zone click always opens the picker; path line: empty = single-click browse, non-empty = double-click to replace.
        File drops use tkinterdnd2 (loaded on the root window in __init__).
        """
        outer = ctk.CTkFrame(
            parent,
            fg_color=self._pal["panel_elev"],
            border_width=2,
            border_color=self._pal["cyan_dim"],
            corner_radius=14,
        )
        outer.pack(fill="x", padx=4, pady=(6, 12))

        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=(16, 12))

        icon = ctk.CTkLabel(inner, text="⬇", font=("Segoe UI", 32), text_color=self._pal["cyan"])
        icon.pack(pady=(0, 2))
        h = ctk.CTkLabel(
            inner,
            text=headline,
            font=("Segoe UI Semibold", 18),
            text_color=self._pal["text"],
            justify="center",
        )
        h.pack()
        sub = ctk.CTkLabel(
            inner,
            text=subtitle,
            font=FONT_HINT,
            text_color=self._pal["muted"],
            justify="center",
            wraplength=520,
        )
        sub.pack(pady=(8, 12))

        ekw = dict(self._entry_kw())
        ekw["textvariable"] = path_var
        entry = ctk.CTkEntry(
            inner,
            placeholder_text="Path — click here when empty to browse; double-click to replace file…",
            **ekw,
        )
        entry._manual_path_var = path_var
        entry.pack(fill="x", pady=(4, 4))
        entry.bind("<Button-1>", lambda e, ew=entry: self._manual_video_entry_click(e, ew), add="+")
        entry.bind("<Double-Button-1>", lambda e, ew=entry: self._manual_video_entry_dblbrowse(e, ew), add="+")

        for w in (outer, inner, icon, h, sub):
            w.bind("<Button-1>", lambda e, ew=entry: self._manual_video_zone_click(ew), add="+")

        if self._tkdnd_ready:
            try:
                from tkinterdnd2 import COPY, DND_FILES

                def on_drop(event, ew=entry):
                    chosen = self._first_matching_video_path_from_tkdnd(event.data)
                    if chosen:
                        sv = getattr(ew, "_manual_path_var", None)
                        if sv is not None:
                            self.after(0, lambda c=chosen, s=sv, ew=ew: self._set_manual_video_entry(s, ew, c))
                        else:
                            self.after(0, lambda c=chosen, e=ew: self._apply_entry_value(e, c))
                    return COPY

                for w in (outer, inner, icon, h, sub, entry):
                    try:
                        w.drop_target_register(DND_FILES)
                        w.dnd_bind("<<Drop>>", on_drop)
                    except (tk.TclError, AttributeError, Exception):
                        pass
            except ImportError:
                pass

        self._manual_compare_zone_parts.append(
            {"outer": outer, "icon": icon, "head": h, "sub": sub, "entry": entry}
        )
        return entry

    def browse_path(self, entry_widget, is_dir=True, strvar=None):
        path = filedialog.askdirectory() if is_dir else filedialog.askopenfilename()
        if path:
            if strvar is not None:
                strvar.set(path)
            else:
                entry_widget.delete(0, "end")
                entry_widget.insert(0, path)
            self.update_processed_log_path_label()

    def build_main_tab(self):
        card = self._section_card(self.panel_main, "Watcher & Paths")
        self._muted_label(card, text="Console language", font=FONT_UI_SM, anchor="w").pack(
            fill="x", padx=4, pady=(0, 4),
        )
        self.combo_lang = ctk.CTkOptionMenu(card, values=["en", "de"], **self._option_kw())
        self.combo_lang.pack(anchor="w", padx=4, pady=(0, 10))

        self.var_afk_watcher = ctk.StringVar(value="1")
        self.cb_afk_watcher = ctk.CTkCheckBox(
            card,
            text=(
                "AFK mode: mark failed compares as processed — avoids endless retries on bad files"
            ),
            variable=self.var_afk_watcher,
            onvalue="1",
            offvalue="0",
            font=("Segoe UI", 14),
            text_color=self._pal["text"],
            fg_color=self._pal["cyan_dim"],
            hover_color=self._pal["cyan"],
            border_color=self._pal["border"],
            checkbox_width=28,
            checkbox_height=28,
        )
        self.cb_afk_watcher.pack(anchor="w", padx=4, pady=(0, 14))

        self.entry_source_dir = self.create_path_row(card, "Original folder (source)…")
        self.entry_df_dir = self.create_path_row(card, "Deepfake folder (watcher)…")
        self.entry_export_dir = self.create_path_row(card, "Optional export folder…")

        card_w = self._section_card(self.panel_main, "Watcher runtime (watcher_settings.ini)")
        row_w1 = ctk.CTkFrame(card_w, fg_color="transparent")
        row_w1.pack(fill="x", pady=6)
        row_w1.columnconfigure(0, weight=1)
        row_w1.columnconfigure(1, weight=1)
        self.entry_wait_seconds = ctk.CTkEntry(
            row_w1,
            placeholder_text="File stability wait (seconds)…",
            **self._entry_kw(),
        )
        self.entry_wait_seconds.grid(row=0, column=0, sticky="ew", padx=(4, 6))
        self.entry_watcher_compare_timeout = ctk.CTkEntry(
            row_w1,
            placeholder_text="Max compare per file (seconds, 0 = unlimited)…",
            **self._entry_kw(),
        )
        self.entry_watcher_compare_timeout.grid(row=0, column=1, sticky="ew", padx=(6, 4))

        self.entry_match_prefix = ctk.CTkEntry(
            card_w,
            placeholder_text="Filename match prefix length (0 = use full base name)…",
            **self._entry_kw(),
        )
        self.entry_match_prefix.pack(fill="x", padx=4, pady=6)

    def build_export_tab(self):
        self._muted_label(
            self.panel_export,
            text=(
                "Export pipeline (independent toggles): DaVinci Resolve, FFmpeg (encoder + which clips), "
                "and EDL fallbacks (AutoDelete / FullCheck)."
            ),
            font=FONT_HINT,
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=12, pady=(0, 8))

        card_dv = self._section_card(self.panel_export, "DaVinci Resolve Export")
        hdr = ctk.CTkFrame(card_dv, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 6))
        self.var_davinci = ctk.StringVar(value="0")
        self.cb_davinci_export = ctk.CTkCheckBox(
            hdr,
            text="Enable DaVinci Resolve 20 Studio export",
            variable=self.var_davinci,
            onvalue="1",
            offvalue="0",
            font=FONT_UI_SM,
            text_color=self._pal["text"],
            fg_color=self._pal["cyan_dim"],
            hover_color=self._pal["cyan"],
            border_color=self._pal["border"],
        )
        self.cb_davinci_export.pack(anchor="w", padx=4)
        self._muted_label(
            card_dv,
            text="API path, Resolve.exe, startup wait, and render timeout are in ⚙ Options → DaVinci (expand).",
            font=FONT_HINT,
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=4, pady=(0, 4))

        card_export_names = self._section_card(self.panel_export, "Video export files")
        self._muted_label(
            card_export_names,
            text="Applies to FFmpeg and DaVinci when writing rendered videos to disk.",
            font=FONT_HINT,
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=4, pady=(0, 4))
        self.var_export_unique = ctk.StringVar(value="0")
        self.cb_export_unique = ctk.CTkCheckBox(
            card_export_names,
            text=(
                "Do not overwrite — add suffix _b…_n…_p… from compare filter (buffer, noise, pixels); "
                "if that name exists, try _2 … _20"
            ),
            variable=self.var_export_unique,
            onvalue="1",
            offvalue="0",
            font=FONT_UI_SM,
            text_color=self._pal["text"],
            fg_color=self._pal["cyan_dim"],
            hover_color=self._pal["cyan"],
            border_color=self._pal["border"],
        )
        self.cb_export_unique.pack(anchor="w", padx=4, pady=(0, 2))

        card_edl = self._section_card(self.panel_export, "EDL")
        row_edl = ctk.CTkFrame(card_edl, fg_color="transparent")
        row_edl.pack(fill="x")
        self.var_edl_auto = ctk.StringVar(value="1")
        self.var_edl_full = ctk.StringVar(value="0")
        self.cb_edl_auto = ctk.CTkCheckBox(
            row_edl, text="EDL: AutoDelete", variable=self.var_edl_auto, onvalue="1", offvalue="0",
            font=FONT_UI_SM, text_color=self._pal["text"], fg_color=self._pal["cyan_dim"],
            hover_color=self._pal["cyan"], border_color=self._pal["border"],
        )
        self.cb_edl_auto.pack(side="left", padx=8, pady=4)
        self.cb_edl_full = ctk.CTkCheckBox(
            row_edl, text="EDL: FullCheck", variable=self.var_edl_full, onvalue="1", offvalue="0",
            font=FONT_UI_SM, text_color=self._pal["text"], fg_color=self._pal["cyan_dim"],
            hover_color=self._pal["cyan"], border_color=self._pal["border"],
        )
        self.cb_edl_full.pack(side="left", padx=8, pady=4)

        card_ff = self._section_card(self.panel_export, "FFmpeg video export")
        self.var_ffmpeg = ctk.StringVar(value="0")

        row_cb = ctk.CTkFrame(card_ff, fg_color="transparent")
        row_cb.pack(fill="x", pady=(0, 6))
        self.cb_ffmpeg_export = ctk.CTkCheckBox(
            row_cb,
            text="Enable FFmpeg video export",
            variable=self.var_ffmpeg,
            onvalue="1",
            offvalue="0",
            command=self.toggle_ffmpeg_options,
            font=FONT_UI_SM,
            text_color=self._pal["text"],
            fg_color=self._pal["cyan_dim"],
            hover_color=self._pal["cyan"],
            border_color=self._pal["border"],
        )
        self.cb_ffmpeg_export.pack(anchor="w", padx=4, pady=2)

        row_combos = ctk.CTkFrame(card_ff, fg_color="transparent")
        row_combos.pack(fill="x", pady=(0, 4))
        self._muted_label(row_combos, text="Video codec", font=FONT_UI_SM, anchor="w").pack(side="left", padx=(4, 6), pady=4)
        self.combo_codec = ctk.CTkOptionMenu(
            row_combos,
            values=["nvidia_av1", "nvidia_hevc", "nvidia_h264", "amd_hevc", "amd_h264", "cpu"],
            **self._option_kw(),
        )
        self.combo_codec.pack(side="left", padx=(0, 16), pady=4)

        self._muted_label(row_combos, text="Target videos", font=FONT_UI_SM, anchor="w").pack(side="left", padx=(0, 6), pady=4)
        self.combo_target = ctk.CTkOptionMenu(row_combos, values=["both", "source", "deepfake"], **self._option_kw())
        self.combo_target.pack(side="left", padx=(0, 4), pady=4)

    def build_filter_tab(self):
        card = self._section_card(self.panel_filter, "Filter & ignore")
        self.entry_ignore_suffix = ctk.CTkEntry(
            card,
            placeholder_text="Watcher ignores files ending with (e.g. suffix)…",
            **self._entry_kw(),
        )
        self.entry_ignore_suffix.pack(fill="x", padx=4, pady=6)

        pat_row = ctk.CTkFrame(card, fg_color="transparent")
        pat_row.pack(fill="x", pady=6)
        pat_row.columnconfigure(0, weight=1)
        self.entry_ignore_pattern = ctk.CTkEntry(
            pat_row,
            placeholder_text="Watcher ignores pattern (RegEx)…",
            **self._entry_kw(),
        )
        self.entry_ignore_pattern.grid(row=0, column=0, sticky="ew", padx=(4, 6))
        self.btn_regex_help = ctk.CTkButton(
            pat_row,
            text="?",
            command=self.show_regex_info,
            **self._button_kw("icon_sq"),
        )
        self.btn_regex_help.grid(row=0, column=1, padx=(0, 4))

        self._muted_label(
            card,
            text="Tip: use the first field for simple suffixes. Clear RegEx if not needed.",
            font=FONT_HINT,
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=4, pady=(0, 6))

        self.entry_buffer_seconds = ctk.CTkEntry(
            card,
            placeholder_text="Buffer seconds (compare stability)…",
            **self._entry_kw(),
        )
        self.entry_buffer_seconds.pack(fill="x", padx=4, pady=6)

        self._muted_label(
            card,
            text=(
                "Compare: how long the picture must look “no swap” (below your pixel rules) before "
                "that stretch is treated as intentional and kept. Lower = more short flicks/glitches "
                "survive in the edit; higher = stricter. 4–8 s is already quite strict."
            ),
            font=FONT_HINT,
            justify="left",
            wraplength=640,
            anchor="w",
        ).pack(fill="x", padx=4, pady=(0, 8))

        row_px = ctk.CTkFrame(card, fg_color="transparent")
        row_px.pack(fill="x", pady=6)
        row_px.columnconfigure(0, weight=1)
        row_px.columnconfigure(1, weight=1)
        self.entry_pixel_noise = ctk.CTkEntry(
            row_px,
            placeholder_text="Pixel noise threshold…",
            **self._entry_kw(),
        )
        self.entry_pixel_noise.grid(row=0, column=0, sticky="ew", padx=(4, 6))
        self.entry_changed_pixels = ctk.CTkEntry(
            row_px,
            placeholder_text="Changed pixels threshold…",
            **self._entry_kw(),
        )
        self.entry_changed_pixels.grid(row=0, column=1, sticky="ew", padx=(6, 4))

    def build_tools_tab(self):
        card = self._section_card(self.panel_tools, "Manual compare")
        self._muted_label(
            card,
            text="Drag & drop from Explorer (tkinterdnd2). Click the highlighted box to browse anytime. Path line: click when empty to browse; double-click when a path is set to replace. Cancel in the dialog keeps the previous path.",
            font=FONT_HINT,
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=4, pady=(0, 6))
        self.entry_manual_source = self.create_manual_video_drop_row(
            card,
            headline="DRAG & DROP — original (source) video",
            subtitle="Drop a file here, or click anywhere in this box to browse (even if a path is already set below). Double-click the path line below to replace that file.",
            path_var=self._var_manual_source,
        )
        self.entry_manual_df = self.create_manual_video_drop_row(
            card,
            headline="DRAG & DROP — deepfake video",
            subtitle="Drop a file here, or click anywhere in this box to browse (even if a path is already set below). Double-click the path line below to replace that file.",
            path_var=self._var_manual_df,
        )

        self.btn_run_compare = ctk.CTkButton(
            card,
            text="▶ RUN COMPARE",
            width=200,
            command=lambda: self.start_process("compare"),
            **self._button_kw("primary_emphasis", height=44),
        )
        self.btn_run_compare.pack(anchor="w", padx=4, pady=12)

        self.sep_tools = ctk.CTkFrame(self.panel_tools, height=2, fg_color=self._pal["border"], corner_radius=1)
        self.sep_tools.pack(fill="x", padx=8, pady=8)

        card2 = self._section_card(self.panel_tools, "Analyzer")
        self.btn_run_analyzer = ctk.CTkButton(
            card2,
            text="📊 ANALYZER UI",
            width=240,
            command=self.launch_analyzer,
            **self._button_kw("primary_emphasis", height=44),
        )
        self.btn_run_analyzer.pack(anchor="w", padx=4, pady=4)

    def build_processed_tab(self):
        card = self._section_card(self.panel_processed, "Processed log (watcher_processed.txt)")
        self.processed_path_label = ctk.CTkLabel(
            card, text="watcher_processed.txt: -", anchor="w", justify="left", font=FONT_UI_SM, text_color=self._pal["muted"],
        )
        self.processed_path_label.pack(fill="x", padx=4, pady=(0, 8))
        self._muted_labels.append(self.processed_path_label)

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 8))

        self.btn_proc_reload = ctk.CTkButton(
            btn_row, text="🔄 RELOAD", width=118, command=self.load_processed_log,
            **self._button_kw("ghost", height=BTN_HEIGHT_COMPACT),
        )
        self.btn_proc_reload.pack(side="left", padx=4)
        self.btn_proc_save = ctk.CTkButton(
            btn_row, text="💾 SAVE", width=118, command=self.save_processed_log,
            **self._button_kw("success", height=BTN_HEIGHT_COMPACT),
        )
        self.btn_proc_save.pack(side="left", padx=4)
        self.btn_proc_dedupe = ctk.CTkButton(
            btn_row, text="🧹 FIX DUP", width=118, command=self.deduplicate_processed_log,
            **self._button_kw("ghost", height=BTN_HEIGHT_COMPACT),
        )
        self.btn_proc_dedupe.pack(side="left", padx=4)
        self.btn_proc_fixln = ctk.CTkButton(
            btn_row, text="🛠 FIX LINE", width=118, command=self.fix_corrupted_processed_log,
            **self._button_kw("ghost", height=BTN_HEIGHT_COMPACT),
        )
        self.btn_proc_fixln.pack(side="left", padx=4)
        self.btn_proc_open = ctk.CTkButton(
            btn_row, text="📂 OPEN", width=100, command=self.open_processed_log_external,
            **self._button_kw("ghost", height=BTN_HEIGHT_COMPACT),
        )
        self.btn_proc_open.pack(side="left", padx=4)
        self.btn_proc_clear = ctk.CTkButton(
            btn_row, text="❌ CLEAR ALL", width=124, command=self.clear_processed_log,
            **self._button_kw("danger_soft", height=BTN_HEIGHT_COMPACT),
        )
        self.btn_proc_clear.pack(side="left", padx=4)

        hint = (
            "Edit watcher_processed.txt here: one video filename per line (basename, e.g. clip.mp4). "
            "Full paths also work. The watcher skips any deepfake file whose name appears in this list. "
            "Save from the GUI to normalize line endings."
        )
        self._muted_label(
            self.panel_processed, text=hint, anchor="w", justify="left", font=FONT_HINT,
        ).pack(fill="x", padx=16, pady=(0, 8))

        self.processed_text = ctk.CTkTextbox(
            self.panel_processed,
            wrap="none",
            font=("Consolas", 12),
            fg_color=self._pal["panel_elev"],
            border_color=self._pal["border"],
            text_color=self._pal["text"],
        )
        self.processed_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _read_ini_manual_paths(self):
        """Last manual video paths from settings.ini ([GUI])."""
        cfg = configparser.ConfigParser()
        if not os.path.isfile(self.settings_file):
            return "", ""
        try:
            with open(self.settings_file, "r", encoding="utf-8-sig") as fh:
                cfg.read_file(fh)
        except Exception:
            cfg.read(self.settings_file)
        if not cfg.has_section("GUI"):
            return "", ""
        s1 = cfg.get("GUI", "last_manual_source", fallback="").strip()
        s2 = cfg.get("GUI", "last_manual_df", fallback="").strip()
        return (
            MasterGUI._recover_nt_path_if_mojibake(s1),
            MasterGUI._recover_nt_path_if_mojibake(s2),
        )

    def _manual_video_paths_resolved(self):
        """
        Prefer Tools-tab entry text; if missing or not an existing file, fall back to [GUI] in settings.ini.
        Re-applies values to the entries when falling back (CustomTkinter sometimes returns '' from .get()
        even though paths were loaded — and Save would otherwise overwrite INI with blanks).
        """
        try:
            self.update_idletasks()
        except Exception:
            pass
        src = self._recover_nt_path_if_mojibake(self._var_manual_source.get().strip())
        df = self._recover_nt_path_if_mojibake(self._var_manual_df.get().strip())
        ini_s, ini_d = self._read_ini_manual_paths()
        synced = False
        if (not src or not os.path.isfile(src)) and ini_s and os.path.isfile(ini_s):
            src = ini_s
            synced = True
        if (not df or not os.path.isfile(df)) and ini_d and os.path.isfile(ini_d):
            df = ini_d
            synced = True
        if synced:
            self._set_manual_video_entry(self._var_manual_source, self.entry_manual_source, src)
            self._set_manual_video_entry(self._var_manual_df, self.entry_manual_df, df)
        return src, df

    def launch_analyzer(self):
        base = self.base_dir
        exe_path = os.path.join(base, "flickercheck_ui.exe")
        py_path = os.path.join(base, "flickercheck_ui.py")
        vid_source, vid_df = self._manual_video_paths_resolved()

        if not os.path.isfile(vid_source) or not os.path.isfile(vid_df):
            self.write_log("\n[ERROR] Please select both valid video files first to run the Analyzer UI.\n")
            return

        if os.path.isfile(exe_path):
            self.write_log(f"\n[SYSTEM] Launching Analyzer UI (exe)...\nSource: {vid_source}\nDeepfake: {vid_df}\n")
            subprocess.Popen([exe_path, vid_source, vid_df], cwd=base)
        elif os.path.isfile(py_path):
            self.write_log(f"\n[SYSTEM] Launching Analyzer UI (Python)...\nSource: {vid_source}\nDeepfake: {vid_df}\n")
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
            'davinci_startup_wait_seconds': '20',
            'davinci_scriptapp_retry_attempts': '60',
            'davinci_scriptapp_retry_delay_seconds': '3',
            'export_avoid_overwrite': '0',
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

        if not config_c.has_section('GUI'):
            config_c.add_section('GUI')
            changed = True
        for key, val in (('last_manual_source', ''), ('last_manual_df', ''), ('ui_theme', 'dark')):
            if not config_c.has_option('GUI', key):
                config_c.set('GUI', key, val)
                changed = True
        return changed

    def load_configs(self):
        config_c = configparser.ConfigParser()
        if os.path.isfile(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8-sig") as fh:
                    config_c.read_file(fh)
            except Exception:
                config_c.read(self.settings_file)

        changed = self.ensure_compare_defaults(config_c)
        if changed:
            with open(self.settings_file, "w", encoding="utf-8", newline="\n") as f:
                config_c.write(f)

        self._apply_entry_value(self.entry_export_dir, config_c.get('PATHS', 'final_export_dir', fallback=''))
        self._var_davinci_api_path.set(
            config_c.get(
                "PATHS",
                "davinci_api_path",
                fallback=r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules",
            ).strip()
        )
        self._var_davinci_exe_path.set(
            config_c.get(
                "PATHS",
                "davinci_exe_path",
                fallback=r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe",
            ).strip()
        )
        self._var_davinci_startup_wait.set(config_c.get("SETTINGS", "davinci_startup_wait_seconds", fallback="20").strip())
        self._var_davinci_render_timeout.set(
            config_c.get("SETTINGS", "davinci_render_timeout_seconds", fallback="1800").strip()
        )
        self.combo_lang.set(config_c.get('SETTINGS', 'language', fallback='en'))
        self.var_davinci.set(config_c.get('SETTINGS', 'enable_davinci_export', fallback='0'))
        self.var_edl_auto.set(config_c.get('SETTINGS', 'enable_autodelete_edl', fallback='1'))
        self.var_edl_full.set(config_c.get('SETTINGS', 'enable_fullcheck_edl', fallback='0'))
        self.var_ffmpeg.set(config_c.get('SETTINGS', 'enable_ffmpeg_export', fallback='0'))
        self.var_export_unique.set(config_c.get('SETTINGS', 'export_avoid_overwrite', fallback='0'))
        self.combo_codec.set(config_c.get('SETTINGS', 'ffmpeg_encoder', fallback='nvidia_h264'))
        self.combo_target.set(config_c.get('SETTINGS', 'ffmpeg_export_target', fallback='both'))
        self._apply_entry_value(self.entry_buffer_seconds, config_c.get('SETTINGS', 'buffer_seconds', fallback='2.0'))
        self._apply_entry_value(self.entry_pixel_noise, config_c.get('SETTINGS', 'pixel_noise_threshold', fallback='15'))
        self._apply_entry_value(self.entry_changed_pixels, config_c.get('SETTINGS', 'changed_pixels_threshold', fallback='200'))

        if config_c.has_section('GUI'):
            self._set_manual_video_entry(
                self._var_manual_source,
                self.entry_manual_source,
                config_c.get('GUI', 'last_manual_source', fallback=''),
            )
            self._set_manual_video_entry(
                self._var_manual_df,
                self.entry_manual_df,
                config_c.get('GUI', 'last_manual_df', fallback=''),
            )

        config_w = configparser.ConfigParser()
        config_w.read(self.watcher_file)

        if not config_w.has_section('PATHS'):
            config_w.add_section('PATHS')
        if not config_w.has_section('SETTINGS'):
            config_w.add_section('SETTINGS')
        if not config_w.has_section('MATCHING'):
            config_w.add_section('MATCHING')

        self._apply_entry_value(self.entry_source_dir, config_w.get('PATHS', 'source_dir', fallback=''))
        self._apply_entry_value(self.entry_df_dir, config_w.get('PATHS', 'deepfake_dir', fallback=''))
        self._apply_entry_value(self.entry_wait_seconds, config_w.get('SETTINGS', 'wait_seconds', fallback='30'))
        self._apply_entry_value(self.entry_watcher_compare_timeout, config_w.get('SETTINGS', 'compare_timeout_seconds', fallback='1800'))
        self._apply_entry_value(self.entry_match_prefix, config_w.get('MATCHING', 'match_prefix_length', fallback='10'))
        self.var_afk_watcher.set(config_w.get('SETTINGS', 'afk_mode', fallback='1'))
        self._apply_entry_value(self.entry_ignore_suffix, config_w.get('MATCHING', 'ignore_suffix', fallback='_p'))
        self._apply_entry_value(self.entry_ignore_pattern, config_w.get('MATCHING', 'ignore_temp_pattern', fallback=r'^\d{6,}_(pro|hyb|exp)(_p)?'))

        self.update_processed_log_path_label()

    def save_configs(self):
        config_c = configparser.ConfigParser()
        if os.path.isfile(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8-sig") as fh:
                    config_c.read_file(fh)
            except Exception:
                config_c.read(self.settings_file)
        self.ensure_compare_defaults(config_c)

        config_c.set('PATHS', 'final_export_dir', self.entry_export_dir.get())
        config_c.set("PATHS", "davinci_api_path", self._var_davinci_api_path.get().strip())
        config_c.set("PATHS", "davinci_exe_path", self._var_davinci_exe_path.get().strip())
        config_c.set('SETTINGS', 'language', self.combo_lang.get())
        config_c.set('SETTINGS', 'enable_davinci_export', self.var_davinci.get())
        config_c.set('SETTINGS', 'enable_autodelete_edl', self.var_edl_auto.get())
        config_c.set('SETTINGS', 'enable_fullcheck_edl', self.var_edl_full.get())
        config_c.set('SETTINGS', 'enable_ffmpeg_export', self.var_ffmpeg.get())
        config_c.set('SETTINGS', 'export_avoid_overwrite', self.var_export_unique.get())
        config_c.set('SETTINGS', 'ffmpeg_encoder', self.combo_codec.get())
        config_c.set('SETTINGS', 'ffmpeg_export_target', self.combo_target.get())
        config_c.set('SETTINGS', 'buffer_seconds', self.entry_buffer_seconds.get())
        config_c.set('SETTINGS', 'pixel_noise_threshold', self.entry_pixel_noise.get())
        config_c.set('SETTINGS', 'changed_pixels_threshold', self.entry_changed_pixels.get())
        config_c.set("SETTINGS", "davinci_render_timeout_seconds", self._var_davinci_render_timeout.get().strip())
        config_c.set("SETTINGS", "davinci_startup_wait_seconds", self._var_davinci_startup_wait.get().strip())
        if not config_c.has_section('GUI'):
            config_c.add_section('GUI')
        raw_ms = self._var_manual_source.get().strip()
        raw_md = self._var_manual_df.get().strip()
        prev_ms = config_c.get("GUI", "last_manual_source", fallback="").strip()
        prev_md = config_c.get("GUI", "last_manual_df", fallback="").strip()
        # Prefer paths that exist on disk; never replace a valid saved path with a broken widget string.
        prev_ms = self._recover_nt_path_if_mojibake(prev_ms)
        prev_md = self._recover_nt_path_if_mojibake(prev_md)
        store_ms = self._best_stored_manual_path(raw_ms, prev_ms)
        store_md = self._best_stored_manual_path(raw_md, prev_md)
        config_c.set("GUI", "last_manual_source", store_ms)
        config_c.set("GUI", "last_manual_df", store_md)
        config_c.set("GUI", "ui_theme", "light" if self._theme_is_light else "dark")
        with open(self.settings_file, "w", encoding="utf-8", newline="\n") as f:
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
        config_w.set("PATHS", "resolve_exe_path", self._var_davinci_exe_path.get().strip())
        config_w.set('SETTINGS', 'language', self.combo_lang.get())
        config_w.set('SETTINGS', 'wait_seconds', self._safe_int_str(self.entry_wait_seconds.get, 30))
        config_w.set(
            'SETTINGS',
            'compare_timeout_seconds',
            self._safe_int_str(self.entry_watcher_compare_timeout.get, 1800),
        )
        config_w.set('SETTINGS', 'afk_mode', self.var_afk_watcher.get())
        config_w.set(
            'MATCHING',
            'match_prefix_length',
            self._safe_int_str(self.entry_match_prefix.get, 10),
        )
        config_w.set('MATCHING', 'ignore_suffix', self.entry_ignore_suffix.get())
        config_w.set('MATCHING', 'ignore_temp_pattern', self.entry_ignore_pattern.get())
        with open(self.watcher_file, 'w') as f:
            config_w.write(f)

        self.update_processed_log_path_label()
        self.write_log(
            "[INFO] Settings saved (watcher paths, compare settings, last manual video paths).\n"
        )

    @staticmethod
    def _safe_int_str(widget_get, default):
        try:
            return str(int(float(widget_get().strip())))
        except (ValueError, TypeError, AttributeError):
            return str(default)

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

    def _log_async(self, msg: str):
        """Marshal log lines to the UI thread (safe from worker threads)."""
        self.after(0, lambda m=msg: self.write_log(m))

    def _ensure_davinci_running_impl(self, dv_exe: str, dv_wait: int, log_fn) -> bool:
        """Start/wait for Resolve; `log_fn(msg)` may be sync (main thread) or `_log_async` from a worker."""
        if self.is_davinci_process_running():
            log_fn("[INFO] DaVinci Resolve is already running.\n")
            try:
                w = int(dv_wait)
            except (ValueError, TypeError):
                w = 20
            precook = max(6, min(30, (w + 4) // 2))
            log_fn(
                f"[INFO] Pausing {precook}s for Resolve scripting API (~half of startup wait {w}s, max 30s; "
                "raise \"DaVinci startup wait\" in Export if imports still fail).\n"
            )
            time.sleep(precook)
            return True

        if not dv_exe:
            log_fn("[ERROR] DaVinci export is enabled, but no Resolve.exe path is set.\n")
            return False
        if not os.path.isfile(dv_exe):
            log_fn(f"[ERROR] Resolve.exe not found: {dv_exe}\n")
            return False

        try:
            wait_seconds = int(float(dv_wait))
        except (ValueError, TypeError):
            wait_seconds = 20
        wait_seconds = max(0, wait_seconds)

        log_fn(f"[SYSTEM] DaVinci is not running. Starting Resolve...\n{dv_exe}\n")
        try:
            subprocess.Popen([dv_exe], cwd=os.path.dirname(dv_exe))
        except Exception as e:
            log_fn(f"[ERROR] Could not start Resolve.exe: {e}\n")
            return False

        log_fn(f"[INFO] Waiting {wait_seconds} seconds for DaVinci startup...\n")
        time.sleep(wait_seconds)

        if self.is_davinci_process_running():
            log_fn("[INFO] DaVinci Resolve started successfully.\n")
            return True

        log_fn(
            "[WARNING] Resolve.exe was started, but no running DaVinci process was detected yet. "
            "Compare will continue and will do the final API check.\n"
        )
        return True

    def _manual_compare_worker(self, vid_source, vid_df, want_davinci, dv_exe, dv_wait):
        """DaVinci sleeps + compare subprocess must not block the Tk main thread (avoids \"Not responding\")."""
        try:
            if want_davinci:
                if not self._ensure_davinci_running_impl(dv_exe, dv_wait, self._log_async):
                    self.after(0, self.reset_ui)
                    return
            self.after(
                0,
                lambda: self.status_label.configure(text="🟡 Compare Running", text_color="#ffee58"),
            )
            self._log_async(
                f"\n[SYSTEM] Starting Manual Compare...\nSource: {vid_source}\nDeepfake: {vid_df}\n"
            )
            self.run_tool("compare.exe", [vid_source, vid_df, "--auto"])
        except Exception as e:
            self._log_async(f"\n[ERROR] Manual compare launch failed: {e}\n")
            self.after(0, self.reset_ui)

    def start_process(self, process_type):
        self.save_configs()
        self.btn_start.configure(state="disabled")
        self.btn_run_compare.configure(state="disabled")
        self.btn_stop.configure(state="normal")

        if process_type == "watcher":
            self.status_label.configure(text="🟢 Watcher Active", text_color="#69f0ae")
            self.write_log("\n[SYSTEM] Starting Watcher...\n")
            threading.Thread(target=self.run_tool, args=("watcher.exe", []), daemon=True).start()

        elif process_type == "compare":
            vid_source, vid_df = self._manual_video_paths_resolved()

            if not os.path.isfile(vid_source) or not os.path.isfile(vid_df):
                self.write_log("\n[ERROR] Please select both valid video files first.\n")
                self.reset_ui()
                return

            want_davinci = self.var_davinci.get() == "1"
            dv_exe = self._var_davinci_exe_path.get().strip()
            try:
                dv_wait = int(float(self._var_davinci_startup_wait.get().strip() or "20"))
            except (ValueError, TypeError):
                dv_wait = 20

            if want_davinci:
                self.status_label.configure(text="🔵 Preparing DaVinci", text_color=self._pal["cyan"])
                self.write_log(
                    "[INFO] DaVinci export is ON: starting Resolve if needed, then a short API warm-up — "
                    "same idea as the watcher after a cold start.\n"
                )

            threading.Thread(
                target=self._manual_compare_worker,
                args=(vid_source, vid_df, want_davinci, dv_exe, dv_wait),
                daemon=True,
            ).start()

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
        child_env = os.environ.copy()
        child_env["PYTHONUNBUFFERED"] = "1"
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=create_no_window,
                cwd=base,
                env=child_env,
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
        self.status_label.configure(text="🔴 Stopped", text_color=self._pal["text"])

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
