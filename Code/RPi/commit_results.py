import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def commit_results(repo_root=REPO_ROOT):
    subprocess.run(
        ["git", "add", "--all", "--", "Results"],
        cwd=repo_root,
        check=True,
    )
    staged_changes = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", "Results"],
        cwd=repo_root,
        check=False,
    )
    if staged_changes.returncode == 0:
        return False
    if staged_changes.returncode != 1:
        raise subprocess.CalledProcessError(
            staged_changes.returncode, staged_changes.args
        )

    subprocess.run(
        ["git", "commit", "-m", "Update Results", "--", "Results"],
        cwd=repo_root,
        check=True,
    )
    subprocess.run(["git", "push"], cwd=repo_root, check=True)
    return True


def main():
    if commit_results():
        print("COMMIT_COMPLETE")


if __name__ == "__main__":
    main()
