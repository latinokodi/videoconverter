# Integrations

**Analysis Date:** 2026-03-23

## External Interfaces

- **(None)**: The application currently operates entirely offline and does not call any third-party HTTP REST/GraphQL APIs.

## Services

- **Local Storage / Caches**: Uses local JSON flat-files (`config.json`, `scan_cache.json`, `thumbs_cache.json`) for persistence rather than a full relational database.
- **Operating System Shell**: Integrates with the Windows shell (`send2trash` library) to safely move original video files to the OS Recycle Bin rather than permanently deleting them.

## Third-party Tools

- **FFmpeg (`ffmpeg_exe`)**: The core utility driving the entire application. The converter expects an ffmpeg executable to either be in the path or placed locally.
- **FFprobe**: Used indirectly via the `opencv-python` and `imageio-ffmpeg` integrations or strictly as an external executable for extracting detailed video information and streams (`get_video_info`).
- **Nvidia Management Library (`pynvml`)**: Integrated for hardware interrogation, specifically checking if an NVIDIA GPU is present and capable of NVENC encoding.
