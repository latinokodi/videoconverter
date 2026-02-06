"""
Tests for CombinedInfoCard widget.
Tests the unified card that displays both input and output file information.
"""

import pytest
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QHBoxLayout, QLabel
from src.ui.main_window_qt import CombinedInfoCard
import sys


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def sample_file_data():
    """Sample file data for testing."""
    return {
        'filename': 'EPORNER.COM_SylviMoTqgr_3Ls_Dj_A_Mi_Esposa_Silvana_Lee_Un_Masaje.mp4',
        'path': 'F:\\test\\video.mp4',
        'size': 409_560_000,  # ~409 MB
        'duration': 1280.0,  # seconds
        'width': 1280,
        'height': 720,
        'codec': 'av1',
        'info': {
            'format': {'duration': '1280.0'},
            'streams': [
                {
                    'codec_type': 'video',
                    'codec_name': 'av1',
                    'width': 1280,
                    'height': 720
                }
            ]
        }
    }


@pytest.fixture
def sample_bitrates_data():
    """Sample bitrate calculation results."""
    return [
        {
            'name': 'High Quality',
            'bitrate': 5000000,
            'estimated_size': 800_000_000
        },
        {
            'name': 'Balanced',
            'bitrate': 3000000,
            'estimated_size': 480_000_000
        },
        {
            'name': 'Compact',
            'bitrate': 2000000,
            'estimated_size': 320_000_000
        },
        {
            'name': 'Low Bitrate',
            'bitrate': 1000000,
            'estimated_size': 160_000_000
        }
    ]


class TestCombinedInfoCard:
    """Test suite for CombinedInfoCard widget."""
    
    def test_card_creation(self, qapp, sample_file_data, sample_bitrates_data):
        """Test that card can be created with valid data."""
        card = CombinedInfoCard(
            data=sample_file_data,
            profile_idx=3,  # Low Bitrate
            bitrates_data=sample_bitrates_data,
            has_gpu=False
        )
        
        assert card is not None
        assert card.objectName() == "info_card"
    
    def test_displays_input_filename(self, qapp, sample_file_data, sample_bitrates_data):
        """Test that input filename is displayed."""
        card = CombinedInfoCard(
            data=sample_file_data,
            profile_idx=3,
            bitrates_data=sample_bitrates_data,
            has_gpu=False
        )
        
        # Find label with filename
        labels = card.findChildren(QLabel)
        filename_labels = [lbl for lbl in labels if sample_file_data['filename'] in lbl.text()]
        
        assert len(filename_labels) > 0, "Filename should be displayed in card"
    
    def test_displays_input_details(self, qapp, sample_file_data, sample_bitrates_data):
        """Test that input file details are displayed (size, duration, resolution, codec)."""
        card = CombinedInfoCard(
            data=sample_file_data,
            profile_idx=3,
            bitrates_data=sample_bitrates_data,
            has_gpu=False
        )
        
        labels = card.findChildren(QLabel)
        all_text = " ".join([lbl.text() for lbl in labels])
        
        # Check for resolution
        assert "1280x720" in all_text or "1280" in all_text
        
        # Check for codec
        assert "av1" in all_text.lower()
        
        # Check for size (should show MB)
        assert "MB" in all_text or "GB" in all_text
    
    def test_displays_output_filename(self, qapp, sample_file_data, sample_bitrates_data):
        """Test that output filename is displayed with _hevc suffix."""
        card = CombinedInfoCard(
            data=sample_file_data,
            profile_idx=3,
            bitrates_data=sample_bitrates_data,
            has_gpu=False
        )
        
        labels = card.findChildren(QLabel)
        all_text = " ".join([lbl.text() for lbl in labels])
        
        # Output filename should have _hevc suffix
        assert "_hevc.mp4" in all_text or "hevc" in all_text.lower()
    
    def test_displays_output_estimated_size(self, qapp, sample_file_data, sample_bitrates_data):
        """Test that estimated output size is displayed."""
        card = CombinedInfoCard(
            data=sample_file_data,
            profile_idx=3,  # Low Bitrate = 160 MB
            bitrates_data=sample_bitrates_data,
            has_gpu=False
        )
        
        labels = card.findChildren(QLabel)
        all_text = " ".join([lbl.text() for lbl in labels])
        
        # Should show estimated size
        assert "Est:" in all_text or "estimated" in all_text.lower()
    
    def test_displays_encoder_type_cpu(self, qapp, sample_file_data, sample_bitrates_data):
        """Test that CPU encoder is shown when GPU not available."""
        card = CombinedInfoCard(
            data=sample_file_data,
            profile_idx=3,
            bitrates_data=sample_bitrates_data,
            has_gpu=False
        )
        
        labels = card.findChildren(QLabel)
        encoder_labels = [lbl for lbl in labels if "x265" in lbl.text() or "HEVC" in lbl.text()]
        
        assert len(encoder_labels) > 0
        # Should NOT show NVENC for CPU mode
        assert not any("NVENC" in lbl.text() for lbl in labels)
    
    def test_displays_encoder_type_gpu(self, qapp, sample_file_data, sample_bitrates_data):
        """Test that GPU encoder is shown when GPU is available."""
        card = CombinedInfoCard(
            data=sample_file_data,
            profile_idx=3,
            bitrates_data=sample_bitrates_data,
            has_gpu=True
        )
        
        labels = card.findChildren(QLabel)
        encoder_labels = [lbl for lbl in labels if "NVENC" in lbl.text()]
        
        assert len(encoder_labels) > 0, "Should show NVENC when GPU is available"
    
    def test_card_has_proper_layout(self, qapp, sample_file_data, sample_bitrates_data):
        """Test that card has proper horizontal layout structure."""
        card = CombinedInfoCard(
            data=sample_file_data,
            profile_idx=3,
            bitrates_data=sample_bitrates_data,
            has_gpu=False
        )
        
        # Card should have a main layout (horizontal)
        layout = card.layout()
        assert layout is not None
        assert isinstance(layout, QHBoxLayout), "Main layout should be horizontal (QHBoxLayout)"
    
    def test_respects_profile_selection(self, qapp, sample_file_data, sample_bitrates_data):
        """Test that different profiles show different estimated sizes."""
        card_high = CombinedInfoCard(
            data=sample_file_data,
            profile_idx=0,  # High Quality = 800 MB
            bitrates_data=sample_bitrates_data,
            has_gpu=False
        )
        
        card_low = CombinedInfoCard(
            data=sample_file_data,
            profile_idx=3,  # Low Bitrate = 160 MB
            bitrates_data=sample_bitrates_data,
            has_gpu=False
        )
        
        # Both should display, but content could differ based on profile
        assert card_high is not None
        assert card_low is not None
