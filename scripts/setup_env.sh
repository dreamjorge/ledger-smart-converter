#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
VENV_PYTHON="${VENV_DIR}/bin/python"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed or not in PATH" >&2
  exit 1
fi

if [ ! -d "${VENV_DIR}" ]; then
  echo "Creating uv-managed virtual environment at ${VENV_DIR}..."
  uv venv "${VENV_DIR}"
else
  echo "uv-managed virtual environment already exists."
fi

if [ ! -x "${VENV_PYTHON}" ]; then
  echo "uv-managed Python executable not found at ${VENV_PYTHON}" >&2
  exit 1
fi

echo "Installing requirements with uv..."
uv pip install --python "${VENV_PYTHON}" -r "${ROOT_DIR}/requirements.txt"

echo "Setup complete. Use the uv-managed environment at ${VENV_DIR}."
