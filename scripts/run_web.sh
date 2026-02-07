#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_PATH="${ROOT_DIR}/src/web_app.py"

if [ -x "${ROOT_DIR}/.venv/bin/streamlit" ]; then
  exec "${ROOT_DIR}/.venv/bin/streamlit" run "${SRC_PATH}"
fi

exec streamlit run "${SRC_PATH}"
