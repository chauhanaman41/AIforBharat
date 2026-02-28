"""
AIforBharat — Local Cache Manager
===================================
In-memory + file-based cache for local development.
Implements strict local caching: check if data exists locally
before downloading. If it exists, skip the download.
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

from shared.config import CACHE_DIR

logger = logging.getLogger("cache")


class LocalCache:
    """
    Two-tier cache: L1 in-memory (fast) + L2 file-based (persistent).
    
    Strict data caching rule:
    - Always check local cache before any download/API call.
    - If data exists locally, return it — never re-download.
    - Only download if cache miss or explicit invalidation.
    """

    def __init__(self, namespace: str = "default", ttl: int = 3600, max_memory_items: int = 500):
        self.namespace = namespace
        self.ttl = ttl  # Time-to-live in seconds
        self.max_memory_items = max_memory_items
        self._memory: dict[str, dict] = {}  # {key: {data, timestamp, expires_at}}
        self._cache_dir = CACHE_DIR / namespace
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cache initialized: namespace={namespace}, ttl={ttl}s, dir={self._cache_dir}")

    def _make_file_key(self, key: str) -> Path:
        """Generate a file path for a cache key."""
        safe_key = hashlib.sha256(key.encode()).hexdigest()
        return self._cache_dir / f"{safe_key}.json"

    def get(self, key: str) -> Optional[Any]:
        """
        Get from cache. Checks L1 (memory) → L2 (file) → None.
        Returns None on miss.
        """
        # L1: In-memory check
        if key in self._memory:
            entry = self._memory[key]
            if time.time() < entry["expires_at"]:
                logger.debug(f"Cache HIT (L1 memory): {key}")
                return entry["data"]
            else:
                del self._memory[key]

        # L2: File check
        file_path = self._make_file_key(key)
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    entry = json.load(f)
                if time.time() < entry.get("expires_at", 0):
                    # Promote to L1
                    self._memory[key] = entry
                    self._evict_if_needed()
                    logger.debug(f"Cache HIT (L2 file): {key}")
                    return entry["data"]
                else:
                    # Expired — remove file
                    file_path.unlink(missing_ok=True)
            except (json.JSONDecodeError, KeyError):
                file_path.unlink(missing_ok=True)

        logger.debug(f"Cache MISS: {key}")
        return None

    def set(self, key: str, data: Any, ttl: int = None):
        """
        Store data in both L1 (memory) and L2 (file) cache.
        """
        expires_at = time.time() + (ttl or self.ttl)
        entry = {
            "data": data,
            "timestamp": time.time(),
            "expires_at": expires_at,
        }

        # L1: Memory
        self._memory[key] = entry
        self._evict_if_needed()

        # L2: File (persistent across restarts)
        file_path = self._make_file_key(key)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(entry, f, default=str)
        except (TypeError, IOError) as e:
            logger.warning(f"Failed to write cache file for {key}: {e}")

    def exists(self, key: str) -> bool:
        """Check if a key exists in cache (without fully loading it)."""
        if key in self._memory:
            if time.time() < self._memory[key]["expires_at"]:
                return True
        file_path = self._make_file_key(key)
        return file_path.exists()

    def invalidate(self, key: str):
        """Remove a key from both cache tiers."""
        self._memory.pop(key, None)
        file_path = self._make_file_key(key)
        file_path.unlink(missing_ok=True)

    def clear(self):
        """Clear all entries in this namespace."""
        self._memory.clear()
        for f in self._cache_dir.glob("*.json"):
            f.unlink(missing_ok=True)

    def _evict_if_needed(self):
        """Evict oldest entries if memory cache exceeds max size."""
        if len(self._memory) > self.max_memory_items:
            sorted_keys = sorted(
                self._memory.keys(),
                key=lambda k: self._memory[k]["timestamp"]
            )
            for k in sorted_keys[:len(self._memory) - self.max_memory_items]:
                del self._memory[k]

    def get_stats(self) -> dict:
        """Get cache statistics."""
        file_count = len(list(self._cache_dir.glob("*.json")))
        return {
            "namespace": self.namespace,
            "memory_entries": len(self._memory),
            "file_entries": file_count,
            "cache_dir": str(self._cache_dir),
        }


def file_exists_locally(path: str) -> bool:
    """
    Check if a file/dataset exists locally before downloading.
    Core implementation of the strict caching rule.
    """
    return Path(path).exists()


def get_cached_download(url: str, cache_dir: str = None) -> Optional[Path]:
    """
    Check if a URL's content has already been downloaded locally.
    Returns the local file path if it exists, None otherwise.
    """
    if cache_dir is None:
        cache_dir = str(CACHE_DIR / "downloads")
    
    os.makedirs(cache_dir, exist_ok=True)
    
    # Use URL hash as filename
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    cached_path = Path(cache_dir) / url_hash
    
    if cached_path.exists():
        logger.info(f"Download already cached locally: {url} → {cached_path}")
        return cached_path
    
    return None
