import tempfile
import unittest
from pathlib import Path

from Code.RPi.results_filter import filter_latest_results


class ResultsFilterTests(unittest.TestCase):
    def test_filters_each_row_in_first_seen_order(self):
        with tempfile.TemporaryDirectory() as tempdir:
            results_path = Path(tempdir) / "2026-09-03_12-00-00.csv"
            results_path.write_text(
                "2026-09-03 12:00:00\t51,42,42,60,42,30,28,28,30,51\n"
                "2026-09-03 12:01:00\t7,8,7,9\n",
                encoding="utf-8",
            )

            filtered_path = filter_latest_results(tempdir)

            self.assertEqual(
                filtered_path,
                Path(tempdir) / "2026-09-03_12-00-00 filtered.csv",
            )
            self.assertEqual(
                filtered_path.read_text(encoding="utf-8"),
                "2026-09-03 12:00:00\t51,42,60,30,28\n"
                "2026-09-03 12:01:00\t7,8,9\n",
            )

    def test_ignores_existing_filtered_results(self):
        with tempfile.TemporaryDirectory() as tempdir:
            results_path = Path(tempdir) / "2026-09-03_12-00-00.csv"
            filtered_path = Path(tempdir) / "2026-09-03_12-00-00 filtered.csv"
            results_path.write_text("row\t1,1\n", encoding="utf-8")
            filtered_path.write_text("old filtered data\n", encoding="utf-8")

            output_path = filter_latest_results(tempdir)

            self.assertEqual(output_path, filtered_path)
            self.assertEqual(
                filtered_path.read_text(encoding="utf-8"), "row\t1\n"
            )


if __name__ == "__main__":
    unittest.main()