import image
import pyb
import sensor

CAPTURE_QUALITY = 50
CAPTURE_DIR = "/sd"
capture_counter = 0


def save_retraction_image(filename=None):
    global capture_counter
    if filename is None:
        capture_counter += 1
        filename = f"ball_retract_{capture_counter:04d}.jpg"
    if not filename.lower().endswith(".jpg"):
        filename = f"{filename}.jpg"
    full_path = f"{CAPTURE_DIR}/{filename}"
    img = sensor.snapshot()
    img.save(full_path, quality=CAPTURE_QUALITY)
    return full_path


def main():
    sensor.reset()
    sensor.set_pixformat(sensor.GRAYSCALE)
    sensor.set_framesize(sensor.QQVGA)
    sensor.set_auto_gain(False)
    sensor.set_auto_whitebal(False)
    sensor.skip_frames(time=2000)

    usb = pyb.USB_VCP()
    command_buffer = ""

    while True:
        if not usb.isconnected():
            pyb.delay(100)
            continue

        if usb.any():
            byte = usb.read(1)
            if byte:
                if byte == b"\n":
                    command = command_buffer.strip()
                    command_key = command.upper()
                    if command_key in {"HELLO", "START"}:
                        usb.write(b"READY\n")
                    elif command_key == "SAVE":
                        image_path = save_retraction_image()
                        usb.write(f"IMAGE:{image_path}\n".encode("ascii"))
                    elif command_key.startswith("SAVE:"):
                        image_name = command.split(":", 1)[1].strip()
                        image_path = save_retraction_image(image_name)
                        usb.write(f"IMAGE:{image_path}\n".encode("ascii"))
                    command_buffer = ""
                else:
                    command_buffer += byte.decode("ascii", "ignore")

        img = sensor.snapshot()
        for tag in img.find_apriltags(families=image.TAG36H11):
            tag_id = tag.id
            usb.write(f"TAG:{tag_id}\n".encode("ascii"))
            break

        pyb.delay(100)


if __name__ == "__main__":
    main()
