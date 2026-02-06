import os
import json
import shutil
from pathlib import Path
from typing import Dict, Optional, List
from .logger import logger
import subprocess
import math

# Try to import imageio_ffmpeg for fallback
try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None

_ffmpeg_path_cache = None

def get_ffmpeg_path() -> str:
    """Returns the path to ffmpeg executable. Prioritizes system PATH, then imageio-ffmpeg."""
    global _ffmpeg_path_cache
    if _ffmpeg_path_cache:
        return _ffmpeg_path_cache

    # check system path first
    if shutil.which("ffmpeg"):
        _ffmpeg_path_cache = "ffmpeg"
        return "ffmpeg"
    
    # check if imageio_ffmpeg is available
    if imageio_ffmpeg:
        try:
             # imageio_ffmpeg might return absolute path
            path = imageio_ffmpeg.get_ffmpeg_exe()
            _ffmpeg_path_cache = path
            return path
        except:
            pass
            
    _ffmpeg_path_cache = "ffmpeg"
    return "ffmpeg" # Fallback


def normalize_path(path: str) -> str:
    if (path.startswith('"') and path.endswith('"')) or (path.startswith("'") and path.endswith("'")):
        path = path[1:-1]
    return str(Path(path))

def format_size(size_bytes: int) -> str:
    if size_bytes == 0: return "0B"
    size_names = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def format_time_simple(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def format_bitrate(bitrate: int) -> str:
    if bitrate < 1000: return f"{bitrate} bps"
    elif bitrate < 1000000: return f"{bitrate/1000:.2f} Kbps"
    else: return f"{bitrate/1000000:.2f} Mbps"

def get_video_info(file_path: str) -> Optional[Dict]:
    try:
        ffmpeg_exe = get_ffmpeg_path()
        # ffprobe is usually in the same dir as ffmpeg if using imageio, but imageio-ffmpeg doesn't expose get_ffprobe_exe directly clearly everywhere.
        # But usually we just need ffmpeg for the converter. 
        # For ffprobe, imageio-ffmpeg DOES NOT bundle it always? 
        # Actually imageio-ffmpeg 0.4.0+ does. 
        
        # Let's assume ffprobe is 'ffprobe' or try to find it relative to ffmpeg if from imageio
        ffprobe_exe = "ffprobe"
        if ffmpeg_exe != "ffmpeg" and os.path.exists(ffmpeg_exe):
             # Try to find ffprobe in same dir
             possible = os.path.join(os.path.dirname(ffmpeg_exe), "ffprobe.exe" if os.name=="nt" else "ffprobe")
             if os.path.exists(possible):
                 ffprobe_exe = possible

        cmd = [ffprobe_exe, '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', file_path]
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, startupinfo=startupinfo)
        return json.loads(result.stdout)
    except Exception as e:
        logger.warning(f"Failed to get video info for {file_path}: {e}")
        # Fallback to ffmpeg parsing
        try:
             ffmpeg_exe = get_ffmpeg_path()
             cmd = [ffmpeg_exe, '-i', file_path]
             startupinfo = None
             if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
             
             result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
             import re
             
             # Extract Duration
             dur_match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d+)", result.stderr)
             duration = 0.0
             if dur_match:
                 h, m, s = dur_match.groups()
                 duration = int(h)*3600 + int(m)*60 + float(s)
             
             # Extract Video Stream Info
             # Stream #0:0(und): Video: h264 (High) (avc1 / 0x31637661), yuv420p, 1920x1080, 1200 kb/s, 30 fps, ...
             v_match = re.search(r"Stream #\d+:\d+.*Video: (\w+).*, (\d+)x(\d+).*, (\d+(?:\.\d+)?) fps", result.stderr)
             
             width = 0
             height = 0
             codec = "unknown"
             fps = "0/0"
             
             if v_match:
                 codec = v_match.group(1)
                 width = int(v_match.group(2))
                 height = int(v_match.group(3))
                 fps_val = v_match.group(4)
                 fps = f"{fps_val}/1" # Approximate
                 
             return {
                 "streams": [{
                     "codec_type": "video",
                     "width": width,
                     "height": height,
                     "codec_name": codec,
                     "avg_frame_rate": fps
                 }],
                 "format": {
                     "duration": str(duration),
                     "filename": file_path
                 }
             }
        except Exception as e2:
             logger.error(f"Fallback info extraction failed: {e2}")
        return None

def get_video_codec_only(file_path: str) -> Optional[str]:
    try:
        ffmpeg_exe = get_ffmpeg_path()
        ffprobe_exe = "ffprobe"
        if ffmpeg_exe != "ffmpeg" and os.path.exists(ffmpeg_exe):
             possible = os.path.join(os.path.dirname(ffmpeg_exe), "ffprobe.exe" if os.name=="nt" else "ffprobe")
             if os.path.exists(possible):
                 ffprobe_exe = possible

        cmd = [ffprobe_exe, '-v', 'quiet', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, startupinfo=startupinfo)
        return result.stdout.strip()
    except Exception as e:
        logger.error(f"Error getting codec for {file_path}: {e}")
        # Fallback to ffmpeg parsing if ffprobe fails
        try:
             ffmpeg_exe = get_ffmpeg_path()
             cmd = [ffmpeg_exe, '-i', file_path]
             startupinfo = None
             if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
             
             # ffmpeg -i exits with 1 usually when no output, but prints info to stderr
             result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
             # Parse stderr for "Stream #0:0(...): Video: hevc ..."
             import re
             # Regex to find video stream and codec
             match = re.search(r'Stream #\d+:\d+.*: Video: (\w+)', result.stderr)
             if match:
                 return match.group(1)
        except Exception as e2:
             logger.error(f"Fallback codec detection failed: {e2}")
        return None

