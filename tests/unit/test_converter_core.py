"""Unit tests for core conversion functions."""

import pytest
from src.core.converter import should_downscale_to_1080p, get_scale_filter, RESOLUTION_1080P


class TestDownscaleLogic:
    """Tests for downscale logic."""

    @pytest.mark.parametrize("width,height,expected", [
        (1920, 1080, False),   # 1080p - no downscale
        (3840, 2160, True),    # 4K - should downscale
        (2560, 1440, True),    # 1440p - should downscale
        (1280, 720, False),    # 720p - no downscale
        (7680, 4320, True),    # 8K - should downscale
        (1920, 1081, True),    # Just above 1080p
    ])
    def test_should_downscale_to_1080p(self, width: int, height: int, expected: bool):
        """Test downscale decision for various resolutions."""
        assert should_downscale_to_1080p(width, height) == expected

    @pytest.mark.parametrize("has_gpu,expected_filter", [
        (True, "scale_cuda=-2:1080"),
        (False, "scale=-2:1080"),
    ])
    def test_get_scale_filter(self, has_gpu: bool, expected_filter: str):
        """Test correct scale filter selection based on GPU availability."""
        result = get_scale_filter(1920, 2160, has_gpu)
        assert result == expected_filter


class TestResolutionConstants:
    """Tests for resolution constants."""

    def test_resolution_1080p_constant(self):
        """Verify 1080p resolution constant is correct."""
        assert RESOLUTION_1080P == 1080
