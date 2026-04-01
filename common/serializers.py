from rest_framework import serializers
from django.core.cache import cache

class OptimizedModelSerializer(serializers.ModelSerializer):
    """Serializer with caching for expensive fields"""
    
    def to_representation(self, instance):
        # Only cache for GET requests
        if getattr(self.context.get('request'), 'method', '') == 'GET':
            cache_key = f"{self.__class__.__name__}_{instance.pk}"
            cached_data = cache.get(cache_key)
            
            if cached_data is not None:
                return cached_data
            
            data = super().to_representation(instance)
            cache.set(cache_key, data, 300)
            return data
        
        return super().to_representation(instance)