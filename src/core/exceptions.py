"""
Custom exceptions for the Video Converter application.

This module provides a hierarchical exception structure for better error
handling and debugging throughout the application.
"""


class VideoConverterError(Exception):
    """Base exception for all video converter errors."""

    pass


class FFmpegNotFoundError(VideoConverterError):
    """Raised when FFmpeg executable is not found."""

    pass


class FFmpegExecutionError(VideoConverterError):
    """Raised when FFmpeg command execution fails."""

    def __init__(self, message: str, returncode: int = None, stderr: str = None):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class ConversionFailedError(VideoConverterError):
    """Raised when video conversion fails."""

    def __init__(self, message: str, input_path: str = None, error_details: str = None):
        super().__init__(message)
        self.input_path = input_path
        self.error_details = error_details


class GPUNotAvailableError(VideoConverterError):
    """Raised when GPU acceleration is requested but not available."""

    pass


class InvalidVideoFileError(VideoConverterError):
    """Raised when video file is invalid or corrupted."""

    def __init__(self, message: str, file_path: str = None):
        super().__init__(message)
        self.file_path = file_path


class ConfigurationError(VideoConverterError):
    """Raised when application configuration is invalid."""

    pass


class OutputPathError(VideoConverterError):
    """Raised when output path is invalid or inaccessible."""

    def __init__(self, message: str, path: str = None):
        super().__init__(message)
        self.path = path
