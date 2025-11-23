#!/usr/bin/env bash
set -euo pipefail

# Build the Solo-Git sidecar (sologit-core) with PyInstaller
# Usage: bash scripts/build_sidecar.sh

PY=${PYTHON:-python3}

echo "[sidecar] Ensuring dependencies..."
$PY -m pip install --upgrade pip
$PY -m pip install -r requirements.txt

echo "[sidecar] Building onefile binary via PyInstaller..."
ENTRY="scripts/sidecar_entry.py"
$PY -m PyInstaller --onefile --name sologit-core --console "$ENTRY"

# Copy artifact into scripts/dist for Tauri build.rs pickup
ROOT_DIR=$(pwd)
DIST_OUT="$ROOT_DIR/dist"
SCRIPTS_DIST="$ROOT_DIR/scripts/dist"
mkdir -p "$SCRIPTS_DIST"

EXE_NAME="sologit-core"
SRC_PATH="$DIST_OUT/$EXE_NAME"
DST_PATH="$SCRIPTS_DIST/$EXE_NAME"

if [[ -f "$SRC_PATH" ]]; then
  cp -f "$SRC_PATH" "$DST_PATH"
  echo "[sidecar] Copied $SRC_PATH -> $DST_PATH"
else
  echo "[sidecar] Expected artifact not found: $SRC_PATH" >&2
fi

echo "[sidecar] Done. You can now run Tauri build."