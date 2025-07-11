# app/services/cache_service.py
"""Caching service for Shopify data with configurable backends"""

import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib


@dataclass
class CacheConfig:
    """Cache configuration settings"""
    default_ttl: int = 300  # 5 minutes
    product_ttl: int = 600  # 10 minutes
    collection_ttl: int = 1800  # 30 minutes
    filter_ttl: int = 3600  # 1 hour
    pagination_ttl: int = 300  # 5 minutes
    max_memory_items: int = 1000  # For in-memory cache


class CacheBackend(ABC):
    """Abstract base class for cache backends"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        pass

    @abstractmethod
    async def clear(self, pattern: Optional[str] = None) -> bool:
        """Clear cache, optionally by pattern"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass


class InMemoryCacheBackend(CacheBackend):
    """In-memory cache backend with LRU eviction"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}

    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache"""
        if key not in self._cache:
            return None

        cache_entry = self._cache[key]
        
        # Check if expired
        if time.time() > cache_entry['expires_at']:
            await self.delete(key)
            return None

        # Update access time for LRU
        self._access_times[key] = time.time()
        
        return cache_entry['value']

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in memory cache"""
        # Evict oldest items if at capacity
        if len(self._cache) >= self.config.max_memory_items:
            await self._evict_lru()

        expires_at = time.time() + ttl
        self._cache[key] = {
            'value': value,
            'expires_at': expires_at,
            'created_at': time.time()
        }
        self._access_times[key] = time.time()
        
        return True

    async def delete(self, key: str) -> bool:
        """Delete value from memory cache"""
        if key in self._cache:
            del self._cache[key]
        if key in self._access_times:
            del self._access_times[key]
        return True

    async def clear(self, pattern: Optional[str] = None) -> bool:
        """Clear memory cache"""
        if pattern:
            keys_to_delete = [key for key in self._cache.keys() if pattern in key]
            for key in keys_to_delete:
                await self.delete(key)
        else:
            self._cache.clear()
            self._access_times.clear()
        return True

    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        if key not in self._cache:
            return False
        
        cache_entry = self._cache[key]
        if time.time() > cache_entry['expires_at']:
            await self.delete(key)
            return False
        
        return True

    async def _evict_lru(self):
        """Evict least recently used items"""
        if not self._access_times:
            return

        # Find oldest accessed key
        oldest_key = min(self._access_times.keys(), 
                        key=lambda k: self._access_times[k])
        await self.delete(oldest_key)


try:
    import redis.asyncio as redis
    
    class RedisCacheBackend(CacheBackend):
        """Redis cache backend"""

        def __init__(self, redis_url: str, config: CacheConfig):
            self.config = config
            self.redis_client = redis.from_url(redis_url)

        async def get(self, key: str) -> Optional[Any]:
            """Get value from Redis cache"""
            try:
                cached = await self.redis_client.get(key)
                if cached:
                    return json.loads(cached)
                return None
            except Exception:
                return None

        async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
            """Set value in Redis cache"""
            try:
                serialized = json.dumps(value, default=str)
                await self.redis_client.setex(key, ttl, serialized)
                return True
            except Exception:
                return False

        async def delete(self, key: str) -> bool:
            """Delete value from Redis cache"""
            try:
                await self.redis_client.delete(key)
                return True
            except Exception:
                return False

        async def clear(self, pattern: Optional[str] = None) -> bool:
            """Clear Redis cache"""
            try:
                if pattern:
                    keys = await self.redis_client.keys(f"*{pattern}*")
                    if keys:
                        await self.redis_client.delete(*keys)
                else:
                    await self.redis_client.flushdb()
                return True
            except Exception:
                return False

        async def exists(self, key: str) -> bool:
            """Check if key exists in Redis"""
            try:
                return await self.redis_client.exists(key) > 0
            except Exception:
                return False

        async def close(self):
            """Close Redis connection"""
            await self.redis_client.close()

except ImportError:
    # Redis not available, create a stub
    class RedisCacheBackend(CacheBackend):
        def __init__(self, redis_url: str, config: CacheConfig):
            raise ImportError("Redis not available. Install redis package to use Redis caching.")


class ShopifyCacheService:
    """Cache service for Shopify data with smart cache keys"""

    def __init__(self, backend: CacheBackend, config: CacheConfig = None):
        self.backend = backend
        self.config = config or CacheConfig()

    def _make_key(self, prefix: str, tenant_id: str, **kwargs) -> str:
        """Create cache key from prefix, tenant, and parameters"""
        # Sort kwargs for consistent key generation
        sorted_params = sorted(kwargs.items())
        params_str = "&".join(f"{k}={v}" for k, v in sorted_params if v is not None)
        
        # Create hash for long parameter strings
        if len(params_str) > 100:
            params_hash = hashlib.md5(params_str.encode()).hexdigest()
            key = f"shopify:{prefix}:{tenant_id}:{params_hash}"
        else:
            key = f"shopify:{prefix}:{tenant_id}:{params_str}"
        
        return key

    async def get_product(self, tenant_id: str, product_id: str) -> Optional[Dict[str, Any]]:
        """Get cached product"""
        key = self._make_key("product", tenant_id, id=product_id)
        return await self.backend.get(key)

    async def set_product(self, tenant_id: str, product_id: str, product_data: Dict[str, Any]) -> bool:
        """Cache product data"""
        key = self._make_key("product", tenant_id, id=product_id)
        return await self.backend.set(key, product_data, self.config.product_ttl)

    async def get_products_page(
        self, 
        tenant_id: str, 
        page: int = 1, 
        limit: int = 50, 
        **filters
    ) -> Optional[Dict[str, Any]]:
        """Get cached products page"""
        key = self._make_key("products_page", tenant_id, page=page, limit=limit, **filters)
        return await self.backend.get(key)

    async def set_products_page(
        self, 
        tenant_id: str, 
        page: int, 
        limit: int, 
        products_data: Dict[str, Any], 
        **filters
    ) -> bool:
        """Cache products page"""
        key = self._make_key("products_page", tenant_id, page=page, limit=limit, **filters)
        return await self.backend.set(key, products_data, self.config.pagination_ttl)

    async def get_collection(self, tenant_id: str, collection_id: str) -> Optional[Dict[str, Any]]:
        """Get cached collection"""
        key = self._make_key("collection", tenant_id, id=collection_id)
        return await self.backend.get(key)

    async def set_collection(self, tenant_id: str, collection_id: str, collection_data: Dict[str, Any]) -> bool:
        """Cache collection data"""
        key = self._make_key("collection", tenant_id, id=collection_id)
        return await self.backend.set(key, collection_data, self.config.collection_ttl)

    async def get_collections(self, tenant_id: str, **filters) -> Optional[List[Dict[str, Any]]]:
        """Get cached collections list"""
        key = self._make_key("collections", tenant_id, **filters)
        return await self.backend.get(key)

    async def set_collections(self, tenant_id: str, collections_data: List[Dict[str, Any]], **filters) -> bool:
        """Cache collections list"""
        key = self._make_key("collections", tenant_id, **filters)
        return await self.backend.set(key, collections_data, self.config.collection_ttl)

    async def get_available_filters(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get cached available filters"""
        key = self._make_key("filters", tenant_id)
        return await self.backend.get(key)

    async def set_available_filters(self, tenant_id: str, filters_data: Dict[str, Any]) -> bool:
        """Cache available filters"""
        key = self._make_key("filters", tenant_id)
        return await self.backend.set(key, filters_data, self.config.filter_ttl)

    async def get_cursor_for_page(self, tenant_id: str, page: int, **filters) -> Optional[str]:
        """Get cached cursor for specific page"""
        key = self._make_key("cursor", tenant_id, page=page, **filters)
        cached_data = await self.backend.get(key)
        return cached_data.get('cursor') if cached_data else None

    async def set_cursor_for_page(self, tenant_id: str, page: int, cursor: str, **filters) -> bool:
        """Cache cursor for specific page"""
        key = self._make_key("cursor", tenant_id, page=page, **filters)
        cursor_data = {'cursor': cursor, 'cached_at': time.time()}
        return await self.backend.set(key, cursor_data, self.config.pagination_ttl)

    async def invalidate_product(self, tenant_id: str, product_id: str) -> bool:
        """Invalidate product cache"""
        key = self._make_key("product", tenant_id, id=product_id)
        return await self.backend.delete(key)

    async def invalidate_products_cache(self, tenant_id: str) -> bool:
        """Invalidate all product-related cache for tenant"""
        patterns = ["products_page", "cursor", "filters"]
        success = True
        for pattern in patterns:
            cache_pattern = f"shopify:{pattern}:{tenant_id}"
            result = await self.backend.clear(cache_pattern)
            success = success and result
        return success

    async def invalidate_collection(self, tenant_id: str, collection_id: str) -> bool:
        """Invalidate collection cache"""
        key = self._make_key("collection", tenant_id, id=collection_id)
        await self.backend.delete(key)
        
        # Also invalidate collections list and product pages that might include this collection
        await self.backend.clear(f"shopify:collections:{tenant_id}")
        await self.invalidate_products_cache(tenant_id)
        
        return True

    async def get_cache_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get cache statistics for tenant"""
        stats = {
            'tenant_id': tenant_id,
            'cache_backend': type(self.backend).__name__,
            'config': {
                'product_ttl': self.config.product_ttl,
                'collection_ttl': self.config.collection_ttl,
                'filter_ttl': self.config.filter_ttl,
                'pagination_ttl': self.config.pagination_ttl
            }
        }

        # Count cached items (approximation for in-memory cache)
        if isinstance(self.backend, InMemoryCacheBackend):
            tenant_keys = [key for key in self.backend._cache.keys() 
                          if f":{tenant_id}:" in key]
            stats['cached_items'] = len(tenant_keys)

        return stats


def create_cache_service(
    backend_type: str = "memory", 
    redis_url: Optional[str] = None,
    config: Optional[CacheConfig] = None
) -> ShopifyCacheService:
    """Factory function to create cache service with specified backend"""
    
    config = config or CacheConfig()
    
    if backend_type == "redis":
        if not redis_url:
            raise ValueError("Redis URL required for Redis backend")
        backend = RedisCacheBackend(redis_url, config)
    elif backend_type == "memory":
        backend = InMemoryCacheBackend(config)
    else:
        raise ValueError(f"Unknown cache backend: {backend_type}")
    
    return ShopifyCacheService(backend, config)


# Global cache service instance to share across requests
_global_cache_service: Optional[ShopifyCacheService] = None


def get_global_cache_service() -> ShopifyCacheService:
    """Get or create global cache service instance"""
    global _global_cache_service
    if _global_cache_service is None:
        _global_cache_service = create_cache_service("memory")
        print("🌐 Created global cache service instance")
    return _global_cache_service
