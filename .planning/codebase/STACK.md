# Technology Stack

**Analysis Date:** 2026-03-23

## Languages

**Primary:**
- Python 3.10+ - Backend processing, orchestrations, and UI application logic.

**Secondary:**
- Batch / Shell Scripting - `start.bat`, `start.sh`, `check_ffmpeg.bat` for launchers and debugging.

## Runtime & Package Managers

**Environment:**
- Python 3.10+ (managed via virtual environments, e.g., `venv/`).

**Package Manager:**
- `pip` (Python) - Managed via `requirements.txt` and `requirements-dev.txt`.
- Code Quality: `ruff` and `mypy` configured in `pyproject.toml`.

## Frameworks

**Core:**
- PyQt6 - The definitive GUI framework driving the desktop experience.
- `qt-material` - Custom material design styles applied dynamically over PyQt6.

**Testing:**
- Pytest 6.0+ - Primary test runner for unit and integration testing.

## Key Dependencies

**Critical:**
- `opencv-python`, `pillow`, `imageio-ffmpeg` - Image and video frame logic, likely used for the thumbnail generation and caching system.
- `send2trash` - OS-level recycling bin API for safe deletions.
- `psutil` - Process monitoring, potentially utilized in the `ConversionWorker` or system validations.
- `pynvml` - NVIDIA GPU hardware monitoring for enabling NVENC (`hevc_nvenc`) features dynamically.

## Platform Requirements

**Production / Development:**
- Expected to primarily target Windows environments based on specific batch scripts (`start.bat`) and taskbar optimizations (`set_app_user_model_id`). However, cross-platform functionality should exist via PySide/PyQt and `start.sh`.

## Application Modes

- **Monolithic Desktop App**: Runs strictly as an isolated desktop client (`src/main.py`) executing local system binaries without remote server dependencies.
