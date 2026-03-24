# Concerns

**Analysis Date:** 2026-03-23

## Known Issues

- **Hardware Acceleration Conflicts:** The `converter.py` logic notes historical decoder instability ("1-minute crash") leading to disabling `-hwaccel` and instead using a hybrid CPU Decode -> GPU Init for Filters strategy (`-init_hw_device cuda=cuda:0`).
- **File Overwrites Context:** When moving the original file to trash, there is an existing risk check of verifying if the output path matches the input path identically. This implies potential vulnerabilities with file naming when conversions happen in place or on identical folders.

## Technical Debt

- **Monolithic main window (`main_window_qt.py`):** UI components are highly centralized in a single large Qt Window controller file instead of being modularized into smaller sub-panels or widget sub-classes.
- **Tightly Coupled Utilities:** `worker.py` does direct logic inferences (like calculating default options if none provided) that should ideally be encapsulated within the `Converter` or a specific Job Orchestrator class.
- **Sync Command Execution:** Although offloaded to a `QRunnable`, `subprocess.Popen` is executed synchronously. Transitioning to truly asynchronous I/O with process wrappers might improve efficiency if more complex polling is required.

## Potential Improvements

- **Componentize the UI:** Extract complex UI components (like the Table Views, Progress Trackers, Settings Panels) into their own distinct `.py` class files within `src/ui/`.
- **AsyncIO transition:** Explore transitioning from `QRunnable` and blocking queues to `asyncio` mixed with `qasync` for more granular, unblocked sub-process communications, especially given Python's good asyncio support for `subprocess`.

## Open Questions

- **Fallback Encoders:** Are CPU encoders thoroughly optimized (like `libx265`), and should there be multiple fallbacks (e.g., QSV for Intel GPUs or AMF for AMD GPUs) instead of just NVENC vs CPU?
