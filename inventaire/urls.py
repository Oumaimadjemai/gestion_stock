# inventaire/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SessionInventaireViewSet, EcartInventaireViewSet

router = DefaultRouter()
router.register(r'sessions', SessionInventaireViewSet, basename='inventaire-session')
router.register(r'ecarts', EcartInventaireViewSet, basename='inventaire-ecart')

urlpatterns = [
    path('', include(router.urls)),
]