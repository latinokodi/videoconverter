"""
TDD Tests for Auto Delete Original File Feature

Test Plan:
- test_auto_delete_success: Mock successful conversion, assert input file is removed.
- test_auto_delete_disabled: Mock successful conversion, assert input file REMAINS.
- test_auto_delete_failure: Mock FAILED conversion, assert input file REMAINS.
"""

import os
import sys
import unittest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.converter import Converter, get_output_path


class TestAutoDeleteFeature(unittest.TestCase):
    """Test cases for the auto-delete original file feature."""

    def setUp(self):
        """Set up test fixtures."""
        self.converter = Converter(has_gpu=False)
        self.test_dir = tempfile.mkdtemp()
        self.input_file = os.path.join(self.test_dir, "test_input.mp4")
        self.output_file = os.path.join(self.test_dir, "test_input_hevc.mp4")
        
        # Create a dummy input file
        with open(self.input_file, 'w') as f:
            f.write("dummy video content")
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_mock_output_file(self, content="mock converted content"):
        """Helper to create a mock output file."""
        with open(self.output_file, 'w') as f:
            f.write(content)

    @patch('src.core.converter.handle_existing_file_auto')
    @patch('src.core.converter.get_output_path')
    @patch('src.core.converter.subprocess.Popen')
    @patch('src.core.converter.send2trash')
    def test_auto_delete_success(self, mock_send2trash, mock_popen, mock_get_output_path, mock_handle_existing):
        """
        Test that original file is deleted when:
        - Conversion reports SUCCESS
        - New file EXISTS
        - New file size is > 0
        - delete_original flag is True
        """
        # Arrange: Setup mocks for successful conversion
        mock_get_output_path.return_value = self.output_file
        mock_handle_existing.return_value = self.output_file
        
        # Mock successful ffmpeg process
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stderr.readline.side_effect = ['', '']  # Empty lines to end loop
        mock_process.poll.return_value = 0
        mock_popen.return_value = mock_process
        
        # Create output file (simulating successful conversion)
        self._create_mock_output_file()
        
        # Pre-condition: Input file exists
        self.assertTrue(os.path.exists(self.input_file), "Input file should exist before conversion")
        
        # Act: Run conversion with delete_original=True
        options = {'bitrate': 2000000}
        success, result_path, error_msg = self.converter.convert_single_file(
            self.input_file, options, delete_original=True
        )
        
        # Assert: Conversion succeeded and original file was deleted
        self.assertTrue(success, "Conversion should report success")
        mock_send2trash.assert_called_once_with(self.input_file)

    @patch('src.core.converter.handle_existing_file_auto')
    @patch('src.core.converter.get_output_path')
    @patch('src.core.converter.subprocess.Popen')
    @patch('src.core.converter.send2trash')
    def test_auto_delete_disabled(self, mock_send2trash, mock_popen, mock_get_output_path, mock_handle_existing):
        """
        Test that original file REMAINS when delete_original flag is False (default).
        Even if conversion is successful.
        """
        # Arrange: Setup mocks for successful conversion
        mock_get_output_path.return_value = self.output_file
        mock_handle_existing.return_value = self.output_file
        
        # Mock successful ffmpeg process
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stderr.readline.side_effect = ['', '']
        mock_process.poll.return_value = 0
        mock_popen.return_value = mock_process
        
        # Create output file
        self._create_mock_output_file()
        
        # Pre-condition: Input file exists
        self.assertTrue(os.path.exists(self.input_file))
        
        # Act: Run conversion with delete_original=False (default)
        options = {'bitrate': 2000000}
        success, result_path, error_msg = self.converter.convert_single_file(
            self.input_file, options, delete_original=False
        )
        
        # Assert: Conversion succeeded but original file was NOT deleted
        self.assertTrue(success, "Conversion should report success")
        mock_send2trash.assert_not_called()
        self.assertTrue(os.path.exists(self.input_file), "Input file should still exist")

    @patch('src.core.converter.handle_existing_file_auto')
    @patch('src.core.converter.get_output_path')
    @patch('src.core.converter.subprocess.Popen')
    @patch('src.core.converter.send2trash')
    def test_auto_delete_failure(self, mock_send2trash, mock_popen, mock_get_output_path, mock_handle_existing):
        """
        Test that original file REMAINS when conversion FAILS.
        Even if delete_original flag is True.
        """
        # Arrange: Setup mocks for FAILED conversion
        mock_get_output_path.return_value = self.output_file
        mock_handle_existing.return_value = self.output_file
        
        # Mock failed ffmpeg process
        mock_process = MagicMock()
        mock_process.returncode = 1  # Failure code
        mock_process.stderr.readline.side_effect = ['error: codec not found', '']
        mock_process.poll.return_value = 1
        mock_popen.return_value = mock_process
        
        # Pre-condition: Input file exists
        self.assertTrue(os.path.exists(self.input_file))
        
        # Act: Run conversion with delete_original=True but conversion fails
        options = {'bitrate': 2000000}
        success, result_path, error_msg = self.converter.convert_single_file(
            self.input_file, options, delete_original=True
        )
        
        # Assert: Conversion failed and original file was NOT deleted
        self.assertFalse(success, "Conversion should report failure")
        mock_send2trash.assert_not_called()
        self.assertTrue(os.path.exists(self.input_file), "Input file should still exist after failed conversion")

    @patch('src.core.converter.handle_existing_file_auto')
    @patch('src.core.converter.get_output_path')
    @patch('src.core.converter.subprocess.Popen')
    @patch('src.core.converter.send2trash')
    def test_auto_delete_output_not_exists(self, mock_send2trash, mock_popen, mock_get_output_path, mock_handle_existing):
        """
        Test that original file REMAINS when output file does NOT exist.
        Safety check: Don't delete original if we can't confirm output was created.
        """
        # Arrange: Setup mocks
        mock_get_output_path.return_value = self.output_file
        mock_handle_existing.return_value = self.output_file
        
        # Mock successful ffmpeg process return code
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stderr.readline.side_effect = ['', '']
        mock_process.poll.return_value = 0
        mock_popen.return_value = mock_process
        
        # NOTE: We do NOT create the output file - simulating a case where
        # ffmpeg reports success but file wasn't actually created
        
        # Pre-condition: Input exists, output does NOT exist
        self.assertTrue(os.path.exists(self.input_file))
        self.assertFalse(os.path.exists(self.output_file))
        
        # Act
        options = {'bitrate': 2000000}
        success, result_path, error_msg = self.converter.convert_single_file(
            self.input_file, options, delete_original=True
        )
        
        # Assert: Original file NOT deleted because output doesn't exist
        mock_send2trash.assert_not_called()
        self.assertTrue(os.path.exists(self.input_file), "Input file should still exist")

    @patch('src.core.converter.handle_existing_file_auto')
    @patch('src.core.converter.get_output_path')
    @patch('src.core.converter.subprocess.Popen')
    @patch('src.core.converter.send2trash')
    def test_auto_delete_output_zero_size(self, mock_send2trash, mock_popen, mock_get_output_path, mock_handle_existing):
        """
        Test that original file REMAINS when output file exists but has 0 bytes.
        Safety check: Don't delete original if output is empty/corrupt.
        """
        # Arrange
        mock_get_output_path.return_value = self.output_file
        mock_handle_existing.return_value = self.output_file
        
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stderr.readline.side_effect = ['', '']
        mock_process.poll.return_value = 0
        mock_popen.return_value = mock_process
        
        # Create output file with ZERO bytes
        with open(self.output_file, 'w') as f:
            f.write("")  # Empty file
        
        # Pre-condition: Input exists, output exists but is empty
        self.assertTrue(os.path.exists(self.input_file))
        self.assertTrue(os.path.exists(self.output_file))
        self.assertEqual(os.path.getsize(self.output_file), 0)
        
        # Act
        options = {'bitrate': 2000000}
        success, result_path, error_msg = self.converter.convert_single_file(
            self.input_file, options, delete_original=True
        )
        
        # Assert: Original file NOT deleted because output is empty
        mock_send2trash.assert_not_called()
        self.assertTrue(os.path.exists(self.input_file), "Input file should still exist")


