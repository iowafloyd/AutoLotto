import os
import select
import sys
import termios
import time
import tty
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
from terminal_io import enable_raw_mode, restore_terminal, sleep_interruptible

DESKTOP_RESULTS_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "Results")

FULL_EXTENSION_TIME = 5.0 # Actuator extension until platform meets bottom of dome
FULL_RETRACTION_TIME = 6.0
BALL_STEP_TIME = 30.0 / 47.0
BALL_STEP_PAUSE = 0.2
NUM_STEPS = 5
MOTOR_RUN_TIME = 7.5
MOTOR_JOG_TIME = 1.5
TOTAL_RUNTIME_SECONDS = 30 * 60


def initialize_csv_output():
    global DESKTOP_RESULTS_DIR
    csv_output.DESKTOP_RESULTS_DIR = DESKTOP_RESULTS_DIR
    return csv_output.initialize_csv_output()


def append_csv_row(csv_row, output_path=None):
    global DESKTOP_RESULTS_DIR
    csv_output.DESKTOP_RESULTS_DIR = DESKTOP_RESULTS_DIR
    return csv_output.append_csv_row(csv_row, output_path=output_path)


def run_cycle(loop_number, camera):
    print("Full retraction...", flush=True)
    actuator_retract()
    if sleep_interruptible(FULL_RETRACTION_TIME):
        return "stopped", None, None
    actuator_stop()

    print("Full extension...", flush=True)
    actuator_extend()
    if sleep_interruptible(FULL_EXTENSION_TIME):
        return "stopped", None, None
    actuator_stop()

    print("Starting randomization...", flush=True)
    motor_run()
    if sleep_interruptible(MOTOR_RUN_TIME):
        return "stopped", None, None
    motor_stop()

    print("Randomization complete. Starting data collection.")
    print("Beginning ball extraction.")
    cycle_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    cycle_values = []

    for step in range(NUM_STEPS):
        actuator_retract()

        if sleep_interruptible(BALL_STEP_TIME):
            return "stopped", None, None
        actuator_stop()
        # 1 second of motor run to allow ball drop
        motor_run()
        if sleep_interruptible(1.0):
            return "stopped", None, None
        motor_stop()

        if step == 0:
            print("Motor jog after first ball retraction...")
            motor_run()
            if sleep_interruptible(MOTOR_JOG_TIME):
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

        if sleep_interruptible(BALL_STEP_PAUSE):
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
    restore_terminal()
    print("Clean shutdown.")


def main():
    try:
        camera = C200Camera()
    except (RuntimeError, ImportError) as exc:
        print(f"Unable to initialize C200 camera: {exc}")
        sys.exit(1)

    setup_gpio()
    initialize_csv_output()
    enable_raw_mode()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setraw(fd)

    try:
        start_time = time.time()
        reason = None
        cycle_number = 0
        while True:
            if select.select([sys.stdin], [], [], 0.1)[0]:
                sys.stdin.read(1)
                print("Exiting.")
                reason = "key press"
                break

            if time.time() - start_time >= TOTAL_RUNTIME_SECONDS:
                reason = "total runtime reached"
                break

            cycle_number += 1
            print(f"Starting loop {cycle_number}...", flush=True)
            status, count, csv_row = run_cycle(cycle_number, camera)
            if status == "stopped":
                reason = "key press"
                print("A key was pressed. Stopping the program.", flush=True)
                break

            if count is None:
                print(f"Loop {cycle_number} ball count: unknown", flush=True)
                if csv_row:
                    print(f"Loop {cycle_number} values: {csv_row}", flush=True)
                print("FAIL", flush=True)
            else:
                print(f"Loop {cycle_number} ball count: {count}", flush=True)
                if csv_row:
                    print(f"Loop {cycle_number} values: {csv_row}", flush=True)
                    append_csv_row(csv_row)
                print("PASS" if count == NUM_STEPS else "FAIL", flush=True)

            print("Cycle complete. Press any key to stop the program.", flush=True)
    except KeyboardInterrupt:
        reason = "keyboard interrupt"
        print("\nInterrupted by user.")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        if reason is not None:
            shutdown_sequence(reason)
        cleanup(camera)


if __name__ == "__main__":
    main()
