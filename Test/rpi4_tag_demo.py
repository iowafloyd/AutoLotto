#!/usr/bin/env python3
"""Simple Raspberry Pi demo for talking to an OpenMV H7 over serial."""

import select
import sys
import termios
import tty

import serial

PORT = "/dev/ttyACM0"
BAUDRATE = 115200
TIMEOUT = 0.1


def main():
    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=TIMEOUT)
    except serial.SerialException as exc:
        print(f"Unable to open {PORT}: {exc}")
        sys.exit(1)

    print(f"Serial link opened to {PORT}.")
    print("Requesting H7 handshake...")
    ser.write(b"HELLO\n")
    ser.flush()
    print("Waiting for H7 confirmation...")

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setraw(fd)

    try:
        confirmed = False
        while True:
            if select.select([sys.stdin], [], [], 0.1)[0]:
                sys.stdin.read(1)
                print("Exiting.")
                break

            if ser.in_waiting:
                line = ser.readline().decode("ascii", errors="ignore").strip()
                if not line:
                    continue

                if line == "READY":
                    if not confirmed:
                        print("H7 present.")
                        confirmed = True
                elif line.startswith("TAG:"):
                    tag_number = line.split(":", 1)[1].strip()
                    print(f"TAG: {tag_number}")
                else:
                    print(line)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        ser.close()


if __name__ == "__main__":
    main()
