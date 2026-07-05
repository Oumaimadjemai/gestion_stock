# stats/views.py - UPDATED with year filter

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import connection
from django.core.cache import cache
from django.db.models import Sum, Count, Q

from authentification.models import Client, Fournisseur
from produits.models import Produit
from ventes.models import VenteFacilite, VenteCache, LigneVenteFacilite
from depenses.models import Depense
from django.contrib.auth import get_user_model
User = get_user_model()
USER_TABLE = User._meta.db_table


# class DashboardStatsAPIView(APIView):
#     """
#     GET /stats/dashboard/
#     ULTRA OPTIMIZED version with caching and year filter
#     """
#     permission_classes = [IsAuthenticated]
    
#     def get_date_range(self, periode, year=None):
#         """
#         Get date range based on periode and optional year
#         """
#         today = timezone.now().date()
        
#         # If year is specified, use that year for calculations
#         if year:
#             try:
#                 year = int(year)
#                 ranges = {
#                     'today': (today, today),
#                     'yesterday': (today - timedelta(days=1), today - timedelta(days=1)),
#                     'this_week': (today - timedelta(days=today.weekday()), today),
#                     'this_month': (datetime(year, 1, 1).date(), datetime(year, 12, 31).date()),
#                     'last_month': (datetime(year, 1, 1).date(), datetime(year, 12, 31).date()),
#                     'this_year': (datetime(year, 1, 1).date(), datetime(year, 12, 31).date()),
#                 }
#             except ValueError:
#                 year = None
        
#         if not year:
#             ranges = {
#                 'today': (today, today),
#                 'yesterday': (today - timedelta(days=1), today - timedelta(days=1)),
#                 'this_week': (today - timedelta(days=today.weekday()), today),
#                 'this_month': (today.replace(day=1), today),
#                 'last_month': ((today.replace(day=1) - timedelta(days=1)).replace(day=1), today.replace(day=1) - timedelta(days=1)),
#                 'this_year': (today.replace(month=1, day=1), today),
#             }
        
#         if periode in ranges:
#             return {'start': ranges[periode][0], 'end': ranges[periode][1]}
#         return {'start': None, 'end': None}
    
#     def get_cached_or_query(self, cache_key, query_func, timeout=300):
#         cached_data = cache.get(cache_key)
#         if cached_data is not None:
#             return cached_data
        
#         data = query_func()
#         cache.set(cache_key, data, timeout)
#         return data
    
#     def get(self, request):
#         periode = request.query_params.get('periode', 'this_month')
#         user_filter = request.query_params.get('user', None)
#         year_filter = request.query_params.get('year', None)  # New year filter
        
#         is_admin = request.user.role == 'admin'
#         if not is_admin:
#             user_filter = str(request.user.id)
        
#         # Get date range with year filter
#         date_range = self.get_date_range(periode, year_filter)
#         start_date = date_range['start']
#         end_date = date_range['end']
        
#         # Cache key includes year filter
#         cache_key = f"dashboard_stats_{periode}_{user_filter}_{year_filter}"
#         cached_response = cache.get(cache_key)
#         if cached_response:
#             return Response(cached_response)
        
#         # ========== 1. Installment sales totals ==========
#         facilite_queryset = VenteFacilite.objects.all()
#         if start_date:
#             facilite_queryset = facilite_queryset.filter(
#                 date_creation__date__gte=start_date,
#                 date_creation__date__lte=end_date
#             )
#         if user_filter:
#             facilite_queryset = facilite_queryset.filter(utilisateur_id=user_filter)
        
#         total_facilite_sales = facilite_queryset.count()
#         total_facilite_amount = facilite_queryset.aggregate(total=Sum('montant_total'))['total'] or 0
#         total_facilite_amount = float(total_facilite_amount)
        
#         # ========== 2. Calculate purchase cost from ligne items ==========
#         ligne_queryset = LigneVenteFacilite.objects.filter(vente__in=facilite_queryset).select_related('produit')
        
#         total_purchase_cost = 0
#         for ligne in ligne_queryset:
#             if ligne.produit and ligne.produit.prix_achat:
#                 total_purchase_cost += float(ligne.produit.prix_achat) * ligne.quantite
        
#         # ========== 3. Cash sales totals ==========
#         cash_queryset = VenteCache.objects.all()
#         if start_date:
#             cash_queryset = cash_queryset.filter(
#                 date_vente__date__gte=start_date,
#                 date_vente__date__lte=end_date
#             )
#         if user_filter:
#             cash_queryset = cash_queryset.filter(utilisateur_id=user_filter)
        
#         total_cash_sales = cash_queryset.count()
#         total_cash_amount = cash_queryset.aggregate(total=Sum('montant_total'))['total'] or 0
#         total_cash_amount = float(total_cash_amount)
        
#         # ========== 4. Product value ==========
#         total_product_value = 0
#         for product in Produit.objects.filter(est_supprime=False).only('prix_achat', 'magasins'):
#             if product.prix_achat and product.magasins:
#                 total_quantity = sum(len(mag.get('codes_barres', [])) for mag in product.magasins)
#                 total_product_value += float(product.prix_achat) * total_quantity
        
#         # ========== 5. Total expenses ==========
#         expense_queryset = Depense.objects.all()
#         if start_date:
#             expense_queryset = expense_queryset.filter(date__gte=start_date, date__lte=end_date)
        
#         total_expenses = expense_queryset.aggregate(total=Sum('montant'))['total'] or 0
#         total_expenses = float(total_expenses)
        
