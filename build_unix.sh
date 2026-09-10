#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="${1:-./venv}"
PYTHON="${VENV_DIR}/bin/python"
PYINSTALLER="${VENV_DIR}/bin/pyinstaller"
SPEC_FILE="edideck.spec"
DIST_NAME="EDIDeck"

echo "Using venv: $VENV_DIR"

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtualenv..."
  python3 -m venv "$VENV_DIR"
fi

echo "Upgrading pip and installing requirements..."
"$PYTHON" -m pip install --upgrade pip setuptools wheel
"$PYTHON" -m pip install -r requirements.txt
"$PYTHON" -m pip install pyinstaller==5.9.0

echo "Cleaning previous builds..."
rm -rf build dist __pycache__ "$DIST_NAME.spec"

if [ -f "$SPEC_FILE" ]; then
  echo "Running PyInstaller with spec: $SPEC_FILE"
  "$PYTHON" -m PyInstaller "$SPEC_FILE"
else
  echo "Running PyInstaller default"
  "$PYTHON" -m PyInstaller --noconfirm --onefile --windowed --name "$DIST_NAME" main.py
fi

if [ -f "dist/$DIST_NAME" ] || [ -f "dist/$DIST_NAME.exe" ]; then
  echo "Build succeeded: dist/$DIST_NAME"
else
  echo "Build failed: dist/$DIST_NAME not found" >&2
  exit 2
fi

echo "Done."
