import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from application import AutoLottoApplication


# Launch the application from the command line.
def main():
    AutoLottoApplication().run()


if __name__ == "__main__":
    main()
