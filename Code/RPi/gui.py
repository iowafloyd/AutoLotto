import base64
import threading
import time
import tkinter as tk

import cv2

import csv_output
from config import (
    DEFAULT_RUNTIME_MINUTES,
    DESKTOP_RESULTS_DIR,
    RUNTIME_STEP_MINUTES,
)
from results_filter import filter_latest_results


class AutoLottoApp:
    def __init__(self, root, camera, controller):
        self.root = root
        self.camera = camera
        self.controller = controller
        self.root.title("AutoLotto")
        self.root.geometry("800x480")
        self.root.minsize(800, 480)

        self.navy = "#071727"
        self.panel = "#0b1d31"
        self.panel_border = "#1d3c5c"
        self.muted = "#91a9c9"
        self.light_blue = "#59c4ee"
        self.green = "#13d77d"
        self.bright_blue = "#238df2"
        self.dark_button = "#1d3552"
        self.root.configure(bg=self.navy)

        self.status_text = tk.StringVar(value="Status: Ready")
        self.cycle_text = tk.StringVar(value="Cycle # 0")
        self.values_text = tk.StringVar(value="")
        self.camera_toggle_text = tk.StringVar(value="◩  WEBCAM OFF")
        self.runtime_minutes = tk.IntVar(value=DEFAULT_RUNTIME_MINUTES)
        self.elapsed_text = tk.StringVar(value="Elapsed Time: 0 min")
        self.stop_event = threading.Event()
        self.worker = None
        self.camera_enabled = False
        self.selected_runtime_seconds = DEFAULT_RUNTIME_MINUTES * 60
        self.run_start_time = None
        self._build_layout()
        self.root.protocol("WM_DELETE_WINDOW", self.close_program)
        self.root.after(100, self.update_camera_preview)
        self.root.after(1000, self.update_elapsed_time)

    def _build_layout(self):
        header = tk.Frame(self.root, bg=self.navy, height=72)
        header.grid(row=0, column=0, columnspan=3, sticky="nsew")
        header.grid_propagate(False)
        tk.Label(header, text="✣", font=("DejaVu Sans", 34, "bold"), fg=self.green, bg=self.navy).pack(side="left", padx=(24, 8))
        logo = tk.Frame(header, bg=self.navy)
        logo.pack(side="left", pady=10)
        tk.Label(logo, text="AUTO ", font=("DejaVu Sans", 25, "bold"), fg="#ffffff", bg=self.navy).pack(side="left")
        tk.Label(logo, text="LOTTO", font=("DejaVu Sans", 25, "bold"), fg=self.green, bg=self.navy).pack(side="left")
        tk.Label(header, text="RANDOM  •  FAIR  •  AUTOMATED", font=("DejaVu Sans", 9), fg=self.muted, bg=self.navy).pack(side="left", padx=18, pady=(15, 0))
        tk.Button(header, text="⚙", command=self.open_settings, font=("DejaVu Sans", 22), fg=self.muted, bg=self.navy, activebackground=self.navy, activeforeground="#ffffff", relief="flat", bd=0).pack(side="right", padx=24)

        content = tk.Frame(self.root, bg=self.navy)
        content.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=16, pady=12)
        content.grid_columnconfigure(1, weight=1)
        controls_frame = tk.Frame(content, bg=self.panel, highlightbackground=self.panel_border, highlightthickness=1)
        controls_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.start_button = tk.Button(controls_frame, text="▶  START", command=self.start_program, font=("DejaVu Sans", 15, "bold"), fg="#ffffff", bg=self.green, activebackground="#0fb96b", width=12, height=2, relief="flat")
        self.start_button.pack(fill="x", padx=16, pady=(20, 10))
        self.camera_toggle_button = tk.Button(controls_frame, textvariable=self.camera_toggle_text, command=self.toggle_camera, font=("DejaVu Sans", 12, "bold"), fg="#ffffff", bg=self.dark_button, activebackground="#1677d4", relief="flat", width=12, height=2)
        self.camera_toggle_button.pack(fill="x", padx=16, pady=(20, 10))

        preview_frame = tk.Frame(content, width=410, height=230, bg="#152334", highlightbackground=self.light_blue, highlightcolor=self.light_blue, highlightthickness=3)
        preview_frame.pack_propagate(False)
        preview_frame.grid(row=0, column=1, sticky="nsew")
        self.preview_label = tk.Label(preview_frame, bg="#152334")
        self.preview_label.pack(expand=True)

        runtime_frame = tk.Frame(content, bg=self.panel, highlightbackground=self.panel_border, highlightthickness=1)
        runtime_frame.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        tk.Label(runtime_frame, text="TOTAL RUNTIME", font=("DejaVu Sans", 12), fg=self.muted, bg=self.panel).pack(anchor="w", padx=18, pady=(26, 12))
        runtime_value_frame = tk.Frame(runtime_frame, bg=self.navy, highlightbackground=self.panel_border, highlightthickness=1)
        runtime_value_frame.pack(fill="x", padx=16, pady=(0, 18))
        tk.Label(runtime_value_frame, textvariable=self.runtime_minutes, font=("DejaVu Sans", 32, "bold"), fg="#ffffff", bg=self.navy).pack(side="left", padx=(28, 8), pady=10)
        tk.Label(runtime_value_frame, text="min", font=("DejaVu Sans", 15), fg=self.muted, bg=self.navy).pack(side="left", pady=(16, 0))
        tk.Label(runtime_frame, textvariable=self.elapsed_text, font=("DejaVu Sans", 12), fg=self.muted, bg=self.panel).pack(anchor="w", padx=18, pady=(0, 12))

        footer = tk.Frame(self.root, bg=self.panel, highlightbackground=self.panel_border, highlightthickness=1)
        footer.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=18, pady=(0, 14))
        status_section = tk.Frame(footer, bg=self.panel)
        status_section.pack(side="left", fill="y", padx=22, pady=10)
        tk.Label(status_section, textvariable=self.status_text, font=("DejaVu Sans", 18, "bold"), fg=self.green, bg=self.panel).pack(anchor="w", pady=8)
        tk.Frame(footer, width=1, bg=self.panel_border).pack(side="left", fill="y", pady=10)
        values_section = tk.Frame(footer, bg=self.panel)
        values_section.pack(side="left", fill="both", expand=True, padx=22, pady=10)
        tk.Label(values_section, text="DRAWN VALUES", font=("DejaVu Sans", 9), fg=self.muted, bg=self.panel).pack(anchor="w")
        tk.Label(values_section, textvariable=self.values_text, font=("DejaVu Sans", 11), fg=self.muted, bg=self.panel, wraplength=360).pack(anchor="w", pady=(4, 0))
        tk.Frame(footer, width=1, bg=self.panel_border).pack(side="left", fill="y", pady=10)
        cycle_section = tk.Frame(footer, bg=self.panel)
        cycle_section.pack(side="right", fill="y", padx=22, pady=10)
        tk.Label(cycle_section, text="CYCLE COUNT", font=("DejaVu Sans", 9), fg=self.muted, bg=self.panel).pack(anchor="w")
        tk.Label(cycle_section, textvariable=self.cycle_text, font=("DejaVu Sans", 15, "bold"), fg="#ffffff", bg=self.panel).pack(anchor="w", pady=(4, 0))

        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)

    def change_runtime(self, amount):
        self.runtime_minutes.set(max(RUNTIME_STEP_MINUTES, self.runtime_minutes.get() + amount))

    def open_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("360x250")
        settings_window.resizable(False, False)
        settings_window.configure(bg=self.panel)
        settings_window.transient(self.root)
        settings_window.grab_set()
        tk.Label(settings_window, text="SETTINGS", font=("DejaVu Sans", 17, "bold"), fg="#ffffff", bg=self.panel).pack(pady=(20, 12))
        tk.Label(settings_window, text="TOTAL RUNTIME", font=("DejaVu Sans", 11), fg=self.muted, bg=self.panel).pack()
        stepper = tk.Frame(settings_window, bg=self.panel)
        stepper.pack(fill="x", padx=28, pady=14)
        options = {"font": ("DejaVu Sans", 24, "bold"), "width": 3, "height": 1, "fg": "#ffffff", "bg": self.dark_button, "activebackground": "#2a486b", "relief": "flat"}
        tk.Button(stepper, text="−", command=lambda: self.change_runtime(-RUNTIME_STEP_MINUTES), **options).pack(side="left", expand=True, fill="x", padx=(0, 8))
        tk.Label(stepper, textvariable=self.runtime_minutes, font=("DejaVu Sans", 24, "bold"), width=5, fg="#ffffff", bg=self.navy).pack(side="left", padx=8, ipady=5)
        tk.Button(stepper, text="+", command=lambda: self.change_runtime(RUNTIME_STEP_MINUTES), **options).pack(side="left", expand=True, fill="x", padx=(8, 0))
        tk.Button(settings_window, text="DONE", command=settings_window.destroy, font=("DejaVu Sans", 12, "bold"), fg="#ffffff", bg=self.light_blue, activebackground="#1a759f", relief="flat", width=12, height=1).pack(pady=(0, 16))

    def update_camera_preview(self):
        if self.camera_enabled:
            frame = self.camera.read_frame()
            if frame is not None:
                frame = cv2.resize(frame, (410, 224))
                success, encoded = cv2.imencode(".png", frame)
                if success:
                    image = tk.PhotoImage(data=base64.b64encode(encoded.tobytes()).decode("ascii"))
                    self.preview_label.configure(image=image)
                    self.preview_label.image = image
        else:
            self.preview_label.configure(image="")
            self.preview_label.image = None
        self.root.after(100, self.update_camera_preview)

    def update_elapsed_time(self):
        if self.run_start_time is not None:
            elapsed_minutes = int((time.time() - self.run_start_time) // 60)
            self.elapsed_text.set(f"Elapsed Time: {elapsed_minutes} min")
        self.root.after(1000, self.update_elapsed_time)

    def update_status(self, message):
        self.root.after(0, self.status_text.set, f"Status: {message}")

    def finished(self):
        self.start_button.config(text="CLOSE", command=self.root.destroy, state="normal", bg=self.light_blue)
        self.status_text.set("Status: Complete")

    def run_program(self):
        reason = None
        cycle_number = 0
        start_time = time.time()
        self.run_start_time = start_time
        runtime_seconds = self.selected_runtime_seconds
        try:
            while not self.stop_event.is_set() and time.time() - start_time < runtime_seconds:
                cycle_number += 1
                self.update_status(f"Starting cycle {cycle_number}")
                status, _count, csv_row = self.controller.run_cycle(
                    self.stop_event,
                    self.update_status,
                    lambda values: self.root.after(0, self.values_text.set, values),
                )
                if status == "stopped":
                    reason = "stop button"
                    break
                if status == "timeout":
                    reason = "ball confirmation timeout"
                    break
                self.root.after(0, self.cycle_text.set, f"Cycle # {cycle_number}")
                if csv_row:
                    self.root.after(0, self.values_text.set, csv_row.split("\t", 1)[-1])
                    csv_output.append_csv_row(csv_row)
                self.update_status("Ready for next cycle")
            if reason is None:
                reason = "total runtime reached"
        finally:
            self.update_status("Stopping systems")
            self.controller.shutdown(reason)
            self.update_status("Filtering results")
            filter_latest_results(DESKTOP_RESULTS_DIR)
            self.controller.cleanup()
            self.root.after(0, self.finished)

    def start_program(self):
        self.stop_event.clear()
        self.selected_runtime_seconds = self.runtime_minutes.get() * 60
        self.run_start_time = time.time()
        self.start_button.config(text="STOP", command=self.stop_program, bg="#d62828")
        self.worker = threading.Thread(target=self.run_program, daemon=True)
        self.worker.start()

    def toggle_camera(self):
        self.camera_enabled = not self.camera_enabled
        self.camera_toggle_text.set("▣  WEBCAM ON" if self.camera_enabled else "◩  WEBCAM OFF")
        self.camera_toggle_button.config(bg=self.bright_blue if self.camera_enabled else self.dark_button)

    def stop_program(self):
        self.stop_event.set()
        self.start_button.config(state="disabled")
        self.status_text.set("Status: Stopping...")

    def close_program(self):
        if self.worker is not None and self.worker.is_alive():
            self.stop_program()
            return
        self.controller.cleanup()
        self.root.destroy()

    def run(self):
        self.root.mainloop()
