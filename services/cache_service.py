# services/cache_service.py
import redis
import json
from typing import Optional, Dict, Any
import hashlib
import pickle

class CacheService:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis = redis.from_url(redis_url)
        self.search_ttl = 300  # 5 minutes for search results
        self.suggestions_ttl = 600  # 10 minutes for suggestions
    
    def _generate_cache_key(self, prefix: str, data: Dict) -> str:
        """Generate unique cache key for any request"""
        key_data = json.dumps(data, sort_keys=True)
        return f"{prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    async def get_cached_search(self, search_params: Dict) -> Optional[Dict]:
        """Get cached search results if available"""
        cache_key = self._generate_cache_key("search", search_params)
        cached = self.redis.get(cache_key)
        if cached:
            return pickle.loads(cached)
        return None
    
    async def cache_search(self, search_params: Dict, results: Dict):
        """Cache search results"""
        cache_key = self._generate_cache_key("search", search_params)
        self.redis.setex(cache_key, self.search_ttl, pickle.dumps(results))
    
    async def get_cached_suggestions(self, query: str) -> Optional[Dict]:
        """Get cached search suggestions"""
        cache_key = f"suggestions:{hashlib.md5(query.encode()).hexdigest()}"
        cached = self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        return None
    
    async def cache_suggestions(self, query: str, suggestions: Dict):
        """Cache search suggestions"""
        cache_key = f"suggestions:{hashlib.md5(query.encode()).hexdigest()}"
        self.redis.setex(cache_key, self.suggestions_ttl, json.dumps(suggestions))
