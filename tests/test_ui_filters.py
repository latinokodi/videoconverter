
import pytest
from PyQt6.QtWidgets import QApplication, QListWidgetItem, QWidget
from PyQt6.QtCore import Qt
import sys
from unittest.mock import MagicMock, patch

# Import MainWindow
try:
    from src.ui.main_window_qt import MainWindow
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from src.ui.main_window_qt import MainWindow

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

class MockWidget(QWidget):
    def __init__(self, codec=None):
        super().__init__()
        self.path = "mock.mp4"
        self.video_info = None
        if codec:
            self.video_info = {
                'streams': [{'codec_type': 'video', 'codec_name': codec}]
            }

def test_filter_logic(qapp):
    with patch('src.ui.main_window_qt.ScanCache') as MockCache:
        # Build window
        window = MainWindow()
        
        # Add Item 1: HEVC
        item1 = QListWidgetItem(window.list_widget)
        w1 = MockWidget(codec='hevc')
        window.list_widget.setItemWidget(item1, w1)
        
        # Add Item 2: H264
        item2 = QListWidgetItem(window.list_widget)
        w2 = MockWidget(codec='h264')
        window.list_widget.setItemWidget(item2, w2)
        
        # Add Item 3: Unknown
        item3 = QListWidgetItem(window.list_widget)
        w3 = MockWidget(codec=None)
        window.list_widget.setItemWidget(item3, w3)
        
        # Ensure Checkbox exists
        assert hasattr(window, 'chk_filter_hevc')
        
        # --- TEST 1: Enable Filter ---
        window.chk_filter_hevc.setChecked(True)
        # apply_filters should be called via signal
        
        # Check Visibility
        # HEVC -> Visible
        assert item1.isHidden() == False, "HEVC item should be visible"
        
        # H264 -> Hidden
        assert item2.isHidden() == True, "H264 item should be hidden"
        
        # Unknown -> Visible (default safe choice)
        assert item3.isHidden() == False, "Unknown codec item should be visible"
        
        # --- TEST 2: Disable Filter (Now "Show Non-HEVC Only") ---
        window.chk_filter_hevc.setChecked(False)
        
        # HEVC -> Hidden (Exclusive Mode)
        assert item1.isHidden() == True, "HEVC item should be hidden when filter is unchecked"
        
        # H264 -> Visible
        assert item2.isHidden() == False, "H264 item should be visible when filter is unchecked"
        
        # Unknown -> Visible (Safe default)
        assert item3.isHidden() == False, "Unknown codec item should be visible"