#         # ========== 6. Sales by user with benefits ==========
#         sales_by_user = []
#         if not user_filter and is_admin:
#             users_data = facilite_queryset.values('utilisateur_id', 'utilisateur__username').annotate(
#                 total_sales=Sum('montant_total')
#             ).order_by('-total_sales')
            
#             for user_data in users_data:
#                 user_id = user_data['utilisateur_id']
#                 user_name = user_data['utilisateur__username'] or 'غير معروف'
#                 user_sales = float(user_data['total_sales'] or 0)
                
#                 user_lignes = LigneVenteFacilite.objects.filter(
#                     vente__in=facilite_queryset.filter(utilisateur_id=user_id)
#                 ).select_related('produit')
                
#                 user_cost = 0
#                 for ligne in user_lignes:
#                     if ligne.produit and ligne.produit.prix_achat:
#                         user_cost += float(ligne.produit.prix_achat) * ligne.quantite
                
#                 user_benefit = user_sales - user_cost
                
#                 sales_by_user.append({
#                     'name': user_name,
#                     'المبيعات': round(user_sales * 100, 2),
#                     'الفائدة': round(user_benefit * 100, 2)
#                 })
        
#         # ========== 7. Monthly profits ==========
#         # Use the selected year if provided, otherwise current year
#         target_year = int(year_filter) if year_filter and year_filter.isdigit() else timezone.now().year
        
#         months = ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان",
#                   "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
        
#         monthly_profits = []
#         for month in range(1, 13):
#             month_ventes = VenteFacilite.objects.filter(
#                 date_creation__year=target_year,
#                 date_creation__month=month
#             )
#             if user_filter:
#                 month_ventes = month_ventes.filter(utilisateur_id=user_filter)
            
#             month_sales = month_ventes.aggregate(total=Sum('montant_total'))['total'] or 0
#             month_sales = float(month_sales)
            
#             month_lignes = LigneVenteFacilite.objects.filter(
#                 vente__in=month_ventes
#             ).select_related('produit')
            
#             month_cost = 0
#             for ligne in month_lignes:
#                 if ligne.produit and ligne.produit.prix_achat:
#                     month_cost += float(ligne.produit.prix_achat) * ligne.quantite
            
#             month_profit = (month_sales - month_cost) * 100
            
#             monthly_profits.append({
#                 'month': f"{months[month-1]} {target_year}",
#                 'value': round(month_profit, 2)
#             })
        
#         # ========== 8. Product families ==========
#         families = {}
#         for product in Produit.objects.filter(est_supprime=False).only('famille', 'prix_achat', 'magasins'):
#             if product.prix_achat and product.magasins:
#                 family = product.famille or "غير مصنف"
#                 total_quantity = sum(len(mag.get('codes_barres', [])) for mag in product.magasins)
#                 value = float(product.prix_achat) * total_quantity
#                 if value > 0:
#                     families[family] = families.get(family, 0) + value
        
#         product_families = [
#             {'name': name, 'value': round(value, 2)}
#             for name, value in sorted(families.items(), key=lambda x: x[1], reverse=True)[:20]
#         ]
        
#         # ========== 9. Fast counts with caching ==========
#         def get_total_clients():
#             return Client.objects.count()
        
#         def get_total_products():
#             return Produit.objects.filter(est_supprime=False).count()
        
#         def get_total_fournisseurs():
#             return Fournisseur.objects.count()
        
#         def get_pending_installments():
#             return VenteFacilite.objects.filter(solde_regle=False).count()
        
#         def get_overdue_payments():
#             return VenteFacilite.objects.filter(
#                 solde_regle=False,
#                 date_fin__lt=timezone.now().date()
#             ).count()
        
#         total_clients = self.get_cached_or_query('total_clients_count', get_total_clients, 3600)
#         total_products = self.get_cached_or_query('total_products_count', get_total_products, 3600)
#         total_fournisseurs = self.get_cached_or_query('total_fournisseurs_count', get_total_fournisseurs, 3600)
#         pending_installments = self.get_cached_or_query('pending_installments_count', get_pending_installments, 300)
#         overdue_payments = self.get_cached_or_query('overdue_payments_count', get_overdue_payments, 300)
        
#         # ========== 10. Profit percentage ==========
#         profit_percentage = 0
#         if total_facilite_amount > 0:
#             profit_percentage = ((total_facilite_amount - total_purchase_cost) / total_facilite_amount) * 100
        
#         response_data = {
#             'total_clients': total_clients,
#             'total_facilite_sales': total_facilite_sales,
#             'total_facilite_amount': round(total_facilite_amount, 2),
#             'total_cash_sales': total_cash_sales,
#             'total_cash_amount': round(total_cash_amount, 2),
#             'total_product_value': round(total_product_value, 2),
#             'total_expenses': round(total_expenses, 2),
#             'profit_percentage': round(profit_percentage, 2),
#             'sales_by_user': sales_by_user,
#             'monthly_profits': monthly_profits,
#             'product_families': product_families,
#             'total_products': total_products,
#             'total_fournisseurs': total_fournisseurs,
#             'pending_installments': pending_installments,
#             'overdue_payments': overdue_payments,
#             'selected_year': target_year,  # Return the year used
#         }
        
#         cache.set(cache_key, response_data, 300)
        
#         return Response(response_data)

# stats/views.py - UPDATED DashboardStatsAPIView with both total_clients and new_clients

