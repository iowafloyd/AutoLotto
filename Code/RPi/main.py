import os
import RPi.GPIO as GPIO
import time
import sys
import tty
import termios
import select
import serial

ERROR_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'error.log')


def log_error(message):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    full_message = f'[{timestamp}] {message}'
    print(f'ERROR: {full_message}', file=sys.stderr)
    with open(ERROR_LOG_PATH, 'a', encoding='utf-8') as handle:
        handle.write(full_message + '\n')


def log_completion(reason):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    message = f'Program completed at {timestamp} ({reason}) \n'
    print(message)
    with open(ERROR_LOG_PATH, 'a', encoding='utf-8') as handle:
        handle.write(f'[{timestamp}] {message}\n')


# ---------------------------
# GPIO SETUP
# ---------------------------
GPIO.setmode(GPIO.BCM)

ACT_IN1 = 19
ACT_IN2 = 26
MOTOR_IN1 = 20
MOTOR_IN2 = 21

GPIO.setup(ACT_IN1, GPIO.OUT)
GPIO.setup(ACT_IN2, GPIO.OUT)
GPIO.setup(MOTOR_IN1, GPIO.OUT)
GPIO.setup(MOTOR_IN2, GPIO.OUT)

# ---------------------------
# SERIAL SETUP (OpenMV)
# ---------------------------
try:
    ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
    print("OpenMV connected on /dev/ttyACM0")
except Exception as exc:
    ser = None
    log_error(f"OpenMV camera not detected: {exc} \n")
    GPIO.cleanup()
    sys.exit(1)

# ---------------------------
# PARAMETERS
# ---------------------------
FULL_EXTENSION_TIME = 4.0
FULL_RETRACTION_TIME = 6.0
BALL_STEP_TIME = 25.0 / 47.0
BALL_STEP_PAUSE = 0.1
NUM_STEPS = 5
MOTOR_RUN_TIME = 7.5
TOTAL_RUNTIME_SECONDS = 5 * 60  # User-defined total runtime in seconds

# ---------------------------
# ACTUATOR CONTROL
# ---------------------------
def actuator_extend():
    GPIO.output(ACT_IN1, GPIO.HIGH)
    GPIO.output(ACT_IN2, GPIO.LOW)


def actuator_retract():
    GPIO.output(ACT_IN1, GPIO.LOW)
    GPIO.output(ACT_IN2, GPIO.HIGH)


def actuator_stop():
    GPIO.output(ACT_IN1, GPIO.LOW)
    GPIO.output(ACT_IN2, GPIO.LOW)


# ---------------------------
# MOTOR CONTROL
# ---------------------------
def motor_run():
    GPIO.output(MOTOR_IN1, GPIO.HIGH)
    GPIO.output(MOTOR_IN2, GPIO.LOW)


def motor_stop():
    GPIO.output(MOTOR_IN1, GPIO.LOW)
    GPIO.output(MOTOR_IN2, GPIO.LOW)


# ---------------------------
# TERMINAL HELPERS
# ---------------------------
old_settings = None


def enable_raw_mode():
    global old_settings
    if sys.stdin.isatty():
        old_settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())


def restore_terminal():
    global old_settings
    if old_settings is not None:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def check_for_keypress():
    if select.select([sys.stdin], [], [], 0)[0]:
        sys.stdin.read(1)
        return True
    return False


def sleep_interruptible(duration):
    deadline = time.time() + duration
    while time.time() < deadline:
        if check_for_keypress():
            return True
        time.sleep(min(0.05, deadline - time.time()))
    return False


# ---------------------------
# CAMERA COMMUNICATION
# ---------------------------
def send_camera_command(command):
    if ser is None:
        print("OpenMV not connected; skipping command. \n")
        return
    ser.write(command.encode('ascii'))
    ser.flush()


def read_camera_line(timeout=1.0):
    if ser is None:
        return None
    ser.timeout = timeout
    line = ser.readline()
    if not line:
        return None
    return line.decode('ascii', 'ignore').strip()


# ---------------------------
# MAIN SEQUENCE
# ---------------------------
def run_cycle():
    print("Full retraction... \n", flush=True)
    actuator_retract()
    if sleep_interruptible(FULL_RETRACTION_TIME):
        return "stopped", None, None
    actuator_stop()

    print("Full extension... \n", flush=True)
    actuator_extend()
    if sleep_interruptible(FULL_EXTENSION_TIME):
        return "stopped", None, None
    actuator_stop()

    print("Starting randomization... \n", flush=True)
    motor_run()
    if sleep_interruptible(MOTOR_RUN_TIME):
        return "stopped", None, None
    motor_stop()
    print("Randomization complete. Starting data collection. \n")

    # print("Sending 'r' to start recording...")
    send_camera_command('r')

    print("Beginning ball extraction. \n")
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

    # print("Sending 's' to stop recording...")
    send_camera_command('s')

    e_timestamp = None
    count = None
    csv_row = None

    print("Examining data collection... \n")
    deadline = time.time() + 10.0
    while time.time() < deadline:
        if check_for_keypress():
            return "stopped", None, None
        line = read_camera_line(timeout=0.2)
        if line is None:
            continue
        if line.lower() == 'e':
            e_timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"Received 'e' at {e_timestamp} \n")
            break

    if e_timestamp is None:
        print("Timed out waiting for 'e' from H7. \n", flush=True)
        return "ok", None, None

    count_line = read_camera_line(timeout=2.0)
    csv_line = read_camera_line(timeout=2.0)

    if count_line and count_line.startswith('COUNT:'):
        count = int(count_line.split(':', 1)[1])
    if csv_line and csv_line.startswith('CSV:'):
        csv_row = csv_line.split(':', 1)[1]

    return "ok", count, csv_row


# ---------------------------
# CLEANUP
# ---------------------------
def shutdown_sequence(reason):
    print(f"Stopping all systems ({reason})... \n")
    motor_stop()
    send_camera_command('s')

    print("Full actuator retraction before shutdown \n")
    actuator_retract()
    time.sleep(FULL_RETRACTION_TIME)
    actuator_stop()

    log_completion(reason)


def cleanup():
    actuator_stop()
    motor_stop()
    GPIO.cleanup()
    if ser is not None:
        ser.close()
    restore_terminal()
    print("\nClean shutdown.")


# ---------------------------
# ENTRY POINT
# ---------------------------
if __name__ == "__main__":
    try:
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
