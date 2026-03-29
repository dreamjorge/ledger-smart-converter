#!/bin/bash
# Script to run the Flet Desktop App

VENV_PATH="./.venv"
# Use .venv_uv if it exists (for compatibility with recent uv migration)
if [ -d "./.venv_uv" ]; then
    VENV_PATH="./.venv_uv"
fi

PYTHON_EXE="$VENV_PATH/bin/python"

if [ ! -f "$PYTHON_EXE" ]; then
    echo "Virtual environment not found at $VENV_PATH. Please run ./scripts/setup_env.sh first."
    exit 1
fi

export PYTHONPATH="src"
echo "Starting Flet Desktop App..."
"$PYTHON_EXE" src/flet_app.py
