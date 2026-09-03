import os
import sys
import threading
import time
import tkinter as tk
from pathlib import Path

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
TOTAL_RUNTIME_SECONDS = 5 * 60


def initialize_csv_output():
    global DESKTOP_RESULTS_DIR
    csv_output.DESKTOP_RESULTS_DIR = DESKTOP_RESULTS_DIR
    return csv_output.initialize_csv_output()


def append_csv_row(csv_row, output_path=None):
    global DESKTOP_RESULTS_DIR
    csv_output.DESKTOP_RESULTS_DIR = DESKTOP_RESULTS_DIR
    return csv_output.append_csv_row(csv_row, output_path=output_path)


def run_cycle(loop_number, camera, stop_event, status_callback):
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

# Added block:
        collected_values = camera.collect_tag_values(timeout=5.0, minimum_values=5)
        if len(collected_values) < 5:
            print(
                f"Step {step + 1}: only {len(collected_values)} tag values captured; recording 5 more seconds"
            )
            extra_values = camera.collect_tag_values(
                timeout=5.0,
                minimum_values=max(1, 5 - len(collected_values)),
            )
            if extra_values:
                collected_values.extend(extra_values)

        if not collected_values:
            print(f"Step {step + 1}: no tag values received")
        else:
            csv_value = ",".join(collected_values)
            print(f"Step {step + 1} values: {csv_value}")
            cycle_values.extend(collected_values)

        if sleep_interruptible(BALL_STEP_PAUSE, stop_event):
            return "stopped", None, None

    print("Examining data collection...", flush=True)
    count = NUM_STEPS
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
    root.configure(bg="#102027")

    status_text = tk.StringVar(value="Ready")
    cycle_text = tk.StringVar(value="No cycles completed")
    values_text = tk.StringVar(value="")
    stop_event = threading.Event()
    worker = None

    title = tk.Label(
        root,
        text="AutoLotto",
        font=("Helvetica", 32, "bold"),
        fg="#ffffff",
        bg="#102027",
    )
    title.pack(pady=(28, 12))
    status_label = tk.Label(
        root,
        textvariable=status_text,
        font=("Helvetica", 25),
        fg="#80cbc4",
        bg="#102027",
    )
    status_label.pack(pady=12)
    tk.Label(
        root,
        textvariable=cycle_text,
        font=("Helvetica", 18),
        fg="#cfd8dc",
        bg="#102027",
    ).pack(pady=4)
    tk.Label(
        root,
        textvariable=values_text,
        font=("Helvetica", 18),
        fg="#cfd8dc",
        bg="#102027",
        wraplength=720,
    ).pack(pady=4)

    try:
        camera = C200Camera()
        setup_gpio()
        initialize_csv_output()
    except (RuntimeError, ImportError) as exc:
        status_text.set(f"Unable to initialize: {exc}")
        tk.Button(
            root, text="CLOSE", command=root.destroy, font=("Helvetica", 24, "bold")
        ).pack(pady=40, ipadx=40, ipady=20)
        root.mainloop()
        return

    button = tk.Button(
        root,
        text="START",
        font=("Helvetica", 28, "bold"),
        fg="#ffffff",
        bg="#168aad",
        activebackground="#1a759f",
        width=10,
        height=2,
        relief="flat",
    )
    button.pack(pady=28)

    def update_status(message):
        root.after(0, status_text.set, message)

    def finished():
        button.config(text="CLOSE", command=root.destroy, state="normal", bg="#168aad")
        status_text.set("Complete")

    def run_program():
        reason = None
        cycle_number = 0
        start_time = time.time()
        try:
            while not stop_event.is_set() and time.time() - start_time < TOTAL_RUNTIME_SECONDS:
                cycle_number += 1
                update_status(f"Starting cycle {cycle_number}")
                status, count, csv_row = run_cycle(
                    cycle_number, camera, stop_event, update_status
                )
                if status == "stopped":
                    reason = "stop button"
                    break
                root.after(0, cycle_text.set, f"Cycle {cycle_number} complete")
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
        nonlocal worker
        stop_event.clear()
        button.config(text="STOP", command=stop_program, bg="#d62828")
        worker = threading.Thread(target=run_program, daemon=True)
        worker.start()

    def stop_program():
        stop_event.set()
        button.config(state="disabled")
        status_text.set("Stopping...")

    def close_program():
        if worker is not None and worker.is_alive():
            stop_program()
            return
        cleanup(camera)
        root.destroy()

    button.config(command=start_program)
    root.protocol("WM_DELETE_WINDOW", close_program)
    root.mainloop()


if __name__ == "__main__":
    main()