# stats/views.py - COMPLETE FIXED VERSION

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import connection
from django.core.cache import cache
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate

from authentification.models import Client, Fournisseur
from produits.models import Produit
from ventes.models import VenteFacilite, VenteCache, LigneVenteFacilite
from depenses.models import Depense
from django.contrib.auth import get_user_model
User = get_user_model()
USER_TABLE = User._meta.db_table


class DashboardStatsAPIView(APIView):
    """
    GET /stats/dashboard/
    ULTRA OPTIMIZED version with caching and year filter
    """
    permission_classes = [IsAuthenticated]
    
    def get_date_range(self, periode, year=None):
        """
        Get date range based on periode and optional year
        If year is provided, the date range will be calculated in that year
        """
        today = timezone.now().date()
        current_year = today.year
        current_month = today.month
        
        # If year is provided and valid, use it as the base year
        target_year = current_year
        if year:
            try:
                target_year = int(year)
            except ValueError:
                pass
        
        # Build date ranges based on the target year
        if periode == 'today':
            # Use today's date but in the target year
            try:
                start_date = datetime(target_year, today.month, today.day).date()
            except ValueError:
                # Handle invalid dates (e.g., Feb 30, 31)
                last_day = min(today.day, 28) if today.month == 2 else min(today.day, 30)
                start_date = datetime(target_year, today.month, last_day).date()
            end_date = start_date
            
        elif periode == 'yesterday':
            yesterday = today - timedelta(days=1)
            try:
                start_date = datetime(target_year, yesterday.month, yesterday.day).date()
            except ValueError:
                last_day = min(yesterday.day, 28) if yesterday.month == 2 else min(yesterday.day, 30)
                start_date = datetime(target_year, yesterday.month, last_day).date()
            end_date = start_date
            
        elif periode == 'this_week':
            # Get Monday of the current week
            days_since_monday = today.weekday()
            monday = today - timedelta(days=days_since_monday)
            
            # Start date: Monday in the target year
            try:
                start_date = datetime(target_year, monday.month, monday.day).date()
            except ValueError:
                last_day = min(monday.day, 28) if monday.month == 2 else min(monday.day, 30)
                start_date = datetime(target_year, monday.month, last_day).date()
            
            # End date: today in the target year
            try:
                end_date = datetime(target_year, today.month, today.day).date()
            except ValueError:
                last_day = min(today.day, 28) if today.month == 2 else min(today.day, 30)
                end_date = datetime(target_year, today.month, last_day).date()
            
        elif periode == 'this_month':
            # Use the current month in the target year
            start_date = datetime(target_year, current_month, 1).date()
            # End date: last day of the month
            if current_month == 12:
                end_date = datetime(target_year, 12, 31).date()
            else:
                end_date = datetime(target_year, current_month + 1, 1).date() - timedelta(days=1)
                
        elif periode == 'last_month':
            # Use the previous month in the target year
            if current_month == 1:
                # If it's January, last month is December of previous year
                start_date = datetime(target_year - 1, 12, 1).date()
                end_date = datetime(target_year - 1, 12, 31).date()
            else:
                month_to_use = current_month - 1
                start_date = datetime(target_year, month_to_use, 1).date()
                if month_to_use == 12:
                    end_date = datetime(target_year, 12, 31).date()
                else:
                    end_date = datetime(target_year, month_to_use + 1, 1).date() - timedelta(days=1)
                    
        elif periode == 'this_year':
            # Use the full target year
            start_date = datetime(target_year, 1, 1).date()
            end_date = datetime(target_year, 12, 31).date()
            
        else:
            start_date = None
            end_date = None
        
        return {'start': start_date, 'end': end_date}
    
    def get_cached_or_query(self, cache_key, query_func, timeout=300):
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        data = query_func()
        cache.set(cache_key, data, timeout)
        return data
    
    def get(self, request):
        periode = request.query_params.get('periode', 'this_month')
        user_filter = request.query_params.get('user', None)
        year_filter = request.query_params.get('year', None)
        
        is_admin = request.user.role == 'admin'
        if not is_admin:
            user_filter = str(request.user.id)
        
        # Get date range with year filter
        date_range = self.get_date_range(periode, year_filter)
        start_date = date_range['start']
        end_date = date_range['end']
        
        # Cache key includes year filter
        cache_key = f"dashboard_stats_{periode}_{user_filter}_{year_filter}"
        cached_response = cache.get(cache_key)
        if cached_response:
            return Response(cached_response)
        
        # ========== 1. Installment sales totals ==========
        facilite_queryset = VenteFacilite.objects.all()
        if start_date:
            facilite_queryset = facilite_queryset.filter(
                date_creation__date__gte=start_date,
                date_creation__date__lte=end_date
            )
        if user_filter:
            facilite_queryset = facilite_queryset.filter(utilisateur_id=user_filter)
        
        total_facilite_sales = facilite_queryset.count()
        total_facilite_amount = facilite_queryset.aggregate(total=Sum('montant_total'))['total'] or 0
        total_facilite_amount = float(total_facilite_amount)
        
        # ========== 2. Calculate purchase cost from ligne items ==========
        ligne_queryset = LigneVenteFacilite.objects.filter(vente__in=facilite_queryset).select_related('produit')
        
        total_purchase_cost = 0
        for ligne in ligne_queryset:
            if ligne.produit and ligne.produit.prix_achat:
                total_purchase_cost += float(ligne.produit.prix_achat) * ligne.quantite
        
        # ========== 3. Cash sales totals ==========
        cash_queryset = VenteCache.objects.all()
        if start_date:
            cash_queryset = cash_queryset.filter(
                date_vente__date__gte=start_date,
                date_vente__date__lte=end_date
            )
        if user_filter:
            cash_queryset = cash_queryset.filter(utilisateur_id=user_filter)
        
        total_cash_sales = cash_queryset.count()
        total_cash_amount = cash_queryset.aggregate(total=Sum('montant_total'))['total'] or 0
        total_cash_amount = float(total_cash_amount)
        
        # ========== 4. Product value ==========
        total_product_value = 0
        for product in Produit.objects.filter(est_supprime=False).only('prix_achat', 'magasins'):
            if product.prix_achat and product.magasins:
                total_quantity = sum(len(mag.get('codes_barres', [])) for mag in product.magasins)
                total_product_value += float(product.prix_achat) * total_quantity
        
        # ========== 5. Total expenses ==========
        expense_queryset = Depense.objects.all()
        if start_date:
            expense_queryset = expense_queryset.filter(date__gte=start_date, date__lte=end_date)
        
        total_expenses = expense_queryset.aggregate(total=Sum('montant'))['total'] or 0
        total_expenses = float(total_expenses)
        
        # ========== 6. NEW CLIENTS (filtered by date) ==========
        new_clients_queryset = Client.objects.all()
        if start_date:
            new_clients_queryset = new_clients_queryset.filter(
                date_creation__date__gte=start_date,
                date_creation__date__lte=end_date
            )
        new_clients = new_clients_queryset.count()
        
        # ========== 7. TOTAL CLIENTS (global count - no date filter) ==========
        def get_total_clients():
            return Client.objects.count()
        
        total_clients = self.get_cached_or_query('total_clients_count', get_total_clients, 3600)
        
        # ========== 8. Sales by user with benefits ==========
        sales_by_user = []
        if not user_filter and is_admin:
            users_data = facilite_queryset.values('utilisateur_id', 'utilisateur__username').annotate(
                total_sales=Sum('montant_total')
            ).order_by('-total_sales')
            
            for user_data in users_data:
                user_id = user_data['utilisateur_id']
                user_name = user_data['utilisateur__username'] or 'غير معروف'
                user_sales = float(user_data['total_sales'] or 0)
                
                user_lignes = LigneVenteFacilite.objects.filter(
                    vente__in=facilite_queryset.filter(utilisateur_id=user_id)
                ).select_related('produit')
                
                user_cost = 0
                for ligne in user_lignes:
                    if ligne.produit and ligne.produit.prix_achat:
                        user_cost += float(ligne.produit.prix_achat) * ligne.quantite
                
                user_benefit = user_sales - user_cost
                
                sales_by_user.append({
                    'name': user_name,
                    'المبيعات': round(user_sales * 100, 2),
                    'الفائدة': round(user_benefit * 100, 2)
                })
        
        # ========== 9. Monthly profits ==========
        # Use the selected year if provided, otherwise current year
        target_year = int(year_filter) if year_filter and year_filter.isdigit() else timezone.now().year
        
        months = ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان",
                  "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
        
        monthly_profits = []
        for month in range(1, 13):
            month_ventes = VenteFacilite.objects.filter(
                date_creation__year=target_year,
                date_creation__month=month
            )
            if user_filter:
                month_ventes = month_ventes.filter(utilisateur_id=user_filter)
            
            month_sales = month_ventes.aggregate(total=Sum('montant_total'))['total'] or 0
            month_sales = float(month_sales)
            
            month_lignes = LigneVenteFacilite.objects.filter(
                vente__in=month_ventes
            ).select_related('produit')
            
            month_cost = 0
            for ligne in month_lignes:
                if ligne.produit and ligne.produit.prix_achat:
                    month_cost += float(ligne.produit.prix_achat) * ligne.quantite
            
            month_profit = (month_sales - month_cost) * 100
            
            monthly_profits.append({
                'month': f"{months[month-1]} {target_year}",
                'value': round(month_profit, 2)
            })
        
        # ========== 10. Product families ==========
        families = {}
        for product in Produit.objects.filter(est_supprime=False).only('famille', 'prix_achat', 'magasins'):
            if product.prix_achat and product.magasins:
                family = product.famille or "غير مصنف"
                total_quantity = sum(len(mag.get('codes_barres', [])) for mag in product.magasins)
                value = float(product.prix_achat) * total_quantity
                if value > 0:
                    families[family] = families.get(family, 0) + value
        
        product_families = [
            {'name': name, 'value': round(value, 2)}
            for name, value in sorted(families.items(), key=lambda x: x[1], reverse=True)[:20]
        ]
        
        # ========== 11. Fast counts with caching ==========
        def get_total_products():
            return Produit.objects.filter(est_supprime=False).count()
        
        def get_total_fournisseurs():
            return Fournisseur.objects.count()
        
        def get_pending_installments():
            return VenteFacilite.objects.filter(solde_regle=False).count()
        
        def get_overdue_payments():
            return VenteFacilite.objects.filter(
                solde_regle=False,
                date_fin__lt=timezone.now().date()
            ).count()
        
        total_products = self.get_cached_or_query('total_products_count', get_total_products, 3600)
        total_fournisseurs = self.get_cached_or_query('total_fournisseurs_count', get_total_fournisseurs, 3600)
        pending_installments = self.get_cached_or_query('pending_installments_count', get_pending_installments, 300)
        overdue_payments = self.get_cached_or_query('overdue_payments_count', get_overdue_payments, 300)
        
        # ========== 12. Profit percentage ==========
        profit_percentage = 0
        if total_facilite_amount > 0:
            profit_percentage = ((total_facilite_amount - total_purchase_cost) / total_facilite_amount) * 100
        
        response_data = {
            # Card stats
            'total_clients': total_clients,
            'new_clients': new_clients,
            'total_facilite_sales': total_facilite_sales,
            'total_facilite_amount': round(total_facilite_amount, 2),
            'total_cash_sales': total_cash_sales,
            'total_cash_amount': round(total_cash_amount, 2),
            'total_product_value': round(total_product_value, 2),
            'total_expenses': round(total_expenses, 2),
            
            # Profit percentage
            'profit_percentage': round(profit_percentage, 2),
            
            # Charts
            'sales_by_user': sales_by_user,
            'monthly_profits': monthly_profits,
            'product_families': product_families,
            
            # Additional stats
            'total_products': total_products,
            'total_fournisseurs': total_fournisseurs,
            'pending_installments': pending_installments,
            'overdue_payments': overdue_payments,
            
            # Selected year
            'selected_year': target_year,
            
            # Date range for debugging
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d') if start_date else None,
                'end': end_date.strftime('%Y-%m-%d') if end_date else None,
                'periode': periode
            }
        }
        
        cache.set(cache_key, response_data, 300)
        
        return Response(response_data)


