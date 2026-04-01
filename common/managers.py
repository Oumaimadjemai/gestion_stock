from django.db import models
from django.core.cache import cache

class CachedQuerySet(models.QuerySet):
    """QuerySet with caching capability"""
    
    def cached(self, key=None, timeout=300):
        if key is None:
            key = f"queryset_{self.model.__name__}_{hash(str(self.query))}"
        
        cached_result = cache.get(key)
        if cached_result is not None:
            return cached_result
        
        result = list(self)
        cache.set(key, result, timeout)
        return result

class BaseManager(models.Manager):
    """Base manager with caching"""
    
    def get_queryset(self):
        return CachedQuerySet(self.model, using=self._db)
    
    def active(self):
        return self.filter(is_active=True)