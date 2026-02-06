"""
TDD Tests for Auto Downscale to 1080p Feature

Test Plan:
- test_4k_video_gets_downscaled: 4K video (>1080p) should have scale filter applied
- test_1080p_video_no_downscale: 1080p video should keep original resolution
- test_720p_video_no_downscale: 720p video should keep original resolution
- test_downscale_with_gpu: GPU path uses scale_cuda or resize parameter
- test_downscale_cpu: CPU path uses scale filter
- test_portrait_video_downscale: Portrait videos (1080x1920) should downscale height to 1080
"""

import os
import sys
import unittest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock, call

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.converter import Converter, get_output_path, should_downscale_to_1080p


class TestDownscaleResolutionDetection(unittest.TestCase):
    """Test cases for resolution detection and downscaling decision."""

    def test_should_downscale_4k_landscape(self):
        """4K landscape (3840x2160) should be downscaled."""
        self.assertTrue(should_downscale_to_1080p(3840, 2160))

    def test_should_downscale_4k_portrait(self):
        """4K portrait (2160x3840) should be downscaled."""
        self.assertTrue(should_downscale_to_1080p(2160, 3840))

    def test_should_downscale_1440p(self):
        """1440p (2560x1440) should be downscaled."""
        self.assertTrue(should_downscale_to_1080p(2560, 1440))

    def test_should_not_downscale_1080p(self):
        """1080p (1920x1080) should NOT be downscaled."""
        self.assertFalse(should_downscale_to_1080p(1920, 1080))

    def test_should_not_downscale_720p(self):
        """720p (1280x720) should NOT be downscaled."""
        self.assertFalse(should_downscale_to_1080p(1280, 720))

    def test_should_downscale_1080p_portrait(self):
        """1080x1920 portrait is actually 1920p height, so it SHOULD be downscaled."""
        self.assertTrue(should_downscale_to_1080p(1080, 1920))

    def test_should_downscale_1081p(self):
        """Anything > 1080p should downscale, e.g., 1920x1081."""
        self.assertTrue(should_downscale_to_1080p(1920, 1081))

    def test_should_downscale_5k(self):
        """5K video should be downscaled."""
        self.assertTrue(should_downscale_to_1080p(5120, 2880))

    def test_should_downscale_8k(self):
        """8K video should be downscaled."""
        self.assertTrue(should_downscale_to_1080p(7680, 4320))


