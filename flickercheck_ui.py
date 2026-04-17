import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image
import os
import sys
import time
from tkinter import messagebox

from theme_palette import PALETTE_DARK, PALETTE_LIGHT, load_ui_theme_is_light

ctk.set_default_color_theme("blue")

FONT_BTN = ("Segoe UI Black", 10)
FONT_UI = ("Segoe UI", 13)
FONT_UI_SM = ("Segoe UI", 11)
FONT_TITLE = ("Segoe UI Semibold", 18)
FONT_STATUS = ("Segoe UI Semibold", 20)
FONT_METRIC = ("Segoe UI", 12)


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _analyzer_theme_colors(light: bool):
    """Merge Control Center palettes with analyzer-only accents (sliders, status pill)."""
    p = dict(PALETTE_LIGHT if light else PALETTE_DARK)
    p["magenta_hover"] = "#ff6ec7" if not light else "#c2185b"
    if light:
        p["magenta"] = "#ad1457"
        p["magenta_dim"] = "#fce4ec"
        p["ok"] = "#2e7d32"
        p["bad"] = "#c62828"
        p["pill_ok_bg"] = "#c8e6c9"
        p["pill_bad_bg"] = "#ffcdd2"
        p["paused_play_fg"] = "#2e7d32"
        p["paused_play_hover"] = "#43a047"
        p["paused_play_border"] = "#1b5e20"
        p["stop_hover"] = "#b71c1c"
        p["stop_border"] = "#1a0505"
    else:
        p["magenta"] = "#ff3dac"
        p["magenta_dim"] = "#5a1a40"
        p["ok"] = "#00e676"
        p["bad"] = "#ff5252"
        p["pill_ok_bg"] = "#0d2818"
        p["pill_bad_bg"] = "#2a1010"
        p["paused_play_fg"] = "#1b5e20"
        p["paused_play_hover"] = "#2e7d32"
        p["paused_play_border"] = "#061a0c"
        p["stop_hover"] = "#b71c1c"
        p["stop_border"] = "#1a0505"
    return p


def _video_frame_to_bgr(frame):
    """Normalize decoder output to 3-channel BGR for OpenCV ops."""
    if frame is None:
        return None
    if frame.ndim == 2:
        return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    channels = frame.shape[2]
    if channels == 1:
        return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    if channels == 4:
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    return frame


def _match_deepfake_to_original(frame_orig_bgr, frame_df_bgr):
    """Resize deepfake frame to original (h, w) when resolutions differ."""
    ho, wo = frame_orig_bgr.shape[:2]
    hd, wd = frame_df_bgr.shape[:2]
    if (hd, wd) == (ho, wo):
        return frame_df_bgr
    return cv2.resize(frame_df_bgr, (wo, ho), interpolation=cv2.INTER_LINEAR)


