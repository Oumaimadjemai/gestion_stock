from rest_framework import generics, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Produit
from .serializers import ProduitSerializer
from django.http import HttpResponse
from tablib import Dataset
from .resources import ProduitResource

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, F, FloatField, ExpressionWrapper


class ProduitListCreateAPIView(generics.ListCreateAPIView):
    queryset = Produit.objects.filter(est_supprime=False)
    serializer_class = ProduitSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['magasin', 'famille']
    search_fields = ['nom', 'marque', 'codes_barres', 'reference', 'famille']

    def get_queryset(self):
        queryset = super().get_queryset()
        magasin = self.request.query_params.get('magasin')
        famille = self.request.query_params.get('famille')
        if magasin:
            queryset = queryset.filter(magasin_id=magasin)
        if famille:
            queryset = queryset.filter(famille=famille)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        # Calcul des totaux
        total_quantite = queryset.aggregate(Sum('quantite'))['quantite__sum'] or 0

        total_valeur = queryset.aggregate(
            total=Sum(
                ExpressionWrapper(F('quantite') * F('prix_achat'), output_field=FloatField())
            )
        )['total'] or 0

        total_capital = queryset.aggregate(
            total=Sum(
                ExpressionWrapper(F('quantite') * F('prix_vente_3'), output_field=FloatField())
            )
        )['total'] or 0

        return Response({
            'produits': serializer.data,
            'totaux': {
                'quantite': total_quantite,
                'valeur_des_produits': total_valeur,
                'capital': total_capital
            }
        })
class ProduitRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Produit.objects.all()
    serializer_class = ProduitSerializer

    def perform_destroy(self, instance):
       if instance.image:
        try:
            # Delete the image from Cloudinary
            instance.image.delete()
        except Exception as e:
            # Log it but don't break deletion
            print(f"Error deleting Cloudinary image: {e}")

    # Mark as deleted in DB
       instance.est_supprime = True
       instance.save()


# class ExportProduitExcelView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         produit_resource = ProduitResource()
#         dataset = produit_resource.export()
#         response = HttpResponse(dataset.xlsx, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
#         response['Content-Disposition'] = 'attachment; filename="produits.xlsx"'
#         return response
from import_export import resources
from import_export.formats.base_formats import XLSX
from django.http import HttpResponse
from .models import Produit
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

class ProduitResource(resources.ModelResource):
    class Meta:
        model = Produit
        # Export all fields
        fields = (
            'id',
            'reference',
            'nom',
            'famille',
            'magasin',  # this will export the FK id
            'marque',
            'codes_barres',
            'prix_achat',
            'prix_vente_cache',
            'prix_vente_3',
            'prix_vente_5',
            'prix_vente_6',
            'prix_vente_8',
            'prix_vente_9',
            'prix_vente_10',
            'prix_vente_12',
            'prix_vente_15',
            'quantite',
            'taux_benefice_cache',
            'taux_benefice_3',
            'taux_benefice_5',
            'taux_benefice_6',
            'taux_benefice_8',
            'taux_benefice_9',
            'taux_benefice_10',
            'taux_benefice_12',
            'taux_benefice_15',
            'date_creation',
            'date_modification',
            'est_supprime',
        )

class ExportProduitExcelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        produit_resource = ProduitResource()
        dataset = produit_resource.export()  # returns tablib.Dataset

        xlsx_format = XLSX()
        data = xlsx_format.export_data(dataset)  # returns bytes

        response = HttpResponse(
            data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="produits.xlsx"'
        return response

  
class ImportProduitExcelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        fichier = request.FILES.get('file')
        if not fichier:
            return HttpResponse({"detail": "Aucun fichier fourni."}, status=400)

        data = fichier.read()
        dataset = Dataset().load(data, format='xlsx')
        produit_resource = ProduitResource()

        result = produit_resource.import_data(dataset, dry_run=True)
        if result.has_errors():
            return HttpResponse({"detail": "Erreur d'importation", "errors": str(result.row_errors())}, status=400)

        produit_resource.import_data(dataset, dry_run=False)
        return HttpResponse({"detail": "Importation réussie."})




from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import F
from produits.models import Produit
from parametres.models import Magasin

from rest_framework.views import APIView
from rest_framework.response import Response
from produits.models import Produit
from parametres.models import Magasin

class ProduitComparaisonView(APIView):
    """
    Retourne la liste des produits regroupés par (nom, référence, famille),
    avec la quantité dans chaque magasin (0 si non présent).
    Permet de filtrer par reference, famille et rechercher par nom.
    """

    def get(self, request):
        # Récupération des paramètres de filtrage
        reference = request.query_params.get("reference")
        famille = request.query_params.get("famille")
        search = request.query_params.get("search")

        # Récupérer tous les magasins
        magasins = list(Magasin.objects.all())

        # Base queryset
        produits = Produit.objects.all()

        # Appliquer filtres
        if reference:
            produits = produits.filter(reference__icontains=reference)
        if famille:
            produits = produits.filter(famille__icontains=famille)
        if search:
            produits = produits.filter(nom__icontains=search)

        # On groupe les produits par clé (nom, référence, famille)
        comparaison = {}
        for produit in produits:
            key = (produit.nom, produit.reference, produit.famille)
            if key not in comparaison:
                comparaison[key] = {m.id: 0 for m in magasins}  # initialiser à 0
            comparaison[key][produit.magasin_id] = produit.quantite

        # Formatter le résultat
        result = []
        for (nom, reference, famille), quantites_par_magasin in comparaison.items():
            result.append({
                "nom": nom,
                "reference": reference,
                "famille": famille,
                "quantites": [
                    {
                        "magasin": m.nom,  # Assure-toi que ton modèle Magasin a un champ nom
                        "quantite": quantites_par_magasin[m.id]
                    } for m in magasins
                ]
            })

        return Response(result)
