# services/cache_service.py
import redis
import json
from typing import Optional
import hashlib

class CacheService:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis = redis.from_url(redis_url)
        self.ttl = 300  # 5 minutes cache
    
    def _generate_cache_key(self, search_request: Dict) -> str:
        """Generate unique cache key for search request"""
        key_data = json.dumps(search_request, sort_keys=True)
        return f"search:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    async def get_cached_results(self, search_request: Dict) -> Optional[Dict]:
        """Get cached search results if available"""
        cache_key = self._generate_cache_key(search_request)
        cached = self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        return None
    
    async def cache_results(self, search_request: Dict, results: Dict):
        """Cache search results"""
        cache_key = self._generate_cache_key(search_request)
        self.redis.setex(cache_key, self.ttl, json.dumps(results))