def calculate_video_bitrate(file_size: int, duration: float) -> int:
    if duration == 0: return 0
    return int(round((file_size * 8) / duration / 1000) * 1000)

def calculate_adaptive_crf(duration_seconds: float, profile_level: str, is_4k: bool = False) -> int:
    """
    Calculate adaptive CRF (Constant Rate Factor) value based on video duration and quality profile.
    
    Longer videos get slightly lower CRF (better quality) to maintain perceptual consistency
    across different video lengths while allowing natural file size scaling.
    
    Args:
        duration_seconds: Video duration in seconds
        profile_level: Quality profile ("High Quality", "Balanced", "Compact", "Low Bitrate")
        is_4k: Whether video is 4K resolution (3840x2160 or higher)
    
    Returns:
        CRF value (15-35 range, lower = better quality)
    """
    # Base CRF values for each profile
    base_crf_map = {
        "High Quality": 20,
        "Balanced": 24,
        "Compact": 28,
        "Low Bitrate": 32
    }
    
    crf = base_crf_map.get(profile_level, 24)  # Default to Balanced if unknown
    
    # Adjust for 4K content (needs lower CRF for acceptable quality)
    if is_4k:
        crf -= 2
    
    # Duration-based adjustment: longer videos get better quality
    # to maintain perceptual consistency
    duration_minutes = duration_seconds / 60
    
    if duration_minutes > 60:  # >1 hour
        crf -= 2
    elif duration_minutes > 30:  # 30-60 min
        crf -= 1
    elif duration_minutes < 5:  # Very short clips
        crf += 1
    
    # Clamp to valid range (15-35)
    return max(15, min(35, crf))


def calculate_bitrates(file_size: int, duration: float, video_info: Dict) -> List[Dict]:
    width, height = 0, 0
    for stream in video_info.get('streams', []):
        if stream.get('codec_type') == 'video':
            width = stream.get('width', 0)
            height = stream.get('height', 0)
            break
    is_4k = width >= 3840 or height >= 2160
    current_bitrate_bps = (file_size * 8) / duration
    options = []
    
    percentages = [
        ("High Quality", 0.8),
        ("Balanced", 0.6),
        ("Compact", 0.4),
        ("Low Bitrate", 0.25)
    ]
    
    for name, factor in percentages:
        options.append({
            "name": name,
            "bitrate": int(current_bitrate_bps * factor),
            "estimated_size": int(file_size * factor),
            "is_4k": is_4k
        })
    
    return options

def calculate_quality_options(file_size: int, duration: float, video_info: Dict) -> List[Dict]:
    """
    Calculate quality encoding options using percentage-based file size reduction.
    
    Uses VBR (Variable Bitrate) encoding to achieve target file sizes:
    - 60% Reduction: Output is 40% of original size
    - 50% Reduction: Output is 50% of original size
    - 40% Reduction: Output is 60% of original size
    
    Args:
        file_size: Input file size in bytes
        duration: Video duration in seconds
        video_info: FFprobe video information dict
    
    Returns:
        List of quality options with target bitrates and estimated sizes
    """
    if duration == 0:
        duration = 1  # Avoid division by zero
    
    width, height = 0, 0
    for stream in video_info.get('streams', []):
        if stream.get('codec_type') == 'video':
            width = stream.get('width', 0)
            height = stream.get('height', 0)
            break
    
    is_4k = width >= 3840 or height >= 2160
    options = []
    
    # Compression percentages: (name, output_size_factor)
    # 60% reduction means output is 40% of original
    percentages = [
        ("60% Reduction", 0.40),
        ("50% Reduction", 0.50),
        ("40% Reduction", 0.60)
    ]
    
    for name, size_factor in percentages:
        target_size = int(file_size * size_factor)
        # Calculate target bitrate: (target_size * 8 bits/byte) / duration
        target_bitrate = int((target_size * 8) / duration)
        
        options.append({
            "name": name,
            "bitrate": target_bitrate,
            "estimated_size": target_size,
            "is_4k": is_4k
        })
    
    return options


def generate_thumbnail(file_path: str, output_path: str) -> Optional[str]:
    """
    Generates a thumbnail for the video at 50% duration.
    """
    try:
        ffmpeg_exe = get_ffmpeg_path()
        
        # Get duration first to find 50% point
        info = get_video_info(file_path)
        seek_time = "5.0" # Default fallback
        
        if info:
             try:
                 dur = float(info.get('format', {}).get('duration', 0))
                 if dur > 0:
                     seek_time = str(dur * 0.5)
             except:
                 pass

        cmd = [
            ffmpeg_exe, 
            '-ss', seek_time,
            '-i', file_path,
            '-vframes', '1',
            '-vf', 'scale=-1:60', 
            '-y',
            output_path
        ]
        
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        # Run blindly
        res = subprocess.run(cmd, capture_output=True, startupinfo=startupinfo)
        
        if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
            
        # Fallback to 0.0s if failed
        cmd[2] = '0.0'
        subprocess.run(cmd, check=True, capture_output=True, startupinfo=startupinfo)
        
        if os.path.exists(output_path):
            return output_path
        return None
    except Exception as e:
        logger.error(f"Error generating thumbnail for {file_path}: {e}")
        return None
