from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from rest_framework.response import Response

class CacheableListMixin:
    """Add caching to list views"""
    cache_timeout = 300  # 5 minutes
    
    @method_decorator(cache_page(cache_timeout))
    @method_decorator(vary_on_headers('Authorization'))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class SelectiveFieldMixin:
    """Allow selecting specific fields"""
    
    def get_queryset(self):
        queryset = super().get_queryset()
        fields = self.request.query_params.get('fields', None)
        
        if fields:
            fields = fields.split(',')
            # Validate fields exist on model
            valid_fields = [f for f in fields if hasattr(queryset.model, f)]
            if valid_fields:
                queryset = queryset.only(*valid_fields)
        
        return queryset

class BulkDeleteMixin:
    """Add bulk delete capability"""
    
    def bulk_delete(self, request, *args, **kwargs):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': 'No IDs provided'}, status=400)
        
        queryset = self.get_queryset().filter(id__in=ids)
        count = queryset.delete()[0]
        
        return Response({'deleted_count': count})