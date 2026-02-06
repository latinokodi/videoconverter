import os
import subprocess
import time
import re
import traceback
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, Callable, Dict, Any
from send2trash import send2trash

from .exceptions import (
    FFmpegNotFoundError,
    FFmpegExecutionError,
    ConversionFailedError,
    InvalidVideoFileError,
)
from ..utils.logger import logger
from ..utils.helpers import get_video_info, format_time_simple, get_ffmpeg_path
from ..utils.config import config


# Constants
RESOLUTION_1080P = 1080
DEFAULT_CRF_VALUE = 24
STDERR_BUFFER_SIZE = 20  # Keep only last N lines of stderr


class CodecType(str, Enum):
    """Supported video codecs."""

    HEVC_NVENC = "hevc_nvenc"
    LIBX265 = "libx265"


@dataclass
class ConversionOptions:
    """Configuration options for video conversion.

    Attributes:
        bitrate: Target bitrate in bps (mutually exclusive with crf)
        crf: Constant Rate Factor for quality-based encoding (mutually exclusive with bitrate)
        preset: Encoding preset (e.g., 'medium', 'p4')
        has_gpu: Whether GPU acceleration should be used
    """

    bitrate: Optional[int] = None
    crf: Optional[int] = None
    preset: str = "medium"
    has_gpu: bool = False

    def __post_init__(self):
        """Validate that either bitrate or crf is set, not both."""
        if self.bitrate is not None and self.crf is not None:
            raise ValueError("Cannot specify both bitrate and crf")
        if self.bitrate is None and self.crf is None:
            # Default to CRF
            self.crf = DEFAULT_CRF_VALUE


@dataclass
class ConversionResult:
    """Result of a video conversion operation.

    Attributes:
        success: Whether the conversion succeeded
        input_path: Path to the input video file
        output_path: Path to the output video file (None if failed)
        error_message: Error message if conversion failed (None if succeeded)
        original_deleted: Whether the original file was deleted
    """

    success: bool
    input_path: Optional[str] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    original_deleted: bool = False


def should_downscale_to_1080p(width: int, height: int) -> bool:
    """
    Determine if video should be downscaled to 1080p.
    
    Args:
        width: Video width in pixels
        height: Video height in pixels
    
    Returns:
        True if the shortest side > 1080 (meaning >1080p resolution)
    """
    return min(width, height) > 1080


def get_scale_filter(width: int, height: int, has_gpu: bool) -> str:
    """
    Get the appropriate scale filter for downscaling to 1080p.
    
    Args:
        width: Source video width
        height: Source video height  
        has_gpu: Whether GPU acceleration is available
    
    Returns:
        FFmpeg scale filter string
    """
    if has_gpu:
        # For GPU, use scale_cuda if available (hwaccel path)
        # scale_cuda=-2:1080 maintains aspect ratio based on height
        return "scale_cuda=-2:1080"
    else:
        # For CPU, use standard scale filter
        # -2:1080 means: calculate width to maintain aspect ratio, height = 1080
        # -2 ensures the width is divisible by 2 (required for many codecs)
        return "scale=-2:1080"


def get_output_path(input_path: str) -> str:
    """Determine output path based on configuration."""
    folder, filename = os.path.split(input_path)
    name, _ = os.path.splitext(filename)
    
    # Remove '2160' from output name if present
    # Remove '2160p' from output name if present
    if "2160p" in name:
        name = name.replace("2160p", "")
    elif "2160" in name: 
        # Fallback for just 2160 without p? User asked specifically for "include the p".
        # Let's assume if 2160p is there, remove it. If 2160 is there but not p, maybe leave it?
        # User said "The string to remove ... should include the p".
        # This implies removal of "2160p".
        # If I have "Movie.2160.mp4", should I remove 2160?
        # The previous request was "If source file has 2160, remove it".
        # This request refines it.
        # I will prioritize 2160p, but maybe I should just clean "2160p" and "2160" to be safe?
        # Let's just do "2160p" first as requested. 
        # But wait, if they have "2160" but not "p", and I stop removing it, I might regress the previous feature if they implicitly meant "also".
        # "The string to remove ... should include the p in 2160p" -> "Remove '2160p'".
        # I will replace "2160p" -> "". 
        # AND I will separate replace "2160" -> "" if I want to be aggressive, but that breaks "2160p" logic order.
        # Let's simple check:
        # replace("2160p", "")
        # replace("2160", "") 
        # No, that's redundant.
        # Let's just use a regex or simple sequential replace.
        # If I replace 2160p, then 2160 is gone too.
        # Actually I'll stick to replacing "2160p" solely for now as per specific instruction, 
        # BUT if I don't remove "2160", then "Movie 2160" remains "Movie 2160".
        # Previous prompt: "If source file has 2160, remove it".
        # So I must still remove 2160.
        # If I remove "2160", then "2160p" becomes "p". This is what the user dislikes.
        # So I should remove "2160p" FIRST.
        pass
    
    # Cleanest logic:
    if "2160p" in name:
        name = name.replace("2160p", "")
    if "2160" in name:
        name = name.replace("2160", "")
        
    new_filename = f"{name}_hevc.mp4"
    
    mode = config.get("output_mode", "auto")
    custom_folder = config.get("custom_output_folder", "")
    
    if mode == "custom" and custom_folder and os.path.exists(custom_folder):
        return os.path.join(custom_folder, new_filename)
    else:
        return os.path.join(folder, new_filename)

