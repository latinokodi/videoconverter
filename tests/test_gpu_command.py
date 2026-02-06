
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path to import converter
# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.core.converter import Converter

class TestGPUCommandGeneration(unittest.TestCase):
    @patch('src.core.converter.get_ffmpeg_path')
    @patch('src.core.converter.get_video_info')
    @patch('subprocess.Popen')
    def test_gpu_downscale_uses_resize_no_filters(self, mock_popen, mock_get_info, mock_get_ffmpeg):
        # Setup
        mock_get_ffmpeg.return_value = 'ffmpeg'
        # Mock 4K video (needs downscale)
        mock_get_info.return_value = {
            'streams': [{'codec_type': 'video', 'width': 3840, 'height': 2160}],
            'format': {'duration': '100'}
        }
        
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stderr.readline.side_effect = ['time=00:00:01.00', '']
        mock_process.poll.side_effect = [None, 0]
        mock_popen.return_value = mock_process

        converter = Converter(has_gpu=True)
        
        # Execute
        converter.convert_single_file('dummy_4k.mp4', {'bitrate': 5000000})
        
        # Verify
        args, _ = mock_popen.call_args
        cmd = args[0]
        cmd_str = ' '.join(cmd)
        
        print(f"\nGenerated Command (Downscale): {cmd_str}")
        
        # Expect hwupload and scale_cuda filter
        self.assertIn('hwupload', cmd_str)
        self.assertIn('scale_cuda', cmd_str)
        
        # Expect NO -resize (encoder option)
        self.assertNotIn('-resize', cmd)
        
        # Expect NO -hwaccel cuda (We are using CPU decoding for robustness)
        self.assertNotIn('-hwaccel', cmd)
        self.assertNotIn('1920x1080', cmd_str.replace('scale_cuda', '')) # 1920x1080 should be in filter, not elsewhere

    @patch('src.core.converter.get_ffmpeg_path')
    @patch('src.core.converter.get_video_info')
    @patch('subprocess.Popen')
    def test_gpu_passthrough_no_filters(self, mock_popen, mock_get_info, mock_get_ffmpeg):
        # Setup
        mock_get_ffmpeg.return_value = 'ffmpeg'
        # Mock 1080p video (no downscale needed)
        mock_get_info.return_value = {
            'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080}],
            'format': {'duration': '100'}
        }
        
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        converter = Converter(has_gpu=True)
        
        # Execute
        converter.convert_single_file('dummy_1080p.mp4', {'bitrate': 5000000})
        
        # Verify
        args, _ = mock_popen.call_args
        cmd = args[0]
        cmd_str = ' '.join(cmd)
        
        print(f"\nGenerated Command (Passthrough): {cmd_str}")
        
        # Expect NO -resize
        self.assertNotIn('-resize', cmd)
        
        # Even for passthrough, if we want GPU encoding, we might need upload?
        # If we use hevc_nvenc, it takes software frames fine usually (hwupload is implicit or handled by driver?).
        # BUT for consistency, we might enforce upload if we want "Always use GPU filters"?
        # Actually passthrough usually doesn't need scaling.
        # If hevc_nvenc is used, we can just feed it software frames. 
        # BUT the crash might also happen there?
        # Let's assume passthrough is strictly "Encoding". 
        # For simplicity, if no scaling needed: 
        # cmd should be just input -> hevc_nvenc.
        
        self.assertNotIn('-vf', cmd) 
        self.assertNotIn('scale_cuda', cmd_str)
        self.assertNotIn('-hwaccel', cmd)

    def test_gpu_real_execution(self):
        """Integration test: Actually run the command on dummy_video.mp4"""
        if not os.path.exists('dummy_video.mp4'):
            print("Skipping integration test: dummy_video.mp4 not found")
            return

        # Use the real Converter, no mocks except maybe callback
        # We patch should_downscale_to_1080p to FORCE resize logic even for 720p video
        with patch('src.core.converter.should_downscale_to_1080p', return_value=True):
             # Force enable GPU output format to reproduce the crash/verify the fix
            with patch.object(Converter, 'convert_single_file', side_effect=Converter(has_gpu=True).convert_single_file) as mock_method:
                 # Actually, better to modify the instance or mock the class behavior if needed.
                 # But since we are testing the class logic, we should probably instantiate it and manually
                 # tweak it if we want to simulate the "Code before my last fix".
                 # OR, better: I will modify the test to failing state by Reverting my code change TEMPORARILY via patch?
                 # No, good TDD means I write the test that EXPECTS the GPU pipeline, and then I modify the code to pass it.
                 # My code currently DISABLES GPU output.
                 # So I should first modify the code to ENABLE it (as requested by user), verifying it fails?
                 # Or just modify the code to ENABLE it + Try to fix it.
                 pass
            
            # I will modify the CODE to re-enable it first, because that's the requirement.
            # But the user said "Make sure...". 
            # I will assume "Red" state is: Enable it -> It Crashes.
            
            converter = Converter(has_gpu=True)
            output = 'dummy_video_hevc.mp4'
        if os.path.exists(output):
            os.remove(output)
            
        print("\n\n--- Running Integration Test with Real FFmpeg ---")
        # We need to un-mock everything. Since this is a method in the same class
        # and previous methods used decorators, this method is clean.
        # BUT import order matters.
        
        success, inp, outp = converter.convert_single_file('dummy_video.mp4', {'bitrate': 1000000})
        
        if success:
            print("Integration Test: SUCCESS")
            if os.path.exists(outp):
                os.remove(outp)
        else:
            print(f"Integration Test: FAILED with error: {inp}")
            self.fail(f"Real conversion failed: {inp}")

if __name__ == '__main__':
    unittest.main()
