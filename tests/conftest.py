"""Shared pytest fixtures for video converter tests."""

import pytest
from pathlib import Path
import tempfile
import shutil
from typing import Generator
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.converter import ConversionOptions
from src.core.exceptions import *


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files.

    Yields:
        Path to temporary directory. Automatically cleaned up after test.
    """
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_video_path(temp_dir: Path) -> Path:
    """Create a minimal valid MP4 file for testing.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path to the sample video file
    """
    # Create a minimal valid MP4 (black frame, 1 second)
    # This is a simplification - in reality, you'd use ffmpeg to generate this
    video_path = temp_dir / "sample.mp4"
    video_path.touch()  # Create empty file for now
    return video_path


@pytest.fixture
def conversion_options_cpu() -> ConversionOptions:
    """Create default conversion options for CPU encoding.

    Returns:
        ConversionOptions configured for CPU
    """
    return ConversionOptions(
        crf=24,
        preset="medium",
        has_gpu=False
    )


@pytest.fixture
def conversion_options_gpu() -> ConversionOptions:
    """Create default conversion options for GPU encoding.

    Returns:
        ConversionOptions configured for GPU
    """
    return ConversionOptions(
        crf=24,
        preset="p4",
        has_gpu=True
    )


@pytest.fixture(params=[1920, 3840, 2560])
def video_widths(request) -> int:
    """Parametrized fixture for various video widths.

    Returns:
        Video width in pixels
    """
    return request.param


@pytest.fixture(params=[1080, 2160, 1440])
def video_heights(request) -> int:
    """Parametrized fixture for various video heights.

    Returns:
        Video height in pixels
    """
    return request.param
