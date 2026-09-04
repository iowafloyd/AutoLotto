import os
import base64
import sys
import threading
import time
import tkinter as tk
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))

from c200_camera import C200Camera
import csv_output
from logging_utils import log_completion
from motion_control import (
    actuator_extend,
    actuator_retract,
    actuator_stop,
    gpio_cleanup,
    motor_run,
    motor_stop,
    setup_gpio,
)
from results_filter import filter_latest_results
from terminal_io import sleep_interruptible

DESKTOP_RESULTS_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "Results")

FULL_EXTENSION_TIME = 5.0 # Actuator extension until platform meets bottom of dome
FULL_RETRACTION_TIME = 6.0
BALL_STEP_TIME = 30.0 / 47.0
BALL_STEP_PAUSE = 0.2
NUM_STEPS = 5
MOTOR_RUN_TIME = 7.5
MOTOR_JOG_TIME = 1.5
DEFAULT_RUNTIME_MINUTES = 15
RUNTIME_STEP_MINUTES = 15


def initialize_csv_output():
    global DESKTOP_RESULTS_DIR
    csv_output.DESKTOP_RESULTS_DIR = DESKTOP_RESULTS_DIR
    return csv_output.initialize_csv_output()


def append_csv_row(csv_row, output_path=None):
    global DESKTOP_RESULTS_DIR
    csv_output.DESKTOP_RESULTS_DIR = DESKTOP_RESULTS_DIR
    return csv_output.append_csv_row(csv_row, output_path=output_path)


def run_cycle(
    loop_number, camera, stop_event, status_callback, drawn_values_callback=None
):
    status_callback("Retracting actuator")
    print("Full retraction...", flush=True)
    actuator_retract()
    if sleep_interruptible(FULL_RETRACTION_TIME, stop_event):
        return "stopped", None, None
    actuator_stop()

    status_callback("Extending actuator")
    print("Full extension...", flush=True)
    actuator_extend()
    if sleep_interruptible(FULL_EXTENSION_TIME, stop_event):
        return "stopped", None, None
    actuator_stop()

    status_callback("Randomizing balls")
    print("Starting randomization...", flush=True)
    motor_run()
    if sleep_interruptible(MOTOR_RUN_TIME, stop_event):
        return "stopped", None, None
    motor_stop()

    print("Randomization complete. Starting data collection.")
    print("Beginning ball extraction.")
    cycle_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    cycle_values = []
    previous_visible_tags = camera.read_tag_ids() or set()

    for step in range(NUM_STEPS):
        status_callback(f"Collecting ball {step + 1} of {NUM_STEPS}")
        actuator_retract()

        if sleep_interruptible(BALL_STEP_TIME, stop_event):
            return "stopped", None, None
        actuator_stop()
        # 1 second of motor run to allow ball drop
        motor_run()
        if sleep_interruptible(1.0, stop_event):
            return "stopped", None, None
        motor_stop()

        if step == 0:
            print("Motor jog after first ball retraction...")
            motor_run()
            if sleep_interruptible(MOTOR_JOG_TIME, stop_event):
                return "stopped", None, None
            motor_stop()

        status_callback("Waiting for ball confirmation")
        confirmed_tag, visible_tags = camera.wait_for_new_tag(
            previous_visible_tags,
            cycle_values,
            stop_event=stop_event,
        )
        if confirmed_tag is None:
            if stop_event.is_set():
                return "stopped", None, None
            status_callback("Ball confirmation timed out")
            return "timeout", None, None

        cycle_values.append(confirmed_tag)
        previous_visible_tags = visible_tags
        print(f"Step {step + 1} confirmed value: {confirmed_tag}")
        if drawn_values_callback is not None:
            drawn_values_callback(",".join(cycle_values))

        if sleep_interruptible(BALL_STEP_PAUSE, stop_event):
            return "stopped", None, None

    print("Examining data collection...", flush=True)
    count = len(cycle_values)
    if cycle_values:
        csv_row = f"{cycle_timestamp}\t{','.join(cycle_values)}"
    else:
        csv_row = cycle_timestamp
    return "ok", count, csv_row


def shutdown_sequence(reason):
    print(f"Stopping all systems ({reason})...")
    motor_stop()
    print("Full actuator retraction before shutdown")
    actuator_retract()
    time.sleep(FULL_RETRACTION_TIME)
    actuator_stop()
    log_completion(reason)


