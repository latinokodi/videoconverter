"""
Tests for calculate_quality_options function.
Verifies VBR percentage-based quality options generation.
"""

import pytest
from src.utils.helpers import calculate_quality_options


class TestQualityOptions:
    """Test suite for percentage-based quality options generation."""
    
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
    
    def test_returns_three_profiles(self, sample_video_info_hd):
        """Test that three percentage reduction profiles are returned."""
        options = calculate_quality_options(
            file_size=500_000_000,  # 500MB
            duration=1800,  # 30 min
            video_info=sample_video_info_hd
        )
        
        assert len(options) == 3
        assert options[0]['name'] == "60% Reduction"
        assert options[1]['name'] == "50% Reduction"
        assert options[2]['name'] == "40% Reduction"
    
    def test_options_have_bitrate_values(self, sample_video_info_hd):
        """Test that all options contain bitrate values."""
        options = calculate_quality_options(
            file_size=500_000_000,
            duration=1800,
            video_info=sample_video_info_hd
        )
        
        for opt in options:
            assert 'bitrate' in opt
            assert opt['bitrate'] > 0
    
    def test_60_percent_reduction_calculation(self, sample_video_info_hd):
        """Test 60% reduction produces 40% of original size."""
        file_size = 1_000_000_000  # 1GB
        duration = 3600  # 60 minutes
        
        options = calculate_quality_options(
            file_size=file_size,
            duration=duration,
            video_info=sample_video_info_hd
        )
        
        # 60% reduction = 40% final size = 400MB
        expected_size = int(file_size * 0.40)
        expected_bitrate = int((expected_size * 8) / duration)
        
        opt_60 = options[0]
        assert opt_60['name'] == "60% Reduction"
        assert opt_60['estimated_size'] == expected_size
        assert opt_60['bitrate'] == expected_bitrate
    
    def test_50_percent_reduction_calculation(self, sample_video_info_hd):
        """Test 50% reduction produces 50% of original size."""
        file_size = 1_000_000_000  # 1GB
        duration = 3600  # 60 minutes
        
        options = calculate_quality_options(
            file_size=file_size,
            duration=duration,
            video_info=sample_video_info_hd
        )
        
        # 50% reduction = 50% final size = 500MB
        expected_size = int(file_size * 0.50)
        expected_bitrate = int((expected_size * 8) / duration)
        
        opt_50 = options[1]
        assert opt_50['name'] == "50% Reduction"
        assert opt_50['estimated_size'] == expected_size
        assert opt_50['bitrate'] == expected_bitrate
    
    def test_40_percent_reduction_calculation(self, sample_video_info_hd):
        """Test 40% reduction produces 60% of original size."""
        file_size = 1_000_000_000  # 1GB
        duration = 3600  # 60 minutes
        
        options = calculate_quality_options(
            file_size=file_size,
            duration=duration,
            video_info=sample_video_info_hd
        )
        
        # 40% reduction = 60% final size = 600MB
        expected_size = int(file_size * 0.60)
        expected_bitrate = int((expected_size * 8) / duration)
        
        opt_40 = options[2]
        assert opt_40['name'] == "40% Reduction"
        assert opt_40['estimated_size'] == expected_size
        assert opt_40['bitrate'] == expected_bitrate
    
    def test_bitrate_decreases_with_higher_reduction(self, sample_video_info_hd):
        """Test that higher reduction percentages produce lower bitrates."""
        options = calculate_quality_options(
            file_size=500_000_000,
            duration=1800,
            video_info=sample_video_info_hd
        )
        
        # 60% reduction should have lowest bitrate (smallest output)
        # 40% reduction should have highest bitrate (largest output)
        assert options[0]['bitrate'] < options[1]['bitrate']
        assert options[1]['bitrate'] < options[2]['bitrate']
    
    def test_estimated_sizes_increase_with_lower_reduction(self, sample_video_info_hd):
        """Test that estimated sizes increase for lower reduction percentages."""
        options = calculate_quality_options(
            file_size=500_000_000,
            duration=1800,
            video_info=sample_video_info_hd
        )
        
        # 60% reduction = smallest output
        # 40% reduction = largest output
        assert options[0]['estimated_size'] < options[1]['estimated_size']
        assert options[1]['estimated_size'] < options[2]['estimated_size']
    
    def test_4k_flag_detected(self, sample_video_info_4k):
        """Test that 4K videos are properly flagged."""
        options = calculate_quality_options(
            file_size=500_000_000,
            duration=1800,
            video_info=sample_video_info_4k
        )
        
        for opt in options:
            assert opt['is_4k'] is True
    
    def test_hd_flag_not_4k(self, sample_video_info_hd):
        """Test that HD videos are not flagged as 4K."""
        options = calculate_quality_options(
            file_size=500_000_000,
            duration=1800,
            video_info=sample_video_info_hd
        )
        
        for opt in options:
            assert opt['is_4k'] is False
    
    def test_different_file_sizes_scale_correctly(self, sample_video_info_hd):
        """Test that different file sizes produce proportional outputs."""
        duration = 1800
        
        small_options = calculate_quality_options(
            file_size=100_000_000,  # 100MB
            duration=duration,
            video_info=sample_video_info_hd
        )
        
        large_options = calculate_quality_options(
            file_size=1_000_000_000,  # 1GB (10x larger)
            duration=duration,
            video_info=sample_video_info_hd
        )
        
        # Bitrates should scale proportionally (10x)
        for i in range(3):
            ratio = large_options[i]['bitrate'] / small_options[i]['bitrate']
            assert 9.5 < ratio < 10.5  # Allow small rounding variance
    
    def test_different_durations_adjust_bitrate(self, sample_video_info_hd):
        """Test that different durations produce appropriate bitrates."""
        file_size = 500_000_000  # 500MB
        
        short_options = calculate_quality_options(
            file_size=file_size,
            duration=600,  # 10 min
            video_info=sample_video_info_hd
        )
        
        long_options = calculate_quality_options(
            file_size=file_size,
            duration=3600,  # 60 min (6x longer)
            video_info=sample_video_info_hd
        )
        
        # For same target size but longer duration, bitrate should be lower
        for i in range(3):
            assert short_options[i]['bitrate'] > long_options[i]['bitrate']
            # Short should be ~6x higher bitrate
            ratio = short_options[i]['bitrate'] / long_options[i]['bitrate']
            assert 5.5 < ratio < 6.5
    
    def test_zero_duration_handled(self, sample_video_info_hd):
        """Test that zero duration is handled gracefully."""
        options = calculate_quality_options(
            file_size=500_000_000,
            duration=0,  # Edge case
            video_info=sample_video_info_hd
        )
        
        # Should not crash and should return 3 options
        assert len(options) == 3
        # All bitrates should be calculated (using duration=1 fallback)
        for opt in options:
            assert opt['bitrate'] > 0
    
    def test_individual_file_calculation(self, sample_video_info_hd):
        """Test that each file's calculation is independent."""
        # File 1: 1000MB, 60min
        file1_size = 1_000_000_000
        file1_duration = 3600
        
        # File 2: 500MB, 30min
        file2_size = 500_000_000
        file2_duration = 1800
        
        opts1 = calculate_quality_options(file1_size, file1_duration, sample_video_info_hd)
        opts2 = calculate_quality_options(file2_size, file2_duration, sample_video_info_hd)
        
        # 60% reduction on file 1 = 400MB
        assert opts1[0]['estimated_size'] == 400_000_000
        
        # 60% reduction on file 2 = 200MB
        assert opts2[0]['estimated_size'] == 200_000_000
        
        # Bitrates should be equal (same bitrate/second for same reduction)
        # Both are encoded at same compression level
        assert opts1[0]['bitrate'] == opts2[0]['bitrate']
