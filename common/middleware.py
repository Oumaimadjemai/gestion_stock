# common/middleware.py

from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
import hashlib
import time
import logging

logger = logging.getLogger(__name__)

class CacheInvalidationMiddleware(MiddlewareMixin):
    """
    Middleware to handle cache invalidation based on request methods
    """
    
    def process_request(self, request):
        # Store the current cache version
        request.cache_version = cache.get('global_cache_version', 1)
    
    def process_response(self, request, response):
        # If this is a write operation, invalidate cache
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            # Increment global cache version
            new_version = cache.get('global_cache_version', 1) + 1
            cache.set('global_cache_version', new_version, timeout=None)
            logger.info(f"Cache version updated to {new_version} due to {request.method} {request.path}")
            
            # Also clear user-specific cache
            if request.user and request.user.is_authenticated:
                from .cache_manager import CacheManager
                CacheManager.clear_user_cache(request.user.id)
        
        return response


class PerformanceMiddleware(MiddlewareMixin):
    """
    Monitor and log slow requests
    """
    
    def process_request(self, request):
        request.start_time = time.time()
    
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Log slow requests (> 2 seconds)
            if duration > 2.0:
                logger.warning(
                    f"SLOW REQUEST: {request.method} {request.path} "
                    f"took {duration:.2f}s"
                )
        
        return response