def cleanup(camera):
    actuator_stop()
    motor_stop()
    gpio_cleanup()
    camera.close()
    print("Clean shutdown.")


def main():
    root = tk.Tk()
    root.title("AutoLotto")
    root.geometry("800x480")
    root.minsize(800, 480)

    navy = "#071727"
    panel = "#0b1d31"
    panel_border = "#1d3c5c"
    muted = "#91a9c9"
    light_blue = "#59c4ee"
    green = "#13d77d"
    bright_blue = "#238df2"
    dark_button = "#1d3552"
    root.configure(bg=navy)

    status_text = tk.StringVar(value="Status: Ready")
    cycle_text = tk.StringVar(value="Cycle # 0")
    values_text = tk.StringVar(value="")
    camera_toggle_text = tk.StringVar(value="◩  WEBCAM OFF")
    runtime_minutes = tk.IntVar(value=DEFAULT_RUNTIME_MINUTES)
    elapsed_text = tk.StringVar(value="Elapsed Time: 0 min")
    stop_event = threading.Event()
    worker = None
    camera_enabled = False
    selected_runtime_seconds = DEFAULT_RUNTIME_MINUTES * 60
    run_start_time = None

    try:
        camera = C200Camera()
        setup_gpio()
        initialize_csv_output()
    except (RuntimeError, ImportError) as exc:
        status_text.set(f"Status: Unable to initialize: {exc}")
        tk.Button(
            root, text="CLOSE", command=root.destroy, font=("Helvetica", 24, "bold")
        ).pack(pady=40, ipadx=40, ipady=20)
        root.mainloop()
        return

    def change_runtime(amount):
        runtime_minutes.set(max(RUNTIME_STEP_MINUTES, runtime_minutes.get() + amount))

    def open_settings():
        settings_window = tk.Toplevel(root)
        settings_window.title("Settings")
        settings_window.geometry("360x250")
        settings_window.resizable(False, False)
        settings_window.configure(bg=panel)
        settings_window.transient(root)
        settings_window.grab_set()

        tk.Label(
            settings_window,
            text="SETTINGS",
            font=("DejaVu Sans", 17, "bold"),
            fg="#ffffff",
            bg=panel,
        ).pack(pady=(20, 12))
        tk.Label(
            settings_window,
            text="TOTAL RUNTIME",
            font=("DejaVu Sans", 11),
            fg=muted,
            bg=panel,
        ).pack()

        stepper = tk.Frame(settings_window, bg=panel)
        stepper.pack(fill="x", padx=28, pady=14)
        step_button_options = {
            "font": ("DejaVu Sans", 24, "bold"),
            "width": 3,
            "height": 1,
            "fg": "#ffffff",
            "bg": dark_button,
            "activebackground": "#2a486b",
            "relief": "flat",
        }
        tk.Button(
            stepper,
            text="−",
            command=lambda: change_runtime(-RUNTIME_STEP_MINUTES),
            **step_button_options,
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))
        tk.Label(
            stepper,
            textvariable=runtime_minutes,
            font=("DejaVu Sans", 24, "bold"),
            width=5,
            fg="#ffffff",
            bg=navy,
        ).pack(side="left", padx=8, ipady=5)
        tk.Button(
            stepper,
            text="+",
            command=lambda: change_runtime(RUNTIME_STEP_MINUTES),
            **step_button_options,
        ).pack(side="left", expand=True, fill="x", padx=(8, 0))
        tk.Button(
            settings_window,
            text="DONE",
            command=settings_window.destroy,
            font=("DejaVu Sans", 12, "bold"),
            fg="#ffffff",
            bg=light_blue,
            activebackground="#1a759f",
            relief="flat",
            width=12,
            height=1,
        ).pack(pady=(0, 16))

    header = tk.Frame(root, bg=navy, height=72)
    header.grid(row=0, column=0, columnspan=3, sticky="nsew")
    header.grid_propagate(False)
    tk.Label(
        header,
        text="✣",
        font=("DejaVu Sans", 34, "bold"),
        fg=green,
        bg=navy,
    ).pack(side="left", padx=(24, 8))
    logo = tk.Frame(header, bg=navy)
    logo.pack(side="left", pady=10)
    tk.Label(
        logo,
        text="AUTO ",
        font=("DejaVu Sans", 25, "bold"),
        fg="#ffffff",
        bg=navy,
    ).pack(side="left")
    tk.Label(
        logo,
        text="LOTTO",
        font=("DejaVu Sans", 25, "bold"),
        fg=green,
        bg=navy,
    ).pack(side="left")
    tk.Label(
        header,
        text="RANDOM  •  FAIR  •  AUTOMATED",
        font=("DejaVu Sans", 9),
        fg=muted,
        bg=navy,
    ).pack(side="left", padx=18, pady=(15, 0))
    tk.Button(
        header,
        text="⚙",
        command=open_settings,
        font=("DejaVu Sans", 22),
        fg=muted,
        bg=navy,
        activebackground=navy,
        activeforeground="#ffffff",
        relief="flat",
        bd=0,
    ).pack(side="right", padx=24)

    content = tk.Frame(root, bg=navy)
    content.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=16, pady=12)
    content.grid_columnconfigure(1, weight=1)

    controls_frame = tk.Frame(
        content, bg=panel, highlightbackground=panel_border, highlightthickness=1
    )
    controls_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

    button = tk.Button(
        controls_frame,
        text="▶  START",
        font=("DejaVu Sans", 15, "bold"),
        fg="#ffffff",
        bg=green,
        activebackground="#0fb96b",
        width=12,
        height=2,
        relief="flat",
    )
    button.pack(fill="x", padx=16, pady=(20, 10))

    camera_toggle_button = tk.Button(
        controls_frame,
        textvariable=camera_toggle_text,
        command=lambda: toggle_camera(),
        font=("DejaVu Sans", 12, "bold"),
        fg="#ffffff",
        bg=dark_button,
        activebackground="#1677d4",
        relief="flat",
        width=12,
        height=2,
    )
    camera_toggle_button.pack(fill="x", padx=16, pady=(20, 10))

    preview_frame = tk.Frame(
        content,
        width=410,
        height=230,
        bg="#152334",
        highlightbackground=light_blue,
        highlightcolor=light_blue,
        highlightthickness=3,
    )
    preview_frame.pack_propagate(False)
    preview_frame.grid(row=0, column=1, sticky="nsew")
    preview_label = tk.Label(preview_frame, bg="#152334")
    preview_label.pack(expand=True)

    runtime_frame = tk.Frame(
        content, bg=panel, highlightbackground=panel_border, highlightthickness=1
    )
    runtime_frame.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
    tk.Label(
        runtime_frame,
        text="TOTAL RUNTIME",
        font=("DejaVu Sans", 12),
        fg=muted,
        bg=panel,
    ).pack(anchor="w", padx=18, pady=(26, 12))
    runtime_value_frame = tk.Frame(
        runtime_frame,
        bg=navy,
        highlightbackground=panel_border,
        highlightthickness=1,
    )
    runtime_value_frame.pack(fill="x", padx=16, pady=(0, 18))
    tk.Label(
        runtime_value_frame,
        textvariable=runtime_minutes,
        font=("DejaVu Sans", 32, "bold"),
        fg="#ffffff",
        bg=navy,
    ).pack(side="left", padx=(28, 8), pady=10)
    tk.Label(
        runtime_value_frame,
        text="min",
        font=("DejaVu Sans", 15),
        fg=muted,
        bg=navy,
    ).pack(side="left", pady=(16, 0))
    tk.Label(
        runtime_frame,
        textvariable=elapsed_text,
        font=("DejaVu Sans", 12),
        fg=muted,
        bg=panel,
    ).pack(anchor="w", padx=18, pady=(0, 12))

    footer = tk.Frame(
        root, bg=panel, highlightbackground=panel_border, highlightthickness=1
    )
    footer.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=18, pady=(0, 14))
    status_section = tk.Frame(footer, bg=panel)
    status_section.pack(side="left", fill="y", padx=22, pady=10)
    status_label = tk.Label(
        status_section,
        textvariable=status_text,
        font=("DejaVu Sans", 18, "bold"),
        fg=green,
        bg=panel,
    )
    status_label.pack(anchor="w", pady=8)
    tk.Frame(footer, width=1, bg=panel_border).pack(side="left", fill="y", pady=10)
    values_section = tk.Frame(footer, bg=panel)
    values_section.pack(side="left", fill="both", expand=True, padx=22, pady=10)
    values_label = tk.Label(
        values_section,
        textvariable=values_text,
        font=("DejaVu Sans", 11),
        fg=muted,
        bg=panel,
        wraplength=360,
    )
    tk.Label(
        values_section,
        text="DRAWN VALUES",
        font=("DejaVu Sans", 9),
        fg=muted,
        bg=panel,
    ).pack(anchor="w")
    values_label.pack(anchor="w", pady=(4, 0))
    tk.Frame(footer, width=1, bg=panel_border).pack(side="left", fill="y", pady=10)
    cycle_section = tk.Frame(footer, bg=panel)
    cycle_section.pack(side="right", fill="y", padx=22, pady=10)
    tk.Label(
        cycle_section,
        text="CYCLE COUNT",
        font=("DejaVu Sans", 9),
        fg=muted,
        bg=panel,
    ).pack(anchor="w")
    cycle_label = tk.Label(
        cycle_section,
        textvariable=cycle_text,
        font=("DejaVu Sans", 15, "bold"),
        fg="#ffffff",
        bg=panel,
    )
    cycle_label.pack(anchor="w", pady=(4, 0))

    root.grid_rowconfigure(1, weight=1)
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)
    root.grid_columnconfigure(2, weight=1)

    def update_camera_preview():
        if camera_enabled:
            frame = camera.read_frame()
            if frame is not None:
                frame = cv2.resize(frame, (410, 224))
                success, encoded = cv2.imencode(".png", frame)
                if success:
                    image = tk.PhotoImage(
                        data=base64.b64encode(encoded.tobytes()).decode("ascii")
                    )
                    preview_label.configure(image=image)
                    preview_label.image = image
        else:
            preview_label.configure(image="")
            preview_label.image = None
        root.after(100, update_camera_preview)

    def update_elapsed_time():
        if run_start_time is not None:
            elapsed_minutes = int((time.time() - run_start_time) // 60)
            elapsed_text.set(f"Elapsed Time: {elapsed_minutes} min")
        root.after(1000, update_elapsed_time)

    def update_status(message):
        root.after(0, status_text.set, f"Status: {message}")

    def finished():
        button.config(text="CLOSE", command=root.destroy, state="normal", bg="#59c4ee")
        status_text.set("Status: Complete")

    def run_program():
        nonlocal run_start_time
        reason = None
        cycle_number = 0
        start_time = time.time()
        run_start_time = start_time
        runtime_seconds = selected_runtime_seconds
        try:
            while not stop_event.is_set() and time.time() - start_time < runtime_seconds:
                cycle_number += 1
                update_status(f"Starting cycle {cycle_number}")
                status, count, csv_row = run_cycle(
                    cycle_number,
                    camera,
                    stop_event,
                    update_status,
                    lambda values: root.after(0, values_text.set, values),
                )
                if status == "stopped":
                    reason = "stop button"
                    break
                if status == "timeout":
                    reason = "ball confirmation timeout"
                    break
                root.after(0, cycle_text.set, f"Cycle # {cycle_number}")
                if csv_row:
                    root.after(0, values_text.set, csv_row.split("\t", 1)[-1])
                    append_csv_row(csv_row)
                update_status("Ready for next cycle")
            if reason is None:
                reason = "total runtime reached"
        finally:
            update_status("Stopping systems")
            shutdown_sequence(reason)
            update_status("Filtering results")
            filter_latest_results(DESKTOP_RESULTS_DIR)
            cleanup(camera)
            root.after(0, finished)

    def start_program():
        nonlocal selected_runtime_seconds, worker, run_start_time
        stop_event.clear()
        selected_runtime_seconds = runtime_minutes.get() * 60
        run_start_time = time.time()
        button.config(text="STOP", command=stop_program, bg="#d62828")
        worker = threading.Thread(target=run_program, daemon=True)
        worker.start()

    def toggle_camera():
        nonlocal camera_enabled
        camera_enabled = not camera_enabled
        camera_toggle_text.set(
            "▣  WEBCAM ON" if camera_enabled else "◩  WEBCAM OFF"
        )
        camera_toggle_button.config(
            bg=bright_blue if camera_enabled else dark_button
        )

    def stop_program():
        stop_event.set()
        button.config(state="disabled")
        status_text.set("Status: Stopping...")

    def close_program():
        if worker is not None and worker.is_alive():
            stop_program()
            return
        cleanup(camera)
        root.destroy()

    button.config(command=start_program)
    root.protocol("WM_DELETE_WINDOW", close_program)
    root.after(100, update_camera_preview)
    root.after(1000, update_elapsed_time)
    root.mainloop()


if __name__ == "__main__":
    main()
