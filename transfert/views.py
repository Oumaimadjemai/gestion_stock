from produits.models import Produit
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Transfert
from .serializers import TransfertSerializer
from rest_framework.filters import SearchFilter
from django.db.models import Q


from .filters import TransfertFilter


class TransfertListView(generics.ListCreateAPIView):
    queryset = Transfert.objects.select_related(
        'produit', 'magasin_source', 'magasin_destination', 'utilisateur'
    )
    serializer_class = TransfertSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]

    filterset_class = TransfertFilter  # ⬅️ Ajout ici
    search_fields = [
        'produit__nom',
        'codes_barres_transferes',
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        search_term = self.request.query_params.get('search', None)

        if search_term:
            queryset = queryset.filter(
                Q(produit__nom__icontains=search_term) |
                Q(codes_barres_transferes__icontains=search_term)
            )
        return queryset

class TransfertDetailView(generics.RetrieveDestroyAPIView):
    queryset = Transfert.objects.select_related(
        'produit', 'magasin_source', 'magasin_destination', 'utilisateur'
    )
    serializer_class = TransfertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
     instance = self.get_object()

     if instance.produit_supprime:
        return Response(
            {"detail": "Impossible d'annuler le transfert : le produit a été supprimé."},
            status=status.HTTP_400_BAD_REQUEST
        )

     produit_source = instance.produit
     produit_source.quantite += instance.quantite
     if instance.codes_barres_transferes:
        produit_source.codes_barres += instance.codes_barres_transferes
     produit_source.est_supprime = False
     produit_source.save()

    # Gérer suppression du produit destination
     try:
        produit_dest = Produit.objects.get(
            nom=produit_source.nom,
            marque=produit_source.marque,
            magasin=instance.magasin_destination
        )
        produit_dest.quantite -= instance.quantite
        if instance.codes_barres_transferes:
            produit_dest.codes_barres = [
                code for code in produit_dest.codes_barres
                if code not in instance.codes_barres_transferes
            ]
        if produit_dest.quantite <= 0:
            produit_dest.est_supprime = True
        produit_dest.save()
     except Produit.DoesNotExist:
        pass

     return super().destroy(request, *args, **kwargs)
