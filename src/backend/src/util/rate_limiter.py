import logging
import time
import redis

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, redis_host: str, redis_port: int = 6379):
        self.redis = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        
    def close(self):
        """
        Close the Redis connection and clean up resources.
        Should be called when the RateLimiter is no longer needed.
        """
        self.redis.close()
        
    def reset(self):
        """
        Reset the rate limiter by clearing all data in Redis.
        """
        self.redis.flushall()
        
    def is_allowed(self, key: str, tokens_per_second: float, bucket_size: int) -> bool:
        """
        Implements a leaky bucket rate limiter using Redis
        
        Args:
            key: Unique identifier for the rate limit (e.g., IP address)
            tokens_per_second: Rate at which tokens are added to the bucket
            bucket_size: Maximum number of tokens the bucket can hold
            
        Returns:
            bool: True if request is allowed, False if rate limit exceeded
        """
        current_time = time.time()
        bucket_key = f"bucket:{key}"

        # Get the last update time and current tokens
        last_time = float(self.redis.hget(bucket_key, "last_time") or current_time)
        current_tokens = float(self.redis.hget(bucket_key, "tokens") or bucket_size)
        
        # Calculate time passed and tokens to add
        time_passed = current_time - last_time
        tokens_to_add = time_passed * tokens_per_second
        
        # Add debug logging
        logger.debug("Time passed: %.3fs" % time_passed)
        logger.debug("Tokens to add: %.3f" % tokens_to_add)
        logger.debug("Current tokens before update: %.3f" % current_tokens)
        logger.debug("Bucket size: %d" % bucket_size)
        
        # Update current tokens
        current_tokens = min(bucket_size, current_tokens + tokens_to_add)
        
        logger.debug("Current tokens after update: %.3f" % current_tokens)
        
        # Check if we can consume a token
        if current_tokens >= 1:
            current_tokens -= 1
            allowed = True
        else:
            allowed = False
            
        logger.debug("Tokens after consumption: %.3f" % current_tokens)
        logger.debug("Request allowed: %s" % allowed)
        logger.debug("---")
            
        # Update Redis
        pipeline = self.redis.pipeline()
        pipeline.hset(bucket_key, "tokens", current_tokens)
        pipeline.hset(bucket_key, "last_time", current_time)
        pipeline.execute()
        
        return allowed 
