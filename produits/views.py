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
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache
# class ProduitListCreateAPIView(generics.ListCreateAPIView):
#     queryset = Produit.objects.filter(est_supprime=False)
#     serializer_class = ProduitSerializer
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter]
#     filterset_fields = ['magasin', 'famille']
#     search_fields = ['nom', 'marque', 'codes_barres', 'reference', 'famille']

#     def get_queryset(self):
#         queryset = super().get_queryset()
#         magasin = self.request.query_params.get('magasin')
#         famille = self.request.query_params.get('famille')
#         if magasin and magasin != "null":
#             queryset = queryset.filter(magasin_id=int(magasin))
#         if famille:
#             queryset = queryset.filter(famille=famille)
#         return queryset.order_by('-date_creation')

    
#     def list(self, request, *args, **kwargs):
#         queryset = self.filter_queryset(self.get_queryset())

#         # Calcul des totaux (toujours sur l’ensemble du queryset filtré)
#         total_quantite = queryset.aggregate(Sum('quantite'))['quantite__sum'] or 0
#         total_valeur = queryset.aggregate(
#             total=Sum(
#                 ExpressionWrapper(F('quantite') * F('prix_achat'), output_field=FloatField())
#             )
#         )['total'] or 0
#         total_capital = queryset.aggregate(
#             total=Sum(
#                 ExpressionWrapper(F('quantite') * F('prix_vente_3'), output_field=FloatField())
#             )
#         )['total'] or 0

#         page = self.paginate_queryset(queryset)
#         if page is not None:
#             serializer = self.get_serializer(page, many=True)
#             response = self.get_paginated_response(serializer.data)
#             # injecter totaux dans la réponse paginée
#             response.data['totaux'] = {
#                 'quantite': total_quantite,
#                 'valeur_des_produits': total_valeur,
#                 'capital': total_capital
#             }
#             return response

#         serializer = self.get_serializer(queryset, many=True)
#         return Response({
#             'produits': serializer.data,
#             'totaux': {
#                 'quantite': total_quantite,
#                 'valeur_des_produits': total_valeur,
#                 'capital': total_capital
#             }
#         })

# class ProduitRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
#     queryset = Produit.objects.all()
#     serializer_class = ProduitSerializer
#     def perform_update(self, serializer):
#         instance = serializer.save()
#         cache.clear()  # ⚡ vide le cache après update
#         return instance

#     def perform_destroy(self, instance):
#        if instance.image:
#         try:
#             # Delete the image from Cloudinary
#             instance.image.delete()
#         except Exception as e:
#             # Log it but don't break deletion
#             print(f"Error deleting Cloudinary image: {e}")

#     # Mark as deleted in DB
#        instance.delete()
#        cache.clear()
from rest_framework import generics, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from .models import Produit
from .serializers import ProduitSerializer
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.cache import cache
from django.db import transaction
from parametres.models import Magasin


# produits/views.py - Updated list method

from django.db.models import Q  # Add this import at the top

