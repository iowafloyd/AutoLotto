import time

RGB565 = "RGB565"
QVGA = "QVGA"


class _FakeImage:
    def find_apriltags(self, families=None):
        return []


class _FakeSensor:
    def __init__(self):
        self.pixformat = None
        self.framesize = None
        self.auto_gain = None
        self.auto_whitebal = None

    def reset(self):
        self.pixformat = None
        self.framesize = None
        self.auto_gain = None
        self.auto_whitebal = None

    def set_pixformat(self, pixel_format):
        self.pixformat = pixel_format

    def set_framesize(self, frame_size):
        self.framesize = frame_size

    def set_auto_gain(self, enabled):
        self.auto_gain = enabled

    def set_auto_whitebal(self, enabled):
        self.auto_whitebal = enabled

    def skip_frames(self, time_ms=0):
        time.sleep_ms(time_ms)

    def snapshot(self):
        return _FakeImage()


sensor = _FakeSensor()

reset = sensor.reset
set_pixformat = sensor.set_pixformat
set_framesize = sensor.set_framesize
set_auto_gain = sensor.set_auto_gain
set_auto_whitebal = sensor.set_auto_whitebal
skip_frames = sensor.skip_frames
snapshot = sensor.snapshot
