
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.converter import should_downscale_to_1080p, get_scale_filter, Converter

class TestResolutionLogic(unittest.TestCase):
    def test_should_downscale_standard(self):
        # 1080p -> False
        self.assertFalse(should_downscale_to_1080p(1920, 1080))
        # 720p -> False
        self.assertFalse(should_downscale_to_1080p(1280, 720))
        # 4K -> True
        self.assertTrue(should_downscale_to_1080p(3840, 2160))
        
    def test_should_downscale_portrait(self):
        # Portrait 1080p (1080x1920) -> Should be False
        # Current logic checks height > 1080, so 1920 > 1080 => True (Incorrect)
        # New logic should return False
        self.assertFalse(should_downscale_to_1080p(1080, 1920), "Portrait 1080p should not be downscaled")
        
        # Portrait 4K (2160x3840) -> Should be True
        self.assertTrue(should_downscale_to_1080p(2160, 3840))

    def test_user_scenarios(self):
        # User Scenario 1: 840p video (e.g. 1500x840) -> Should NOT downscale
        # min(1500, 840) = 840 < 1080 -> False
        self.assertFalse(should_downscale_to_1080p(1500, 840), "840p video should NOT be downscaled")
        
        # User Scenario 2: 1440p video (2560x1440) -> Should downscale
        # min(2560, 1440) = 1440 > 1080 -> True
        self.assertTrue(should_downscale_to_1080p(2560, 1440), "1440p video SHOULD be downscaled")

    def test_get_scale_filter_gpu(self):
        # Should be scale_cuda=-2:1080, NOT scale_cuda=1920:-2
        filter_str = get_scale_filter(3840, 2160, has_gpu=True)
        self.assertIn("scale_cuda=-2:1080", filter_str)
        
    def test_get_scale_filter_cpu(self):
        filter_str = get_scale_filter(3840, 2160, has_gpu=False)
        self.assertEqual(filter_str, "scale=-2:1080")

if __name__ == '__main__':
    unittest.main()
