# Testing

**Analysis Date:** 2026-03-23

## Testing Frameworks

- **Primary Tool:** Pytest is configured as the main test runner (`minversion = "6.0"`).
- **Configuration:** Stored in `pyproject.toml` under `[tool.pytest.ini_options]`.

## Test Coverage & Strategies

- **Unit Testing:** Found in `tests/unit/`. Focuses on validating string matching, calculations (`test_adaptive_crf.py`, `test_quality_options.py`), logic flags (`test_resolution_logic.py`, `test_metadata_filter.py`).
- **Integration Testing:** Tests that ensure multiple components interact properly, typically simulating or mocking the CLI side-effects of `ffmpeg` (`test_auto_delete.py`, `test_downscale_1080p.py`, `test_gpu_command.py`).
- **UI Testing:** Validating `PyQt6` components headless (`test_ui.py`, `test_ui_filters.py`).
- **Concurrency Testing:** Testing data races on the caches (`test_thumb_cache_race.py`).

## Directory Locations

- **Location:** All testing source files exist under the root `/tests/` directory.
- **Fixtures:** `conftest.py` resides at the top of the test suite configuring reusable mock parameters or contexts across the tests.
- **Outputs & Mocks:** Test artifacts and logs are occasionally written out locally, examples include `test_results.txt` and `test_auto_delete_results.txt`.

## CI/CD

- **Automated Execution:** While Pytest is robust, there is no explicit `.github/workflows/` mapping seen that would execute these tests automatically on push. Given the presence of a `.github/` folder, there may be hidden configurations, but local verification is standard via `pytest`. Markers like `@pytest.mark.slow`, `@pytest.mark.gpu`, and `@pytest.mark.integration` are explicitly defined for fine-grained test execution (`pytest -m "not slow"`).
