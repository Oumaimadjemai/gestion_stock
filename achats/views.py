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


    
from django.db.models import Q

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from .models import AchatGroupe
from .serializers import AchatGroupeSerializer


class AchatGroupeListCreateAPIView(generics.ListCreateAPIView):
    queryset = AchatGroupe.objects.all().order_by('-date')
    serializer_class = AchatGroupeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['fournisseur', 'date']
    search_fields = ['fournisseur__nom', 'achats__produit__nom']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Calculate statistics
        total_sum = 0
        paid_sum = 0
        remaining_sum = 0
        
        for ag in queryset:
            total_sum += ag.total or 0
            paid_sum += ag.somme_payee or 0
            remaining_sum += ag.somme_restante or 0
        
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

        deleted_barcodes = []
        validation_errors = []

        try:
            # Save the achat groupe first
            achat_groupe = serializer.save()

            # Process each line in the achat
            for ligne in achat_groupe.achats.all():
                produit = ligne.produit
                qty = ligne.quantite or 0
                prix_achat = ligne.prix_achat or 0

                # 🔴 NEGATIVE QUANTITY → REMOVE STOCK (Stock correction)
                if qty < 0:
                    qty_to_remove = abs(qty)

                    # Check if product exists and has enough stock
                    if not produit:
                        validation_errors.append(f"Produit introuvable pour la ligne {ligne.id}")
                        continue

                    # Check stock availability
                    current_stock = produit.quantite or 0
                    if current_stock < qty_to_remove:
                        validation_errors.append(
                            f"Stock insuffisant pour '{produit.nom}'. "
                            f"Stock actuel: {current_stock}, "
                            f"Quantité à retirer: {qty_to_remove}"
                        )
                        continue

                    # Update product quantity
                    produit.quantite = current_stock - qty_to_remove

                    # 🔻 Remove barcodes (LIFO - Last In First Out)
                    if hasattr(produit, 'codes_barres') and produit.codes_barres:
                        # Ensure codes_barres is a list
                        if isinstance(produit.codes_barres, list):
                            codes_list = produit.codes_barres
                            # Calculate how many barcodes we can actually remove
                            actual_qty_to_remove = min(qty_to_remove, len(codes_list))
                            
                            if actual_qty_to_remove > 0:
                                # Get the last 'actual_qty_to_remove' barcodes
                                removed_codes = codes_list[-actual_qty_to_remove:]
                                # Keep the remaining barcodes
                                produit.codes_barres = codes_list[:-actual_qty_to_remove]
                                deleted_barcodes.extend(removed_codes)
                                
                                # If we need to remove more than available barcodes
                                if qty_to_remove > actual_qty_to_remove:
                                    extra_removal = qty_to_remove - actual_qty_to_remove
                                    print(f"Note: Removed {actual_qty_to_remove} barcodes but needed to remove {qty_to_remove} for product {produit.nom}. {extra_removal} items had no barcodes.")
                        else:
                            print(f"Warning: codes_barres is not a list for product {produit.nom}, type: {type(produit.codes_barres)}")
                            produit.codes_barres = []
                    
                    # Update purchase price if provided
                    if prix_achat > 0 and produit.prix_achat != prix_achat:
                        produit.prix_achat = prix_achat
                        print(f"Updated purchase price for {produit.nom} to {prix_achat}")

                # 🟢 POSITIVE QUANTITY → ADD STOCK (Normal purchase)
                elif qty > 0:
                    # Update product quantity
                    current_stock = produit.quantite or 0
                    produit.quantite = current_stock + qty

                    # Update purchase price if different
                    if prix_achat > 0 and produit.prix_achat != prix_achat:
                        produit.prix_achat = prix_achat
                        print(f"Updated purchase price for {produit.nom} to {prix_achat}")

                    # Add generated barcodes if provided in the line
                    # Note: You might need to generate barcodes here or receive them from frontend
                    if hasattr(ligne, 'nouveaux_codes_barres') and ligne.nouveaux_codes_barres:
                        if not hasattr(produit, 'codes_barres') or not produit.codes_barres:
                            produit.codes_barres = []
                        elif not isinstance(produit.codes_barres, list):
                            produit.codes_barres = []
                        
                        produit.codes_barres.extend(ligne.nouveaux_codes_barres)

                # If qty == 0, do nothing (just update price if needed)
                elif qty == 0 and prix_achat > 0 and produit.prix_achat != prix_achat:
                    produit.prix_achat = prix_achat
                    print(f"Updated purchase price for {produit.nom} to {prix_achat} (zero quantity)")

                # Save the product
                produit.save()

            # Check if there were any validation errors
            if validation_errors:
                # Rollback the transaction
                transaction.set_rollback(True)
                return Response({
                    'error': 'Erreurs de validation',
                    'details': validation_errors
                }, status=status.HTTP_400_BAD_REQUEST)

            headers = self.get_success_headers(serializer.data)
            
            # Prepare response data
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
            
            # Add warning if not all barcodes could be removed
            total_negative_qty = sum(abs(l.quantite) for l in achat_groupe.achats.all() if l.quantite < 0)
            if len(deleted_barcodes) < total_negative_qty:
                response_data['warning'] = f"Seulement {len(deleted_barcodes)} codes-barres supprimés sur {total_negative_qty} quantités négatives. Certains produits n'avaient pas de codes-barres."

            return Response(
                response_data,
                status=status.HTTP_201_CREATED,
                headers=headers
            )

        except ValueError as e:
            transaction.set_rollback(True)
            return Response({
                'error': 'Erreur de traitement',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
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
            # Reverse stock changes before deleting
            for ligne in instance.achats.all():
                produit = ligne.produit
                qty = ligne.quantite or 0
                
                if qty > 0:
                    # Was an addition, now subtract
                    produit.quantite = max(0, (produit.quantite or 0) - qty)
                elif qty < 0:
                    # Was a removal, now add back
                    produit.quantite = (produit.quantite or 0) + abs(qty)
                    # Note: We can't recover deleted barcodes
                
                produit.save()
            
            # Now delete the instance
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
