
import unittest
from unittest.mock import MagicMock, patch
import os
import sys

try:
    from src.ui.main_window_qt import MetadataRunnable, MainWindow
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from src.ui.main_window_qt import MetadataRunnable, MainWindow

class TestMetadataFilter(unittest.TestCase):
    @patch('src.ui.main_window_qt.ScanCache')
    @patch('src.ui.main_window_qt.get_video_codec_only')
    def test_metadata_runnable_updates_cache_and_signals(self, mock_get_codec, MockCache):
        # Setup
        path = "test_video.mp4"
        mock_signaller = MagicMock()
        mock_get_codec.return_value = "hevc"
        
        # Mock Cache
        mock_cache_inst = MockCache.return_value
        mock_cache_inst.get_cached_result.return_value = None # Not cached yet
        
        # Mock OS stat
        with patch('os.stat') as mock_stat:
            mock_stat.return_value.st_mtime = 1000
            mock_stat.return_value.st_size = 500
            
            # Run
            runnable = MetadataRunnable(path, mock_signaller)
            runnable.run()
            
            # Verify
            # 1. Codec was fetched
            mock_get_codec.assert_called_with(path)
            
            # 2. Cache updated ? NO, the runnable no longer updates cache directly.
            # mock_cache_inst.update_result.assert_called_with(path, 1000, 500, "hevc")
            # mock_cache_inst.save.assert_called()
            
            # The runnable is now read-only for cache, it emits signal.
            # The Main Thread does the saving.
            
            # 3. Signal emitted
            mock_signaller.finished.emit.assert_called_with(path, "hevc")

if __name__ == '__main__':
    unittest.main()
