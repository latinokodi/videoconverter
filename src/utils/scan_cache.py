import json
import os
import time
from typing import Dict, Optional
from .logger import logger

CACHE_FILE = "scan_cache.json"

class ScanCache:
    def __init__(self, filename=CACHE_FILE):
        self.filename = filename
        self.cache: Dict[str, Dict] = {}
        self.load()

    def load(self):
        if not os.path.exists(self.filename):
             return
        try:
            # Add simple retry logic for reading (as it might be replaced by save)
            for _ in range(3):
                try:
                    with open(self.filename, 'r', encoding='utf-8') as f:
                        self.cache = json.load(f)
                    break
                except (OSError, json.JSONDecodeError):
                    time.sleep(0.05)
        except Exception as e:
            logger.error(f"Failed to load scan cache: {e}")
            self.cache = {}

    def save(self):
        # Atomic write with unique temp file to avoid WinError 32
        import uuid
        temp_filename = f"{self.filename}.{uuid.uuid4()}.tmp"
        try:
            with open(temp_filename, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=4)
            os.replace(temp_filename, self.filename)
        except Exception as e:
            logger.error(f"Failed to save scan cache: {e}")
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

    def get_cached_result(self, path: str, mtime: float, size: int) -> Optional[str]:
        """Returns cached codec if file matches mtime/size, else None."""
        key = str(path)
        if key in self.cache:
            entry = self.cache[key]
            if entry.get('mtime') == mtime and entry.get('size') == size:
                return entry.get('codec')
        return None

    def update_result(self, path: str, mtime: float, size: int, codec: str):
        key = str(path)
        self.cache[key] = {
            'mtime': mtime,
            'size': size,
            'codec': codec,
            'timestamp': time.time()
        }

    def remove_result(self, path: str):
        key = str(path)
        if key in self.cache:
            del self.cache[key]
            self.save()
