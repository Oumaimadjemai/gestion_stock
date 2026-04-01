from rest_framework import generics, permissions,status,filters
from .models import *
from .serializers import *
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from datetime import date, timedelta
from django.utils.timezone import now
from dateutil.relativedelta import relativedelta
from django.utils.timezone import localtime,datetime

from rest_framework.permissions import IsAuthenticated

class AchatListCreateAPIView(generics.ListCreateAPIView):
    queryset = Achat.objects.all()
    serializer_class = AchatSerializer
    permission_classes = [permissions.IsAuthenticated]

class AchatRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Achat.objects.all()
    serializer_class = AchatSerializer
    permission_classes = [permissions.IsAuthenticated]


    
# from rest_framework import generics, status, filters
# from rest_framework.response import Response
# from django_filters.rest_framework import DjangoFilterBackend
# from django.db import transaction
# from rest_framework.permissions import IsAuthenticated
# from .models import AchatGroupe
# from .serializers import AchatGroupeSerializer


# class AchatGroupeListCreateAPIView(generics.ListCreateAPIView):
#     queryset = AchatGroupe.objects.all().order_by('-date')
#     serializer_class = AchatGroupeSerializer
#     permission_classes = [IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter]
#     filterset_fields = ['fournisseur', 'date']
#     search_fields = ['fournisseur__nom', 'achats__produit__nom']

#     def get_queryset(self):
#         queryset = super().get_queryset()
        
#         # ✅ Filter by product ID if provided (through related achats)
#         produit_id = self.request.query_params.get('produit')
#         if produit_id:
#             queryset = queryset.filter(achats__produit_id=produit_id).distinct()
        
#         return queryset

#     def list(self, request, *args, **kwargs):
#         queryset = self.filter_queryset(self.get_queryset())

#         # Calculate statistics
#         total_sum = sum(ag.total or 0 for ag in queryset)
#         paid_sum = sum(ag.somme_payee or 0 for ag in queryset)
#         remaining_sum = sum(ag.somme_restante or 0 for ag in queryset)

#         # Serialize data
#         page = self.paginate_queryset(queryset)
#         if page is not None:
#             serializer = self.get_serializer(page, many=True)
#             return self.get_paginated_response({
#                 'nombre_achats': queryset.count(),
#                 'somme_totale': f"{total_sum:.2f}",
#                 'somme_payee': f"{paid_sum:.2f}",
#                 'somme_restante': f"{remaining_sum:.2f}",
#                 'achats_groupes': serializer.data
#             })

#         serializer = self.get_serializer(queryset, many=True)
#         return Response({
#             'nombre_achats': queryset.count(),
#             'somme_totale': f"{total_sum:.2f}",
#             'somme_payee': f"{paid_sum:.2f}",
#             'somme_restante': f"{remaining_sum:.2f}",
#             'achats_groupes': serializer.data
#         }, status=status.HTTP_200_OK)

#     @transaction.atomic
#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         validation_errors = []
#         deleted_barcodes = []

#         try:
#             achat_groupe = serializer.save()

#             for ligne in achat_groupe.achats.all():
#                 produit = ligne.produit
#                 qty = ligne.quantite or 0
#                 prix_achat = ligne.prix_achat or 0

#                 if not produit:
#                     validation_errors.append(f"Produit introuvable pour la ligne {ligne.id}")
#                     continue

#                 # 🟢 FIXED: Set exact quantity purchased
#                 produit.quantite = qty

#                 # Update purchase price if provided
#                 if prix_achat > 0:
#                     produit.prix_achat = prix_achat

#                 # Handle barcodes without duplicates
#                 if hasattr(ligne, 'nouveaux_codes_barres') and ligne.nouveaux_codes_barres:
#                     if not hasattr(produit, 'codes_barres') or not isinstance(produit.codes_barres, list):
#                         produit.codes_barres = []

#                     for code in ligne.nouveaux_codes_barres:
#                         if code not in produit.codes_barres:
#                             produit.codes_barres.append(code)
#                             deleted_barcodes.append(code)  # keep track of added codes

#                 produit.save()

#             # Check validation errors
#             if validation_errors:
#                 transaction.set_rollback(True)
#                 return Response({
#                     'error': 'Erreurs de validation',
#                     'details': validation_errors
#                 }, status=status.HTTP_400_BAD_REQUEST)

#             headers = self.get_success_headers(serializer.data)
#             response_data = {
#                 "success": "Achat enregistré avec succès",
#                 "achat_groupe_id": achat_groupe.id,
#                 "total_achat": f"{achat_groupe.total:.2f}",
#                 "somme_payee": f"{achat_groupe.somme_payee:.2f}",
#                 "somme_restante": f"{achat_groupe.somme_restante:.2f}",
#                 "nombre_lignes": achat_groupe.achats.count(),
#                 "deleted_barcodes": deleted_barcodes,
#                 "deleted_count": len(deleted_barcodes),
#                 "data": serializer.data
#             }

#             return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

