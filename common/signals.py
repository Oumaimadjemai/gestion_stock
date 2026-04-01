# common/signals.py

from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.apps import apps
from .cache_manager import CacheManager
import logging

logger = logging.getLogger(__name__)

# List of models that should trigger cache clear on change
CACHE_CLEAR_MODELS = [
    'AchatGroupe',
    'Vente',
    'Produit',
    'Client',
    'Fournisseur',
    'Depense',
    'LigneAchat',
    'LigneVente',
]

@receiver(post_save)
@receiver(post_delete)
def clear_cache_on_model_change(sender, **kwargs):
    """
    Clear cache whenever any model is saved or deleted
    """
    model_name = sender.__name__
    app_label = sender._meta.app_label
    
    # Check if this model should trigger cache clear
    if model_name in CACHE_CLEAR_MODELS:
        logger.info(f"Clearing cache due to change in {app_label}.{model_name}")
        
        # Clear app-specific cache
        CacheManager.clear_app_cache(app_label)
        
        # Clear dashboard cache (since dashboard shows data from all apps)
        CacheManager.clear_app_cache('dashboard')
        
        # Clear user cache if applicable
        instance = kwargs.get('instance')
        if instance and hasattr(instance, 'utilisateur') and instance.utilisateur:
            CacheManager.clear_user_cache(instance.utilisateur.id)
        elif instance and hasattr(instance, 'user') and instance.user:
            CacheManager.clear_user_cache(instance.user.id)

@receiver(m2m_changed)
def clear_cache_on_m2m_change(sender, **kwargs):
    """
    Clear cache on many-to-many relationship changes
    """
    model_name = sender.__name__
    if model_name in CACHE_CLEAR_MODELS:
        CacheManager.clear_app_cache(sender._meta.app_label)