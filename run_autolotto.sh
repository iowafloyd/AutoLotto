#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON="$PROJECT_DIR/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
    printf '%s\n' "AutoLotto virtual-environment Python was not found: $PYTHON" >&2
    exit 1
fi

cd "$PROJECT_DIR"
exec "$PYTHON" "$PROJECT_DIR/Code/RPi/main.py"