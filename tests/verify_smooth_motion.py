
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock modules to allow importing converter without GUI/System dependencies
with patch.dict(sys.modules, {
    'send2trash': MagicMock(),
    'src.utils.logger': MagicMock(),
    'src.utils.config': MagicMock(),
}):
    # Mock specific imports inside converter if needed
    # We will import the actual class but mock its dependencies
    import src.core.converter as converter_module

# Mock helpers
converter_module.get_ffmpeg_path = MagicMock(return_value="ffmpeg")
converter_module.get_video_info = MagicMock(return_value={
    'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080}],
    'format': {'duration': 10}
})
converter_module.config = {'output_mode': 'auto'}
converter_module.logger = MagicMock()

def test_command_generation():
    print("Testing GPU Command Generation...")
    
    # Instantiate Converter with GPU=True
    conv = converter_module.Converter(has_gpu=True)
    
    # Test 1: Smooth Motion + 1080p (No Downscale needed, so no scale_cuda?)
    # Wait, the logic says: if needs_downscale: hwupload -> scale_cuda.
    # If NO downscale, we probably don't use hwupload unless we found a reason to.
    # Let's check logic:
    # if has_gpu: ... if needs_downscale: filters.append(hwupload)...
    # If not needs_downscale, filters is empty?
    # If filters is empty, we just pass -c:v hevc_nvenc.
    # If we add smooth motion:
    # if smooth_motion: filters.append(minterpolate)
    # So if smooth_motion=True and needs_downscale=False: filter chain = [minterpolate]
    # Does NVENC accept output from minterpolate (software yuv420p) directly? Yes.
    
    options = {'smooth_motion': True, 'crf': 24}
    
    # We need to mock subprocess.Popen to capture the command without running it
    with patch('subprocess.Popen') as mock_popen:
        mock_popen.return_value.stderr.readline.return_value = "" # EOF
        mock_popen.return_value.poll.return_value = 0 # Success
        mock_popen.return_value.returncode = 0
        
        # We need a dummy input file
        input_file = "test_1080p.mp4"
        
        # Run
        conv.convert_single_file(input_file, options)
        
        # Inspect args
        args, _ = mock_popen.call_args
        cmd = args[0]
        cmd_str = " ".join(cmd)
        
        print(f"Command 1 (1080p + Smooth): {cmd_str}")
        
        # Verify minterpolate is present
        if "minterpolate" in cmd_str:
            print("PASS: minterpolate found.")
        else:
            print("FAIL: minterpolate missing.")
            
    print("\nTesting GPU Command with Downscale...")
    # Mock video info to be 4K to trigger downscale
    converter_module.get_video_info = MagicMock(return_value={
        'streams': [{'codec_type': 'video', 'width': 3840, 'height': 2160}],
        'format': {'duration': 10}
    })
    
    with patch('subprocess.Popen') as mock_popen:
        mock_popen.return_value.stderr.readline.return_value = ""
        mock_popen.return_value.poll.return_value = 0
        mock_popen.return_value.returncode = 0
        
        conv.convert_single_file("test_4k.mp4", options)
        
        args, _ = mock_popen.call_args
        cmd = args[0]
        cmd_str = " ".join(cmd)
        
        print(f"Command 2 (4K + Smooth): {cmd_str}")
        
        # Verify Order: minterpolate BEFORE hwupload
        if "minterpolate" in cmd_str and "hwupload" in cmd_str:
            idx_mint = cmd_str.find("minterpolate")
            idx_hw = cmd_str.find("hwupload")
            
            if idx_mint < idx_hw:
                print("PASS: minterpolate appears BEFORE hwupload.")
            else:
                print(f"FAIL: Order incorrect! minterpolate at {idx_mint}, hwupload at {idx_hw}")
        else:
            print("FAIL: Missing filters.")

if __name__ == "__main__":
    test_command_generation()
