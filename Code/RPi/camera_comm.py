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
        if stripped.startswith('TAG:'):
            tag_id = stripped.split(':', 1)[1]
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp}] H7 detected tag: {tag_id}", flush=True)
            continue

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
        if line.startswith('COUNT:'):
            continue
        if line.startswith('CSV:'):
            continue

    if csv_row is None:
        return None, None

    values = csv_row.split(',')
    count = max(0, len(values) - 1)
    return count, csv_row
