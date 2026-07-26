import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FakeUSB:
    def __init__(self):
        self.writes = []

    def isconnected(self):
        return True

    def any(self):
        return False

    def read(self, _size):
        return b""

    def write(self, data):
        self.writes.append(data)


class FakeSerial:
    def __init__(self, lines):
        self._lines = list(lines)
        self.timeout = None
        self.writes = []

    def write(self, data):
        self.writes.append(data)

    def flush(self):
        return None

    def readline(self):
        if self._lines:
            return self._lines.pop(0)
        return b""

    def close(self):
        return None


class H7ProtocolTests(unittest.TestCase):
    def load_h7_module(self):
        stub_pyb = types.ModuleType("pyb")
        stub_pyb.USB_VCP = lambda: FakeUSB()
        sys.modules["pyb"] = stub_pyb

        stub_sensor = types.ModuleType("sensor")
        stub_sensor.reset = lambda: None
        stub_sensor.set_pixformat = lambda *args, **kwargs: None
        stub_sensor.set_framesize = lambda *args, **kwargs: None
        stub_sensor.set_auto_gain = lambda *args, **kwargs: None
        stub_sensor.set_auto_whitebal = lambda *args, **kwargs: None
        stub_sensor.skip_frames = lambda *args, **kwargs: None
        stub_sensor.snapshot = lambda: None
        stub_sensor.RGB565 = "RGB565"
        stub_sensor.QVGA = "QVGA"
        sys.modules["sensor"] = stub_sensor

        stub_image = types.ModuleType("image")
        stub_image.TAG36H11 = "TAG36H11"
        sys.modules["image"] = stub_image

        spec = importlib.util.spec_from_file_location("h7_main", ROOT / "Code" / "H7" / "main.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_h7_emits_acknowledgment_for_record_start(self):
        module = self.load_h7_module()
        usb = FakeUSB()

        recording, csv_tags = module.handle_command("r", usb, False, "")

        self.assertTrue(recording)
        self.assertEqual(csv_tags, "")
        self.assertIn("ACK:r\n", usb.writes)
        self.assertIn("REC\n", usb.writes)

    def test_h7_emits_unique_count_and_csv_row(self):
        module = self.load_h7_module()
        usb = FakeUSB()

        recording, csv_tags = module.handle_command("s", usb, True, "1,2,2,3,4,5,")

        self.assertFalse(recording)
        self.assertEqual(csv_tags, "1,2,2,3,4,5")
        self.assertIn("ACK:s\n", usb.writes)
        self.assertTrue(any(write.startswith("COUNT:5") for write in usb.writes))
        self.assertTrue(any(write.startswith("CSV:") for write in usb.writes))

    def test_pi_requires_ack_before_reporting_success(self):
        stub_gpio = types.ModuleType("RPi")
        stub_gpio_gpio = types.ModuleType("RPi.GPIO")

        class DummyGPIO:
            BCM = "BCM"
            OUT = "OUT"
            HIGH = 1
            LOW = 0

            def setmode(self, *args, **kwargs):
                pass

            def setup(self, *args, **kwargs):
                pass

            def output(self, *args, **kwargs):
                pass

            def cleanup(self):
                pass

        stub_gpio_gpio.setmode = DummyGPIO().setmode
        stub_gpio_gpio.setup = DummyGPIO().setup
        stub_gpio_gpio.output = DummyGPIO().output
        stub_gpio_gpio.cleanup = DummyGPIO().cleanup
        stub_gpio_gpio.BCM = DummyGPIO.BCM
        stub_gpio_gpio.OUT = DummyGPIO.OUT
        stub_gpio_gpio.HIGH = DummyGPIO.HIGH
        stub_gpio_gpio.LOW = DummyGPIO.LOW
        stub_gpio.GPIO = stub_gpio_gpio
        sys.modules["RPi"] = stub_gpio
        sys.modules["RPi.GPIO"] = stub_gpio_gpio

        stub_serial = types.ModuleType("serial")
        stub_serial.Serial = lambda *args, **kwargs: FakeSerial([b"ACK:r\n"])
        sys.modules["serial"] = stub_serial

        stub_tty = types.ModuleType("tty")
        stub_tty.setraw = lambda *args, **kwargs: None
        sys.modules["tty"] = stub_tty

        stub_termios = types.ModuleType("termios")
        stub_termios.tcgetattr = lambda *args, **kwargs: None
        stub_termios.tcsetattr = lambda *args, **kwargs: None
        stub_termios.TCSADRAIN = 0
        sys.modules["termios"] = stub_termios

        stub_select = types.ModuleType("select")
        stub_select.select = lambda *args, **kwargs: ([], [], [])
        sys.modules["select"] = stub_select

        spec = importlib.util.spec_from_file_location("pi_main", ROOT / "Code" / "RPi" / "main.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        serial_stub = FakeSerial([b"ACK:r\n"])
        module.ser = serial_stub
        self.assertTrue(module.send_camera_command("r", expected_ack="ACK:r", timeout=0.1))

    def test_pi_creates_timestamped_csv_in_results_folder(self):
        stub_gpio = types.ModuleType("RPi")
        stub_gpio_gpio = types.ModuleType("RPi.GPIO")

        class DummyGPIO:
            BCM = "BCM"
            OUT = "OUT"
            HIGH = 1
            LOW = 0

            def setmode(self, *args, **kwargs):
                pass

            def setup(self, *args, **kwargs):
                pass

            def output(self, *args, **kwargs):
                pass

            def cleanup(self):
                pass

        stub_gpio_gpio.setmode = DummyGPIO().setmode
        stub_gpio_gpio.setup = DummyGPIO().setup
        stub_gpio_gpio.output = DummyGPIO().output
        stub_gpio_gpio.cleanup = DummyGPIO().cleanup
        stub_gpio_gpio.BCM = DummyGPIO.BCM
        stub_gpio_gpio.OUT = DummyGPIO.OUT
        stub_gpio_gpio.HIGH = DummyGPIO.HIGH
        stub_gpio_gpio.LOW = DummyGPIO.LOW
        stub_gpio.GPIO = stub_gpio_gpio
        sys.modules["RPi"] = stub_gpio
        sys.modules["RPi.GPIO"] = stub_gpio_gpio

        stub_serial = types.ModuleType("serial")
        stub_serial.Serial = lambda *args, **kwargs: FakeSerial([b"ACK:r\n"])
        sys.modules["serial"] = stub_serial

        stub_tty = types.ModuleType("tty")
        stub_tty.setraw = lambda *args, **kwargs: None
        sys.modules["tty"] = stub_tty

        stub_termios = types.ModuleType("termios")
        stub_termios.tcgetattr = lambda *args, **kwargs: None
        stub_termios.tcsetattr = lambda *args, **kwargs: None
        stub_termios.TCSADRAIN = 0
        sys.modules["termios"] = stub_termios

        stub_select = types.ModuleType("select")
        stub_select.select = lambda *args, **kwargs: ([], [], [])
        sys.modules["select"] = stub_select

        spec = importlib.util.spec_from_file_location("pi_main", ROOT / "Code" / "RPi" / "main.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tempdir:
            module.DESKTOP_RESULTS_DIR = tempdir
            output_path = module.initialize_csv_output()
            self.assertTrue(output_path.endswith('.csv'))
            self.assertTrue(os.path.exists(output_path))
            self.assertTrue(os.path.dirname(output_path) == tempdir)
            self.assertTrue(module.append_csv_row("2024-01-01,1,2,3,4,5", output_path))
            with open(output_path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "2024-01-01,1,2,3,4,5\n")


if __name__ == "__main__":
    unittest.main()
