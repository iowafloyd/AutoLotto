#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DESKTOP_ENTRY="$PROJECT_DIR/autolotto.desktop"
DESKTOP_DIR=${XDG_DESKTOP_DIR:-"$HOME/Desktop"}
AUTOSTART_DIR=${XDG_CONFIG_HOME:-"$HOME/.config"}/autostart
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

if [ ! -x "$VENV_PYTHON" ] || ! "$VENV_PYTHON" -c 'import cv2, apriltag, RPi.GPIO' >/dev/null 2>&1; then
    python3 -m venv --system-site-packages --clear "$PROJECT_DIR/.venv"
fi

mkdir -p "$DESKTOP_DIR" "$AUTOSTART_DIR"
cp "$DESKTOP_ENTRY" "$DESKTOP_DIR/AutoLotto.desktop"
cp "$DESKTOP_ENTRY" "$AUTOSTART_DIR/AutoLotto.desktop"
chmod +x "$PROJECT_DIR/run_autolotto.sh" \
    "$PROJECT_DIR/install_autolotto.sh" \
    "$DESKTOP_DIR/AutoLotto.desktop"

printf '%s\n' "AutoLotto desktop launcher installed."
printf '%s\n' "Desktop icon: $DESKTOP_DIR/AutoLotto.desktop"
printf '%s\n' "Autostart entry: $AUTOSTART_DIR/AutoLotto.desktop"