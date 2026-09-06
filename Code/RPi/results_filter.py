from pathlib import Path


# Filter the newest raw results file into a deduplicated companion file.
def filter_latest_results(results_dir):
    results_path = _latest_results_path(Path(results_dir))
    if results_path is None:
        return None

    filtered_path = results_path.with_name(
        f"{results_path.stem} filtered{results_path.suffix}"
    )
    with results_path.open("r", encoding="utf-8") as results_file, filtered_path.open(
        "w", encoding="utf-8"
    ) as filtered_file:
        for line in results_file:
            filtered_file.write(_filter_result_line(line))

    return filtered_path


# Locate the newest unfiltered CSV result file.
def _latest_results_path(results_dir):
    result_paths = [
        path
        for path in results_dir.glob("*.csv")
        if not path.stem.endswith("filtered")
    ]
    return max(result_paths, key=lambda path: path.stat().st_mtime) if result_paths else None


# Remove duplicate values from one tab-separated result row.
def _filter_result_line(line):
    line_ending = "\n" if line.endswith("\n") else ""
    content = line[:-1] if line_ending else line
    timestamp, separator, values_text = content.partition("\t")
    if not separator:
        return line

    unique_values = []
    seen_values = set()
    for value in values_text.split(","):
        value = value.strip()
        if value and value not in seen_values:
            seen_values.add(value)
            unique_values.append(value)

    return f"{timestamp}\t{','.join(unique_values)}{line_ending}"