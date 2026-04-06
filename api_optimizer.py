"""
CONFIT API Performance Optimizer
=================================
Production-ready optimizations for API endpoints.
Includes caching, connection pooling, rate limiting, and error handling.
"""

import asyncio
import aiohttp
import json
import time
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from functools import wraps, lru_cache
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class APIConfig:
    """Configuration for API optimization"""
    base_url: str = "http://localhost:8000"
    timeout: int = 30
    max_connections: int = 100
    retry_attempts: int = 3
    retry_delay: float = 1.0
    cache_ttl: int = 300  # 5 minutes
    rate_limit_per_minute: int = 60

class APIClient:
    """Production-ready API client with optimizations"""
    
    def __init__(self, config: APIConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache: Dict[str, Dict] = {}
        self.rate_limit_tracker: Dict[str, List[datetime]] = {}
        self.request_stats: Dict[str, Any] = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'rate_limited': 0
        }
    
    async def __aenter__(self):
        """Initialize session with connection pooling"""
        connector = aiohttp.TCPConnector(
            limit=self.config.max_connections,
            limit_per_host=self.config.max_connections // 4,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'CONFIT-API-Client/1.0',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up session"""
        if self.session:
            await self.session.close()
    
    def _get_cache_key(self, method: str, endpoint: str, data: Dict = None) -> str:
        """Generate cache key for request"""
        key_data = f"{method}:{endpoint}"
        if data:
            key_data += f":{json.dumps(data, sort_keys=True)}"
        return key_data
    
    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid"""
        return datetime.now() - cache_entry['timestamp'] < timedelta(seconds=self.config.cache_ttl)
    
    def _check_rate_limit(self, endpoint: str) -> bool:
        """Check if request is within rate limit"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Clean old entries
        if endpoint in self.rate_limit_tracker:
            self.rate_limit_tracker[endpoint] = [
                req_time for req_time in self.rate_limit_tracker[endpoint]
                if req_time > minute_ago
            ]
        else:
            self.rate_limit_tracker[endpoint] = []
        
        # Check rate limit
        if len(self.rate_limit_tracker[endpoint]) >= self.config.rate_limit_per_minute:
            self.request_stats['rate_limited'] += 1
            return False
        
        # Add current request
        self.rate_limit_tracker[endpoint].append(now)
        return True
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get response from cache if valid"""
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            self.request_stats['cache_hits'] += 1
            return self.cache[cache_key]['data']
        return None
    
    def _store_in_cache(self, cache_key: str, data: Dict):
        """Store response in cache"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    async def _make_request_with_retry(self, method: str, url: str, 
                                      data: Dict = None, headers: Dict = None) -> Dict:
        """Make request with retry logic"""
        last_exception = None
        
        for attempt in range(self.config.retry_attempts):
            try:
                async with self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    headers=headers
                ) as response:
                    content = await response.text()
                    
                    if response.status >= 400:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=content
                        )
                    
                    return {
                        'status': response.status,
                        'content': content,
                        'headers': dict(response.headers)
                    }
                    
            except Exception as e:
                last_exception = e
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                    logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                else:
                    logger.error(f"Request failed after {self.config.retry_attempts} attempts: {e}")
        
        raise last_exception
    
    async def request(self, method: str, endpoint: str, 
                     data: Dict = None, headers: Dict = None,
                     use_cache: bool = True, skip_rate_limit: bool = False) -> Dict:
        """
        Make optimized API request with caching, rate limiting, and retry logic
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request data
            headers: Additional headers
            use_cache: Whether to use caching (only for GET requests)
            skip_rate_limit: Whether to skip rate limiting
        
        Returns:
            Response data
        """
        self.request_stats['total_requests'] += 1
        
        # Check rate limit
        if not skip_rate_limit and not self._check_rate_limit(endpoint):
            raise Exception(f"Rate limit exceeded for {endpoint}")
        
        # Check cache (only for GET requests)
        cache_key = None
        if use_cache and method.upper() == 'GET':
            cache_key = self._get_cache_key(method, endpoint, data)
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                return cached_response
        
        # Make request
        start_time = time.time()
        try:
            url = f"{self.config.base_url}{endpoint}"
            response = await self._make_request_with_retry(method, url, data, headers)
            
            # Cache successful GET responses
            if use_cache and method.upper() == 'GET' and cache_key:
                self._store_in_cache(cache_key, response)
            
            self.request_stats['successful_requests'] += 1
            
            # Log performance
            response_time = time.time() - start_time
            if response_time > 1.0:  # Log slow requests
                logger.warning(f"Slow request: {method} {endpoint} took {response_time:.2f}s")
            
            return response
            
        except Exception as e:
            self.request_stats['failed_requests'] += 1
            logger.error(f"Request failed: {method} {endpoint} - {e}")
            raise

