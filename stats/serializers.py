from rest_framework import serializers

class DashboardStatsSerializer(serializers.Serializer):
    # Card stats
    total_clients = serializers.IntegerField()
    total_facilite_sales = serializers.IntegerField()
    total_facilite_amount = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_cash_sales = serializers.IntegerField()
    total_cash_amount = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_product_value = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=20, decimal_places=2)
    
    # Profit percentage
    profit_percentage = serializers.FloatField()
    
    # Charts
    sales_by_user = serializers.ListField(child=serializers.DictField())
    monthly_profits = serializers.ListField(child=serializers.DictField())
    product_families = serializers.ListField(child=serializers.DictField())
    
    # Additional stats
    total_products = serializers.IntegerField()
    total_fournisseurs = serializers.IntegerField()
    pending_installments = serializers.IntegerField()
    overdue_payments = serializers.IntegerField()