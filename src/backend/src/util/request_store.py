import redis
from typing import Optional
import json
import os
from datetime import timedelta

class RequestStore:
    def __init__(self, redis_host: str = None, redis_port: int = None):
        self.redis = redis.Redis(
            host=redis_host or os.getenv('REDIS_HOST', 'localhost'),
            port=redis_port or int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        # Set default TTL to 24 hours
        self.default_ttl = timedelta(hours=24)

    def store_request(self, request_id: str, request_data: dict, ttl: Optional[timedelta] = None) -> None:
        """Store HTTP request data with TTL"""
        self.redis.setex(
            f"request:{request_id}",
            ttl or self.default_ttl,
            json.dumps(request_data)
        )

    def get_request(self, request_id: str) -> Optional[dict]:
        """Retrieve HTTP request data"""
        data = self.redis.get(f"request:{request_id}")
        return json.loads(data) if data else None

    def delete_request(self, request_id: str) -> None:
        """Delete HTTP request data"""
        self.redis.delete(f"request:{request_id}")

    def close(self) -> None:
        """Close Redis connection"""
        self.redis.close()

def get_request_store():
    """Dependency injection function for FastAPI"""
    store = RequestStore()
    try:
        yield store
    finally:
        store.close() 