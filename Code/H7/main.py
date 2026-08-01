import image
import pyb
import sensor


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
                    command = command_buffer.strip().upper()
                    if command in {"HELLO", "START"}:
                        usb.write(b"READY\n")
                    command_buffer = ""
                else:
                    command_buffer += byte.decode("ascii", "ignore")

        img = sensor.snapshot()
        for tag in img.find_apriltags(families=image.TAG36H11):
            tag_id = tag.id
            usb.write(f"{tag_id}\n".encode("ascii"))
            break

        pyb.delay(100)


if __name__ == "__main__":
    main()
