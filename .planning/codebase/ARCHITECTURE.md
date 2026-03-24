# Architecture

**Analysis Date:** 2026-03-23

## Pattern Overview

**Overall:** Desktop Application with Background Worker Architecture

**Key Characteristics:**
- Desktop UI built with PyQt6 and styled using `qt-material`.
- Asynchronous execution of heavy tasks using PyQt `QThreadPool` and `QRunnable` for non-blocking UI.
- Direct invocation of external CLI tools (`ffmpeg` via `subprocess`) for core video processing capabilities.
- Local configuration and state management using JSON files (`config.json`, `scan_cache.json`, `thumbs_cache.json`).

## Layers

**Presentation Layer (Frontend/UI):**
- Purpose: User interaction, settings management, and progress display.
- Location: `src/ui/`
- Contains: `MainWindow` (PyQt6 window), `worker.py` (background thread management), `preview_window_qt.py`.
- Depends on: `PyQt6`, `qt-material`, `src/core/`.

**Business Logic Layer (Core):**
- Purpose: Orchestrating the conversion commands and monitoring external processes.
- Location: `src/core/`
- Contains: `Converter` logic, command-line arguments builder for ffmpeg, logic for hardware acceleration (NVENC vs CPU), exception definitions.
- Depends on: External `ffmpeg` executable.

**Utility/Data Layer:**
- Purpose: Shared functions, configuration storage, and caches.
- Location: `src/utils/`
- Contains: `config.py` (persistent settings), `helpers.py` (video metadata extraction via `ffprobe`), `logger.py`, `thumb_cache.py`.

## Data Flow

**Conversion Flow:**
1. User drops files or selects files in the `MainWindow`.
2. UI triggers `ConversionWorker` in `worker.py` with configurations (from `config.json` and UI overrides).
3. `ConversionWorker` spawns a `FileConversionRunnable` which holds a `Converter` instance.
4. `Converter` dynamically builds `ffmpeg` arguments based on input metadata, GPU availability, and target CRF/Bitrate.
5. `subprocess.Popen` launches `ffmpeg`. The stdout/stderr is read in a loop to extract `time=XZ` patterns.
6. The `Converter` triggers a callback with progress (0.0 to 1.0) and ETA.
7. The `FileConversionRunnable` emits a Qt signal (`progress`) mapped to the `MainWindow` UI update slots to animate progress bars.
8. Upon completion or failure, the `Converter` cleans up incomplete files and optionally auto-deletes the original file, emitting a `finished` Qt signal.

## Key Abstractions

**Converter (`src/core/converter.py`):**
- Handles formatting FFmpeg commands (e.g., hybrid CPU decode -> GPU filter -> GPU encode using `hwupload` and `scale_cuda`).
- Parses FFmpeg `stderr` synchronously to push progress to the thread manager.

**ConversionWorker & FileConversionRunnable (`src/ui/worker.py`):**
- Bridge between Qt UI Event Loop and blocking synchronous file processing. 
- Manages concurrency (`QThreadPool.setMaxThreadCount`) and batch jobs.

**Config (`src/utils/config.py`):**
- Singleton pattern holding user preferences and application settings, backed by `config.json`.

## Entry Points

**Main Application Entry:**
- Location: `src/main.py`
- Triggers: Script execution (`python src/main.py` or `start.bat`).
- Responsibilities: Initializes the configuration singleton, sets the Windows App User Model ID, configures PyQt6 application and global theme, and mounts `MainWindow`.

## Error Handling

**Strategy:** Graceful catching and UI emission.
- **Conversion Errors:** Exceptions during conversion (such as `subprocess` failures or invalid videos) are caught in the worker thread and emitted up as a `finished` signal with `success=False` and the error message string. The UI handles these by updating the status cell and notifying the user.
- **File System Errors:** Errors during file interactions (like `send2trash` failures) are logged but do not crash the app.

## Cross-Cutting Concerns

**Logging:** Uses the standard python `logging` module configured in `src/utils/logger.py` with both file output (`app.log`) and console output limits.
**State Persistence:** In-memory caching dictionaries flushed to JSON (`scan_cache.json`, `thumbs_cache.json`) for quick re-evaluations. Use of JSON for human-readable configurations.
