import os
import json
import pytest
import time
from src.utils.thumb_cache import ThumbnailCache

# Fake temp dir for tests
CACHE_FILE = "tests_thumb_cache.json"

@pytest.fixture
def cache():
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    c = ThumbnailCache(CACHE_FILE)
    yield c
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)

def test_save_and_load(cache):
    """Test that entries are persisted to disk."""
    cache.update_entry("video.mp4", 1000.0, 500, "thumb.jpg")
    cache.save()
    
    # Reload
    new_cache = ThumbnailCache(CACHE_FILE)
    assert new_cache.get_entry("video.mp4", 1000.0, 500) == "thumb.jpg"

def test_cache_invalidation_on_change(cache):
    """Test that cache returns None if file modified time or size changes."""
    cache.update_entry("video.mp4", 1000.0, 500, "thumb.jpg")
    cache.save()
    
    # Different mtime
    assert cache.get_entry("video.mp4", 2000.0, 500) is None
    # Different size
    assert cache.get_entry("video.mp4", 1000.0, 600) is None

def test_clear_cache(cache):
    """Test clearing all thumbnails."""
    cache.update_entry("video.mp4", 1000, 500, "thumb.jpg")
    cache.clear()
    assert cache.get_entry("video.mp4", 1000, 500) is None
    
    # Verify file is empty/reset on disk
    new_cache = ThumbnailCache(CACHE_FILE)
    assert new_cache.get_entry("video.mp4", 1000, 500) is None

def test_remove_entry(cache):
    """Test removing a single entry (e.g. when file deleted)."""
    cache.update_entry("video.mp4", 1000, 500, "thumb.jpg")
    cache.remove_entry("video.mp4")
    assert cache.get_entry("video.mp4", 1000, 500) is None
