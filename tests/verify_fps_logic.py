
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock modules
with patch.dict(sys.modules, {
    'send2trash': MagicMock(),
    'src.utils.logger': MagicMock(),
    'src.utils.config': MagicMock(),
}):
    import src.core.converter as converter_module

# Mock helpers
converter_module.get_ffmpeg_path = MagicMock(return_value="ffmpeg")
converter_module.get_video_info = MagicMock(return_value={
    'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080}],
    'format': {'duration': 10}
})
converter_module.config = {'output_mode': 'auto'}
converter_module.logger = MagicMock()

def test_fps_flags():
    print("Testing FPS Flag Logic...")
    conv = converter_module.Converter(has_gpu=True)
    
    # Case 1: Smooth Motion = False
    print("\nCase 1: Smooth Motion OFF")
    with patch('subprocess.Popen') as mock_popen:
        mock_popen.return_value.stderr.readline.return_value = ""
        mock_popen.return_value.poll.return_value = 0
        mock_popen.return_value.returncode = 0
        
        conv.convert_single_file("test.mp4", {'smooth_motion': False, 'crf': 24})
        
        args, _ = mock_popen.call_args
        cmd_str = " ".join(args[0])
        
        if "-fps_mode passthrough" in cmd_str:
            print("PASS: '-fps_mode passthrough' is PRESENT.")
        else:
            print(f"FAIL: '-fps_mode passthrough' is MISSING. Cmd: {cmd_str}")

    # Case 2: Smooth Motion = True
    print("\nCase 2: Smooth Motion ON")
    with patch('subprocess.Popen') as mock_popen:
        mock_popen.return_value.stderr.readline.return_value = ""
        mock_popen.return_value.poll.return_value = 0
        mock_popen.return_value.returncode = 0
        
        conv.convert_single_file("test.mp4", {'smooth_motion': True, 'crf': 24})
        
        args, _ = mock_popen.call_args
        cmd_str = " ".join(args[0])
        
        args, _ = mock_popen.call_args
        cmd_str = " ".join(args[0])
        
        if "-r 60" not in cmd_str:
            print("PASS: '-r 60' is ABSENT (Relying on filter).")
        else:
            print(f"FAIL: '-r 60' is PRESENT! Cmd: {cmd_str}")
            
        if "-fps_mode passthrough" not in cmd_str:
            print("PASS: '-fps_mode passthrough' is ABSENT.")
        else:
            print(f"FAIL: '-fps_mode passthrough' is PRESENT! Cmd: {cmd_str}")

if __name__ == "__main__":
    test_fps_flags()
