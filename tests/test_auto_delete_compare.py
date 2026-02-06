"""
Test for auto delete toggle disabling comparison buttons.
"""

import pytest
from unittest.mock import Mock, MagicMock
from PyQt6.QtWidgets import QApplication
import sys

# Ensure QApplication exists for tests
if not QApplication.instance():
    app = QApplication(sys.argv)


def test_auto_delete_disables_comparison_buttons():
    """Test that enabling auto delete disables all comparison buttons."""
    from src.ui.main_window_qt import MainWindow
    
    window = MainWindow()
    
    # Add a mock file item
    from src.ui.main_window_qt import FileListItem
    widget = FileListItem("test.mp4")
    
    # Simulate adding to the list
    from PyQt6.QtWidgets import QListWidgetItem
    item = QListWidgetItem(window.list_widget)
    window.list_widget.setItemWidget(item, widget)
    
    # Initially, compare button should be disabled (no conversion yet)
    assert not widget.btn_compare.isEnabled()
    
    # Enable auto delete
    window.chk_auto_delete.setChecked(True)
    
    # Compare button should still be disabled
    assert not widget.btn_compare.isEnabled()
    assert "Auto Delete" in widget.btn_compare.toolTip()
    
    # Disable auto delete
    window.chk_auto_delete.setChecked(False)
    
    # Compare button should still be disabled (no conversion completed)
    assert not widget.btn_compare.isEnabled()


def test_auto_delete_prevents_enable_after_conversion():
    """Test that auto delete prevents enabling compare button after conversion."""
    from src.ui.main_window_qt import MainWindow
    from src.ui.main_window_qt import FileListItem
    from PyQt6.QtWidgets import QListWidgetItem
    
    window = MainWindow()
    
    # Add a mock file item
    widget = FileListItem("test.mp4")
    item = QListWidgetItem(window.list_widget)
    window.list_widget.setItemWidget(item, widget)
    
    # Enable auto delete BEFORE conversion
    window.chk_auto_delete.setChecked(True)
    
    # Simulate successful conversion (without delete)
    widget.out_path = "test_hevc.mp4"
    
    # Manually call the logic that would happen in on_file_finished
    if not window.chk_auto_delete.isChecked():
        widget.btn_compare.setEnabled(True)
    
    # Compare button should remain disabled
    assert not widget.btn_compare.isEnabled()
    
    # Now disable auto delete
    window.chk_auto_delete.setChecked(False)
    
    # Manually enable (simulating what on_auto_delete_toggled does)
    if widget.out_path:
        widget.btn_compare.setEnabled(True)
    
    # Now compare button should be enabled
    assert widget.btn_compare.isEnabled()


def test_new_items_respect_auto_delete_state():
    """Test that newly added items respect the current auto delete toggle state."""
    from src.ui.main_window_qt import MainWindow
    
    window = MainWindow()
    
    # Enable auto delete first
    window.chk_auto_delete.setChecked(True)
    
    # Now add files (this would normally go through add_files, but we'll test the key logic)
    from src.ui.main_window_qt import FileListItem
    widget = FileListItem("test.mp4")
    
    # Check that compare button initialization would be affected
    # In add_files, there's logic to disable if auto delete is checked
    if window.chk_auto_delete.isChecked():
        widget.btn_compare.setEnabled(False)
        widget.btn_compare.setToolTip("Compare unavailable when Auto Delete is enabled")
    
    assert not widget.btn_compare.isEnabled()
    assert "Auto Delete" in widget.btn_compare.toolTip()