#         except Exception as e:
#             transaction.set_rollback(True)
#             print(f"Unexpected error in create achat: {str(e)}")
#             return Response({
#                 'error': 'Erreur interne du serveur',
#                 'details': str(e)
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#     @transaction.atomic
#     def perform_destroy(self, instance):
#         """
#         Override destroy to handle stock reversal when deleting an achat
#         """
#         try:
#             for ligne in instance.achats.all():
#                 produit = ligne.produit
#                 qty = ligne.quantite or 0

#                 if not produit:
#                     continue

#                 # Reverse stock
#                 produit.quantite = max(0, (produit.quantite or 0) - qty)
#                 # Note: barcodes cannot be restored
#                 produit.save()

#             instance.delete()
#         except Exception as e:
#             transaction.set_rollback(True)
#             raise e
# achats/views.py

# achats/views.py

from rest_framework import generics, status, filters
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db.models import Sum, Count, Prefetch, Q
from rest_framework.permissions import IsAuthenticated
from .models import AchatGroupe, LigneAchat
from .serializers import AchatGroupeSerializer
from django.core.cache import cache


class AchatGroupeListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = AchatGroupeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['fournisseur', 'date']
    search_fields = ['fournisseur__nom', 'achats__produit__nom']
    
    def get_queryset(self):
        # Optimize with select_related and only needed fields
        queryset = AchatGroupe.objects.select_related(
            'fournisseur', 'utilisateur'
        ).prefetch_related(
            Prefetch('achats', queryset=LigneAchat.objects.select_related(
                'produit', 'magasin'
            ).only(
                'id', 'quantite', 'prix_achat', 'produit_id', 'magasin_id', 
                'nouveaux_codes_barres', 'achat_groupe_id'
            ))
        ).only(
            'id', 'fournisseur', 'utilisateur_id', 'date', 'total', 
            'somme_payee', 'somme_restante'
        ).order_by('-date')
        
        # Apply filters
        produit_id = self.request.query_params.get('produit')
        if produit_id:
            queryset = queryset.filter(achats__produit_id=produit_id).distinct()
        
        fournisseur = self.request.query_params.get('fournisseur')
        if fournisseur:
            queryset = queryset.filter(fournisseur_id=fournisseur)
        
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        
        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        return queryset

    def list(self, request, *args, **kwargs):
        # Try to get from cache first (15 minutes)
        cache_key = f"achat_list_{request.user.id}_{request.query_params.urlencode()}"
        cached_response = cache.get(cache_key)
        
        if cached_response:
            return Response(cached_response)
        
        # Get filtered queryset
        queryset = self.filter_queryset(self.get_queryset())
        
        # Use database aggregation (much faster than Python loops)
        stats = queryset.aggregate(
            total_sum=Sum('total'),
            paid_sum=Sum('somme_payee'),
            remaining_sum=Sum('somme_restante'),
            nombre_achats=Count('id', distinct=True)
        )
        
        # Paginate (reduce page size for faster loading)
        page_size = int(request.query_params.get('page_size', 20))
        self.pagination_class.page_size = page_size
        
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = {
                'nombre_achats': stats['nombre_achats'] or 0,
                'somme_totale': f"{stats['total_sum'] or 0:.2f}",
                'somme_payee': f"{stats['paid_sum'] or 0:.2f}",
                'somme_restante': f"{stats['remaining_sum'] or 0:.2f}",
                'achats_groupes': serializer.data
            }
            
            # Cache the response
            cache.set(cache_key, response_data, 60 * 15)  # 15 minutes cache
            
            return self.get_paginated_response(response_data)
        
        serializer = self.get_serializer(queryset, many=True)
        response_data = {
            'nombre_achats': stats['nombre_achats'] or 0,
            'somme_totale': f"{stats['total_sum'] or 0:.2f}",
            'somme_payee': f"{stats['paid_sum'] or 0:.2f}",
            'somme_restante': f"{stats['remaining_sum'] or 0:.2f}",
            'achats_groupes': serializer.data
        }
        
        # Cache the response
        cache.set(cache_key, response_data, 60 * 15)  # 15 minutes cache
        
        return Response(response_data, status=status.HTTP_200_OK)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class AchatGroupeRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = AchatGroupe.objects.all()
    serializer_class = AchatGroupeSerializer
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Clear cache after update
        cache.delete_pattern(f"achat_list_*")
        
        return Response(serializer.data)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """
        Delete purchase with automatic stock rollback
        """
        instance = self.get_object()

        try:
            # Restore stock for all lines
            for ligne in instance.achats.all():
                if ligne.produit and ligne.magasin:
                    try:
                        # Remove the stock that was added
                        ligne.produit.decrement_quantite_par_magasin(
                            ligne.magasin.id, 
                            ligne.quantite
                        )
                    except ValueError as e:
                        print(f"Warning: Could not restore stock for product {ligne.produit.id}: {e}")

            # Delete the purchase group (cascade deletes lines)
            self.perform_destroy(instance)
            
            # Clear cache
            cache.delete_pattern(f"achat_list_*")

            return Response(
                {"success": "Achat supprimé avec succès et stock corrigé"},
                status=status.HTTP_204_NO_CONTENT
            )

        except Exception as e:
            transaction.set_rollback(True)
            print(f"Error deleting purchase: {e}")
            return Response(
                {"error": f"Suppression annulée : {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )