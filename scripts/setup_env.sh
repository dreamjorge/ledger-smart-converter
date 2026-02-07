#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v python >/dev/null 2>&1; then
  echo "python is not installed or not in PATH" >&2
  exit 1
fi

if [ ! -d "${ROOT_DIR}/.venv" ]; then
  if ! python -m venv "${ROOT_DIR}/.venv"; then
    echo "venv creation failed; falling back to system pip install." >&2
    python -m pip install --break-system-packages -r "${ROOT_DIR}/requirements.txt"
    echo "Setup complete."
    exit 0
  fi
fi

if [ -x "${ROOT_DIR}/.venv/bin/python" ] && [ -x "${ROOT_DIR}/.venv/bin/pip" ]; then
  "${ROOT_DIR}/.venv/bin/python" -m pip install --upgrade pip
  "${ROOT_DIR}/.venv/bin/pip" install -r "${ROOT_DIR}/requirements.txt"
else
  python -m pip install --break-system-packages -r "${ROOT_DIR}/requirements.txt"
fi

echo "Setup complete."
