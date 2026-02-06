
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import QApplication
from unittest.mock import patch

# Mocking config and logger before importing UI
with patch('src.utils.config.config') as mock_config, \
     patch('src.utils.logger.logger') as mock_logger:

    try:
        from src.ui.main_window_qt import CombinedInfoCard
    except ImportError:
        # path setup
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from src.ui.main_window_qt import CombinedInfoCard

# We likely need full imports or better isolate the logic.
# Since CombinedInfoCard uses should_downscale_to_1080p, we verify that interaction.

import pytest
from PyQt6.QtWidgets import QLabel

# Helper to find child by type and content roughly
def find_label_with_text(widget, text_part):
    for child in widget.findChildren(QLabel):
        if text_part in child.text():
            return True
    return False

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

def test_output_card_resolution_scaled(qapp):
    # Data that requires scaling (4K)
    data = {'filename': 'video.mp4', 'width': 3840, 'height': 2160, 'size': 1000, 'duration': 60, 'codec': 'h264'}
    bitrates = [{'estimated_size': 500, 'bitrate': 1000}]
    
    card = CombinedInfoCard(data, 0, bitrates, has_gpu=True)
    
    # Logic: 3840x2160 -> min(3840, 2160) = 2160 > 1080 -> Scaled.
    # Output height = 1080.
    # Output width = 3840 * (1080/2160) = 1920.
    # Text should be "1920x1080 (Scaled)"
    
    assert find_label_with_text(card, "1920x1080 (Scaled)")

def test_output_card_resolution_original(qapp):
    # Data that does NOT require scaling (1080p)
    data = {'filename': 'video.mp4', 'width': 1920, 'height': 1080, 'size': 1000, 'duration': 60, 'codec': 'h264'}
    bitrates = [{'estimated_size': 500, 'bitrate': 1000}]
    
    card = CombinedInfoCard(data, 0, bitrates, has_gpu=True)
    
    assert find_label_with_text(card, "1920x1080 (Original)")

# Updated: Vertical 4K (2160x3840) -> min(2160, 3840)=2160 > 1080 -> Scaled
def test_output_card_resolution_portrait_scaled(qapp):
    # 2160x3840. min(2160, 3840) = 2160 > 1080 -> Scaled.
    data = {'filename': 'video.mp4', 'width': 2160, 'height': 3840, 'size': 1000, 'duration': 60, 'codec': 'h264'}
    bitrates = [{'estimated_size': 500, 'bitrate': 1000}]
    
    card = CombinedInfoCard(data, 0, bitrates, has_gpu=True)
    
    # Logic: Same as logic in converter.py
    # width/height > ? 
    # If scaled: height=1080 fixed? NO.
    # The scaler logic usually targets 1080p HEIGHT for landscape.
    # For portrait, if we use should_downscale_to_1080p -> True.
    # Then get_scale_filter uses "scale_cuda=-2:1080" (or similar).
    # If we pass 2160x3840 to -2:1080, FFmpeg resizes height to 1080.
    # So 3840 -> 1080. Width = 2160 * (1080/3840) = 607.5 -> 608.
    # Checks out.
    
    assert find_label_with_text(card, "608x1080 (Scaled)")

def test_output_card_resolution_portrait_hd(qapp):
    # 720x1280 (Vertical HD). min(720, 1280) = 720 <= 1080 -> No scaling.
    data = {'filename': 'video.mp4', 'width': 720, 'height': 1280, 'size': 1000, 'duration': 60, 'codec': 'h264'}
    bitrates = [{'estimated_size': 500, 'bitrate': 1000}]
    
    card = CombinedInfoCard(data, 0, bitrates, has_gpu=True)
    
    assert find_label_with_text(card, "720x1280 (Original)")
    
