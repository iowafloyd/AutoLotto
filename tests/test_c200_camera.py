import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from Code.RPi.c200_camera import C200Camera


class FakeCapture:
    def __init__(self, frames):
        self.frames = iter(frames)
        self.released = False

    def isOpened(self):
        return True

    def read(self):
        return True, next(self.frames, object())

    def release(self):
        self.released = True


class C200CameraTests(unittest.TestCase):
    def test_collects_tag_ids_and_writes_timestamped_log(self):
        with tempfile.TemporaryDirectory() as tempdir:
            camera = C200Camera(
                log_dir=tempdir,
                detector=lambda _gray: [SimpleNamespace(tag_id=17)],
                capture=FakeCapture([object(), object(), object()]),
            )

            with patch("Code.RPi.c200_camera.cv2.cvtColor", side_effect=lambda frame, _mode: frame):
                values = camera.collect_tag_values(timeout=0.1, minimum_values=3)
            camera.close()

            self.assertEqual(values, ["17", "17", "17"])
            self.assertTrue(camera.capture.released)
            self.assertRegex(
                Path(camera.log_path).name,
                r"^c200_camera_\d{8}_\d{6}_\d{6}\.log$",
            )
            self.assertIn("Detections: 1", Path(camera.log_path).read_text())


if __name__ == "__main__":
    unittest.main()