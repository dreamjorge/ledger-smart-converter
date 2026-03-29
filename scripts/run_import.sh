#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ $# -lt 1 ]; then
  echo "Usage: $0 --bank <bank_id> [other generic_importer args]" >&2
  exit 1
fi

if [ ! -x "${ROOT_DIR}/.venv/bin/python" ]; then
  echo "uv-managed virtual environment not found at ${ROOT_DIR}/.venv. Please run ./scripts/setup_env.sh first." >&2
  exit 1
fi

exec "${ROOT_DIR}/.venv/bin/python" "${ROOT_DIR}/src/generic_importer.py" "$@"
