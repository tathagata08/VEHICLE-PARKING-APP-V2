# redis_cache.py
import redis
import json
from functools import wraps
from flask import current_app

# ------------------ REDIS CONNECTION ------------------
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

# ------------------ CACHE DECORATOR ------------------
def cache(ttl=60):
    """
    Decorator to cache function results in Redis.
    ttl: time-to-live in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate a unique key based on function name and arguments
            key_parts = [func.__name__] + [str(a) for a in args] + [f"{k}-{v}" for k, v in kwargs.items()]
            cache_key = "cache:" + ":".join(key_parts)

            try:
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            except Exception as e:
                current_app.logger.error(f"Redis error: {e}")

            # Run the actual function
            result = func(*args, **kwargs)

            # Store result in Redis
            try:
                redis_client.setex(cache_key, ttl, json.dumps(result))
            except Exception as e:
                current_app.logger.error(f"Redis cache set failed: {e}")

            return result
        return wrapper
    return decorator

# ------------------ CLEAR CACHE FUNCTION ------------------
def clear_cache(pattern="cache:*"):
    """
    Clear cached keys in Redis. Useful after DB updates.
    """
    try:
        for key in redis_client.scan_iter(pattern):
            redis_client.delete(key)
    except Exception as e:
        current_app.logger.error(f"Redis cache clear failed: {e}")
