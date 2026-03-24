# Coding Conventions

**Analysis Date:** 2026-03-23

## Naming Patterns

- **Functions/Methods:** `snake_case` with descriptive verbs (e.g., `should_downscale_to_1080p`, `get_output_path`).
- **Variables:** `snake_case` (e.g., `input_path`, `ffmpeg_exe`).
- **Classes:** `PascalCase` representing entities or components (e.g., `ConversionWorker`, `Converter`).
- **Constants:** `UPPER_SNAKE_CASE` declared near module roots (e.g., `DEFAULT_CRF_VALUE`, `STDERR_BUFFER_SIZE`).

## Code Style

- **Formatter & Linter:** Maintained globally via `ruff` (configured in `pyproject.toml`).
  - Max line length of 120.
  - Rules enabled: E, F, B, I, N, UP, C90, RUF.
  - Double quotes enabled as standard via `[tool.ruff.format]`.
- **Type Checking:** Validated via `mypy` with Python 3.10 targets. Includes checks for untyped definitions (`check_untyped_defs = true`).

## Error Handling Patterns

- **Try-Except Wrapping:** Heavy use of `try...except Exception as e:` in workers and processes to ensure background threads fail gracefully without taking the UI thread with them.
- **Signal Emitting:** Exceptions are caught, translated to strings, and propagated via PyQt signals (`self.signals.finished.emit(input_path, False, str(e), False)`).
- **Core Custom Exceptions:** Specific logical errors use custom domain exceptions like `ConversionFailedError`, `FFmpegNotFoundError`, or `InvalidVideoFileError`.

## Logging & Comments

- **Logging:** Facilitated by a singleton `logger` from `src/utils/logger.py`. Output logs use severity identifiers (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).
- **Comments:** Focused on context, specifically describing "Why" certain FFmpeg flags are present (e.g., explaining the hybrid GPU-CPU decoding pipeline).
- **Docstrings:** Required for exposed functions and dataclasses, formatting uses Google or standard Sphinx-like style with typed attributes description.

## State Management & Function Design

- **Dataclasses for State:** Configurations and intermediate static parameters are strictly typed using Python's `@dataclass` (e.g., `ConversionOptions`, `ConversionResult`). This is excellent for keeping parameter lists clean.
- **Global State:** Minimal. Handled mainly by the `config` module via dynamic property lookups.
- **Concurrency Locks:** Avoids generic locks by leveraging `QThreadPool` for sandboxed stateless executors, emitting Qt Signals rather than mutating shared python dicts/lists directly (with the exception of single-property dictionary tracking in the UI orchestrator).
