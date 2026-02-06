import os
import json
import time
import threading
from typing import Dict, Optional
from .logger import logger

# Global lock for the cache file (instance-independent)
CACHE_LOCK = threading.RLock()

class ThumbnailCache:
    _instance = None
    _lock = threading.RLock() # Singleton initialization lock

    def __new__(cls, filename="thumbs_cache.json"):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ThumbnailCache, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, filename="thumbs_cache.json"):
        if getattr(self, '_initialized', False):
            return
        
        self.filename = filename
        self.cache: Dict[str, Dict] = {}
        self.load()
        self._initialized = True

    def load(self):
        with CACHE_LOCK:
            if not os.path.exists(self.filename):
                return
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load thumb cache: {e}")
                self.cache = {}

    def save(self):
        with CACHE_LOCK:
            temp_filename = f"{self.filename}.tmp"
            try:
                # Atomic write to temp
                with open(temp_filename, 'w', encoding='utf-8') as f:
                    json.dump(self.cache, f, indent=4)
                
                # Robust Rename with Retries (Windows workaround)
                max_retries = 3
                for i in range(max_retries):
                    try:
                        if os.path.exists(self.filename):
                            os.replace(temp_filename, self.filename) # os.replace allows overwrite on Py3.3+ (even on Windows usually, but safer than rename)
                        else:
                            os.rename(temp_filename, self.filename)
                        break # Success
                    except OSError as e:
                        if i == max_retries - 1:
                            raise e 
                        time.sleep(0.05) # Wait for file to be released
                        
            except Exception as e:
                logger.error(f"Failed to save thumb cache: {e}")
                if os.path.exists(temp_filename):
                    try:
                         os.remove(temp_filename)
                    except:
                        pass

    def get_entry(self, path: str, mtime: float, size: int) -> Optional[str]:
        with CACHE_LOCK:
            key = str(path)
            if key in self.cache:
                entry = self.cache[key]
                if abs(entry.get('mtime', 0) - mtime) < 0.1 and entry.get('size') == size:
                    thumb_path = entry.get('thumb_path')
                    if thumb_path and os.path.exists(thumb_path):
                        return thumb_path
            return None

    def update_entry(self, path: str, mtime: float, size: int, thumb_path: str):
        with CACHE_LOCK:
            key = str(path)
            self.cache[key] = {
                'mtime': mtime,
                'size': size,
                'thumb_path': thumb_path,
                'timestamp': time.time()
            }

    def remove_entry(self, path: str):
        with CACHE_LOCK:
            key = str(path)
            if key in self.cache:
                entry = self.cache[key]
                thumb_path = entry.get('thumb_path')
                if thumb_path and os.path.exists(thumb_path):
                    try:
                        os.remove(thumb_path)
                    except OSError:
                        pass
                
                del self.cache[key]
                self.save()

    def clear(self):
        with CACHE_LOCK:
            for key, entry in self.cache.items():
                thumb_path = entry.get('thumb_path')
                if thumb_path and os.path.exists(thumb_path):
                    try:
                        os.remove(thumb_path)
                    except OSError:
                        pass
            
            self.cache = {}
            self.save()
