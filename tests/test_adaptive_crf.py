"""
Tests for adaptive CRF (Constant Rate Factor) calculation.
CRF should adapt based on video duration and resolution for consistent quality.
"""

import pytest
from src.utils.helpers import calculate_adaptive_crf


class TestAdaptiveCRF:
    """Test suite for adaptive CRF calculation."""
    
    def test_high_quality_base_crf(self):
        """Test that High Quality profile uses CRF ~20."""
        # Medium duration video (30 min)
        crf = calculate_adaptive_crf(duration_seconds=1800, profile_level="High Quality", is_4k=False)
        assert 18 <= crf <= 22, f"High Quality CRF should be ~20, got {crf}"
    
    def test_balanced_base_crf(self):
        """Test that Balanced profile uses CRF ~24."""
        crf = calculate_adaptive_crf(duration_seconds=1800, profile_level="Balanced", is_4k=False)
        assert 22 <= crf <= 26, f"Balanced CRF should be ~24, got {crf}"
    
    def test_compact_base_crf(self):
        """Test that Compact profile uses CRF ~28."""
        crf = calculate_adaptive_crf(duration_seconds=1800, profile_level="Compact", is_4k=False)
        assert 26 <= crf <= 30, f"Compact CRF should be ~28, got {crf}"
    
    def test_low_bitrate_base_crf(self):
        """Test that Low Bitrate profile uses CRF ~32."""
        crf = calculate_adaptive_crf(duration_seconds=1800, profile_level="Low Bitrate", is_4k=False)
        assert 30 <= crf <= 34, f"Low Bitrate CRF should be ~32, got {crf}"
    
    def test_long_video_gets_better_quality(self):
        """Test that videos >60min get lower CRF (better quality)."""
        normal_crf = calculate_adaptive_crf(duration_seconds=1800, profile_level="Balanced", is_4k=False)
        long_crf = calculate_adaptive_crf(duration_seconds=3900, profile_level="Balanced", is_4k=False)  # 65 min
        
        assert long_crf < normal_crf, f"Long video should have lower CRF: {long_crf} vs {normal_crf}"
        assert (normal_crf - long_crf) >= 2, f"Should be at least 2 CRF points better"
    
    def test_medium_long_video_adjustment(self):
        """Test that 30-60min videos get slight quality boost."""
        short_crf = calculate_adaptive_crf(duration_seconds=1200, profile_level="Balanced", is_4k=False)  # 20 min
        medium_crf = calculate_adaptive_crf(duration_seconds=2700, profile_level="Balanced", is_4k=False)  # 45 min
        
        assert medium_crf < short_crf, f"Medium video should have lower CRF: {medium_crf} vs {short_crf}"
        assert (short_crf - medium_crf) >= 1, f"Should be at least 1 CRF point better"
    
    def test_short_video_gets_higher_crf(self):
        """Test that very short videos (<5min) get higher CRF."""
        normal_crf = calculate_adaptive_crf(duration_seconds=1800, profile_level="Balanced", is_4k=False)  # 30 min
        short_crf = calculate_adaptive_crf(duration_seconds=180, profile_level="Balanced", is_4k=False)  # 3 min
        
        assert short_crf > normal_crf, f"Short video should have higher CRF: {short_crf} vs {normal_crf}"
    
    def test_4k_video_gets_lower_crf(self):
        """Test that 4K videos get 2 points lower CRF."""
        normal_crf = calculate_adaptive_crf(duration_seconds=1800, profile_level="Balanced", is_4k=False)
        crf_4k = calculate_adaptive_crf(duration_seconds=1800, profile_level="Balanced", is_4k=True)
        
        assert crf_4k < normal_crf, f"4K should have lower CRF: {crf_4k} vs {normal_crf}"
        assert (normal_crf - crf_4k) == 2, f"4K should be exactly 2 CRF points better"
    
    def test_crf_clamped_to_valid_range(self):
        """Test that CRF is clamped to 15-35 range."""
        # Test lower bound
        crf_low = calculate_adaptive_crf(duration_seconds=7200, profile_level="High Quality", is_4k=True)
        assert crf_low >= 15, f"CRF should not go below 15, got {crf_low}"
        
        # Test upper bound  
        crf_high = calculate_adaptive_crf(duration_seconds=120, profile_level="Low Bitrate", is_4k=False)
        assert crf_high <= 35, f"CRF should not exceed 35, got {crf_high}"
    
    def test_combined_adjustments(self):
        """Test that multiple adjustments stack correctly."""
        # Long 4K video at High Quality should get multiple adjustments
        crf = calculate_adaptive_crf(duration_seconds=3900, profile_level="High Quality", is_4k=True)
        
        # Base 20 - 2 (4K) - 2 (long) = 16
        assert crf == 16, f"Long 4K High Quality should be CRF 16, got {crf}"