# Keep your other views (QuickStatsAPIView, SalesReportAPIView, etc.) as they are
# The rest of your views remain the same...
class QuickStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM authentification_client")
            total_clients = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ventes_ventefacilite")
            total_facilite = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ventes_ventecache")
            total_cash = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ventes_ventefacilite WHERE solde_regle = false")
            pending = cursor.fetchone()[0]
        
        return Response({
            'total_clients': total_clients,
            'total_facilite_sales': total_facilite,
            'total_cash_sales': total_cash,
            'pending_installments': pending,
        })
    

# stats/views.py - Complete Sales Report API
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q, F, DecimalField, Value
from django.db.models.functions import Coalesce
from django.core.cache import cache
from django.contrib.auth import get_user_model

from authentification.models import Client, Fournisseur
from produits.models import Produit
from ventes.models import VenteFacilite, VenteCache, LigneVenteFacilite, LigneVenteCache
from depenses.models import Depense

User = get_user_model()


# stats/views.py - FIXED SalesReportAPIView without Coalesce issues
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from django.core.cache import cache
from django.contrib.auth import get_user_model

from authentification.models import Client
from produits.models import Produit
from ventes.models import VenteFacilite, VenteCache, LigneVenteFacilite, LigneVenteCache
from depenses.models import Depense

