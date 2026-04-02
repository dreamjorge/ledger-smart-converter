#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_PATH="${ROOT_DIR}/src/web_app.py"

if [ ! -x "${ROOT_DIR}/.venv/bin/python" ]; then
  echo "uv-managed virtual environment not found at ${ROOT_DIR}/.venv. Please run ./scripts/setup_env.sh first." >&2
  exit 1
fi

exec "${ROOT_DIR}/.venv/bin/python" -m streamlit run "${SRC_PATH}"
