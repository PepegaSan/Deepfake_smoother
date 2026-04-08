import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image, ImageTk
import os
import sys
import time
from tkinter import messagebox

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

class FlickercheckUI(ctk.CTk):
    def __init__(self, video_orig_path, video_df_path):
        super().__init__()
        self.title("Deepfake Flickercheck Analyzer")
        self.geometry("1100x850")
        
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
        
        self.rowconfigure(0, weight=1) 
        self.columnconfigure(0, weight=1)
        
        self.video_frame = ctk.CTkFrame(self, fg_color="black")
        self.video_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        self.lbl_video_display = ctk.CTkLabel(self.video_frame, text="")
        self.lbl_video_display.pack(fill="both", expand=True)

        self.frame_controls = ctk.CTkFrame(self)
        self.frame_controls.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.frame_controls.columnconfigure(2, weight=1)

        # Row 0: Slider, Frame Count & Pixels
        self.lbl_frame_info = ctk.CTkLabel(self.frame_controls, text=f"Frame: 0 / {self.total_frames}", font=("Arial", 12, "bold"))
        self.lbl_frame_info.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.slider_scrub = ctk.CTkSlider(self.frame_controls, from_=0, to=self.total_frames-1, number_of_steps=self.total_frames, command=self.set_frame_manual)
        self.slider_scrub.grid(row=0, column=1, columnspan=3, padx=10, pady=5, sticky="ew")
        self.slider_scrub.set(0)

        self.lbl_pixel_info = ctk.CTkLabel(self.frame_controls, text="Diff Pixels: 0", font=("Arial", 14, "bold"), text_color="#ff00ff")
        self.lbl_pixel_info.grid(row=0, column=4, padx=10, pady=5, sticky="e")
        
        # Row 1: Navigation
        self.btn_rewind = ctk.CTkButton(self.frame_controls, text="⏪ -100", width=80, command=lambda: self.jump_frames(-100))
        self.btn_rewind.grid(row=1, column=0, padx=5, pady=5)
        
        self.btn_prev = ctk.CTkButton(self.frame_controls, text="< 1", width=50, command=lambda: self.jump_frames(-1))
        self.btn_prev.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.btn_play_pause = ctk.CTkButton(self.frame_controls, text="⏸ Pause [Space]", fg_color="#b8860b", hover_color="#8b6508", command=self.toggle_play)
        self.btn_play_pause.grid(row=1, column=2, padx=10, pady=10)

        self.btn_next = ctk.CTkButton(self.frame_controls, text="1 >", width=50, command=lambda: self.jump_frames(1))
        self.btn_next.grid(row=1, column=3, padx=5, pady=5, sticky="e")

        self.btn_forward = ctk.CTkButton(self.frame_controls, text="⏩ +100", width=80, command=lambda: self.jump_frames(100))
        self.btn_forward.grid(row=1, column=4, padx=5, pady=5)

        # Row 2: Status (Zentriert unter dem Play Button, extra groß)
        self.lbl_status = ctk.CTkLabel(self.frame_controls, text="Status: -", font=("Arial", 24, "bold"))
        self.lbl_status.grid(row=2, column=2, padx=10, pady=(10, 5))

        # Row 3: Sensitivity Slider
        self.lbl_sens = ctk.CTkLabel(self.frame_controls, text="Difference Sensitivity (Threshold):", font=("Arial", 11, "bold"))
        self.lbl_sens.grid(row=3, column=0, columnspan=2, padx=10, pady=(5,0), sticky="w")
        
        self.slider_sens = ctk.CTkSlider(self.frame_controls, from_=5, to=150, number_of_steps=145, fg_color="magenta", command=self.change_threshold)
        self.slider_sens.grid(row=4, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")
        self.slider_sens.set(self.threshold)
        
        self.lbl_sens_val = ctk.CTkLabel(self.frame_controls, text=str(self.threshold))
        self.lbl_sens_val.grid(row=4, column=2, padx=5, pady=(0, 10), sticky="w")

        # Row 5: View Options & Limits
        self.frame_options = ctk.CTkFrame(self.frame_controls, fg_color="transparent")
        self.frame_options.grid(row=5, column=0, columnspan=4, padx=10, pady=10, sticky="w")

        self.var_sbs = ctk.StringVar(value="0")
        self.cb_sbs = ctk.CTkCheckBox(self.frame_options, text="Side-by-Side View", variable=self.var_sbs, onvalue="1", offvalue="0")
        self.cb_sbs.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(self.frame_options, text="Error Pixel Limit:").pack(side="left", padx=(0, 5))
        self.entry_pixel_limit = ctk.CTkEntry(self.frame_options, width=80)
        self.entry_pixel_limit.pack(side="left")
        self.entry_pixel_limit.insert(0, "200")

        self.btn_apply_ini = ctk.CTkButton(
            self.frame_options,
            text="Apply thresholds → settings.ini",
            width=210,
            command=self.apply_thresholds_to_settings,
        )
        self.btn_apply_ini.pack(side="left", padx=(16, 0))

        self.btn_stop = ctk.CTkButton(self.frame_controls, text="⏹ Stop Analyzer", fg_color="red", hover_color="darkred", command=self.close_analyzer)
        self.btn_stop.grid(row=5, column=4, padx=10, pady=10)

        self.bind("<space>", lambda e: self.toggle_play())
        self.bind("<Left>", lambda e: self.jump_frames(-1))
        self.bind("<Right>", lambda e: self.jump_frames(1))

        self.update_frame_loop()

    def update_frame_loop(self):
        if self.is_playing:
            elapsed_time = time.time() - self.last_update_time
            if elapsed_time < 0.033: 
                self.after(5, self.update_frame_loop)
                return

            self.current_frame += 1
            if self.current_frame >= self.total_frames:
                self.current_frame = 0 

            self.last_update_time = time.time()
            self.draw_single_frame()
            self.after(1, self.update_frame_loop)

    def draw_single_frame(self):
        self.cap_orig.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        self.cap_df.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)

        ret_o, frame_orig = self.cap_orig.read()
        ret_d, frame_df = self.cap_df.read()

        if not ret_o or not ret_d:
            print("[SYSTEM] Video ended or read error.")
            self.toggle_play()
            return

        frame_diff_gray = cv2.absdiff(cv2.cvtColor(frame_orig, cv2.COLOR_BGR2GRAY), 
                                      cv2.cvtColor(frame_df, cv2.COLOR_BGR2GRAY))
        
        _, mask = cv2.threshold(frame_diff_gray, self.threshold, 255, cv2.THRESH_BINARY)
        
        diff_pixels = cv2.countNonZero(mask)
        self.lbl_pixel_info.configure(text=f"Diff Pixels: {diff_pixels}")

        try:
            pixel_limit = int(self.entry_pixel_limit.get())
        except ValueError:
            pixel_limit = 200 
            
        # Korrigierte Logik: Über Limit = Swap hat stattgefunden (OK). Unter Limit = Swap-Fehler (NOT OK).
        if diff_pixels >= pixel_limit:
            self.lbl_status.configure(text="Status: OK", text_color="green")
        else:
            self.lbl_status.configure(text="Status: NOT OK", text_color="red")
        
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
        if disp_w < 10: disp_w = 800 # Fallback beim ersten Laden
        disp_h = int(disp_w * (self.height / (self.width * aspect_modifier))) 
        if disp_h < 1: disp_h = 100 

        img_ctk = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=(disp_w, disp_h))
        self.lbl_video_display.configure(image=img_ctk)
        
        self.slider_scrub.configure(command=None) 
        self.slider_scrub.set(self.current_frame)
        self.slider_scrub.configure(command=self.set_frame_manual) 
        self.lbl_frame_info.configure(text=f"Frame: {self.current_frame} / {self.total_frames}")

    def toggle_play(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.btn_play_pause.configure(text="⏸ Pause [Space]", fg_color="#b8860b")
            self.last_update_time = time.time()
            self.update_frame_loop()
        else:
            self.btn_play_pause.configure(text="▶ Play [Space]", fg_color="green")

    def jump_frames(self, delta):
        self.current_frame = max(0, min(self.total_frames-1, self.current_frame + delta))
        if not self.is_playing:
            self.draw_single_frame()

    def set_frame_manual(self, value):
        self.current_frame = int(value)
        if not self.is_playing:
            self.draw_single_frame()

    def change_threshold(self, value):
        self.threshold = int(value)
        self.lbl_sens_val.configure(text=str(self.threshold))
        if not self.is_playing:
            self.draw_single_frame()

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

if __name__ == "__main__":
    if len(sys.argv) < 3:
        root = ctk.CTk()
        ctk.CTkLabel(root, text="Error: This tool must be launched via the Main Control Center.", padx=20, pady=20).pack()
        root.mainloop()
    else:
        video_orig = sys.argv[1]
        video_df = sys.argv[2]
        app = FlickercheckUI(video_orig, video_df)
        app.mainloop()