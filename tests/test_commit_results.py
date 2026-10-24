import subprocess
import tempfile
import unittest
from pathlib import Path

from Code.RPi.commit_results import commit_results


class CommitResultsTests(unittest.TestCase):
    def test_commits_and_pushes_only_results_changes(self):
        with tempfile.TemporaryDirectory() as tempdir:
            repo_root = Path(tempdir) / "repo"
            remote_path = Path(tempdir) / "remote.git"
            repo_root.mkdir()
            self._git(repo_root, "init", "-b", "main")
            self._git(repo_root, "config", "user.name", "AutoLotto Test")
            self._git(repo_root, "config", "user.email", "autolotto@example.invalid")
            (repo_root / "README.md").write_text("baseline\n", encoding="utf-8")
            results_dir = repo_root / "Results"
            results_dir.mkdir()
            (results_dir / "draw.csv").write_text("baseline\n", encoding="utf-8")
            self._git(repo_root, "add", ".")
            self._git(repo_root, "commit", "-m", "Initial commit")
            self._git(Path(tempdir), "init", "--bare", "-b", "main", str(remote_path))
            self._git(repo_root, "remote", "add", "origin", str(remote_path))
            self._git(repo_root, "push", "-u", "origin", "main")

            (results_dir / "draw.csv").write_text("updated results\n", encoding="utf-8")
            (repo_root / "README.md").write_text("unrelated change\n", encoding="utf-8")

            self.assertTrue(commit_results(repo_root))
            self.assertEqual(
                self._git(repo_root, "show", "--format=", "--name-only", "HEAD"),
                "Results/draw.csv",
            )
            self.assertEqual(
                self._git(
                    Path(tempdir),
                    "--git-dir",
                    str(remote_path),
                    "show",
                    "main:Results/draw.csv",
                ),
                "updated results",
            )
            self.assertEqual(
                self._git(repo_root, "status", "--short"),
                "M README.md",
            )
            self.assertFalse(commit_results(repo_root))

    @staticmethod
    def _git(cwd, *args):
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()


if __name__ == "__main__":
    unittest.main()