class FlickercheckUI(ctk.CTk):
    def __init__(self, video_orig_path, video_df_path):
        super().__init__()
        settings_file = os.path.join(get_base_dir(), "settings.ini")
        self._theme_is_light = load_ui_theme_is_light(settings_file)
        ctk.set_appearance_mode("Light" if self._theme_is_light else "Dark")
        self.c = _analyzer_theme_colors(self._theme_is_light)

        self.title("Deepfake Analyzer")
        self.geometry("1200x920")
        self.minsize(980, 720)
        self.configure(fg_color=self.c["bg"])

        self.orig_path = video_orig_path
        self.df_path = video_df_path

        self.cap_orig = cv2.VideoCapture(self.orig_path)
        self.cap_df = cv2.VideoCapture(self.df_path)

        self.total_frames = int(self.cap_orig.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap_orig.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap_orig.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.current_frame = 0
        self.is_playing = True
        self.last_update_time = time.time()

        self.threshold = 15
        self.overlay_opacity = 0.6
        self.max_playback_fps = 30
        self._logged_frame_shape_mismatch = False
        # Next frame index that OpenCV will return with read() without seek (both caps stay in sync).
        self._sequential_next_index = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # —— Header ——
        self.frame_header = ctk.CTkFrame(
            self, fg_color=self.c["panel"], corner_radius=0, height=52, border_width=0,
        )
        self.frame_header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.frame_header.grid_propagate(False)
        self.frame_header.grid_columnconfigure(1, weight=1)

        self.lbl_title = ctk.CTkLabel(
            self.frame_header,
            text="Deepfake Analyzer",
            font=FONT_TITLE,
            text_color=self.c["text"],
        )
        self.lbl_title.grid(row=0, column=0, padx=(20, 12), pady=12, sticky="w")

        self.frame_header_mid = ctk.CTkFrame(self.frame_header, fg_color="transparent")
        self.frame_header_mid.grid(row=0, column=1, sticky="e", padx=8, pady=8)

        self.var_sbs = ctk.StringVar(value="0")
        self.cb_sbs_header = ctk.CTkCheckBox(
            self.frame_header_mid,
            text="Side View",
            variable=self.var_sbs,
            onvalue="1",
            offvalue="0",
            font=FONT_UI_SM,
            text_color=self.c["text"],
            fg_color=self.c["cyan_dim"],
            hover_color=self.c["cyan"],
            border_color=self.c["border"],
            checkbox_width=20,
            checkbox_height=20,
        )
        self.cb_sbs_header.pack(side="left", padx=(0, 16))

        self.lbl_brand = ctk.CTkLabel(
            self.frame_header_mid,
            text="DEEPFAKE",
            font=("Segoe UI Semibold", 11),
            text_color=self.c["magenta"],
        )
        self.lbl_brand.pack(side="left", padx=(0, 12))

        self.frame_header_actions = ctk.CTkFrame(self.frame_header, fg_color="transparent")
        self.frame_header_actions.grid(row=0, column=2, padx=(8, 16), pady=8, sticky="e")

        self.btn_minimize = ctk.CTkButton(
            self.frame_header_actions,
            text="—",
            width=36,
            height=32,
            font=("Segoe UI Black", 12),
            fg_color=self.c["panel_elev"],
            hover_color=self.c["border"],
            text_color=self.c["text"],
            corner_radius=10,
            border_width=2,
            border_color=self.c["btn_rim"],
            command=self.iconify,
        )
        self.btn_minimize.pack(side="left", padx=(0, 6))

        self.btn_help = ctk.CTkButton(
            self.frame_header_actions,
            text="⚙",
            width=36,
            height=32,
            font=("Segoe UI Black", 12),
            fg_color=self.c["panel_elev"],
            hover_color=self.c["border"],
            text_color=self.c["text"],
            corner_radius=10,
            border_width=2,
            border_color=self.c["btn_rim"],
            command=self._show_shortcuts_help,
        )
        self.btn_help.pack(side="left")

        # —— Video ——
        self.video_frame = ctk.CTkFrame(
            self,
            fg_color=self.c["panel"],
            corner_radius=16,
            border_width=1,
            border_color=self.c["border"],
        )
        self.video_frame.grid(row=1, column=0, padx=16, pady=(12, 8), sticky="nsew")
        self.video_frame.grid_rowconfigure(0, weight=1)
        self.video_frame.grid_columnconfigure(0, weight=1)

        self.lbl_video_display = ctk.CTkLabel(self.video_frame, text="", fg_color=self.c["bg"])
        self.lbl_video_display.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")

        # —— Timeline ——
        self.frame_timeline = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_timeline.grid(row=2, column=0, padx=16, pady=(0, 4), sticky="ew")
        self.frame_timeline.columnconfigure(0, weight=1)

        self.lbl_frame_info = ctk.CTkLabel(
            self.frame_timeline,
            text=f"Frame: 0 / {self.total_frames}",
            font=("Segoe UI Semibold", 12),
            text_color=self.c["muted"],
        )
        self.lbl_frame_info.grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.slider_scrub = ctk.CTkSlider(
            self.frame_timeline,
            from_=0,
            to=max(0, self.total_frames - 1),
            number_of_steps=max(1, self.total_frames),
            command=self.set_frame_manual,
            progress_color=self.c["cyan"],
            button_color=self.c["cyan"],
            button_hover_color=self.c["cyan_hover"],
            fg_color=self.c["panel_elev"],
            height=18,
        )
        self.slider_scrub.grid(row=1, column=0, sticky="ew")
        self.slider_scrub.set(0)

        # —— Bottom dashboard (3 columns) ——
        self.frame_controls = ctk.CTkFrame(
            self, fg_color=self.c["panel"], corner_radius=14, border_width=1, border_color=self.c["border"],
        )
        self.frame_controls.grid(row=3, column=0, padx=16, pady=(4, 16), sticky="ew")
        self.frame_controls.grid_columnconfigure((0, 1, 2), weight=1, uniform="dash")

        # Left: status + metrics
        self.frame_left = ctk.CTkFrame(self.frame_controls, fg_color="transparent")
        self.frame_left.grid(row=0, column=0, padx=14, pady=14, sticky="nsew")

        self.frame_status_pill = ctk.CTkFrame(
            self.frame_left, fg_color=self.c["panel_elev"], corner_radius=22, height=44,
        )
        self.frame_status_pill.pack(fill="x", pady=(0, 10))
        self.frame_status_pill.pack_propagate(False)

        self.lbl_status = ctk.CTkLabel(
            self.frame_status_pill,
            text="Status: -",
            font=FONT_STATUS,
            text_color=self.c["muted"],
        )
        self.lbl_status.pack(expand=True)

        self.lbl_pixel_info = ctk.CTkLabel(
            self.frame_left,
            text="Diff Pixels: 0",
            font=FONT_METRIC,
            text_color=self.c["magenta"],
            anchor="w",
        )
        self.lbl_pixel_info.pack(fill="x", pady=2)

        self.lbl_limit_hint = ctk.CTkLabel(
            self.frame_left,
            text="Error Limit: 200",
            font=FONT_METRIC,
            text_color=self.c["muted"],
            anchor="w",
        )
        self.lbl_limit_hint.pack(fill="x", pady=2)

        ctk.CTkLabel(
            self.frame_left,
            text="Playback (max FPS)",
            font=FONT_UI_SM,
            text_color=self.c["muted"],
            anchor="w",
        ).pack(fill="x", pady=(10, 2))

        self.frame_fps_row = ctk.CTkFrame(self.frame_left, fg_color="transparent")
        self.frame_fps_row.pack(fill="x")

        self.slider_fps = ctk.CTkSlider(
            self.frame_fps_row,
            from_=5,
            to=60,
            number_of_steps=55,
            command=self.change_playback_fps,
            progress_color=self.c["cyan"],
            button_color=self.c["cyan"],
            button_hover_color=self.c["cyan_hover"],
            fg_color=self.c["panel_elev"],
            height=14,
        )
        self.slider_fps.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.slider_fps.set(self.max_playback_fps)

        self.lbl_fps_val = ctk.CTkLabel(
            self.frame_fps_row,
            text=str(self.max_playback_fps),
            font=("Segoe UI Semibold", 12),
            text_color=self.c["text"],
            width=32,
        )
        self.lbl_fps_val.pack(side="right")

        # Center: transport
        self.frame_center = ctk.CTkFrame(self.frame_controls, fg_color="transparent")
        self.frame_center.grid(row=0, column=1, padx=8, pady=14, sticky="nsew")

        self.frame_transport = ctk.CTkFrame(self.frame_center, fg_color="transparent")
        self.frame_transport.pack(expand=True)

        nav_kw = dict(
            height=40,
            font=("Segoe UI Black", 9),
            fg_color=self.c["panel_elev"],
            hover_color=self.c["border"],
            text_color=self.c["text"],
            corner_radius=10,
            border_width=2,
            border_color=self.c["btn_rim"],
        )
        self.btn_rewind = ctk.CTkButton(
            self.frame_transport,
            text="⏪ −100",
            width=72,
            command=lambda: self.jump_frames(-100),
            **nav_kw,
        )
        self.btn_rewind.pack(side="left", padx=3, pady=8)

        self.btn_prev = ctk.CTkButton(
            self.frame_transport,
            text="◀ 1",
            width=52,
            command=lambda: self.jump_frames(-1),
            **nav_kw,
        )
        self.btn_prev.pack(side="left", padx=3, pady=8)

        self.btn_play_pause = ctk.CTkButton(
            self.frame_transport,
            text="⏸",
            width=64,
            height=64,
            font=("Segoe UI Black", 22),
            fg_color=self.c["cyan_dim"],
            hover_color=self.c["cyan"],
            text_color=self.c["text"],
            corner_radius=32,
            border_width=2,
            border_color=self.c["primary_border"],
            command=self.toggle_play,
        )
        self.btn_play_pause.pack(side="left", padx=12, pady=8)

        self.btn_next = ctk.CTkButton(
            self.frame_transport,
            text="1 ▶",
            width=52,
            command=lambda: self.jump_frames(1),
            **nav_kw,
        )
        self.btn_next.pack(side="left", padx=3, pady=8)

        self.btn_forward = ctk.CTkButton(
            self.frame_transport,
            text="+100 ⏩",
            width=72,
            command=lambda: self.jump_frames(100),
            **nav_kw,
        )
        self.btn_forward.pack(side="left", padx=3, pady=8)

        # Right: sensitivity + options + apply + stop
        self.frame_right = ctk.CTkFrame(self.frame_controls, fg_color="transparent")
        self.frame_right.grid(row=0, column=2, padx=14, pady=14, sticky="nsew")

        self.lbl_sens = ctk.CTkLabel(
            self.frame_right,
            text="Sensitivity (threshold)",
            font=FONT_UI_SM,
            text_color=self.c["muted"],
            anchor="w",
        )
        self.lbl_sens.pack(fill="x")

        self.frame_sens_row = ctk.CTkFrame(self.frame_right, fg_color="transparent")
        self.frame_sens_row.pack(fill="x", pady=(0, 8))

        self.slider_sens = ctk.CTkSlider(
            self.frame_sens_row,
            from_=5,
            to=150,
            number_of_steps=145,
            command=self.change_threshold,
            progress_color=self.c["magenta"],
            button_color=self.c["magenta"],
            button_hover_color=self.c["magenta_hover"],
            fg_color=self.c["magenta_dim"],
            height=16,
        )
        self.slider_sens.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.slider_sens.set(self.threshold)

        self.lbl_sens_val = ctk.CTkLabel(
            self.frame_sens_row,
            text=str(self.threshold),
            font=("Segoe UI Semibold", 14),
            text_color=self.c["text"],
            width=36,
        )
        self.lbl_sens_val.pack(side="right")

        self.lbl_overlay = ctk.CTkLabel(
            self.frame_right,
            text="Diff overlay (heatmap strength %)",
            font=FONT_UI_SM,
            text_color=self.c["muted"],
            anchor="w",
        )
        self.lbl_overlay.pack(fill="x", pady=(10, 2))

        self.frame_overlay_row = ctk.CTkFrame(self.frame_right, fg_color="transparent")
        self.frame_overlay_row.pack(fill="x", pady=(0, 6))

        self.slider_overlay = ctk.CTkSlider(
            self.frame_overlay_row,
            from_=5,
            to=100,
            number_of_steps=95,
            command=self.change_overlay_pct,
            progress_color=self.c["magenta"],
            button_color=self.c["magenta"],
            button_hover_color=self.c["magenta_hover"],
            fg_color=self.c["magenta_dim"],
            height=16,
        )
        self.slider_overlay.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.slider_overlay.set(int(round(self.overlay_opacity * 100)))

        self.lbl_overlay_pct = ctk.CTkLabel(
            self.frame_overlay_row,
            text=f"{int(round(self.overlay_opacity * 100))}%",
            font=("Segoe UI Semibold", 14),
            text_color=self.c["text"],
            width=40,
        )
        self.lbl_overlay_pct.pack(side="right")

        self.frame_options = ctk.CTkFrame(self.frame_right, fg_color="transparent")
        self.frame_options.pack(fill="x", pady=(4, 8))

        self.cb_sbs = ctk.CTkCheckBox(
            self.frame_options,
            text="Side-by-Side View",
            variable=self.var_sbs,
            onvalue="1",
            offvalue="0",
            font=FONT_UI_SM,
            text_color=self.c["text"],
            fg_color=self.c["cyan_dim"],
            hover_color=self.c["cyan"],
            border_color=self.c["border"],
            checkbox_width=20,
            checkbox_height=20,
        )
        self.cb_sbs.pack(side="left", padx=(0, 14))

        ctk.CTkLabel(
            self.frame_options, text="Error pixel limit:", font=FONT_UI_SM, text_color=self.c["muted"],
        ).pack(side="left", padx=(0, 6))

        self.entry_pixel_limit = ctk.CTkEntry(
            self.frame_options,
            width=72,
            height=32,
            font=FONT_METRIC,
            fg_color=self.c["panel_elev"],
            border_color=self.c["border"],
            text_color=self.c["text"],
        )
        self.entry_pixel_limit.pack(side="left")
        self.entry_pixel_limit.insert(0, "200")
        self.entry_pixel_limit.bind("<KeyRelease>", self._on_limit_entry_change)

        self.btn_apply_ini = ctk.CTkButton(
            self.frame_right,
            text="APPLY → SETTINGS.INI",
            height=36,
            font=FONT_BTN,
            fg_color=self.c["cyan_dim"],
            hover_color=self.c["cyan"],
            text_color=self.c["text"],
            corner_radius=10,
            border_width=2,
            border_color=self.c["primary_border"],
            command=self.apply_thresholds_to_settings,
        )
        self.btn_apply_ini.pack(fill="x", pady=(6, 10))

        self.btn_stop = ctk.CTkButton(
            self.frame_right,
            text="ANALYZER STOPPEN",
            height=40,
            font=("Segoe UI Black", 11),
            fg_color=self.c["stop"],
            hover_color=self.c["stop_hover"],
            text_color="#ffffff",
            corner_radius=10,
            border_width=2,
            border_color=self.c["stop_border"],
            command=self.close_analyzer,
        )
        self.btn_stop.pack(fill="x")

        self.bind("<space>", lambda e: self.toggle_play())
        self.bind("<Left>", lambda e: self.jump_frames(-1))
        self.bind("<Right>", lambda e: self.jump_frames(1))

        self._on_limit_entry_change()
        self.update_frame_loop()

    def _on_limit_entry_change(self, event=None):
        try:
            v = int(self.entry_pixel_limit.get())
            self.lbl_limit_hint.configure(text=f"Error Limit: {v}")
        except ValueError:
            self.lbl_limit_hint.configure(text="Error Limit: (invalid)")

    def _show_shortcuts_help(self):
        # Defer so a long-running draw callback can finish; avoids multi-second click delay.
        self.after(0, self._show_shortcuts_help_deferred)

    def _show_shortcuts_help_deferred(self):
        messagebox.showinfo(
            "Analyzer",
            "Keyboard:\n"
            "  Space — Play / Pause\n"
            "  Left / Right — Previous / next frame\n\n"
            "Playback:\n"
            "  “Max FPS” is only an upper limit. If decoding + diff is slow, the real\n"
            "  frame rate drops (that is load, not an extra artificial slowdown).\n\n"
            "Use “Apply thresholds → settings.ini” for sensitivity + error pixel limit.",
        )

    def update_frame_loop(self):
        if self.is_playing:
            elapsed_time = time.time() - self.last_update_time
            min_interval = 1.0 / max(1, self.max_playback_fps)
            if elapsed_time < min_interval:
                wait_ms = max(1, int((min_interval - elapsed_time) * 1000))
                self.after(wait_ms, self.update_frame_loop)
                return

            self.current_frame += 1
            if self.current_frame >= self.total_frames:
                self.current_frame = 0
                self._sequential_next_index = None

            self.last_update_time = time.time()
            self.draw_single_frame()
            self.after(1, self.update_frame_loop)

    def draw_single_frame(self):
        use_sequential = (
            self._sequential_next_index is not None
            and self.current_frame == self._sequential_next_index
        )
        if use_sequential:
            ret_o, frame_orig = self.cap_orig.read()
            ret_d, frame_df = self.cap_df.read()
        else:
            self.cap_orig.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            self.cap_df.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            ret_o, frame_orig = self.cap_orig.read()
            ret_d, frame_df = self.cap_df.read()

        if not ret_o or not ret_d:
            print("[SYSTEM] Video ended or read error.")
            self._sequential_next_index = None
            self.toggle_play()
            return

        frame_orig = _video_frame_to_bgr(frame_orig)
        frame_df = _video_frame_to_bgr(frame_df)
        if frame_orig.shape[:2] != frame_df.shape[:2]:
            if not self._logged_frame_shape_mismatch:
                self._logged_frame_shape_mismatch = True
                ho, wo = frame_orig.shape[:2]
                hd, wd = frame_df.shape[:2]
                print(
                    "[Analyzer] Frame size mismatch (orig vs deepfake). "
                    f"Scaling deepfake {wd}x{hd} → {wo}x{ho} for pixel diff."
                )
            frame_df = _match_deepfake_to_original(frame_orig, frame_df)

        frame_diff_gray = cv2.absdiff(
            cv2.cvtColor(frame_orig, cv2.COLOR_BGR2GRAY),
            cv2.cvtColor(frame_df, cv2.COLOR_BGR2GRAY),
        )

        _, mask = cv2.threshold(frame_diff_gray, self.threshold, 255, cv2.THRESH_BINARY)

        diff_pixels = cv2.countNonZero(mask)
        self.lbl_pixel_info.configure(text=f"Diff Pixels: {diff_pixels:,}")

        try:
            pixel_limit = int(self.entry_pixel_limit.get())
        except ValueError:
            pixel_limit = 200

        if diff_pixels >= pixel_limit:
            self.lbl_status.configure(text="STATUS: OK", text_color=self.c["ok"])
            self.frame_status_pill.configure(
                fg_color=self.c["pill_ok_bg"], border_width=1, border_color=self.c["ok"]
            )
        else:
            self.lbl_status.configure(text="STATUS: NOT OK", text_color=self.c["bad"])
            self.frame_status_pill.configure(
                fg_color=self.c["pill_bad_bg"], border_width=1, border_color=self.c["bad"]
            )

        mask_colored = cv2.merge([mask, np.zeros_like(mask), mask])

        frame_orig_final = cv2.addWeighted(frame_orig, 1.0, mask_colored, self.overlay_opacity, 0)

        is_sbs = self.var_sbs.get() == "1"

        if is_sbs:
            frame_df_final = cv2.addWeighted(frame_df, 1.0, mask_colored, self.overlay_opacity, 0)
            cv2.putText(frame_orig_final, "ORIGINAL", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
            cv2.putText(frame_df_final, "DEEPFAKE", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            frame_final = cv2.hconcat([frame_orig_final, frame_df_final])
            aspect_modifier = 2
        else:
            frame_final = frame_orig_final
            aspect_modifier = 1

        frame_rgb = cv2.cvtColor(frame_final, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(frame_rgb)

        disp_w = int(self.lbl_video_display.winfo_width())
        if disp_w < 10:
            disp_w = 800
        disp_h = int(disp_w * (self.height / (self.width * aspect_modifier)))
        if disp_h < 1:
            disp_h = 100

        img_ctk = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=(disp_w, disp_h))
        self.lbl_video_display.configure(image=img_ctk)

        self.slider_scrub.configure(command=None)
        self.slider_scrub.set(self.current_frame)
        self.slider_scrub.configure(command=self.set_frame_manual)
        self.lbl_frame_info.configure(text=f"Frame: {self.current_frame} / {self.total_frames}")

        if self.current_frame + 1 < self.total_frames:
            self._sequential_next_index = self.current_frame + 1
        else:
            self._sequential_next_index = None

        self.update_idletasks()

    def toggle_play(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self._sequential_next_index = None
            self.btn_play_pause.configure(
                text="⏸",
                fg_color=self.c["cyan_dim"],
                hover_color=self.c["cyan"],
                border_width=2,
                border_color=self.c["primary_border"],
            )
            self.last_update_time = time.time()
            self.update_frame_loop()
        else:
            self.btn_play_pause.configure(
                text="▶",
                fg_color=self.c["paused_play_fg"],
                hover_color=self.c["paused_play_hover"],
                border_width=2,
                border_color=self.c["paused_play_border"],
            )

    def jump_frames(self, delta):
        self._sequential_next_index = None
        self.current_frame = max(0, min(self.total_frames - 1, self.current_frame + delta))
        if not self.is_playing:
            self.draw_single_frame()

    def set_frame_manual(self, value):
        self._sequential_next_index = None
        self.current_frame = int(value)
        if not self.is_playing:
            self.draw_single_frame()

    def change_threshold(self, value):
        self.threshold = int(value)
        self.lbl_sens_val.configure(text=str(self.threshold))
        if not self.is_playing:
            self.draw_single_frame()

    def change_overlay_pct(self, value):
        pct = int(round(float(value)))
        pct = max(5, min(100, pct))
        self.overlay_opacity = pct / 100.0
        self.lbl_overlay_pct.configure(text=f"{pct}%")
        if not self.is_playing:
            self.draw_single_frame()

    def change_playback_fps(self, value):
        self.max_playback_fps = max(1, int(round(float(value))))
        self.lbl_fps_val.configure(text=str(self.max_playback_fps))

    def apply_thresholds_to_settings(self):
        ini_path = os.path.join(get_base_dir(), 'settings.ini')
        if not os.path.isfile(ini_path):
            messagebox.showerror(
                "settings.ini",
                "settings.ini was not found next to this program.\n"
                "Create it via the Control Center (Save) or run Compare once.",
            )
            return
        try:
            from compare import write_settings_pixel_thresholds
        except ImportError:
            messagebox.showerror(
                "Import",
                "compare.py must be in the same folder (typical in src / dev).",
            )
            return
        try:
            pix_limit = int(self.entry_pixel_limit.get())
        except ValueError:
            pix_limit = 200
        if write_settings_pixel_thresholds(
            get_base_dir(),
            pixel_noise_threshold=self.threshold,
            changed_pixels_threshold=pix_limit,
        ):
            messagebox.showinfo(
                "Saved",
                "settings.ini updated:\n"
                f"pixel_noise_threshold = {self.threshold}\n"
                f"changed_pixels_threshold = {pix_limit}",
            )
        else:
            messagebox.showerror(
                "Save failed",
                "Could not write settings.ini (missing [SETTINGS] section?).",
            )

    def close_analyzer(self):
        self.is_playing = False
        self.cap_orig.release()
        self.cap_df.release()
        self.destroy()


def _strip_flickercheck_script_from_argv(parts):
    """``python flickercheck_ui.py A B`` puts this script at argv[1]; frozen exe has only video paths."""
    if not parts:
        return parts
    if getattr(sys, "frozen", False):
        return parts
    try:
        here = os.path.abspath(__file__)
        p0 = os.path.abspath(parts[0])
        if os.path.isfile(parts[0]) and os.path.normcase(p0) == os.path.normcase(here):
            return parts[1:]
    except (OSError, ValueError, TypeError):
        pass
    return parts


if __name__ == "__main__":
    tail = _strip_flickercheck_script_from_argv(list(sys.argv[1:]))
    if len(tail) < 2:
        root = ctk.CTk()
        ctk.CTkLabel(
            root,
            text="Error: Launch from the Control Center with two video paths, or run:\n"
            "  flickercheck_ui.exe <original> <deepfake>\n"
            "  python flickercheck_ui.py <original> <deepfake>",
            padx=20,
            pady=20,
        ).pack()
        root.mainloop()
    else:
        video_orig = tail[0]
        video_df = tail[1]
        app = FlickercheckUI(video_orig, video_df)
        app.mainloop()
