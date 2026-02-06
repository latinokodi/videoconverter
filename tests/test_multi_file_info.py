"""
Test multi-file selection info display
"""
import pytest
import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.main_window_qt import MainWindow

@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

def test_single_file_info(qapp):
    """Test that single file shows individual info"""
    window = MainWindow()
    # Simulate single file data
    file_data = {
        'path': 'test.mp4',
        'size': 3221225472,  # 3 GB
        'duration': 4008,
        'bitrate': 6000,
        'resolution': '3840x2160',
        'codec': 'h264'
    }
    
    info_text = window._format_file_info([file_data])
    assert 'test.mp4' in info_text
    assert '3.0 GB' in info_text or '3.00 GB' in info_text
    assert '4008' in info_text or '1:06:48' in info_text
    
def test_multiple_files_aggregate_info(qapp):
    """Test that multiple files show aggregate statistics"""
    window = MainWindow()
    
    files_data = [
        {'path': 'file1.mp4', 'size': 1073741824, 'duration': 1800, 'bitrate': 6000, 'codec': 'h264'},
        {'path': 'file2.mp4', 'size': 2147483648, 'duration': 3600, 'bitrate': 5000, 'codec': 'h264'},
        {'path': 'file3.mp4', 'size': 536870912, 'duration': 900, 'bitrate': 4500, 'codec': 'h264'},
    ]
    
    info_text = window._format_file_info(files_data)
    
    # Should show count
    assert '3 files' in info_text.lower() or '3 Files' in info_text
    
    # Should show total size (3.5 GB)
    assert 'Total' in info_text or 'total' in info_text
    
    # Should show total duration
    assert 'Duration' in info_text or 'duration' in info_text
    
def test_multiple_files_separate_bitrate_calculation(qapp):
    """Test that bitrate is calculated separately for each file in multi-selection"""
    window = MainWindow()
    
    files_data = [
        {'path': 'file1.mp4', 'size': 1073741824, 'duration': 1800, 'codec': 'h264'},
        {'path': 'file2.mp4', 'size': 2147483648, 'duration': 3600, 'codec': 'h264'},
    ]
    
    output_text = window._format_output_preview(files_data, profile='balanced')
    
    # Should calculate and show separate estimates
    assert 'file1' in output_text.lower() or 'File 1' in output_text or 'separately' in output_text.lower()
    
def test_output_preview_multi_file(qapp):
    """Test output preview shows aggregate estimates for multiple files"""
    window = MainWindow()
    
    files_data = [
        {'path': 'file1.mp4', 'size': 1073741824, 'duration': 1800},
        {'path': 'file2.mp4', 'size': 2147483648, 'duration': 3600},
    ]
    
    output_text = window._format_output_preview(files_data, profile='balanced')
    
    # Should show total estimated size
    assert 'Est' in output_text or 'Estimated' in output_text
    assert 'Total' in output_text or 'total' in output_text
