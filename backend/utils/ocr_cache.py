"""
OCR Cache Utility
Cache OCR results to reduce redundant API calls and costs
"""
from typing import Dict, Any, Optional
from PIL import Image
import hashlib
import json
import os
from pathlib import Path
from backend.config import settings

class OCRCache:
    """Cache OCR results for similar forms"""
    
    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir is None:
            cache_dir = os.path.join(settings.UPLOAD_DIR, "ocr_cache")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = getattr(settings, 'OCR_CACHE_ENABLED', True)
    
    def _image_hash(self, image: Image.Image) -> str:
        """Generate hash for image"""
        # Convert image to bytes
        import io
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        
        # Generate hash
        return hashlib.sha256(img_bytes).hexdigest()
    
    def _cache_key(
        self,
        image: Image.Image,
        provider: str,
        language: Optional[str] = None
    ) -> str:
        """Generate cache key"""
        image_hash = self._image_hash(image)
        key_parts = [image_hash, provider]
        if language:
            key_parts.append(language)
        return "_".join(key_parts)
    
    def _cache_path(self, cache_key: str) -> Path:
        """Get cache file path"""
        # Use first 2 chars of hash for directory structure
        subdir = self.cache_dir / cache_key[:2]
        subdir.mkdir(exist_ok=True)
        return subdir / f"{cache_key}.json"
    
    def get(
        self,
        image: Image.Image,
        provider: str,
        language: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached OCR result
        
        Returns:
            Cached result or None if not found
        """
        if not self.enabled:
            return None
        
        cache_key = self._cache_key(image, provider, language)
        cache_file = self._cache_path(cache_key)
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading cache: {e}")
                return None
        
        return None
    
    def set(
        self,
        image: Image.Image,
        provider: str,
        result: Dict[str, Any],
        language: Optional[str] = None
    ):
        """Store OCR result in cache"""
        if not self.enabled:
            return
        
        cache_key = self._cache_key(image, provider, language)
        cache_file = self._cache_path(cache_key)
        
        try:
            # Add metadata
            cached_result = {
                "result": result,
                "cached_at": str(Path(cache_file).stat().st_mtime) if cache_file.exists() else None,
                "provider": provider,
                "language": language
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cached_result, f, indent=2)
        except Exception as e:
            print(f"Error writing cache: {e}")
    
    def clear(self, older_than_days: Optional[int] = None):
        """Clear cache entries"""
        import time
        
        if older_than_days:
            cutoff_time = time.time() - (older_than_days * 24 * 60 * 60)
        
        cleared = 0
        for cache_file in self.cache_dir.rglob("*.json"):
            if older_than_days:
                if cache_file.stat().st_mtime < cutoff_time:
                    cache_file.unlink()
                    cleared += 1
            else:
                cache_file.unlink()
                cleared += 1
        
        return cleared
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        cache_files = list(self.cache_dir.rglob("*.json"))
        
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            "enabled": self.enabled,
            "cache_dir": str(self.cache_dir),
            "total_entries": len(cache_files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }

# Global instance
ocr_cache = OCRCache()

