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

class AchatGroupeListCreateAPIView(generics.ListCreateAPIView):
    queryset = AchatGroupe.objects.all().order_by('-date')
    serializer_class = AchatGroupeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['fournisseur', 'date']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'nombre_achats': queryset.count(),
            'somme_totale': "%.2f" % sum(ag.total for ag in queryset),
            'somme_payee': "%.2f" % sum(ag.somme_payee for ag in queryset),
            'somme_restante': "%.2f" % sum(ag.somme_restante for ag in queryset),
            'achats_groupes': serializer.data
        }, status=status.HTTP_200_OK)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        deleted_barcodes = []

        achat_groupe = serializer.save()

        for ligne in achat_groupe.achats.all():
            produit = ligne.produit
            qty = ligne.quantite or 0

            # 🔴 NEGATIVE QUANTITY → REMOVE STOCK
            if qty < 0:
                qty_to_remove = abs(qty)

                if produit.quantite < qty_to_remove:
                    raise ValueError("Stock insuffisant")

                produit.quantite -= qty_to_remove

                # 🔻 Remove barcodes (LIFO)
                if produit.codes_barres:
                    removed = produit.codes_barres[-qty_to_remove:]
                    produit.codes_barres = produit.codes_barres[:-qty_to_remove]
                    deleted_barcodes.extend(removed)

            # 🟢 POSITIVE QUANTITY → ADD STOCK
            else:
                produit.quantite += qty

                # add generated barcodes if you have them
                if ligne.nouveaux_codes_barres:
                    produit.codes_barres.extend(ligne.nouveaux_codes_barres)

            produit.save()

        headers = self.get_success_headers(serializer.data)

        return Response(
            {
                "success": "Achat enregistré avec succès",
                "achat_groupe_id": achat_groupe.id,
                "deleted_barcodes": deleted_barcodes,
                "deleted_count": len(deleted_barcodes),
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED,
            headers=headers
        )

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
