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


    
from rest_framework import generics, status, filters
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from .models import AchatGroupe
from .serializers import AchatGroupeSerializer


class AchatGroupeListCreateAPIView(generics.ListCreateAPIView):
    queryset = AchatGroupe.objects.all().order_by('-date')
    serializer_class = AchatGroupeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['fournisseur', 'date']
    search_fields = ['fournisseur__nom', 'achats__produit__nom']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # ✅ Filter by product ID if provided (through related achats)
        produit_id = self.request.query_params.get('produit')
        if produit_id:
            queryset = queryset.filter(achats__produit_id=produit_id).distinct()
        
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Calculate statistics
        total_sum = sum(ag.total or 0 for ag in queryset)
        paid_sum = sum(ag.somme_payee or 0 for ag in queryset)
        remaining_sum = sum(ag.somme_restante or 0 for ag in queryset)

        # Serialize data
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'nombre_achats': queryset.count(),
                'somme_totale': f"{total_sum:.2f}",
                'somme_payee': f"{paid_sum:.2f}",
                'somme_restante': f"{remaining_sum:.2f}",
                'achats_groupes': serializer.data
            })

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'nombre_achats': queryset.count(),
            'somme_totale': f"{total_sum:.2f}",
            'somme_payee': f"{paid_sum:.2f}",
            'somme_restante': f"{remaining_sum:.2f}",
            'achats_groupes': serializer.data
        }, status=status.HTTP_200_OK)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validation_errors = []
        deleted_barcodes = []

        try:
            achat_groupe = serializer.save()

            for ligne in achat_groupe.achats.all():
                produit = ligne.produit
                qty = ligne.quantite or 0
                prix_achat = ligne.prix_achat or 0

                if not produit:
                    validation_errors.append(f"Produit introuvable pour la ligne {ligne.id}")
                    continue

                # 🟢 FIXED: Set exact quantity purchased
                produit.quantite = qty

                # Update purchase price if provided
                if prix_achat > 0:
                    produit.prix_achat = prix_achat

                # Handle barcodes without duplicates
                if hasattr(ligne, 'nouveaux_codes_barres') and ligne.nouveaux_codes_barres:
                    if not hasattr(produit, 'codes_barres') or not isinstance(produit.codes_barres, list):
                        produit.codes_barres = []

                    for code in ligne.nouveaux_codes_barres:
                        if code not in produit.codes_barres:
                            produit.codes_barres.append(code)
                            deleted_barcodes.append(code)  # keep track of added codes

                produit.save()

            # Check validation errors
            if validation_errors:
                transaction.set_rollback(True)
                return Response({
                    'error': 'Erreurs de validation',
                    'details': validation_errors
                }, status=status.HTTP_400_BAD_REQUEST)

            headers = self.get_success_headers(serializer.data)
            response_data = {
                "success": "Achat enregistré avec succès",
                "achat_groupe_id": achat_groupe.id,
                "total_achat": f"{achat_groupe.total:.2f}",
                "somme_payee": f"{achat_groupe.somme_payee:.2f}",
                "somme_restante": f"{achat_groupe.somme_restante:.2f}",
                "nombre_lignes": achat_groupe.achats.count(),
                "deleted_barcodes": deleted_barcodes,
                "deleted_count": len(deleted_barcodes),
                "data": serializer.data
            }

            return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

        except Exception as e:
            transaction.set_rollback(True)
            print(f"Unexpected error in create achat: {str(e)}")
            return Response({
                'error': 'Erreur interne du serveur',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @transaction.atomic
    def perform_destroy(self, instance):
        """
        Override destroy to handle stock reversal when deleting an achat
        """
        try:
            for ligne in instance.achats.all():
                produit = ligne.produit
                qty = ligne.quantite or 0

                if not produit:
                    continue

                # Reverse stock
                produit.quantite = max(0, (produit.quantite or 0) - qty)
                # Note: barcodes cannot be restored
                produit.save()

            instance.delete()
        except Exception as e:
            transaction.set_rollback(True)
            raise e

from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

class AchatGroupeRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = AchatGroupe.objects.all()
    serializer_class = AchatGroupeSerializer
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """
        Suppression d'un achat avec rollback automatique
        et restauration correcte du stock et codes-barres.
        """
        instance = self.get_object()

        try:
            # 🔄 Restaurer les produits liés
            for ligne in instance.achats.all():
                produit = ligne.produit

                # Supprimer les codes-barres générés pour cet achat
                if ligne.nouveaux_codes_barres:
                    produit.codes_barres = [
                        cb for cb in produit.codes_barres
                        if cb not in ligne.nouveaux_codes_barres
                    ]

                # Décrémenter la quantité
                produit.quantite -= ligne.quantite
                if produit.quantite < 0:
                    produit.quantite = 0  # sécurité

                produit.save()

            # Supprimer l'achat (et ses lignes via cascade)
            self.perform_destroy(instance)

            return Response(
                {"success": "Achat supprimé avec succès et stock corrigé"},
                status=status.HTTP_204_NO_CONTENT
            )

        except Exception as e:
            transaction.set_rollback(True)
            return Response(
                {"error": f"Suppression annulée : {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
