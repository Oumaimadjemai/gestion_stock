from django.db.models import Sum, Count, Q, F, DecimalField, Value
from django.db.models.functions import Coalesce, TruncMonth, ExtractMonth
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from authentification.models import Client, Fournisseur
from produits.models import Produit
from ventes.models import VenteFacilite, VenteCache
from depenses.models import Depense
from django.contrib.auth import get_user_model

User = get_user_model()


class DashboardStatsService:
    def __init__(self, user=None, periode='this_month', user_filter=None):
        self.user = user
        self.periode = periode
        self.user_filter = user_filter
        self.date_range = self._get_date_range()
    
    def _get_date_range(self):
        """Get date range based on periode parameter"""
        today = timezone.now().date()
        
        if self.periode == 'today':
            start_date = today
            end_date = today
        elif self.periode == 'yesterday':
            start_date = today - timedelta(days=1)
            end_date = today - timedelta(days=1)
        elif self.periode == 'this_week':
            start_date = today - timedelta(days=today.weekday())
            end_date = today
        elif self.periode == 'this_month':
            start_date = today.replace(day=1)
            end_date = today
        elif self.periode == 'last_month':
            first_day_of_this_month = today.replace(day=1)
            last_day_of_last_month = first_day_of_this_month - timedelta(days=1)
            start_date = last_day_of_last_month.replace(day=1)
            end_date = last_day_of_last_month
        elif self.periode == 'this_year':
            start_date = today.replace(month=1, day=1)
            end_date = today
        else:
            start_date = None
            end_date = None
        
        return {'start': start_date, 'end': end_date}
    
    def _apply_filters(self, queryset, date_field='date_creation'):
        """Apply user and date filters to a queryset"""
        # Apply user filter
        if self.user_filter:
            if hasattr(queryset.model, 'utilisateur'):
                queryset = queryset.filter(utilisateur_id=self.user_filter)
            elif hasattr(queryset.model, 'user'):
                queryset = queryset.filter(user_id=self.user_filter)
        
        # Apply date filter
        if self.date_range['start'] and date_field:
            filter_kwargs = {f"{date_field}__date__gte": self.date_range['start']}
            queryset = queryset.filter(**filter_kwargs)
            if self.date_range['end']:
                filter_kwargs = {f"{date_field}__date__lte": self.date_range['end']}
                queryset = queryset.filter(**filter_kwargs)
        
        return queryset
    
    def get_total_clients(self):
        """Get total number of clients"""
        queryset = Client.objects.all()
        return self._apply_filters(queryset, 'date_creation').count()
    
    def get_total_facilite_sales(self):
        """Get total number of installment sales"""
        queryset = VenteFacilite.objects.all()
        queryset = self._apply_filters(queryset, 'date_creation')
        return queryset.count()
    
    def get_total_facilite_amount(self):
        """Get total amount of installment sales"""
        queryset = VenteFacilite.objects.all()
        queryset = self._apply_filters(queryset, 'date_creation')
        result = queryset.aggregate(total=Coalesce(Sum('montant_total'), 0))
        return result['total'] or 0
    
    def get_total_cash_sales(self):
        """Get total number of cash sales"""
        queryset = VenteCache.objects.all()
        queryset = self._apply_filters(queryset, 'date_vente')
        return queryset.count()
    
    def get_total_cash_amount(self):
        """Get total amount of cash sales"""
        queryset = VenteCache.objects.all()
        queryset = self._apply_filters(queryset, 'date_vente')
        result = queryset.aggregate(total=Coalesce(Sum('montant_total'), 0))
        return result['total'] or 0
    
    def get_total_product_value(self):
        """Get total value of products in stock"""
        products = Produit.objects.all()
        total_value = 0
        for product in products:
            if product.prix_achat:
                total_value += float(product.prix_achat) * product.quantite_totale
        return total_value
    
    def get_total_expenses(self):
        """Get total expenses"""
        try:
            from depenses.models import Depense
            queryset = Depense.objects.all()
            queryset = self._apply_filters(queryset, 'date_depense')
            result = queryset.aggregate(total=Coalesce(Sum('montant'), 0))
            return result['total'] or 0
        except:
            return 0
    
    def get_profit_percentage(self):
        """Calculate profit percentage for installment sales"""
        queryset = VenteFacilite.objects.all()
        queryset = self._apply_filters(queryset, 'date_creation')
        
        # Calculate total benefit
        total_benefit = 0
        total_sales_amount = 0
        
        for vente in queryset:
            vente_total = float(vente.montant_total)
            total_sales_amount += vente_total
            
            # Calculate purchase cost from snapshot
            cout_achat = 0
            for ligne in vente.lignes.all():
                if ligne.stock_snapshot and 'produit' in ligne.stock_snapshot:
                    # You would need to calculate from snapshot
                    pass
                if ligne.produit and ligne.produit.prix_achat:
                    cout_achat += float(ligne.produit.prix_achat) * ligne.quantite
            
            benefit = vente_total - cout_achat
            total_benefit += benefit
        
        if total_sales_amount > 0:
            return round((total_benefit / total_sales_amount) * 100, 2)
        return 0
    
    def get_sales_by_user(self):
        """Get sales grouped by user"""
        ventes = VenteFacilite.objects.all()
        ventes = self._apply_filters(ventes, 'date_creation')
        
        user_sales = {}
        for vente in ventes:
            user_id = vente.utilisateur_id
            user_name = vente.utilisateur.username if vente.utilisateur else 'غير معروف'
            
            if user_id not in user_sales:
                user_sales[user_id] = {
                    'name': user_name,
                    'sales': 0,
                    'profit': 0
                }
            
            vente_total = float(vente.montant_total)
            user_sales[user_id]['sales'] += vente_total
            
            # Calculate benefit
            cout_achat = 0
            for ligne in vente.lignes.all():
                if ligne.produit and ligne.produit.prix_achat:
                    cout_achat += float(ligne.produit.prix_achat) * ligne.quantite
            benefit = vente_total - cout_achat
            user_sales[user_id]['profit'] += benefit
        
        return [
            {
                'name': data['name'],
                'المبيعات': round(data['sales'] * 100, 2),
                'الفائدة': round(data['profit'] * 100, 2)
            }
            for data in user_sales.values()
        ]
    
    def get_monthly_profits(self):
        """Get monthly profits for the current year"""
        months = [
            "جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان",
            "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
        ]
        
        current_year = timezone.now().year
        monthly_benefits = [0] * 12
        
        # Get all sales for the current year
        ventes = VenteFacilite.objects.filter(
            date_creation__year=current_year
        )
        
        if self.user_filter:
            ventes = ventes.filter(utilisateur_id=self.user_filter)
        
        for vente in ventes:
            month_index = vente.date_creation.month - 1
            
            # Calculate benefit
            cout_achat = 0
            for ligne in vente.lignes.all():
                if ligne.produit and ligne.produit.prix_achat:
                    cout_achat += float(ligne.produit.prix_achat) * ligne.quantite
            
            benefit = float(vente.montant_total) - cout_achat
            monthly_benefits[month_index] += round(benefit * 100, 2)
        
        return [
            {'month': f"{months[i]} {current_year}", 'value': val}
            for i, val in enumerate(monthly_benefits)
        ]
    
    def get_product_families(self):
        """Get product families distribution"""
        families = {}
        products = Produit.objects.filter(est_supprime=False)
        
        for product in products:
            family = product.famille or "غير مصنف"
            value = float(product.prix_achat or 0) * product.quantite_totale
            
            if value > 0:
                if family not in families:
                    families[family] = 0
                families[family] += value
        
        return [
            {'name': name, 'value': round(value, 2)}
            for name, value in families.items()
        ]
    
    def get_total_products(self):
        """Get total number of products"""
        return Produit.objects.filter(est_supprime=False).count()
    
    def get_total_fournisseurs(self):
        """Get total number of fournisseurs"""
        try:
            from authentification.models import Fournisseur
            return Fournisseur.objects.count()
        except:
            return 0
    
    def get_pending_installments(self):
        """Get number of pending installment sales"""
        return VenteFacilite.objects.filter(solde_regle=False).count()
    
    def get_overdue_payments(self):
        """Get number of overdue payments"""
        today = timezone.now().date()
        overdue = VenteFacilite.objects.filter(
            solde_regle=False,
            date_fin__lt=today
        )
        return overdue.count()
    
    def get_all_stats(self):
        """Get all dashboard statistics"""
        return {
            # Card stats
            'total_clients': self.get_total_clients(),
            'total_facilite_sales': self.get_total_facilite_sales(),
            'total_facilite_amount': self.get_total_facilite_amount(),
            'total_cash_sales': self.get_total_cash_sales(),
            'total_cash_amount': self.get_total_cash_amount(),
            'total_product_value': self.get_total_product_value(),
            'total_expenses': self.get_total_expenses(),
            
            # Profit percentage
            'profit_percentage': self.get_profit_percentage(),
            
            # Charts
            'sales_by_user': self.get_sales_by_user(),
            'monthly_profits': self.get_monthly_profits(),
            'product_families': self.get_product_families(),
            
            # Additional stats
            'total_products': self.get_total_products(),
            'total_fournisseurs': self.get_total_fournisseurs(),
            'pending_installments': self.get_pending_installments(),
            'overdue_payments': self.get_overdue_payments(),
        }