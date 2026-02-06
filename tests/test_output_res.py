
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import QApplication
from unittest.mock import patch

# Mocking config and logger before importing UI
with patch('src.utils.config.config') as mock_config, \
     patch('src.utils.logger.logger') as mock_logger:

    try:
        from src.ui.main_window_qt import OutputInfoCard
    except ImportError:
        # path setup
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from src.ui.main_window_qt import OutputInfoCard

# We likely need full imports or better isolate the logic.
# Since OutputInfoCard uses should_downscale_to_1080p, we verify that interaction.

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
    data = {'filename': 'video.mp4', 'width': 3840, 'height': 2160, 'size': 1000, 'duration': 60}
    bitrates = [{'estimated_size': 500, 'bitrate': 1000}]
    
    card = OutputInfoCard(data, 0, bitrates, has_gpu=True)
    
    # Logic: 3840x2160 -> min(3840, 2160) = 2160 > 1080 -> Scaled.
    # Output height = 1080.
    # Output width = 3840 * (1080/2160) = 1920.
    # Text should be "1920x1080 (Scaled)"
    
    assert find_label_with_text(card, "1920x1080 (Scaled)")

def test_output_card_resolution_original(qapp):
    # Data that does NOT require scaling (1080p)
    data = {'filename': 'video.mp4', 'width': 1920, 'height': 1080, 'size': 1000, 'duration': 60}
    bitrates = [{'estimated_size': 500, 'bitrate': 1000}]
    
    card = OutputInfoCard(data, 0, bitrates, has_gpu=True)
    
    assert find_label_with_text(card, "1920x1080 (Original)")

def test_output_card_resolution_portrait_scaled(qapp):
    # Data that requires scaling (Portrait 4Kish)
    # 2160x3840. min(2160, 3840) = 2160 > 1080 -> Scaled.
    data = {'filename': 'video.mp4', 'width': 2160, 'height': 3840, 'size': 1000, 'duration': 60}
    bitrates = [{'estimated_size': 500, 'bitrate': 1000}]
    
    card = OutputInfoCard(data, 0, bitrates, has_gpu=True)
    
    # Logic: Output height = 1080.
    # Output width = 2160 * (1080/3840) = 2160 * 0.28125 = 607.5 -> 607 -> 608 (even).
    # Width = int(2160 * (1080/3840)) = 607.
    # Code ensures even: 607 % 2 != 0 -> 608.
    
    assert find_label_with_text(card, "608x1080 (Scaled)")
    
