#!/bin/bash

# Ensure we are in the script's directory
cd "$(dirname "$0")"

# Check if venv_linux exists and has the correct structure (Linux)
if [ ! -f "venv_linux/bin/activate" ]; then
    echo "Virtual environment venv_linux not found."
    echo "Creating new virtual environment..."
    python3 -m venv venv_linux
else
    echo "Virtual environment venv_linux found."
fi

# Activate venv_linux
source venv_linux/bin/activate

# Install/Update dependencies
echo "Checking for dependency updates..."
pip install -r requirements.txt

# Run the application
echo "Starting Video Converter (PyQt6)..."
# Set PYTHONPATH to current directory to ensure src module is found
export PYTHONPATH=$PYTHONPATH:.
python -m src.main

# Keep terminal open if there's an error (optional, mostly for debugging)
if [ $? -ne 0 ]; then
    read -p "Press enter to exit..."
fi
