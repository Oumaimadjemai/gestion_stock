import redis
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client wrapper with error handling"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            try:
                # Get Redis URL from settings
                redis_url = getattr(settings, 'REDIS_URL', None)
                
                if redis_url:
                    cls._instance = redis.from_url(redis_url, decode_responses=True)
                else:
                    cls._instance = None
                    logger.warning("Redis URL not configured")
                    
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                cls._instance = None
                
        return cls._instance
    
    @classmethod
    def get_client(cls):
        """Get Redis client instance"""
        return cls._instance
    
    @classmethod
    def is_available(cls):
        """Check if Redis is available"""
        client = cls.get_client()
        if client:
            try:
                return client.ping()
            except:
                return False
        return False

# Usage in other files
# from common.redis_client import RedisClient
# client = RedisClient.get_client()
# if client:
#     client.set('key', 'value')