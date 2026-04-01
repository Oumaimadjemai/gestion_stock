# common/decorators.py

from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
import hashlib
import json

def cache_page_with_version(timeout=300, key_prefix=''):
    """
    Cache a view with versioning support
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Get global cache version
            version = cache.get('global_cache_version', 1)
            
            # Generate cache key
            cache_key = f"{key_prefix}_{version}_{request.user.id}_{request.path}_{hashlib.md5(str(request.GET).encode()).hexdigest()}"
            
            # Try to get from cache
            cached_response = cache.get(cache_key)
            if cached_response:
                return JsonResponse(cached_response, safe=False)
            
            # Call the view
            response = view_func(request, *args, **kwargs)
            
            # Cache the response if successful
            if response.status_code == 200:
                cache.set(cache_key, response.data, timeout)
            
            return response
        
        return wrapped_view
    return decorator