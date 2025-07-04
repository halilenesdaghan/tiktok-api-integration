# app/core/cache.py
import json
import time
import redis
from typing import Optional, Any
from datetime import timedelta
from app.config.settings import settings


class CacheManager:
    """
    Cache management - Redis veya memory based
    """
    def __init__(self):
        self.use_redis = True
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True
            )
            # Redis bağlantısını test et
            self.redis_client.ping()
        except Exception as e:
            print(f"Redis cache başlatılamadı, memory cache kullanılacak: {e}")
            self.use_redis = False
            self.memory_cache = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Cache'den veri al
        """
        if self.use_redis:
            try:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                print(f"Redis get error: {e}")
        else:
            # Memory cache
            if key in self.memory_cache:
                value, expiry = self.memory_cache[key]
                if expiry is None or expiry > time.time():
                    return value
                else:
                    # Süresi dolmuş, sil
                    del self.memory_cache[key]
        
        return None
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        Cache'e veri kaydet
        
        Args:
            key: Cache key
            value: Kaydedilecek değer
            expire: Saniye cinsinden expire süresi
        """
        if self.use_redis:
            try:
                serialized = json.dumps(value)
                if expire:
                    self.redis_client.setex(key, expire, serialized)
                else:
                    self.redis_client.set(key, serialized)
                return True
            except Exception as e:
                print(f"Redis set error: {e}")
                return False
        else:
            # Memory cache
            expiry = time.time() + expire if expire else None
            self.memory_cache[key] = (value, expiry)
            return True
    
    async def delete(self, key: str) -> bool:
        """
        Cache'den veri sil
        """
        if self.use_redis:
            try:
                self.redis_client.delete(key)
                return True
            except Exception as e:
                print(f"Redis delete error: {e}")
                return False
        else:
            # Memory cache
            if key in self.memory_cache:
                del self.memory_cache[key]
                return True
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Pattern'e uyan tüm key'leri sil
        """
        count = 0
        if self.use_redis:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    count = self.redis_client.delete(*keys)
            except Exception as e:
                print(f"Redis clear pattern error: {e}")
        else:
            # Memory cache
            keys_to_delete = [k for k in self.memory_cache.keys() if pattern.replace('*', '') in k]
            for key in keys_to_delete:
                del self.memory_cache[key]
                count += 1
        
        return count


# Global cache manager instance
cache_manager = CacheManager()