class OptimizedAPIEndpoints:
    """Optimized API endpoint implementations"""
    
    def __init__(self, client: APIClient):
        self.client = client
    
    async def get_products_optimized(self, limit: int = 50, offset: int = 0, 
                                   category: str = None, gender: str = None) -> Dict:
        """Get products with optimized caching and parameters"""
        params = []
        if limit:
            params.append(f"limit={limit}")
        if offset:
            params.append(f"offset={offset}")
        if category:
            params.append(f"category={category}")
        if gender:
            params.append(f"gender={gender}")
        
        endpoint = f"/api/products"
        if params:
            endpoint += "?" + "&".join(params)
        
        return await self.client.request("GET", endpoint)
    
    async def get_featured_products_optimized(self, limit: int = 12, 
                                            gender: str = "men") -> Dict:
        """Get featured products with caching"""
        endpoint = f"/api/products/featured?limit={limit}&gender={gender}"
        return await self.client.request("GET", endpoint)
    
    async def process_virtual_tryon_optimized(self, user_image: str, 
                                           garment_url: str, 
                                           garment_name: str) -> Dict:
        """Process virtual try-on with optimized handling"""
        data = {
            "userImageBase64": user_image,
            "garmentImageUrl": garment_url,
            "garmentName": garment_name
        }
        
        # Skip cache for POST requests
        return await self.client.request("POST", "/api/virtual-tryon/process", 
                                        data=data, use_cache=False)
    
    async def get_quests_optimized(self) -> Dict:
        """Get quests with caching"""
        return await self.client.request("GET", "/api/challenges/quests")
    
    async def get_leaderboard_optimized(self) -> Dict:
        """Get leaderboard with caching"""
        return await self.client.request("GET", "/api/challenges/leaderboard")

def performance_monitor(func):
    """Decorator to monitor function performance"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            if execution_time > 2.0:  # Log slow functions
                logger.warning(f"Slow function: {func.__name__} took {execution_time:.2f}s")
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Function {func.__name__} failed after {execution_time:.2f}s: {e}")
            raise
    return wrapper

# LRU Cache for frequently accessed data
@lru_cache(maxsize=128)
def get_cached_product_categories():
    """Get product categories with LRU cache"""
    return ["tops", "bottoms", "dresses", "outerwear", "shoes", "accessories", "bags"]

@lru_cache(maxsize=64)
def get_cached_colors():
    """Get color options with LRU cache"""
    return ["Black", "White", "Gray", "Navy", "Brown", "Beige", "Red", "Blue", "Green", "Pink"]

async def benchmark_api_performance():
    """Benchmark API performance with optimizations"""
    config = APIConfig()
    
    async with APIClient(config) as client:
        endpoints = OptimizedAPIEndpoints(client)
        
        print("🚀 Running Performance Benchmarks with Optimizations")
        print("=" * 60)
        
        # Test with optimizations
        start_time = time.time()
        
        tasks = [
            endpoints.get_products_optimized(limit=20),
            endpoints.get_featured_products_optimized(),
            endpoints.get_quests_optimized(),
            endpoints.get_leaderboard_optimized(),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        print(f"⚡ Total time for 4 concurrent requests: {total_time:.2f}s")
        print(f"📊 Average per request: {total_time/4:.2f}s")
        
        # Print client stats
        stats = client.request_stats
        print(f"\n📈 Client Statistics:")
        print(f"   Total Requests: {stats['total_requests']}")
        print(f"   Successful: {stats['successful_requests']}")
        print(f"   Failed: {stats['failed_requests']}")
        print(f"   Cache Hits: {stats['cache_hits']}")
        print(f"   Rate Limited: {stats['rate_limited']}")
        
        # Test cache effectiveness
        print(f"\n🔄 Testing Cache Effectiveness:")
        cache_start = time.time()
        
        # Make same requests again (should hit cache)
        await endpoints.get_featured_products_optimized()
        await endpoints.get_quests_optimized()
        
        cache_time = time.time() - cache_start
        print(f"⚡ Cached requests time: {cache_time:.2f}s")
        print(f"📊 Cache hit rate: {stats['cache_hits']/(stats['total_requests']-2)*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(benchmark_api_performance())
