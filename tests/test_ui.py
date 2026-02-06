"""
Test UI components and styling
"""
import pytest
from PyQt6.QtWidgets import QApplication
from src.ui.main_window_qt import MainWindow
import sys

@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

def test_main_window_loads(qapp):
    """Test that main window loads without errors"""
    window = MainWindow()
    assert window.windowTitle() == "Pro Video Converter - HEVC Batch Edition"
    assert window.width() == 1200
    assert window.height() == 800

def test_theme_applied(qapp):
    """Test that modern theme is applied"""
    window = MainWindow()
    stylesheet = window.styleSheet()
    assert "QMainWindow" in stylesheet
    assert "qlineargradient" in stylesheet
    
def test_stat_cards_created(qapp):
    """Test that stat dashboard cards are created"""
    window = MainWindow()
    assert hasattr(window, 'stat_total')
    assert hasattr(window, 'stat_pending')
    assert hasattr(window, 'stat_converting')
    assert hasattr(window, 'stat_complete')
    
def test_stat_card_structure(qapp):
    """Test stat card has correct structure"""
    window = MainWindow()
    card = window.stat_total
    assert card is not None
    assert hasattr(card, 'value_label')
    assert card.objectName() == "stat_card"

def test_buttons_exist(qapp):
    """Test that all action buttons are created"""
    window = MainWindow()
    assert hasattr(window, 'btn_add')
    assert hasattr(window, 'btn_scan')
    assert hasattr(window, 'btn_convert')
    assert hasattr(window, 'btn_clear')

def test_list_widget_exists(qapp):
    """Test that file list widget is created"""
    window = MainWindow()
    assert hasattr(window, 'list_widget')
    assert window.list_widget is not None
