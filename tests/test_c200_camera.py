import tempfile
import unittest
import json
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
    # Confirm that a new tag is returned after the camera observes it.
    def test_waits_for_a_new_stable_tag(self):
        detections = iter(
            [
                [SimpleNamespace(tag_id=17)],
                [SimpleNamespace(tag_id=17, center=(1, 1))],
                [SimpleNamespace(tag_id=23, center=(1, 1))],
                [SimpleNamespace(tag_id=23, center=(1, 1))],
                [SimpleNamespace(tag_id=23, center=(1, 1))],
            ]
        )
        with tempfile.TemporaryDirectory() as tempdir:
            camera = C200Camera(
                log_dir=tempdir,
                detector=lambda _gray: next(detections),
                capture=FakeCapture([object()] * 5),
            )

            with patch("Code.RPi.c200_camera.cv2.cvtColor", side_effect=lambda frame, _mode: frame):
                previous_tags = camera.read_tag_ids()
                value, visible_tags = camera.wait_for_new_tag(
                    previous_tags, set(), stable_frames=3, poll_interval=0
                )
            camera.close()

            self.assertEqual(previous_tags, {"17"})
            self.assertEqual(value, "23")
            self.assertEqual(visible_tags, {"23"})

    # Confirm the first unseen detection wins when multiple tags appear together.
    def test_accepts_first_new_tag_when_multiple_are_visible(self):
        detections = [
            SimpleNamespace(tag_id=42),
            SimpleNamespace(tag_id=11),
        ]
        with tempfile.TemporaryDirectory() as tempdir:
            camera = C200Camera(
                log_dir=tempdir,
                detector=lambda _gray: detections,
                capture=FakeCapture([object()]),
            )

            with patch("Code.RPi.c200_camera.cv2.cvtColor", side_effect=lambda frame, _mode: frame):
                value, visible_tags = camera.wait_for_new_tag(set(), set(), poll_interval=0)
            camera.close()

            self.assertEqual(value, "42")
            self.assertEqual(visible_tags, {"42", "11"})

    # Confirm collection returns values and creates a timestamped camera log.
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

    # Confirm optional diagnostics capture detections and acceptance decisions.
    def test_tag_diagnostics_records_detection_and_decision(self):
        with tempfile.TemporaryDirectory() as tempdir:
            camera = C200Camera(
                log_dir=tempdir,
                detector=lambda _gray: [
                    SimpleNamespace(tag_id=23, center=(1, 2), corners=[[1, 2]])
                ],
                capture=FakeCapture([object(), object()]),
            )
            camera.set_tag_diagnostics_enabled(True)
            camera.set_diagnostic_context(phase="ball_confirmation", step=5)

            with patch("Code.RPi.c200_camera.cv2.cvtColor", side_effect=lambda frame, _mode: frame):
                value, _visible_tags = camera.wait_for_new_tag(set(), set(), poll_interval=0)
            diagnostics_path = camera.diagnostics.log_path
            camera.close()

            events = [json.loads(line)["event"] for line in diagnostics_path.read_text().splitlines()]
            self.assertEqual(value, "23")
            self.assertIn("detections", events)
            self.assertIn("tag_decision", events)


if __name__ == "__main__":
    unittest.main()