class TestWorkerIntegration(unittest.TestCase):
    """Test Worker integration with auto-delete flag."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.input_file = os.path.join(self.test_dir, "test_input.mp4")
        self.output_file = os.path.join(self.test_dir, "test_input_hevc.mp4")
        
        with open(self.input_file, 'w') as f:
            f.write("dummy video content")
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_worker_emits_deleted_flag(self):
        """Test that FileConversionRunnable emits the correct deleted flag in finished signal."""
        from src.ui.worker import FileConversionRunnable
        from PyQt6.QtCore import QCoreApplication
        
        # We need a QCoreApplication to use signals properly in tests
        app = QCoreApplication.instance()
        if not app:
            app = QCoreApplication([])

        mock_item = {
            'path': self.input_file,
            'profile_idx': 1,
            'delete_flag': True,
            'options': {'bitrate': 2000000}
        }
        
        runnable = FileConversionRunnable(mock_item, has_gpu=False)
        
        # Mock the converter to avoid actual ffmpeg call
        runnable.converter.convert_single_file = Mock(return_value=(True, self.output_file, None))
        
        # Record signal emit
        recorded_signals = []
        def on_finished(path, success, result, deleted):
            recorded_signals.append((path, success, result, deleted))
            
        runnable.signals.finished.connect(on_finished)
        
        # Act
        runnable.run()
        
        # Assert
        self.assertEqual(len(recorded_signals), 1)
        self.assertEqual(recorded_signals[0][3], True, "Signal should emit deleted=True")

    def test_worker_emits_not_deleted_flag(self):
        """Test that FileConversionRunnable emits deleted=False when flag is off."""
        from src.ui.worker import FileConversionRunnable
        from PyQt6.QtCore import QCoreApplication
        
        app = QCoreApplication.instance()
        if not app:
            app = QCoreApplication([])

        mock_item = {
            'path': self.input_file,
            'profile_idx': 1,
            'delete_flag': False,
            'options': {'bitrate': 2000000}
        }
        
        runnable = FileConversionRunnable(mock_item, has_gpu=False)
        runnable.converter.convert_single_file = Mock(return_value=(True, self.output_file, None))
        
        recorded_signals = []
        def on_finished(path, success, result, deleted):
            recorded_signals.append((path, success, result, deleted))
            
        runnable.signals.finished.connect(on_finished)
        
        runnable.run()
        
        self.assertEqual(len(recorded_signals), 1)
        self.assertEqual(recorded_signals[0][3], False, "Signal should emit deleted=False")


if __name__ == '__main__':
    unittest.main()