User = get_user_model()


# stats/views.py - FIXED SalesReportAPIView with only telephones

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from django.core.cache import cache
from django.contrib.auth import get_user_model

from authentification.models import Client
from produits.models import Produit
from ventes.models import VenteFacilite, VenteCache, LigneVenteFacilite, LigneVenteCache
from depenses.models import Depense

User = get_user_model()


class SalesReportAPIView(APIView):
    """
    GET /stats/sales-report/
    """
    permission_classes = [IsAuthenticated]
    
    def get_date_range(self, periode, date_from=None, date_to=None):
        """Get date range based on periode or custom dates"""
        today = timezone.now().date()
        
        if date_from and date_to:
            return {'start': date_from, 'end': date_to}
        
        ranges = {
            'today': (today, today),
            'yesterday': (today - timedelta(days=1), today - timedelta(days=1)),
            'this_week': (today - timedelta(days=today.weekday()), today),
            'this_month': (today.replace(day=1), today),
            'last_month': ((today.replace(day=1) - timedelta(days=1)).replace(day=1), today.replace(day=1) - timedelta(days=1)),
            'this_year': (today.replace(month=1, day=1), today),
        }
        
        if periode in ranges:
            return {'start': ranges[periode][0], 'end': ranges[periode][1]}
        return {'start': None, 'end': None}
    
    def get(self, request):
        periode = request.query_params.get('periode', 'this_month')
        user_filter = request.query_params.get('user', None)
        date_from = request.query_params.get('date_from', None)
        date_to = request.query_params.get('date_to', None)
        
        if date_from:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        if date_to:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        
        if request.user.role != 'admin':
            user_filter = str(request.user.id)
        
        date_range = self.get_date_range(periode, date_from, date_to)
        start_date = date_range['start']
        end_date = date_range['end']
        
        # Build querysets with filters
        facilite_queryset = VenteFacilite.objects.all()
        cash_queryset = VenteCache.objects.all()
        depense_queryset = Depense.objects.all()
        
        if start_date:
            facilite_queryset = facilite_queryset.filter(date_creation__date__gte=start_date, date_creation__date__lte=end_date)
            cash_queryset = cash_queryset.filter(date_vente__date__gte=start_date, date_vente__date__lte=end_date)
            depense_queryset = depense_queryset.filter(date__gte=start_date, date__lte=end_date)
        
        if user_filter:
            facilite_queryset = facilite_queryset.filter(utilisateur_id=user_filter)
            cash_queryset = cash_queryset.filter(utilisateur_id=user_filter)
        
        # ========== 1. Installment Sales Totals ==========
        total_facilite_sales = facilite_queryset.count()
        
        total_facilite_amount = 0
        total_facilite_paid = 0
        total_facilite_remaining = 0
        
        for vente in facilite_queryset:
            total_facilite_amount += float(vente.montant_total)
            total_facilite_paid += float(vente.montant_verse)
            total_facilite_remaining += float(vente.montant_restant)
        
        # ========== 2. Purchase Cost & Benefit ==========
        total_purchase_cost = 0
        for ligne in LigneVenteFacilite.objects.filter(vente__in=facilite_queryset).select_related('produit'):
            if ligne.produit and ligne.produit.prix_achat:
                total_purchase_cost += float(ligne.produit.prix_achat) * ligne.quantite
        
        total_benefit = total_facilite_amount - total_purchase_cost
        profit_percentage = (total_benefit / total_facilite_amount * 100) if total_facilite_amount > 0 else 0
        
        # ========== 3. Cash Sales Totals ==========
        total_cash_sales = cash_queryset.count()
        
        total_cash_amount = 0
        for vente in cash_queryset:
            total_cash_amount += float(vente.montant_total)
        
        # ========== 4. Expenses ==========
        total_expenses = 0
        for depense in depense_queryset:
            total_expenses += float(depense.montant)
        
        # ========== 5. User Performance (Installment) ==========
        user_installment_performance = []
        if not user_filter:
            users_data = {}
            for vente in facilite_queryset:
                user_id = vente.utilisateur_id
                if not user_id:
                    continue
                if user_id not in users_data:
                    users_data[user_id] = {
                        'username': vente.utilisateur.username if vente.utilisateur else 'غير معروف',
                        'total_amount': 0,
                        'total_paid': 0,
                        'total_remaining': 0,
                    }
                users_data[user_id]['total_amount'] += float(vente.montant_total)
                users_data[user_id]['total_paid'] += float(vente.montant_verse)
                users_data[user_id]['total_remaining'] += float(vente.montant_restant)
            
            for user_id, data in users_data.items():
                user_sales = data['total_amount']
                
                # Calculate benefit for this user
                user_lignes = LigneVenteFacilite.objects.filter(
                    vente__in=facilite_queryset.filter(utilisateur_id=user_id)
                ).select_related('produit')
                
                user_cost = 0
                for ligne in user_lignes:
                    if ligne.produit and ligne.produit.prix_achat:
                        user_cost += float(ligne.produit.prix_achat) * ligne.quantite
                
                user_benefit = user_sales - user_cost
                user_profit_percentage = (user_benefit / user_sales * 100) if user_sales > 0 else 0
                
                user_installment_performance.append({
                    'username': data['username'],
                    'total_montant_total': user_sales,
                    'total_montant_verse': data['total_paid'],
                    'benefice_total': user_benefit,
                    'pourcentage_benefice_total': round(user_profit_percentage, 2),
                })
            
            user_installment_performance.sort(key=lambda x: x['total_montant_total'], reverse=True)
        
        # ========== 6. User Performance (Cash) ==========
        user_cash_performance = []
        if not user_filter:
            users_cash_data = {}
            for vente in cash_queryset:
                user_id = vente.utilisateur_id
                if not user_id:
                    continue
                if user_id not in users_cash_data:
                    users_cash_data[user_id] = {
                        'username': vente.utilisateur.username if vente.utilisateur else 'غير معروف',
                        'total_amount': 0,
                        'total_count': 0,
                    }
                users_cash_data[user_id]['total_amount'] += float(vente.montant_total)
                users_cash_data[user_id]['total_count'] += 1
            
            for user_id, data in users_cash_data.items():
                user_cash_performance.append({
                    'username': data['username'],
                    'total_montant': data['total_amount'],
                    'nombre_de_ventes': data['total_count'],
                })
            
            user_cash_performance.sort(key=lambda x: x['total_montant'], reverse=True)
        
        # ========== 7. Top Products (Installment) ==========
        top_products_installment = []
        product_data = {}
        for ligne in LigneVenteFacilite.objects.filter(vente__in=facilite_queryset).select_related('produit'):
            product_id = ligne.produit_id
            if not product_id:
                continue
            if product_id not in product_data:
                product_data[product_id] = {
                    'id': product_id,
                    'nom': ligne.produit.nom if ligne.produit else 'غير معروف',
                    'reference': ligne.produit.reference if ligne.produit else '',
                    'quantity': 0,
                    'amount': 0,
                }
            product_data[product_id]['quantity'] += ligne.quantite
            product_data[product_id]['amount'] += float(ligne.sous_total)
        
        top_products_installment = sorted(product_data.values(), key=lambda x: x['amount'], reverse=True)[:10]
        
        # ========== 8. Top Products (Cash) ==========
        top_products_cash = []
        product_cash_data = {}
        for ligne in LigneVenteCache.objects.filter(vente__in=cash_queryset).select_related('produit'):
            product_id = ligne.produit_id
            if not product_id:
                continue
            if product_id not in product_cash_data:
                product_cash_data[product_id] = {
                    'id': product_id,
                    'nom': ligne.produit.nom if ligne.produit else 'غير معروف',
                    'reference': ligne.produit.reference if ligne.produit else '',
                    'quantity': 0,
                    'amount': 0,
                }
            product_cash_data[product_id]['quantity'] += ligne.quantite
            product_cash_data[product_id]['amount'] += float(ligne.sous_total)
        
        top_products_cash = sorted(product_cash_data.values(), key=lambda x: x['amount'], reverse=True)[:10]
        
        # ========== 9. Top Clients (Installment) ==========
        top_clients_installment = []
        client_data = {}
        for vente in facilite_queryset.select_related('client'):
            client_id = vente.client_id
            if not client_id:
                continue
            if client_id not in client_data:
                # ✅ FIXED: Get telephones array correctly
                client_telephones = vente.client.telephones if vente.client and hasattr(vente.client, 'telephones') and vente.client.telephones else []
                client_data[client_id] = {
                    'id': client_id,
                    'nom_famille': vente.client.nom_famille_ar if vente.client else '',
                    'prenom': vente.client.prenom_ar if vente.client else '',
                    'ccp': vente.client.ccp if vente.client else '',
                    'telephones': client_telephones,  # ✅ Only telephones array
                    'total_amount': 0,
                    'total_paid': 0,
                    'total_remaining': 0,
                }
            client_data[client_id]['total_amount'] += float(vente.montant_total)
            client_data[client_id]['total_paid'] += float(vente.montant_verse)
            client_data[client_id]['total_remaining'] += float(vente.montant_restant)
        
        for client_id, data in client_data.items():
            top_clients_installment.append({
                'id': data['id'],
                'client': f"{data['nom_famille']} {data['prenom']}",
                'ccp': data['ccp'],
                'telephones': data['telephones'],  # ✅ Only telephones array
                'total_montant_total': data['total_amount'],
                'total_montant_verse': data['total_paid'],
                'total_montant_restant': data['total_remaining'],
            })
        
        top_clients_installment.sort(key=lambda x: x['total_montant_total'], reverse=True)
        
        # ========== 10. Top Clients (Cash) ==========
        top_clients_cash = []
        client_cash_data = {}
        for vente in cash_queryset.select_related('client'):
            client_id = vente.client_id
            if not client_id:
                continue
            if client_id not in client_cash_data:
                # ✅ FIXED: Get telephones array correctly
                client_telephones = vente.client.telephones if vente.client and hasattr(vente.client, 'telephones') and vente.client.telephones else []
                client_cash_data[client_id] = {
                    'id': client_id,
                    'nom_famille': vente.client.nom_famille_ar if vente.client else '',
                    'prenom': vente.client.prenom_ar if vente.client else '',
                    'ccp': vente.client.ccp if vente.client else '',
                    'telephones': client_telephones,  # ✅ Only telephones array
                    'total_amount': 0,
                    'total_count': 0,
                }
            client_cash_data[client_id]['total_amount'] += float(vente.montant_total)
            client_cash_data[client_id]['total_count'] += 1
        
        for client_id, data in client_cash_data.items():
            top_clients_cash.append({
                'id': data['id'],
                'client': f"{data['nom_famille']} {data['prenom']}",
                'ccp': data['ccp'],
                'telephones': data['telephones'],  # ✅ Only telephones array
                'total_montant': data['total_amount'],
                'nombre_de_ventes': data['total_count'],
            })
        
        top_clients_cash.sort(key=lambda x: x['total_montant'], reverse=True)
        
        # Return response
        return Response({
            'totals': {
                'total_montant_total': total_facilite_amount,
                'total_montant_verse': total_facilite_paid,
                'total_montant': total_cash_amount,
                'total_ventes': total_facilite_sales,
                'nombre_de_ventes': total_cash_sales,
                'total_montant_depense': total_expenses,
                'pourcentage_benefice_total': round(profit_percentage, 2),
                'benefice_total': total_benefit,
            },
            'user_installment_performance': user_installment_performance,
            'user_cash_performance': user_cash_performance,
            'top_products_installment': [
                {
                    'id': p['id'],
                    'produit': p['nom'],
                    'reference': p['reference'],
                    'quantite_vendue_produit': p['quantity'],
                    'montant_total_produit': p['amount'],
                }
                for p in top_products_installment
            ],
            'top_products_cash': [
                {
                    'id': p['id'],
                    'produit': p['nom'],
                    'reference': p['reference'],
                    'quantite_vendue_produit': p['quantity'],
                    'montant_total_produit': p['amount'],
                }
                for p in top_products_cash
            ],
            'top_clients_installment': top_clients_installment[:10],
            'top_clients_cash': top_clients_cash[:10],
        })


