import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Code" / "RPi"))
import csv_output


class CsvOutputTests(unittest.TestCase):
    def test_initializes_timestamped_file_in_results_directory(self):
        with tempfile.TemporaryDirectory() as tempdir:
            results_dir = Path(tempdir) / "Results"
            with (
                patch.object(csv_output, "RESULTS_DIR", results_dir),
                patch.object(csv_output.time, "strftime", return_value="2026-10-24_09-00-00"),
            ):
                output_path = csv_output.initialize_csv_output()

            output_file = Path(output_path)
            self.assertEqual(output_file, results_dir / "2026-10-24_09-00-00.csv")
            self.assertTrue(output_file.is_file())
            self.assertEqual(output_file.read_text(encoding="utf-8"), "")


if __name__ == "__main__":
    unittest.main()
