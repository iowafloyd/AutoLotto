import os
import sys
import time
from camera_comm import initialize_camera_serial, send_camera_command, read_camera_line
from csv_output import append_csv_row, initialize_csv_output
from logging_utils import log_completion, log_error
from motion_control import actuator_extend, actuator_retract, actuator_stop, gpio_cleanup, motor_run, motor_stop, setup_gpio
from terminal_io import check_for_keypress, enable_raw_mode, restore_terminal, sleep_interruptible


# ---------------------------
# GPIO SETUP
# ---------------------------
setup_gpio()

# ---------------------------
# SERIAL SETUP (OpenMV)
# ---------------------------
ser = initialize_camera_serial('/dev/ttyACM0', 115200, timeout=10)
if ser is None:
    gpio_cleanup()
    sys.exit(1)

# ---------------------------
# PARAMETERS
# ---------------------------
FULL_EXTENSION_TIME = 5.0 # 5 seconds from base to bottom of dome
FULL_RETRACTION_TIME = 6.0 # 6 seconds from bottom of dome to base ensuring full retraction
BALL_STEP_TIME = 25.0 / 47.0 # Time for each ball step (25mm ball)
BALL_STEP_PAUSE = 0.1 # Pause between ball steps to ensure motor has time to stop and settle, camera can capture the ball
NUM_STEPS = 5 # Number of balls per drawing
MOTOR_RUN_TIME = 7.5 # Time for motor to run (tweak as needed for more/less randomization)
TOTAL_RUNTIME_SECONDS = 2 * 60  # Two minutes total runtime for testing purposes

# ---------------------------
# MAIN SEQUENCE
# ---------------------------
def run_cycle():
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

    print("Sending 'r' to start recording...")
    # send_camera_command('r', expected_ack='ACK:r')

    print("Beginning ball extraction.")
    for _ in range(NUM_STEPS):
        actuator_retract()
        if sleep_interruptible(BALL_STEP_TIME):
            return "stopped", None, None
        actuator_stop()
        motor_run()
        if sleep_interruptible(1.0):
            return "stopped", None, None
        motor_stop()
        if sleep_interruptible(BALL_STEP_PAUSE):
            return "stopped", None, None

    print("Sending 's' to stop recording...")
    # send_camera_command('s', expected_ack='ACK:s')

    # Handshake and camera data collection disabled for testing.
    print("Skipping camera handshake and data collection for testing.", flush=True)
    return "ok", None, None


# ---------------------------
# CLEANUP
# ---------------------------
def shutdown_sequence(reason):
    print(f"Stopping all systems ({reason})...")
    motor_stop()
    # send_camera_command('s', expected_ack='ACK:s')

    print("Full actuator retraction before shutdown")
    actuator_retract()
    time.sleep(FULL_RETRACTION_TIME)
    actuator_stop()

    log_completion(reason)


def cleanup():
    actuator_stop()
    motor_stop()
    gpio_cleanup()
    if ser is not None:
        ser.close()
    restore_terminal()
    print("Clean shutdown.")


# ---------------------------
# ENTRY POINT
# ---------------------------
if __name__ == "__main__":
    try:
        initialize_csv_output()
        enable_raw_mode()
        start_time = time.time()
        reason = None
        cycle_number = 0

        while True:
            if time.time() - start_time >= TOTAL_RUNTIME_SECONDS:
                reason = "total runtime reached"
                break

            if check_for_keypress():
                reason = "key press"
                print("A key was pressed. Stopping the program.", flush=True)
                break

            cycle_number += 1
            print(f"Starting loop {cycle_number}...", flush=True)
            status, count, csv_row = run_cycle()
            if status == "stopped":
                reason = "key press"
                print("A key was pressed. Stopping the program.", flush=True)
                break

            if count is None:
                print(f"Loop {cycle_number} did not receive a valid count.", flush=True)
            else:
                print(f"Loop {cycle_number} ball count: {count}", flush=True)
                print("PASS" if count == 5 else "FAIL", flush=True)

            if csv_row:
                print(f"Loop {cycle_number} CSV row: {csv_row}", flush=True)

            print("Cycle complete. Press any key to stop the program.", flush=True)
    except KeyboardInterrupt:
        reason = "keyboard interrupt"
        print("\nInterrupted by user.")
    finally:
        if reason is not None:
            shutdown_sequence(reason)
        cleanup()
