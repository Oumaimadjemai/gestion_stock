# common/cache_manager.py

from django.core.cache import cache
from django.conf import settings
import hashlib
import json

class CacheManager:
    """
    Centralized cache management for the entire project
    """
    
    # Define cache key patterns for different parts of the app
    CACHE_PATTERNS = {
        'dashboard': [
            'dashboard_stats_*',
            'dashboard_charts_*',
            'dashboard_totals_*',
        ],
        'achats': [
            'achat_list_*',
            'achat_stats_*',
            'achat_detail_*',
        ],
        'ventes': [
            'vente_list_*',
            'vente_stats_*',
            'vente_detail_*',
        ],
        'produits': [
            'produit_list_*',
            'produit_detail_*',
            'produit_stats_*',
        ],
        'clients': [
            'client_list_*',
            'client_stats_*',
        ],
        'fournisseurs': [
            'fournisseur_list_*',
            'fournisseur_stats_*',
        ],
        'depenses': [
            'depense_list_*',
            'depense_stats_*',
        ],
        'rapports': [
            'rapport_*',
        ],
    }
    
    @classmethod
    def clear_all_cache(cls):
        """
        Clear ALL cache - use sparingly
        """
        try:
            cache.clear()
            print("All cache cleared successfully")
            return True
        except Exception as e:
            print(f"Error clearing all cache: {e}")
            return False
    
    @classmethod
    def clear_pattern(cls, pattern):
        """
        Clear cache keys matching a pattern
        """
        try:
            if hasattr(cache, 'delete_pattern'):
                cache.delete_pattern(pattern)
            else:
                # For backends that don't support pattern deletion
                # You might need to implement a different strategy
                cls.clear_all_cache()
            return True
        except Exception as e:
            print(f"Error clearing pattern {pattern}: {e}")
            return False
    
    @classmethod
    def clear_by_prefix(cls, prefix):
        """
        Clear all cache keys with a specific prefix
        """
        pattern = f"{prefix}*"
        return cls.clear_pattern(pattern)
    
    @classmethod
    def clear_app_cache(cls, app_name):
        """
        Clear cache for a specific app
        """
        if app_name in cls.CACHE_PATTERNS:
            for pattern in cls.CACHE_PATTERNS[app_name]:
                cls.clear_pattern(pattern)
            return True
        return False
    
    @classmethod
    def clear_user_cache(cls, user_id):
        """
        Clear cache specific to a user
        """
        patterns = [
            f"*user_{user_id}_*",
            f"*_{user_id}_*",
        ]
        for pattern in patterns:
            cls.clear_pattern(pattern)
    
    @classmethod
    def get_cache_key(cls, prefix, *args, **kwargs):
        """
        Generate a consistent cache key
        """
        key_parts = [prefix]
        key_parts.extend([str(arg) for arg in args])
        key_parts.extend([f"{k}_{v}" for k, v in sorted(kwargs.items())])
        
        key = "_".join(key_parts)
        # Hash long keys to keep them manageable
        if len(key) > 200:
            key = f"{prefix}_{hashlib.md5(key.encode()).hexdigest()}"
        
        return key