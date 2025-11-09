#!/bin/bash
# Run script for Study Sleep application

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Use the parent directory's virtual environment
VENV_PATH="/home/abhiramk/Documents/hack-princeton/.venv"

if [ -d "$VENV_PATH" ]; then
    echo "Activating virtual environment from $VENV_PATH..."
    source "$VENV_PATH/bin/activate"
    python main.py
    deactivate
elif [ -d ".venv" ]; then
    echo "Activating local virtual environment..."
    source .venv/bin/activate
    python main.py
    deactivate
else
    echo "Virtual environment not found. Running with system Python..."
    echo "If you get import errors, please run: ./install_with_venv.sh"
    python3 main.py
fi

