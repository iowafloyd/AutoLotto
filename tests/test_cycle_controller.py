import sys
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Code" / "RPi"))
import cycle_controller


class CycleControllerTests(unittest.TestCase):
    def test_jogs_again_and_retries_when_no_new_tag_is_detected(self):
        camera = MagicMock()
        camera.read_tag_ids.return_value = {"old"}
        camera.wait_for_new_tag.side_effect = [
            (None, {"old"}),
            ("23", {"23"}),
        ]
        controller = cycle_controller.CycleController(camera)
        statuses = []

        with (
            patch.object(cycle_controller, "NUM_STEPS", 1),
            patch.object(cycle_controller, "sleep_interruptible", return_value=False),
            patch.object(cycle_controller, "actuator_retract"),
            patch.object(cycle_controller, "actuator_extend"),
            patch.object(cycle_controller, "actuator_stop"),
            patch.object(cycle_controller, "motor_run") as motor_run,
            patch.object(cycle_controller, "motor_stop"),
        ):
            result = controller.run_cycle(Event(), statuses.append)

        self.assertEqual(result[0:2], ("ok", 1))
        self.assertTrue(result[2].endswith("\t23"))
        self.assertEqual(camera.wait_for_new_tag.call_count, 2)
        self.assertEqual(motor_run.call_count, 4)
        self.assertIn("No new ball detected; jogging motor again", statuses)


if __name__ == "__main__":
    unittest.main()