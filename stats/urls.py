from django.urls import path
from .views import *

urlpatterns = [
    path('dashboard/', DashboardStatsAPIView.as_view(), name='dashboard-stats'),
    path('quick/', QuickStatsAPIView.as_view(), name='quick-stats'),
    path('sales-report/', SalesReportAPIView.as_view(), name='sales-report'),
    path('client/<int:client_id>/', ClientDetailAPIView.as_view(), name='client-detail'),
    path('product/<int:product_id>/', ProductDetailAPIView.as_view(), name='product-detail'),
]