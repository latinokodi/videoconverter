"""
Tests for calculate_quality_options function.
Verifies CRF-based quality options generation.
"""

import pytest
from src.utils.helpers import calculate_quality_options


class TestQualityOptions:
    """Test suite for quality options generation."""
    
    @pytest.fixture
    def sample_video_info_hd(self):
        """Sample 1080p video info."""
        return {
            'streams': [{
                'codec_type': 'video',
                'width': 1920,
                'height': 1080
            }]
        }
    
    @pytest.fixture
    def sample_video_info_4k(self):
        """Sample 4K video info."""
        return {
            'streams': [{
                'codec_type': 'video',
                'width': 3840,
                'height': 2160
            }]
        }
    
    def test_returns_four_profiles(self, sample_video_info_hd):
        """Test that four quality profiles are returned."""
        options = calculate_quality_options(
            file_size=500_000_000,  # 500MB
            duration=1800,  # 30 min
            video_info=sample_video_info_hd
        )
        
        assert len(options) == 4
        assert options[0]['name'] == "High Quality"
        assert options[1]['name'] == "Balanced"
        assert options[2]['name'] == "Compact"
        assert options[3]['name'] == "Low Bitrate"
    
    def test_options_have_crf_values(self, sample_video_info_hd):
        """Test that all options contain CRF values."""
        options = calculate_quality_options(
            file_size=500_000_000,
            duration=1800,
            video_info=sample_video_info_hd
        )
        
        for opt in options:
            assert 'crf' in opt
            assert 15 <= opt['crf'] <= 35
    
    def test_crf_increases_with_lower_quality(self, sample_video_info_hd):
        """Test that CRF values increase (quality decreases) across profiles."""
        options = calculate_quality_options(
            file_size=500_000_000,
            duration=1800,
            video_info=sample_video_info_hd
        )
        
        # CRF should increase: High Quality < Balanced < Compact < Low Bitrate
        assert options[0]['crf'] < options[1]['crf']
        assert options[1]['crf'] < options[2]['crf']
        assert options[2]['crf'] < options[3]['crf']
    
    def test_estimated_sizes_decrease_with_quality(self, sample_video_info_hd):
        """Test that estimated sizes decrease for lower quality profiles."""
        options = calculate_quality_options(
            file_size=500_000_000,
            duration=1800,
            video_info=sample_video_info_hd
        )
        
        # Sizes should decrease: High Quality > Balanced > Compact > Low Bitrate
        assert options[0]['estimated_size'] > options[1]['estimated_size']
        assert options[1]['estimated_size'] > options[2]['estimated_size']
        assert options[2]['estimated_size'] > options[3]['estimated_size']
    
    def test_4k_flag_detected(self, sample_video_info_4k):
        """Test that 4K videos are properly flagged."""
        options = calculate_quality_options(
            file_size=500_000_000,
            duration=1800,
            video_info=sample_video_info_4k
        )
        
        for opt in options:
            assert opt['is_4k'] is True
    
    def test_4k_gets_lower_crf(self, sample_video_info_hd, sample_video_info_4k):
        """Test that 4K videos get lower CRF values."""
        hd_options = calculate_quality_options(
            file_size=500_000_000,
            duration=1800,
            video_info=sample_video_info_hd
        )
        
        uhd_options = calculate_quality_options(
            file_size=500_000_000,
            duration=1800,
            video_info=sample_video_info_4k
        )
        
        # All 4K CRF values should be lower (better quality)
        for i in range(4):
            assert uhd_options[i]['crf'] < hd_options[i]['crf']
    
    def test_long_video_gets_better_quality(self, sample_video_info_hd):
        """Test that longer videos get lower CRF (better quality)."""
        short_options = calculate_quality_options(
            file_size=200_000_000,  # 200MB
            duration=600,  # 10 min
            video_info=sample_video_info_hd
        )
        
        long_options = calculate_quality_options(
            file_size=2_000_000_000,  # 2GB
            duration=3900,  # 65 min
            video_info=sample_video_info_hd
        )
        
        # Long video should have lower CRF
        for i in range(4):
            assert long_options[i]['crf'] < short_options[i]['crf']
