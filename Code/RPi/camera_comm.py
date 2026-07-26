import serial
import time
from logging_utils import log_error


def initialize_camera_serial(path='/dev/ttyACM0', baudrate=115200, timeout=10):
    try:
        ser = serial.Serial(path, baudrate, timeout=timeout)
        print(f"OpenMV connected on {path}")
        return ser
    except Exception as exc:
        log_error(f"OpenMV camera not detected: {exc}")
        return None


def send_camera_command(ser, command, expected_ack=None, timeout=10.0):
    if ser is None:
        print("OpenMV not connected; skipping command.")
        return False

    try:
        ser.reset_input_buffer()
    except Exception:
        try:
            ser.flushInput()
        except Exception:
            pass

    ser.write(command.encode('ascii'))
    ser.flush()

    if expected_ack is None:
        return True

    deadline = time.time() + timeout
    while time.time() < deadline:
        remaining = max(0.0, deadline - time.time())
        ack = read_camera_line(ser, timeout=remaining)
        if ack is None:
            continue

        if ack == command:
            continue

        if ack.upper() == expected_ack.upper():
            print(f"H7 acknowledged '{command}' with '{ack}'.", flush=True)
            return True

        if ack.upper().startswith('ACK:'):
            print(f"Unexpected confirmation from H7 for '{command}': {ack}", flush=True)
            return False

    print(f"No confirmation received from H7 for command '{command}'.", flush=True)
    return False


def read_camera_line(ser, timeout=10.0):
    if ser is None:
        return None
    ser.timeout = timeout
    line = ser.readline()
    if not line:
        return None
    return line.decode('ascii', 'ignore').strip()


def read_h7_results(ser, timeout=10.0):
    if ser is None:
        return None, None

    deadline = time.time() + timeout
    while time.time() < deadline:
        line = read_camera_line(ser, timeout=max(0.0, deadline - time.time()))
        if line is None:
            continue
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower() in ('r', 's', 'rec'):
            continue
        if stripped.lower() == 'e':
            break

    else:
        return None, None

    csv_row = None
    result_deadline = time.time() + 4.0
    while time.time() < result_deadline and csv_row is None:
        line = read_camera_line(ser, timeout=max(0.0, result_deadline - time.time()))
        if line is None:
            continue
        if line.startswith('ROW:'):
            csv_row = line.split(':', 1)[1]
            break

    if csv_row is None:
        return None, None

    values = csv_row.split(',')
    count = max(0, len(values) - 1)
    return count, csv_row
