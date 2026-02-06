@echo off
cd /d "%~dp0"

:: Check if venv exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment found.
)

:: Activate venv
call venv\Scripts\activate

:: Install/Update dependencies
echo Checking for dependency updates...
python -m pip install --upgrade pip
pip install -r requirements.txt

:: Run the application
echo Starting Video Converter (PyQt6)...
python -m src.main

:: Keep window open if it crashes immediately
if %errorlevel% neq 0 pause