class ClientDetailAPIView(APIView):
    """
    GET /stats/client/{id}/
    Returns detailed information about a client
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, client_id):
        # Get client details
        client = Client.objects.get(id=client_id)
        
        # Get installment sales
        facilite_ventes = VenteFacilite.objects.filter(client_id=client_id)
        
        total_facilite = 0
        total_paid = 0
        total_remaining = 0
        
        for vente in facilite_ventes:
            total_facilite += float(vente.montant_total)
            total_paid += float(vente.montant_verse)
            total_remaining += float(vente.montant_restant)
        
        # Get cash sales
        cash_ventes = VenteCache.objects.filter(client_id=client_id)
        
        total_cash = 0
        for vente in cash_ventes:
            total_cash += float(vente.montant_total)
        
        # ✅ FIXED: Get telephones array
        client_telephones = client.telephones if hasattr(client, 'telephones') and client.telephones else []
        
        return Response({
            'id': client.id,
            'nom_famille_ar': client.nom_famille_ar,
            'prenom_ar': client.prenom_ar,
            'nom_famille_fr': client.nom_famille_fr,
            'prenom_fr': client.prenom_fr,
            'ccp': client.ccp,
            'cle': client.cle,
            'telephones': client_telephones,  # ✅ Only telephones array
            'adresse': client.adresse,
            'statut': client.statut,
            'bloque': client.bloque,
            'note': client.note,
            'revenu': client.revenu,
            'profession': client.profession,
            'jour': client.jour,
            'numero_national': client.numero_national,
            'date_naissance': client.date_naissance,
            'lieu_naissance': client.lieu_naissance,
            'nom_pere': client.nom_pere,
            'nom_mere': client.nom_mere,
            'type_piece_identite': client.type_piece_identite,
            'numero_piece_identite': client.numero_piece_identite,
            'date_emission_piece': client.date_emission_piece,
            'lieu_emission_piece': client.lieu_emission_piece,
            'total_facilite': total_facilite,
            'paye_facilite': total_paid,
            'reste_facilite': total_remaining,
            'total_cash': total_cash,
            'ventes_facilite': list(facilite_ventes.values('id', 'date_creation', 'montant_total', 'nombre_mois', 'montant_mensuel')),
            'ventes_cash': list(cash_ventes.values('id', 'date_vente', 'montant_total')),
        })


class ProductDetailAPIView(APIView):
    """
    GET /stats/product/{id}/
    Returns detailed information about a product
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, product_id):
        # Get product details
        product = Produit.objects.get(id=product_id)
        
        # Get installment sales
        facilite_lignes = LigneVenteFacilite.objects.filter(produit_id=product_id).select_related('vente')
        
        total_facilite_amount = 0
        total_facilite_quantity = 0
        
        for ligne in facilite_lignes:
            total_facilite_amount += float(ligne.sous_total)
            total_facilite_quantity += ligne.quantite
        
        # Get cash sales
        cash_lignes = LigneVenteCache.objects.filter(produit_id=product_id).select_related('vente')
        
        total_cash_amount = 0
        total_cash_quantity = 0
        
        for ligne in cash_lignes:
            total_cash_amount += float(ligne.sous_total)
            total_cash_quantity += ligne.quantite
        
        # Calculate total quantity from magasins
        total_quantity = 0
        if product.magasins:
            for mag in product.magasins:
                total_quantity += len(mag.get('codes_barres', []))
        
        return Response({
            'id': product.id,
            'nom': product.nom,
            'reference': product.reference,
            'famille': product.famille,
            'marque': product.marque,
            'prix_achat': float(product.prix_achat) if product.prix_achat else 0,
            'prix_vente_cache': float(product.prix_vente_cache) if product.prix_vente_cache else 0,
            'quantite': total_quantity,
            'total_facilite': total_facilite_amount,
            'quantite_facilite': total_facilite_quantity,
            'total_cash': total_cash_amount,
            'quantite_cash': total_cash_quantity,
            'ventes_facilite': [
                {
                    'id': ligne.vente.id,
                    'date_formatee': ligne.vente.date_creation.strftime('%d/%m/%Y'),
                    'quantite': ligne.quantite,
                    'montant_total': float(ligne.sous_total),
                }
                for ligne in facilite_lignes
            ],
            'ventes_cash': [
                {
                    'id': ligne.vente.id,
                    'date_formatee': ligne.vente.date_vente.strftime('%d/%m/%Y'),
                    'quantite': ligne.quantite,
                    'montant_total': float(ligne.sous_total),
                }
                for ligne in cash_lignes
            ],
        })

