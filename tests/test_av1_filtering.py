"""
Tests for AV1 and HEVC codec filtering.
Files with these codecs should be excluded from the conversion queue.
"""

import pytest
from src.ui.main_window_qt import MainWindow


class TestCodecFiltering:
    """Test suite for codec filtering logic."""
    
    def test_should_exclude_av1(self):
        """Test that AV1 codec is excluded from queue."""
        # AV1 is already a modern, efficient codec
        assert MainWindow._should_exclude_codec("av1") is True
        assert MainWindow._should_exclude_codec("AV1") is True
        assert MainWindow._should_exclude_codec("libaom-av1") is True
    
    def test_should_exclude_hevc(self):
        """Test that HEVC/H265 codec is excluded (already target format)."""
        assert MainWindow._should_exclude_codec("hevc") is True
        assert MainWindow._should_exclude_codec("HEVC") is True
        assert MainWindow._should_exclude_codec("h265") is True
        assert MainWindow._should_exclude_codec("H265") is True
        assert MainWindow._should_exclude_codec("libx265") is True
    
    def test_should_include_h264(self):
        """Test that H264 codec is included in queue (needs conversion)."""
        assert MainWindow._should_exclude_codec("h264") is False
        assert MainWindow._should_exclude_codec("H264") is False
        assert MainWindow._should_exclude_codec("avc") is False
        assert MainWindow._should_exclude_codec("libx264") is False
    
    def test_should_include_vp9(self):
        """Test that VP9 codec is included in queue (can be converted)."""
        assert MainWindow._should_exclude_codec("vp9") is False
        assert MainWindow._should_exclude_codec("VP9") is False
    
    def test_should_include_mpeg2(self):
        """Test that older codecs are included in queue."""
        assert MainWindow._should_exclude_codec("mpeg2video") is False
        assert MainWindow._should_exclude_codec("mpeg4") is False
    
    def test_should_include_unknown(self):
        """Test that unknown codecs are included (to avoid false exclusions)."""
        assert MainWindow._should_exclude_codec("unknown") is False
        assert MainWindow._should_exclude_codec("") is False
    
    def test_case_insensitive(self):
        """Test that codec checking is case-insensitive."""
        assert MainWindow._should_exclude_codec("Av1") is True
        assert MainWindow._should_exclude_codec("HEvC") is True
        assert MainWindow._should_exclude_codec("h264") is False
