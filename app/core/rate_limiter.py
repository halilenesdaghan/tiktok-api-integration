# app/core/rate_limiter.py
import time
import redis
import json
from typing import Optional
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from app.config.settings import settings


class RateLimiter:
    """
    Rate limiting implementation - Redis veya memory based
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
            print(f"Redis bağlantısı başarısız, memory-based rate limiting kullanılacak: {e}")
            self.use_redis = False
            self.memory_store = defaultdict(list)
    
    async def check_rate_limit(
        self, 
        key: str, 
        max_requests: Optional[int] = None, 
        window_seconds: int = 60
    ) -> bool:
        """
        Rate limit kontrolü yapar
        
        Args:
            key: Rate limit key (örn: "user_123", "api_endpoint")
            max_requests: İzin verilen maksimum istek sayısı
            window_seconds: Zaman penceresi (saniye)
            
        Returns:
            bool: True if allowed, raises HTTPException if not
        """
        if max_requests is None:
            max_requests = settings.RATE_LIMIT_PER_MINUTE
        
        current_time = time.time()
        
        if self.use_redis:
            return await self._check_redis_rate_limit(key, max_requests, window_seconds, current_time)
        else:
            return self._check_memory_rate_limit(key, max_requests, window_seconds, current_time)
    
    async def _check_redis_rate_limit(
        self, 
        key: str, 
        max_requests: int, 
        window_seconds: int, 
        current_time: float
    ) -> bool:
        """Redis based rate limiting"""
        redis_key = f"rate_limit:{key}"
        
        try:
            # Sliding window log algorithm
            pipeline = self.redis_client.pipeline()
            
            # Eski kayıtları sil
            min_time = current_time - window_seconds
            pipeline.zremrangebyscore(redis_key, 0, min_time)
            
            # Mevcut istek sayısını al
            pipeline.zcard(redis_key)
            
            # Yeni isteği ekle
            pipeline.zadd(redis_key, {str(current_time): current_time})
            
            # TTL ayarla
            pipeline.expire(redis_key, window_seconds + 1)
            
            results = pipeline.execute()
            request_count = results[1]
            
            if request_count >= max_requests:
                retry_after = int(window_seconds)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)}
                )
            
            return True
            
        except redis.RedisError as e:
            print(f"Redis error in rate limiting: {e}")
            # Redis hatası durumunda izin ver
            return True
    
    def _check_memory_rate_limit(
        self, 
        key: str, 
        max_requests: int, 
        window_seconds: int, 
        current_time: float
    ) -> bool:
        """Memory based rate limiting"""
        # Eski kayıtları temizle
        min_time = current_time - window_seconds
        self.memory_store[key] = [
            timestamp for timestamp in self.memory_store[key] 
            if timestamp > min_time
        ]
        
        # Mevcut istek sayısını kontrol et
        if len(self.memory_store[key]) >= max_requests:
            retry_after = int(window_seconds)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)}
            )
        
        # Yeni isteği ekle
        self.memory_store[key].append(current_time)
        return True
    
    async def get_rate_limit_info(self, key: str, window_seconds: int = 60) -> dict:
        """
        Rate limit bilgilerini döndürür
        """
        current_time = time.time()
        
        if self.use_redis:
            redis_key = f"rate_limit:{key}"
            try:
                # Eski kayıtları temizle
                min_time = current_time - window_seconds
                self.redis_client.zremrangebyscore(redis_key, 0, min_time)
                
                # Mevcut istek sayısını al
                request_count = self.redis_client.zcard(redis_key)
                
                # En eski isteği bul
                oldest_request = self.redis_client.zrange(redis_key, 0, 0, withscores=True)
                
                if oldest_request:
                    reset_time = oldest_request[0][1] + window_seconds
                else:
                    reset_time = current_time + window_seconds
                
                return {
                    "limit": settings.RATE_LIMIT_PER_MINUTE,
                    "remaining": max(0, settings.RATE_LIMIT_PER_MINUTE - request_count),
                    "reset": int(reset_time),
                    "window_seconds": window_seconds
                }
            except redis.RedisError:
                return {
                    "limit": settings.RATE_LIMIT_PER_MINUTE,
                    "remaining": settings.RATE_LIMIT_PER_MINUTE,
                    "reset": int(current_time + window_seconds),
                    "window_seconds": window_seconds
                }
        else:
            # Memory based
            min_time = current_time - window_seconds
            valid_requests = [
                timestamp for timestamp in self.memory_store.get(key, [])
                if timestamp > min_time
            ]
            
            request_count = len(valid_requests)
            
            if valid_requests:
                reset_time = min(valid_requests) + window_seconds
            else:
                reset_time = current_time + window_seconds
            
            return {
                "limit": settings.RATE_LIMIT_PER_MINUTE,
                "remaining": max(0, settings.RATE_LIMIT_PER_MINUTE - request_count),
                "reset": int(reset_time),
                "window_seconds": window_seconds
            }


# Global rate limiter instance
rate_limiter = RateLimiter()