class ProduitListCreateAPIView(generics.ListCreateAPIView):
    queryset = Produit.objects.filter(est_supprime=False)
    serializer_class = ProduitSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['famille']
    search_fields = ['nom', 'marque', 'codes_barres', 'reference', 'famille']

    def get_queryset(self):
        queryset = super().get_queryset()
        magasin = self.request.query_params.get('magasin')
        famille = self.request.query_params.get('famille')
        
        if magasin and magasin != "null":
            queryset = queryset.filter(
                Q(magasin_principal_id=int(magasin)) | 
                Q(magasins__contains=[{'id': int(magasin)}])
            ).distinct()
        
        if famille:
            queryset = queryset.filter(famille=famille)
            
        return queryset.order_by('-date_creation')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Calculate totals for filtered products
        total_quantite = 0
        total_valeur = 0
        total_capital = 0
        
        for produit in queryset:
            # CORRECTION: Parcourir tous les magasins une seule fois
            for mag in produit.magasins:
                qty = len(mag.get('codes_barres', []))
                total_quantite += qty
                total_valeur += qty * (produit.prix_achat or 0)
                total_capital += qty * (produit.prix_vente_3 or 0)

        # Calculate total quantity for ALL products (without any filters)
        all_products = Produit.objects.filter(est_supprime=False)
        total_quantite_all = 0
        for produit in all_products:
            for mag in produit.magasins or []:
                total_quantite_all += len(mag.get('codes_barres', []))

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['totaux'] = {
                'total_quantite': total_quantite,
                'total_valeur': total_valeur,
                'total_capital': total_capital,
                'total_quantite_all_products': total_quantite_all
            }
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'totaux': {
                'total_quantite': total_quantite,
                'total_valeur': total_valeur,
                'total_capital': total_capital,
                'total_quantite_all_products': total_quantite_all
            }
        })

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        magasin_principal_id = request.data.get('magasin_principal')
        
        magasin_principal = None
        if magasin_principal_id:
            try:
                magasin_principal = Magasin.objects.get(id=magasin_principal_id)
            except Magasin.DoesNotExist:
                pass
        
        data = request.data.copy()
        data['magasin_principal'] = magasin_principal_id
        data.pop('quantite', None)
        data.pop('magasin', None)
        data.pop('magasin_principal_quantite', None)
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        produit = serializer.save()
        
        quantite_initiale = request.data.get('quantite', 0)
        if quantite_initiale > 0 and magasin_principal:
            nouveaux_codes = generer_codes_barres_uniques([], quantite_initiale)
            
            produit.magasins.append({
                'id': magasin_principal.id,
                'nom': magasin_principal.nom,
                'adresse': getattr(magasin_principal, 'adresse', ''),
                'codes_barres': nouveaux_codes
            })
            produit._sync_quantite()
            produit.save()
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
class ProduitRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Produit.objects.all()
    serializer_class = ProduitSerializer
    
    def perform_update(self, serializer):
        instance = serializer.save()
        cache.clear()
        return instance

    def perform_destroy(self, instance):
        if instance.image:
            try:
                instance.image.delete()
            except Exception as e:
                print(f"Error deleting Cloudinary image: {e}")
        instance.delete()
        cache.clear()