def handle_existing_file_auto(output_path: str) -> str:
    """Automatically rename if file exists (append _1, _2, etc)."""
    if not os.path.exists(output_path):
        return output_path
        
    base, ext = os.path.splitext(output_path)
    counter = 1
    while os.path.exists(f"{base}_{counter}{ext}"):
        counter += 1
    return f"{base}_{counter}{ext}"

class Converter:
    def __init__(self, has_gpu: bool, update_callback: Optional[Callable] = None):
        self.stop_event = False
        self.has_gpu = has_gpu
        self.update_callback = update_callback # Func(progress, percent_str, eta_str)

    def stop(self):
        self.stop_event = True

    def convert_single_file(self, input_path: str, option: dict, delete_original: bool = False) -> Tuple[bool, Optional[str], Optional[str]]:
        self.stop_event = False
        try:
            output_path = get_output_path(input_path)
            final_output_path = handle_existing_file_auto(output_path)
            
            # Get correct ffmpeg executable
            ffmpeg_exe = get_ffmpeg_path()

            # Get video info first to check resolution
            info = get_video_info(input_path)
            video_width = 0
            video_height = 0
            if info:
                for stream in info.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        video_width = stream.get('width', 0)
                        video_height = stream.get('height', 0)
                        break
            
            # Determine if downscaling is needed
            needs_downscale = should_downscale_to_1080p(video_width, video_height)
            
            # Base command setup
            cmd_base = [ffmpeg_exe, '-y']
            
            # Hardware Acceleration
            if self.has_gpu:
                # HYBRID PIPELINE: CPU Decode -> GPU Init for Filters
                # We disable GPU decoding (-hwaccel) to avoid the "1-minute crash" (decoder instability).
                # Instead, we initialize CUDA context for the filters/encoder.
                cmd_base.extend(['-init_hw_device', 'cuda=cuda:0', '-filter_hw_device', 'cuda'])
            
            cmd_base.extend(['-i', input_path])
            cmd_codec = []
            video_filters = []

            # Smooth Motion Filter (CPU-based)
            smooth_motion = option.get('smooth_motion', False)
            minterpolate_filter = "minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"

            # Codec selection logic
            if self.has_gpu:
                cmd_codec = ['-c:v', 'hevc_nvenc', '-preset', 'p4']
                
                # Apply minterpolate BEFORE upload to GPU
                if smooth_motion:
                    video_filters.append(minterpolate_filter)
                    # We might need to ensure format compatibility, but usually minterpolate outputs standard pixel formats
                    logger.info("Smooth motion enabled (CPU filter before GPU encode)")

                # Use scale_cuda filter for robust GPU resizing
                if needs_downscale:
                    # CPU Decode -> (Optional Minterpolate) -> hwupload (move to VRAM) -> scale_cuda (resize) -> Encoder
                    video_filters.append('hwupload')
                    video_filters.append('scale_cuda=-2:1080:format=nv12')
                    logger.info(f"Hybrid downscaling enabled (hwupload -> scale_cuda): {video_width}x{video_height} -> 1080p")
                
                # If smooth motion is ON but downscale is OFF, we still need hwupload if we want to use scale_cuda?
                # Wait, if we use NVENC, we need frames in GPU memory ONLY if we use GPU filters.
                # If we don't use scale_cuda (no downscale), can we feed CPU frames to NVENC?
                # Yes, standard NVENC accepts pixel formats like yuv420p directly if no GPU filters are used in between.
                # BUT if we have GPU filters (scale_cuda), we MUST have hwupload.
                
            else:
                cmd_codec = ['-c:v', 'libx265', '-preset', 'medium']
                
                if smooth_motion:
                    video_filters.append(minterpolate_filter)
                    logger.info("Smooth motion enabled (CPU)")

                # For CPU, use scale filter
                if needs_downscale:
                    scale_filter = get_scale_filter(video_width, video_height, has_gpu=False)
                    video_filters.append(scale_filter)
                    logger.info(f"CPU downscaling enabled: {video_width}x{video_height} -> 1080p")

            # Build filter chain if needed
            filter_args = []
            if video_filters:
                filter_args = ['-vf', ','.join(video_filters)]

            # Quality/Bitrate arguments - Support both new CRF and legacy bitrate
            quality_args = []
            if 'crf' in option:
                # New CRF-based encoding (adaptive quality) - GPU ONLY
                crf_value = option['crf']
                if self.has_gpu:
                    # NVENC uses -cq with constqp rate control
                    quality_args = ['-rc', 'constqp', '-cq', str(crf_value)]
                    logger.info(f"Using NVENC CQ (constant quality): {crf_value}")
                else:
                    # CPU fallback (avoid per user preference, but keep for safety)
                    quality_args = ['-crf', str(crf_value)]
                    logger.warning("CPU encoding used - GPU preferred for performance")
            elif 'bitrate' in option:
                # Legacy bitrate mode (backward compatibility)
                bitrate_kbps = option['bitrate'] // 1000
                if self.has_gpu:
                    quality_args = ['-rc', 'vbr', '-b:v', f'{bitrate_kbps}k']
                else:
                    quality_args = ['-b:v', f'{bitrate_kbps}k']
                logger.info(f"Using legacy bitrate mode: {bitrate_kbps}k")
            else:
                # Fallback to default CRF
                logger.warning("No quality settings in option, using default CRF 24")
                quality_args = ['-rc', 'constqp', '-cq', '24'] if self.has_gpu else ['-crf', '24']

            # Add -fps_mode passthrough ONLY if NOT using smooth motion
            # (Smooth motion needs to change the frame rate to 60fps via filter)
            fps_mode_args = []
            if not smooth_motion:
                fps_mode_args = ['-fps_mode', 'passthrough']
            
            cmd = cmd_base + cmd_codec + filter_args + quality_args + \
                  fps_mode_args + ['-c:a', 'copy', final_output_path]
            
            logger.info(f"Executing: {' '.join(cmd)}")
            
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                startupinfo=startupinfo
            )
            
            # Get duration for progress (reuse info we already fetched)
            duration = float(info.get('format', {}).get('duration', 0)) if info else 0
            start_time = time.time()
            
            stderr_output = []
            
            while True:
                if self.stop_event:
                    process.terminate()
                    logger.info("Conversion stopped by user.")
                    
                    # Cleanup incomplete file
                    if final_output_path and os.path.exists(final_output_path):
                        try:
                            time.sleep(0.5) # Wait for handle release
                            os.remove(final_output_path)
                            logger.info(f"Deleted incomplete file: {final_output_path}")
                        except Exception as e:
                            logger.error(f"Failed to delete incomplete file: {e}")
                            
                    return False, None, None
                    
                line = process.stderr.readline()
                if line:
                    stderr_output.append(line)
                    
                if not line and process.poll() is not None:
                    break
                    
                time_match = re.search(r'time=(\d+):(\d+):(\d+)', line)
                if time_match:
                    hours, minutes, seconds = map(int, time_match.groups())
                    current_seconds = hours * 3600 + minutes * 60 + seconds
                    progress = min(current_seconds / duration, 1.0) if duration > 0 else 0
                    
                    elapsed = time.time() - start_time
                    if progress > 0:
                        eta = (elapsed / progress) - elapsed
                        eta_str = format_time_simple(eta)
                    else:
                        eta_str = "--:--"
                        
                    if self.update_callback:
                        self.update_callback(progress, f"{int(progress*100)}%", f"ETA: {eta_str}")
            
            if process.returncode == 0:
                logger.info(f"Conversion success: {final_output_path}")
                
                # Auto Delete Logic
                if delete_original:
                    try:
                        # Safety checks:
                        # 1. Output must exist and be > 0 bytes
                        if os.path.exists(final_output_path) and os.path.getsize(final_output_path) > 0:
                            # 2. Input path must still exist (sanity)
                            if os.path.exists(input_path):
                                # 3. Ensure we aren't deleting the output (if paths same? ffmpeg -y changes behavior but let's be safe)
                                if os.path.abspath(input_path) != os.path.abspath(final_output_path):
                                    send2trash(input_path)
                                    logger.info(f"Original file moved to trash: {input_path}")
                                else:
                                    logger.warning("Input and output paths are identical, skipping delete.")
                        else:
                            logger.error("Output file invalid, skipping auto-delete.")
                    except Exception as e:
                        logger.error(f"Failed to auto-delete original: {e}")

                return True, input_path, final_output_path
            else:
                error_msg = "".join(stderr_output[-10:])
                logger.error(f"FFmpeg failed: {error_msg}")
                return False, error_msg, None
            
        except Exception as e:
            logger.error(f"Unexpected error converting {input_path}: {e}")
            logger.error(traceback.format_exc())
            return False, str(e), None
