from django.db import models
from django.core.cache import cache

class BaseModel(models.Model):
    """Base model with common fields and optimization methods"""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True,null=True,blank=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True,null=True,blank=True)
    is_active = models.BooleanField(default=True, db_index=True,null=True,blank=True)
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['-updated_at']),
            models.Index(fields=['is_active', '-created_at']),
        ]
    
    def clear_cache(self):
        """Clear cache for this instance"""
        cache_key = f"{self.__class__.__name__}_{self.pk}"
        cache.delete(cache_key)
    
    def save(self, *args, **kwargs):
        """Clear cache on save"""
        self.clear_cache()
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Clear cache on delete"""
        self.clear_cache()
        super().delete(*args, **kwargs)