class ProduitIncrementMagasinQuantityView(APIView):
    """Increment quantity for a specific magasin in a product (for purchases)"""
    permission_classes = [IsAuthenticated]

    def post(self, request, produit_id):
        magasin_id = request.data.get('magasin_id')
        magasin_nom = request.data.get('magasin_nom')
        magasin_adresse = request.data.get('magasin_adresse', '')
        quantite = request.data.get('quantite', 0)
        
        if not magasin_id or not magasin_nom or quantite <= 0:
            return Response(
                {"error": "magasin_id, magasin_nom, and positive quantite are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            produit = Produit.objects.get(id=produit_id)
            produit.increment_quantite_par_magasin(
                magasin_id=int(magasin_id),
                magasin_nom=magasin_nom,
                quantite=int(quantite),
                magasin_adresse=magasin_adresse
            )
            
            return Response({
                'id': produit.id,
                'magasin_principal': {
                    'id': produit.magasin_principal.id if produit.magasin_principal else None,
                    'quantite': produit.magasin_principal_quantite
                },
                'magasins': produit.magasins,
                'quantite_totale': produit.quantite_totale
            })
            
        except Produit.DoesNotExist:
            return Response(
                {"error": "Product not found"},
                status=status.HTTP_404_NOT_FOUND
            )


class ProduitDecrementMagasinQuantityView(APIView):
    """Decrement quantity for a specific magasin in a product (for sales)"""
    permission_classes = [IsAuthenticated]

    def post(self, request, produit_id):
        magasin_id = request.data.get('magasin_id')
        quantite = request.data.get('quantite', 0)
        
        if not magasin_id or quantite <= 0:
            return Response(
                {"error": "magasin_id and positive quantite are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            produit = Produit.objects.get(id=produit_id)
            produit.decrement_quantite_par_magasin(
                magasin_id=int(magasin_id),
                quantite=int(quantite)
            )
            
            return Response({
                'id': produit.id,
                'magasin_principal': {
                    'id': produit.magasin_principal.id if produit.magasin_principal else None,
                    'quantite': produit.magasin_principal_quantite
                },
                'magasins': produit.magasins,
                'quantite_totale': produit.quantite_totale
            })
            
        except Produit.DoesNotExist:
            return Response(
                {"error": "Product not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


# Keep other views (ProduitComparaisonView, ResetQuantiteCodesBarresView, etc.)
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

# produits/views.py - Fixed ProduitComparaisonView

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import Produit
from parametres.models import Magasin
from collections import defaultdict


class ProduitComparaisonView(APIView):
    """
    Retourne la liste des produits regroupés par (nom, référence, famille),
    avec la quantité dans chaque magasin (0 si non présent).
    Permet de filtrer par reference, famille et rechercher par nom.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Récupération des paramètres de filtrage
        reference = request.query_params.get("reference")
        famille = request.query_params.get("famille")
        search = request.query_params.get("search")

        # Récupérer tous les magasins
        magasins = list(Magasin.objects.all().values('id', 'nom'))
        magasin_dict = {m['id']: m['nom'] for m in magasins}

        # Base queryset - exclure les produits supprimés
        produits = Produit.objects.filter(est_supprime=False)

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
            key = (produit.nom, produit.reference or "", produit.famille)
            
            if key not in comparaison:
                # Initialiser les quantités pour tous les magasins à 0
                quantites_par_magasin = {m['id']: 0 for m in magasins}
                comparaison[key] = {
                    'quantites': quantites_par_magasin,
                    'total_quantite': 0,
                    'prix_achat': produit.prix_achat,
                    'prix_vente_cache': produit.prix_vente_cache
                }
            
            # Ajouter les quantités de ce produit
            if produit.magasins and isinstance(produit.magasins, list):
                for mag in produit.magasins:
                    mag_id = mag.get('id')
                    if mag_id and mag_id in comparaison[key]['quantites']:
                        quantity = len(mag.get('codes_barres', []))
                        comparaison[key]['quantites'][mag_id] += quantity
                        comparaison[key]['total_quantite'] += quantity

        # Formatter le résultat
        result = []
        for (nom, reference, famille), data in comparaison.items():
            # Construire la liste des quantités par magasin
            quantites_list = []
            for mag in magasins:
                mag_id = mag['id']
                quantites_list.append({
                    "magasin_id": mag_id,
                    "magasin": mag['nom'],
                    "quantite": data['quantites'].get(mag_id, 0)
                })
            
            result.append({
                "nom": nom,
                "reference": reference,
                "famille": famille,
                "prix_achat": float(data['prix_achat']) if data['prix_achat'] else 0,
                "prix_vente_cache": float(data['prix_vente_cache']) if data['prix_vente_cache'] else 0,
                "total_quantite": data['total_quantite'],
                "quantites": quantites_list
            })
        
        # Trier par nom
        result.sort(key=lambda x: x['nom'])
        
        return Response({
            "produits": result,
            "total_produits": len(result),
            "magasins": list(magasin_dict.values())
        })


class ProduitDetailComparaisonView(APIView):
    """
    GET /prod/comparaison/detail/<product_id>/
    Retourne les détails complets d'un produit avec ses quantités par magasin
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, product_id):
        try:
            produit = Produit.objects.get(id=product_id, est_supprime=False)
        except Produit.DoesNotExist:
            return Response({"error": "Produit non trouvé"}, status=404)
        
        # Récupérer tous les magasins
        magasins = list(Magasin.objects.all().values('id', 'nom'))
        
        # Initialiser les quantités
        quantites_par_magasin = {m['id']: 0 for m in magasins}
        
        # Remplir avec les quantités réelles
        if produit.magasins and isinstance(produit.magasins, list):
            for mag in produit.magasins:
                mag_id = mag.get('id')
                if mag_id and mag_id in quantites_par_magasin:
                    quantites_par_magasin[mag_id] = len(mag.get('codes_barres', []))
        
        # Construire la réponse
        quantites_list = []
        for mag in magasins:
            mag_id = mag['id']
            quantites_list.append({
                "magasin_id": mag_id,
                "magasin": mag['nom'],
                "quantite": quantites_par_magasin.get(mag_id, 0)
            })
        
        return Response({
            "id": produit.id,
            "nom": produit.nom,
            "reference": produit.reference,
            "famille": produit.famille,
            "marque": produit.marque,
            "prix_achat": float(produit.prix_achat) if produit.prix_achat else 0,
            "prix_vente_cache": float(produit.prix_vente_cache) if produit.prix_vente_cache else 0,
            "prix_vente_3": float(produit.prix_vente_3) if produit.prix_vente_3 else 0,
            "prix_vente_5": float(produit.prix_vente_5) if produit.prix_vente_5 else 0,
            "prix_vente_6": float(produit.prix_vente_6) if produit.prix_vente_6 else 0,
            "prix_vente_8": float(produit.prix_vente_8) if produit.prix_vente_8 else 0,
            "prix_vente_9": float(produit.prix_vente_9) if produit.prix_vente_9 else 0,
            "prix_vente_10": float(produit.prix_vente_10) if produit.prix_vente_10 else 0,
            "prix_vente_12": float(produit.prix_vente_12) if produit.prix_vente_12 else 0,
            "prix_vente_15": float(produit.prix_vente_15) if produit.prix_vente_15 else 0,
            "total_quantite": sum(quantites_par_magasin.values()),
            "quantites_par_magasin": quantites_list,
            "magasins_details": produit.tous_les_magasins if produit.magasins else []
        })


class ProduitMagasinStockView(APIView):
    """
    GET /prod/comparaison/magasin/<magasin_id>/
    Retourne tous les produits avec leur quantité dans un magasin spécifique
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, magasin_id):
        try:
            magasin = Magasin.objects.get(id=magasin_id)
        except Magasin.DoesNotExist:
            return Response({"error": "Magasin non trouvé"}, status=404)
        
        produits = Produit.objects.filter(est_supprime=False)
        
        result = []
        for produit in produits:
            quantite = 0
            codes_barres = []
            if produit.magasins and isinstance(produit.magasins, list):
                for mag in produit.magasins:
                    if mag.get('id') == magasin_id:
                        codes_barres = mag.get('codes_barres', [])
                        quantite = len(codes_barres)
                        break
            
            result.append({
                "id": produit.id,
                "nom": produit.nom,
                "reference": produit.reference,
                "famille": produit.famille,
                "quantite": quantite,
                "codes_barres": codes_barres[:5] if codes_barres else [],  # First 5 barcodes
                "prix_achat": float(produit.prix_achat) if produit.prix_achat else 0,
                "prix_vente_cache": float(produit.prix_vente_cache) if produit.prix_vente_cache else 0
            })
        
        # Filtrer les produits avec quantité > 0 en premier
        result.sort(key=lambda x: (x['quantite'] == 0, -x['quantite']))
        
        return Response({
            "magasin": {
                "id": magasin.id,
                "nom": magasin.nom,
                "adresse": magasin.adresse
            },
            "produits": result,
            "total_produits": len([p for p in result if p['quantite'] > 0]),
            "total_quantite": sum(p['quantite'] for p in result)
        })

# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum, F, ExpressionWrapper, FloatField
from django.db.models.functions import Coalesce
from .models import Produit

class FamillesProduitView(APIView):
    def get(self, request):
        # Get all products and calculate totals per famille
        produits = Produit.objects.filter(est_supprime=False)
        
        # Group by famille and calculate totals
        familles_dict = {}
        
        for produit in produits:
            famille = produit.famille or "Sans famille"
            reference = produit.reference
            
            # Calculate total quantity for this product across all magasins
            quantite_totale = produit.magasin_principal_quantite or 0
            for mag in produit.magasins:
                quantite_totale += mag.get('quantite', 0)
            
            # Calculate total value (quantity * prix_achat)
            valeur_totale = quantite_totale * (produit.prix_achat or 0)
            
            # Aggregate by famille and reference
            key = (famille, reference)
            if key not in familles_dict:
                familles_dict[key] = {
                    'famille': famille,
                    'reference': reference,
                    'total_prix_achat': 0,
                    'total_quantite': 0,
                    'total_valeur': 0
                }
            
            familles_dict[key]['total_prix_achat'] += produit.prix_achat or 0
            familles_dict[key]['total_quantite'] += quantite_totale
            familles_dict[key]['total_valeur'] += valeur_totale
        
        # Convert to list
        familles_list = list(familles_dict.values())
        
        return Response({"familles": familles_list})
# produits/views.py
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
import pandas as pd
from .models import Produit

@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def importer_prix_produits(request):
    """
    Upload Excel file to update products' prix_achat & prix_vente (3,5,8,10)
    and calculate taux de bénéfice automatically.
    Updates all products that have the same name.
    """
    fichier = request.FILES.get("file")
    if not fichier:
        return Response({"error": "Aucun fichier fourni"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        df = pd.read_excel(fichier)
    except Exception as e:
        return Response({"error": f"Erreur lecture fichier: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    updated, not_found = [], []

    for _, row in df.iterrows():
        nom = str(row.get("الاسم")).strip()
        if not nom:
            continue

        produits = Produit.objects.filter(nom=nom)
        if not produits.exists():
            not_found.append(nom)
            continue

        for produit in produits:
            # Update prices
            prix_achat = row.get("سعر الشراء") or produit.prix_achat
            produit.prix_achat = prix_achat

            prix_vente_3 = row.get("سعر 3") or produit.prix_vente_3
            prix_vente_5 = row.get("سعر 5") or produit.prix_vente_5
            prix_vente_8 = row.get("سعر 8") or produit.prix_vente_8
            prix_vente_10 = row.get("سعر 10") or produit.prix_vente_10

            produit.prix_vente_3 = prix_vente_3
            produit.prix_vente_5 = prix_vente_5
            produit.prix_vente_8 = prix_vente_8
            produit.prix_vente_10 = prix_vente_10

            # Calculate profit rates
            def calc_taux(prix_vente, prix_achat):
                if prix_achat and prix_achat > 0 and prix_vente:
                    return round(((prix_vente - prix_achat) / prix_achat) * 100, 2)
                return None

            produit.taux_benefice_3 = calc_taux(prix_vente_3, prix_achat)
            produit.taux_benefice_5 = calc_taux(prix_vente_5, prix_achat)
            produit.taux_benefice_8 = calc_taux(prix_vente_8, prix_achat)
            produit.taux_benefice_10 = calc_taux(prix_vente_10, prix_achat)

            produit.save(update_fields=[
                "prix_achat", "prix_vente_3", "prix_vente_5", "prix_vente_8", "prix_vente_10",
                "taux_benefice_3", "taux_benefice_5", "taux_benefice_8", "taux_benefice_10"
            ])
            updated.append(produit.nom)

    return Response({
        "updated": updated,
        "not_found": not_found,
        "message": f"{len(updated)} produits mis à jour, {len(not_found)} introuvables"
    }, status=status.HTTP_200_OK)
# produits/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Produit

class ResetQuantiteCodesBarresView(APIView):
    """
    Endpoint to reset all product quantities to 0 and remove all barcodes.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Reset quantity and codes_barres for all products
        updated_count = Produit.objects.update(quantite=0, codes_barres=[])
        
        return Response(
            {"message": f"Quantities reset to 0 and barcodes deleted for {updated_count} products."},
            status=status.HTTP_200_OK
        )

# produits/views.py - Add this new view

import pandas as pd
import io
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Produit
from parametres.models import Magasin
import cloudinary.uploader
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class ProduitImportExcelAPIView(APIView):
    """
    POST /prod/produits/import-excel/
    Upload an Excel file with product data to update magasins, prices, and benefits
    
    Expected Excel columns:
    - reference (required): Product reference
    - nom (required): Product name
    - famille (optional): Product family
    - magasin_nom (optional): Magasin name
    - quantite (optional): Quantity to add to magasin
    - prix_achat (optional): Purchase price
    - prix_vente_cache (optional): Cash selling price
    - prix_vente_3, prix_vente_5, prix_vente_6, prix_vente_8, prix_vente_9, prix_vente_10, prix_vente_12, prix_vente_15 (optional)
    - taux_benefice_cache, taux_benefice_3, taux_benefice_5, taux_benefice_6, taux_benefice_8, taux_benefice_9, taux_benefice_10, taux_benefice_12, taux_benefice_15 (optional)
    """
    permission_classes = [IsAuthenticated]
    
    # Mapping of Excel columns to model fields
    FIELD_MAPPING = {
        'reference': 'reference',
        'nom': 'nom',
        'famille': 'famille',
        'marque': 'marque',
        'prix_achat': 'prix_achat',
        'prix_vente_cache': 'prix_vente_cache',
        'prix_vente_3': 'prix_vente_3',
        'prix_vente_5': 'prix_vente_5',
        'prix_vente_6': 'prix_vente_6',
        'prix_vente_8': 'prix_vente_8',
        'prix_vente_9': 'prix_vente_9',
        'prix_vente_10': 'prix_vente_10',
        'prix_vente_12': 'prix_vente_12',
        'prix_vente_15': 'prix_vente_15',
        'taux_benefice_cache': 'taux_benefice_cache',
        'taux_benefice_3': 'taux_benefice_3',
        'taux_benefice_5': 'taux_benefice_5',
        'taux_benefice_6': 'taux_benefice_6',
        'taux_benefice_8': 'taux_benefice_8',
        'taux_benefice_9': 'taux_benefice_9',
        'taux_benefice_10': 'taux_benefice_10',
        'taux_benefice_12': 'taux_benefice_12',
        'taux_benefice_15': 'taux_benefice_15',
    }
    
    def parse_decimal(self, value):
        """Parse decimal value from Excel"""
        if value is None or value == '' or pd.isna(value):
            return None
        try:
            return Decimal(str(value))
        except:
            return None
    
    def parse_int(self, value):
        """Parse integer value from Excel"""
        if value is None or value == '' or pd.isna(value):
            return None
        try:
            return int(float(value))
        except:
            return None
    
    def parse_float(self, value):
        """Parse float value from Excel"""
        if value is None or value == '' or pd.isna(value):
            return None
        try:
            return float(value)
        except:
            return None
    
    def update_product_magasin(self, product, magasin_nom, quantite):
        """Update product's magasin stock"""
        if not magasin_nom or not quantite:
            return
        
        try:
            magasin = Magasin.objects.get(nom__iexact=magasin_nom)
        except Magasin.DoesNotExist:
            # Try to create magasin if it doesn't exist
            try:
                magasin = Magasin.objects.create(nom=magasin_nom, adresse="")
                logger.info(f"Created new magasin: {magasin_nom}")
            except Exception as e:
                logger.error(f"Failed to create magasin {magasin_nom}: {e}")
                return
        
        quantite_int = int(quantite)
        
        # Check if product already has this magasin
        magasin_found = False
        if product.magasins and isinstance(product.magasins, list):
            for mag in product.magasins:
                if mag.get('id') == magasin.id:
                    mag['codes_barres'] = mag.get('codes_barres', [])[:quantite_int]
                    magasin_found = True
                    break
        
        if not magasin_found and quantite_int > 0:
            # Generate barcodes for the quantity
            from .models import generer_codes_barres_uniques
            nouveaux_codes = generer_codes_barres_uniques(product.codes_barres or [], quantite_int)
            
            product.magasins.append({
                'id': magasin.id,
                'nom': magasin.nom,
                'adresse': getattr(magasin, 'adresse', ''),
                'codes_barres': nouveaux_codes
            })
        
        product._sync_quantite()
        product.save()
    
    def process_row(self, row, row_index):
        """Process a single row from Excel"""
        errors = []
        warnings = []
        
        # Get required fields
        reference = row.get('reference')
        nom = row.get('nom')
        
        if not reference or not nom:
            errors.append(f"Row {row_index}: Missing required fields 'reference' or 'nom'")
            return None, errors, warnings
        
        # Find existing product or create new one
        try:
            product = Produit.objects.get(reference=reference)
            warnings.append(f"Row {row_index}: Updating existing product: {reference}")
        except Produit.DoesNotExist:
            # Create new product
            product = Produit.objects.create(
                reference=reference,
                nom=nom,
                famille=row.get('famille', ''),
                marque=row.get('marque', '')
            )
            warnings.append(f"Row {row_index}: Created new product: {reference}")
        except Exception as e:
            errors.append(f"Row {row_index}: Error finding/creating product: {str(e)}")
            return None, errors, warnings
        
        # Update product fields
        try:
            for excel_col, model_field in self.FIELD_MAPPING.items():
                if excel_col in row and pd.notna(row[excel_col]):
                    value = row[excel_col]
                    
                    if 'prix' in excel_col or 'montant' in excel_col:
                        value = self.parse_decimal(value)
                    elif 'taux' in excel_col:
                        value = self.parse_float(value)
                    
                    if value is not None:
                        setattr(product, model_field, value)
            
            product.save()
            
            # Update magasin stock
            magasin_nom = row.get('magasin_nom')
            quantite = row.get('quantite')
            if magasin_nom and quantite:
                self.update_product_magasin(product, magasin_nom, quantite)
            
            return product, errors, warnings
            
        except Exception as e:
            errors.append(f"Row {row_index}: Error updating product: {str(e)}")
            return None, errors, warnings
    
    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response(
                {"error": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check file extension
        if not file.name.endswith(('.xlsx', '.xls', '.csv')):
            return Response(
                {"error": "File must be Excel (.xlsx, .xls) or CSV (.csv)"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Read Excel file
            df = pd.read_excel(file, engine='openpyxl')
            
            # Or handle CSV
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            
            # Convert column names to lowercase
            df.columns = df.columns.str.lower()
            
            # Validate required columns
            required_columns = ['reference', 'nom']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return Response(
                    {"error": f"Missing required columns: {', '.join(missing_columns)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Process each row
            products_updated = []
            products_created = []
            errors = []
            warnings = []
            
            with transaction.atomic():
                for index, row in df.iterrows():
                    product, row_errors, row_warnings = self.process_row(row.to_dict(), index + 2)
                    
                    if product:
                        if product.id not in [p.id for p in products_updated if p]:
                            if product.date_creation == product.date_modification:
                                products_created.append(product)
                            else:
                                products_updated.append(product)
                    
                    errors.extend(row_errors)
                    warnings.extend(row_warnings)
            
            # Prepare response
            response_data = {
                "success": True,
                "message": f"Import completed. Created: {len(products_created)}, Updated: {len(products_updated)}",
                "products_created": len(products_created),
                "products_updated": len(products_updated),
                "total_rows": len(df),
                "errors": errors[:20],  # Limit errors to 20
                "warnings": warnings[:20]  # Limit warnings to 20
            }
            
            if errors:
                response_data["has_errors"] = True
                response_data["error_count"] = len(errors)
            
            if warnings:
                response_data["has_warnings"] = True
                response_data["warning_count"] = len(warnings)
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception("Error importing Excel file")
            return Response(
                {"error": f"Error processing file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProduitExportExcelAPIView(APIView):
    """
    GET /prod/produits/export-excel/
    Export products to Excel file
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        import pandas as pd
        from io import BytesIO
        from django.http import HttpResponse
        
        # Get all products
        products = Produit.objects.filter(est_supprime=False)
        
        # Prepare data for export
        data = []
        for product in products:
            row = {
                'reference': product.reference,
                'nom': product.nom,
                'famille': product.famille,
                'marque': product.marque,
                'prix_achat': float(product.prix_achat) if product.prix_achat else '',
                'prix_vente_cache': float(product.prix_vente_cache) if product.prix_vente_cache else '',
                'prix_vente_3': float(product.prix_vente_3) if product.prix_vente_3 else '',
                'prix_vente_5': float(product.prix_vente_5) if product.prix_vente_5 else '',
                'prix_vente_6': float(product.prix_vente_6) if product.prix_vente_6 else '',
                'prix_vente_8': float(product.prix_vente_8) if product.prix_vente_8 else '',
                'prix_vente_9': float(product.prix_vente_9) if product.prix_vente_9 else '',
                'prix_vente_10': float(product.prix_vente_10) if product.prix_vente_10 else '',
                'prix_vente_12': float(product.prix_vente_12) if product.prix_vente_12 else '',
                'prix_vente_15': float(product.prix_vente_15) if product.prix_vente_15 else '',
                'taux_benefice_cache': product.taux_benefice_cache if product.taux_benefice_cache else '',
                'taux_benefice_3': product.taux_benefice_3 if product.taux_benefice_3 else '',
                'taux_benefice_5': product.taux_benefice_5 if product.taux_benefice_5 else '',
                'taux_benefice_6': product.taux_benefice_6 if product.taux_benefice_6 else '',
                'taux_benefice_8': product.taux_benefice_8 if product.taux_benefice_8 else '',
                'taux_benefice_9': product.taux_benefice_9 if product.taux_benefice_9 else '',
                'taux_benefice_10': product.taux_benefice_10 if product.taux_benefice_10 else '',
                'taux_benefice_12': product.taux_benefice_12 if product.taux_benefice_12 else '',
                'taux_benefice_15': product.taux_benefice_15 if product.taux_benefice_15 else '',
                'quantite_totale': product.quantite_totale,
            }
            
            # Add magasin quantities
            if product.magasins and isinstance(product.magasins, list):
                for mag in product.magasins:
                    mag_name = mag.get('nom', '')
                    row[f'magasin_{mag_name}'] = len(mag.get('codes_barres', []))
            
            data.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Create Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Products', index=False)
        
        # Prepare response
        output.seek(0)
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="produits_export.xlsx"'
        
        return response