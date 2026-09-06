import os
import time

DESKTOP_RESULTS_DIR = os.path.join(os.path.expanduser('~'), 'Desktop', 'Results')
CSV_OUTPUT_PATH = None


# Create a timestamped output file for the current run.
def initialize_csv_output():
    global CSV_OUTPUT_PATH
    os.makedirs(DESKTOP_RESULTS_DIR, exist_ok=True)
    timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
    CSV_OUTPUT_PATH = os.path.join(DESKTOP_RESULTS_DIR, f'{timestamp}.csv')
    with open(CSV_OUTPUT_PATH, 'a', encoding='utf-8') as handle:
        handle.write('')
    return CSV_OUTPUT_PATH


# Append one completed cycle to the active output file.
def append_csv_row(csv_row, output_path=None):
    if not csv_row:
        return False

    target_path = output_path or CSV_OUTPUT_PATH
    if target_path is None:
        return False

    with open(target_path, 'a', encoding='utf-8') as handle:
        handle.write(csv_row + '\n')
    return True
