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
            instance.image.delete()
        instance.est_supprime = True
        instance.save()

class ExportProduitExcelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        produit_resource = ProduitResource()
        dataset = produit_resource.export()
        response = HttpResponse(dataset.xlsx, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
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

# views.py
# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from .barcode_svg import generate_custom_ean13_svg


# views.py
# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
import os
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg
from django.conf import settings
import win32print
import win32api

class PrintBarcodeServerView(APIView):
    def post(self, request):
        svg_content = request.data.get("svg")
        code = request.data.get("code")

        if not svg_content or not code:
            return Response({"error": "SVG and code required"}, status=400)

        # Save SVG
        barcodes_dir = os.path.join(settings.MEDIA_ROOT, "barcodes")
        os.makedirs(barcodes_dir, exist_ok=True)
        svg_path = os.path.join(barcodes_dir, f"{code}.svg")
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

        # Convert SVG → PDF
        pdf_path = svg_path.replace(".svg", ".pdf")
        drawing = svg2rlg(svg_path)
        renderPDF.drawToFile(drawing, pdf_path)

        # --- Windows auto-print ---
        printer_name = win32print.GetDefaultPrinter()
        try:
            win32api.ShellExecute(
                0,
                "print",
                pdf_path,
                None,
                ".",
                0
            )
            return Response({"message": f"Barcode sent to printer {printer_name}", "pdf": pdf_path})
        except Exception as e:
            return Response({"error": str(e)}, status=500)


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
