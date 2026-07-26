import sensor
import image
import time
import pyb
import os


def sleep_ms(milliseconds):
    if hasattr(time, "sleep_ms"):
        time.sleep_ms(milliseconds)
    else:
        time.sleep(milliseconds / 1000.0)


# Configure the camera for AprilTag detection.
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)
sensor.skip_frames(time=2000)

usb = pyb.USB_VCP()

recording = False
csv_tags = ""


def build_timestamp():
    t = time.localtime()
    return "%04d-%02d-%02d %02d:%02d:%02d" % (t[0], t[1], t[2], t[3], t[4], t[5])


def handle_command(cmd, usb_handle, recording_state, csv_tags_state):
    if isinstance(cmd, bytes):
        parsed_cmd = cmd.decode('ascii', 'ignore').strip().lower()
    else:
        parsed_cmd = str(cmd).strip().lower()

    if parsed_cmd == 'r':
        recording_state = True
        csv_tags_state = ""
        usb_handle.write("ACK:r\n")
        usb_handle.write("REC\n")
        return recording_state, csv_tags_state

    if parsed_cmd == 's':
        recording_state = False

        # Remove trailing comma from the raw tag list.
        if csv_tags_state.endswith(','):
            csv_tags_state = csv_tags_state[:-1]

        # Build the list of unique values.
        values = []
        if csv_tags_state:
            values = csv_tags_state.split(',')

        unique_values = []
        for value in values:
            if value not in unique_values:
                unique_values.append(value)

        # Create the CSV row with timestamp and unique values.
        timestamp = build_timestamp()
        csv_row = timestamp
        for value in unique_values:
            csv_row += "," + value

        usb_handle.write("ACK:s\n")

        # Announce that the H7 is examining the data.
        usb_handle.write("e\n")

        # Send the count of unique values.
        usb_handle.write("COUNT:" + str(len(unique_values)) + "\n")

        # Send the CSV row of unique values.
        usb_handle.write("CSV:" + csv_row + "\n")

        # Save the CSV row to a file on the flash filesystem if possible.
        try:
            with open("/flash/tag_report.csv", "a") as f:
                f.write(csv_row + "\n")
        except Exception:
            pass

    return recording_state, csv_tags_state


def main():
    while True:
        # Read any command sent over USB from the Raspberry Pi.
        if usb.isconnected() and usb.any():
            cmd = usb.read(1)
            if cmd:
                recording, csv_tags = handle_command(cmd, usb, recording, csv_tags)

        if recording:
            img = sensor.snapshot()

            # Detect AprilTag 36H11 tags in the current frame.
            for tag in img.find_apriltags(families=image.TAG36H11):
                csv_tags += str(tag.id()) + ","

        sleep_ms(10)


if __name__ == "__main__":
    main()
