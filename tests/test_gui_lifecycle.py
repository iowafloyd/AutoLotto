import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Code" / "RPi"))
from gui import AutoLottoApp


class GuiLifecycleTests(unittest.TestCase):
    def test_successful_runtime_invokes_results_commit_helper(self):
        app = AutoLottoApp.__new__(AutoLottoApp)
        app.selected_runtime_seconds = 1
        app.run_error = None
        app.run_start_time = None
        app.close_requested = False
        app.controller = MagicMock()
        app.controller.run_cycle.return_value = ("ok", 0, None)
        app.root = MagicMock()
        app.values_text = MagicMock()
        app.cycle_text = MagicMock()
        stop_event = threading.Event()
        app.update_status = MagicMock()

        with patch(
            "gui.time.time", side_effect=[100, 100, 102, 102]
        ), patch("gui.filter_latest_results"), patch(
            "gui.subprocess.run"
        ) as run_helper:
            run_helper.return_value.stdout = "COMMIT_COMPLETE\n"
            app.run_program(stop_event, 1)

        self.assertEqual(run_helper.call_count, 1)
        app.update_status.assert_any_call("Committing", 1)
        self.assertEqual(
            app.root.after.call_args.args[2:],
            (1, "Commit complete"),
        )
        self.assertEqual(
            run_helper.call_args.args[0][1],
            str(Path(__file__).resolve().parents[1] / "Code" / "RPi" / "commit_results.py"),
        )

    def test_operator_stop_does_not_invoke_results_commit_helper(self):
        app = AutoLottoApp.__new__(AutoLottoApp)
        app.selected_runtime_seconds = 60
        app.run_error = None
        app.run_start_time = None
        app.close_requested = False
        app.controller = MagicMock()
        stop_event = threading.Event()

        def stop_during_cycle(*_args):
            stop_event.set()
            return "stopped", None, None

        app.controller.run_cycle.side_effect = stop_during_cycle
        app.root = MagicMock()
        app.update_status = MagicMock()

        with patch("gui.time.time", side_effect=[100, 100]), patch(
            "gui.filter_latest_results"
        ), patch("gui.subprocess.run") as run_helper:
            app.run_program(stop_event, 1)

        run_helper.assert_not_called()

    def test_preview_read_does_not_block_tk_callback(self):
        app = AutoLottoApp.__new__(AutoLottoApp)
        read_started = threading.Event()
        release_read = threading.Event()

        class BlockingCamera:
            def read_frame(self):
                read_started.set()
                release_read.wait(timeout=2)
                return None

        app.camera_enabled = True
        app.camera = BlockingCamera()
        app.preview_lock = threading.Lock()
        app.preview_reading = False
        app.preview_frame = None
        app.preview_label = MagicMock()
        app.root = MagicMock()

        app.update_camera_preview()

        try:
            self.assertTrue(read_started.wait(timeout=1))
            app.root.after.assert_called_once_with(100, app.update_camera_preview)
        finally:
            release_read.set()

    def test_stuck_worker_triggers_emergency_stop_and_closes_window(self):
        app = AutoLottoApp.__new__(AutoLottoApp)
        app.close_requested = True
        app.close_timeout_id = None
        app.worker = MagicMock()
        app.worker.is_alive.return_value = True
        app.controller = MagicMock()
        app.root = MagicMock()

        app._force_close_if_worker_stuck()

        app.controller.emergency_stop.assert_called_once_with()
        app.root.destroy.assert_called_once_with()

    def test_idle_close_does_not_wait_for_camera_cleanup(self):
        app = AutoLottoApp.__new__(AutoLottoApp)
        app.close_requested = False
        app.close_timeout_id = None
        app.worker = None
        app.root = MagicMock()
        cleanup_started = threading.Event()
        release_cleanup = threading.Event()

        class BlockingController:
            def emergency_stop(self):
                pass

            def cleanup(self):
                cleanup_started.set()
                release_cleanup.wait(timeout=2)

        app.controller = BlockingController()

        app.close_program()

        try:
            self.assertTrue(cleanup_started.wait(timeout=1))
            app.root.destroy.assert_called_once_with()
        finally:
            release_cleanup.set()


if __name__ == "__main__":
    unittest.main()