class ProductDetailAPIView(APIView):
    """
    GET /stats/product/{id}/
    Returns detailed information about a product
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, product_id):
        # Get product details
        product = Produit.objects.get(id=product_id)
        
        # Get installment sales
        facilite_lignes = LigneVenteFacilite.objects.filter(produit_id=product_id).select_related('vente')
        
        total_facilite_amount = 0
        total_facilite_quantity = 0
        
        for ligne in facilite_lignes:
            total_facilite_amount += float(ligne.sous_total)
            total_facilite_quantity += ligne.quantite
        
        # Get cash sales
        cash_lignes = LigneVenteCache.objects.filter(produit_id=product_id).select_related('vente')
        
        total_cash_amount = 0
        total_cash_quantity = 0
        
        for ligne in cash_lignes:
            total_cash_amount += float(ligne.sous_total)
            total_cash_quantity += ligne.quantite
        
        # Calculate total quantity from magasins
        total_quantity = 0
        if product.magasins:
            for mag in product.magasins:
                total_quantity += len(mag.get('codes_barres', []))
        
        return Response({
            'id': product.id,
            'nom': product.nom,
            'reference': product.reference,
            'famille': product.famille,
            'marque': product.marque,
            'prix_achat': float(product.prix_achat) if product.prix_achat else 0,
            'prix_vente_cache': float(product.prix_vente_cache) if product.prix_vente_cache else 0,
            'quantite': total_quantity,
            'total_facilite': total_facilite_amount,
            'quantite_facilite': total_facilite_quantity,
            'total_cash': total_cash_amount,
            'quantite_cash': total_cash_quantity,
            'ventes_facilite': [
                {
                    'id': ligne.vente.id,
                    'date_formatee': ligne.vente.date_creation.strftime('%d/%m/%Y'),
                    'quantite': ligne.quantite,
                    'montant_total': float(ligne.sous_total),
                }
                for ligne in facilite_lignes
            ],
            'ventes_cash': [
                {
                    'id': ligne.vente.id,
                    'date_formatee': ligne.vente.date_vente.strftime('%d/%m/%Y'),
                    'quantite': ligne.quantite,
                    'montant_total': float(ligne.sous_total),
                }
                for ligne in cash_lignes
            ],
        })