class TestDownscaleIntegration(unittest.TestCase):
    """Test integration of downscaling in converter."""

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

    def _create_mock_video_info(self, width, height):
        """Helper to create mock video info dict."""
        return {
            "streams": [{
                "codec_type": "video",
                "width": width,
                "height": height,
                "codec_name": "h264",
                "avg_frame_rate": "30/1"
            }],
            "format": {
                "duration": "60.0",
                "filename": self.input_file
            }
        }

    @patch('src.core.converter.handle_existing_file_auto')
    @patch('src.core.converter.get_output_path')
    @patch('src.core.converter.subprocess.Popen')
    @patch('src.core.converter.get_video_info')
    def test_4k_video_gets_downscaled_cpu(self, mock_get_info, mock_popen, mock_get_output_path, mock_handle_existing):
        """
        Test that 4K video (3840x2160) gets downscaled to 1080p on CPU path.
        Should include scale filter in ffmpeg command.
        """
        # Arrange
        mock_get_output_path.return_value = self.output_file
        mock_handle_existing.return_value = self.output_file
        mock_get_info.return_value = self._create_mock_video_info(3840, 2160)
        
        # Mock successful ffmpeg process
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stderr.readline.side_effect = ['', '']
        mock_process.poll.return_value = 0
        mock_popen.return_value = mock_process
        
        # Create output file
        with open(self.output_file, 'w') as f:
            f.write("mock output")
        
        # Act - CPU path (has_gpu=False)
        self.converter.has_gpu = False
        options = {'bitrate': 2000000}
        success, _, _ = self.converter.convert_single_file(self.input_file, options)
        
        # Assert
        self.assertTrue(success)
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        
        # Check that scale filter is in command for downscaling
        cmd_str = ' '.join(cmd)
        self.assertIn('scale=', cmd_str, "Should include scale filter for 4K video")
        # Should scale to height 1080, maintaining aspect ratio (-2:1080)
        self.assertIn('1080', cmd_str, "Should scale to 1080p height")

    @patch('src.core.converter.handle_existing_file_auto')
    @patch('src.core.converter.get_output_path')
    @patch('src.core.converter.subprocess.Popen')
    @patch('src.core.converter.get_video_info')
    def test_1080p_video_no_downscale_cpu(self, mock_get_info, mock_popen, mock_get_output_path, mock_handle_existing):
        """
        Test that 1080p video (1920x1080) does NOT get downscaled on CPU path.
        Should NOT include scale filter.
        """
        # Arrange
        mock_get_output_path.return_value = self.output_file
        mock_handle_existing.return_value = self.output_file
        mock_get_info.return_value = self._create_mock_video_info(1920, 1080)
        
        # Mock successful ffmpeg process
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stderr.readline.side_effect = ['', '']
        mock_process.poll.return_value = 0
        mock_popen.return_value = mock_process
        
        # Create output file
        with open(self.output_file, 'w') as f:
            f.write("mock output")
        
        # Act - CPU path
        self.converter.has_gpu = False
        options = {'bitrate': 2000000}
        success, _, _ = self.converter.convert_single_file(self.input_file, options)
        
        # Assert
        self.assertTrue(success)
        cmd = mock_popen.call_args[0][0]
        cmd_str = ' '.join(cmd)
        
        # Should NOT have scale filter for 1080p
        self.assertNotIn('scale=', cmd_str, "Should NOT include scale filter for 1080p video")

    @patch('src.core.converter.handle_existing_file_auto')
    @patch('src.core.converter.get_output_path')
    @patch('src.core.converter.subprocess.Popen')
    @patch('src.core.converter.get_video_info')
    def test_720p_video_no_downscale(self, mock_get_info, mock_popen, mock_get_output_path, mock_handle_existing):
        """
        Test that 720p video (1280x720) does NOT get downscaled.
        """
        # Arrange
        mock_get_output_path.return_value = self.output_file
        mock_handle_existing.return_value = self.output_file
        mock_get_info.return_value = self._create_mock_video_info(1280, 720)
        
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stderr.readline.side_effect = ['', '']
        mock_process.poll.return_value = 0
        mock_popen.return_value = mock_process
        
        with open(self.output_file, 'w') as f:
            f.write("mock output")
        
        # Act
        options = {'bitrate': 2000000}
        success, _, _ = self.converter.convert_single_file(self.input_file, options)
        
        # Assert
        self.assertTrue(success)
        cmd = mock_popen.call_args[0][0]
        cmd_str = ' '.join(cmd)
        
        # Should NOT have scale filter
        self.assertNotIn('scale=', cmd_str, "Should NOT downscale 720p video")

    @patch('src.core.converter.handle_existing_file_auto')
    @patch('src.core.converter.get_output_path')
    @patch('src.core.converter.subprocess.Popen')
    @patch('src.core.converter.get_video_info')
    def test_4k_video_downscale_gpu(self, mock_get_info, mock_popen, mock_get_output_path, mock_handle_existing):
        """
        Test that 4K video gets downscaled on GPU path.
        GPU path should use resize parameter or scale_cuda.
        """
        # Arrange
        mock_get_output_path.return_value = self.output_file
        mock_handle_existing.return_value = self.output_file
        mock_get_info.return_value = self._create_mock_video_info(3840, 2160)
        
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stderr.readline.side_effect = ['', '']
        mock_process.poll.return_value = 0
        mock_popen.return_value = mock_process
        
        with open(self.output_file, 'w') as f:
            f.write("mock output")
        
        # Act - GPU path
        self.converter.has_gpu = True
        options = {'bitrate': 2000000}
        success, _, _ = self.converter.convert_single_file(self.input_file, options)
        
        # Assert
        self.assertTrue(success)
        cmd = mock_popen.call_args[0][0]
        cmd_str = ' '.join(cmd)
        
        # GPU should have some form of scaling (resize param or scale filter)
        has_scaling = 'resize' in cmd_str or 'scale' in cmd_str
        self.assertTrue(has_scaling, f"GPU should downscale 4K video. Command: {cmd_str}")

    @patch('src.core.converter.handle_existing_file_auto')
    @patch('src.core.converter.get_output_path')
    @patch('src.core.converter.subprocess.Popen')
    @patch('src.core.converter.get_video_info')
    def test_portrait_4k_video_downscale(self, mock_get_info, mock_popen, mock_get_output_path, mock_handle_existing):
        """
        Test that 4K portrait video (2160x3840) gets downscaled.
        Height (3840) > 1080, so should downscale.
        """
        # Arrange
        mock_get_output_path.return_value = self.output_file
        mock_handle_existing.return_value = self.output_file
        mock_get_info.return_value = self._create_mock_video_info(2160, 3840)  # Portrait
        
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stderr.readline.side_effect = ['', '']
        mock_process.poll.return_value = 0
        mock_popen.return_value = mock_process
        
        with open(self.output_file, 'w') as f:
            f.write("mock output")
        
        # Act
        self.converter.has_gpu = False
        options = {'bitrate': 2000000}
        success, _, _ = self.converter.convert_single_file(self.input_file, options)
        
        # Assert
        self.assertTrue(success)
        cmd = mock_popen.call_args[0][0]
        cmd_str = ' '.join(cmd)
        
        # Should downscale portrait 4K (height 3840 > 1080)
        self.assertIn('scale=', cmd_str, "Should downscale portrait 4K video")


class TestScaleFilterFormat(unittest.TestCase):
    """Test that scale filters are properly formatted."""

    def test_scale_filter_maintains_aspect_ratio(self):
        """
        Scale filter should use -2:1080 format to maintain aspect ratio.
        -2 means calculate width based on height 1080 while maintaining aspect.
        """
        from src.core.converter import get_scale_filter
        
        # For CPU path
        scale_filter = get_scale_filter(3840, 2160, has_gpu=False)
        self.assertIn('1080', scale_filter)
        # Should maintain aspect ratio
        self.assertTrue('-2:' in scale_filter or ':1080' in scale_filter)


if __name__ == '__main__':
    unittest.main()
