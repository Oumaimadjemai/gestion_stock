
from docx import Document
from .models import *
from .serializers import *
from django.db.models import Sum,Count,Value, DecimalField
from rest_framework import generics, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from .filters import *
from django.db.models.functions import Coalesce

from django.db.models import Sum, Count, Value, DecimalField, IntegerField, Q
from django.db.models.functions import Coalesce
from rest_framework.response import Response
from rest_framework import generics, filters
from django_filters.rest_framework import DjangoFilterBackend

from .models import VenteFacilite
from .serializers import VenteFaciliteSerializer
from .filters import VenteFaciliteFilter  # if you already have it
from rest_framework.decorators import action



from django.db.models import Count, Sum, F, DecimalField, IntegerField, Value, Q, Prefetch
from django.db.models.functions import Coalesce
from decimal import Decimal
from rest_framework import generics, filters
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import VenteFacilite, LigneVenteFacilite
from .serializers import VenteFaciliteSerializer
from .filters import VenteFaciliteFilter
from django.core.cache import cache
from django.db import connection
import time


from django.db.models import Count, Sum, F, DecimalField, IntegerField, Value, Q, Prefetch
from django.db.models.functions import Coalesce
from decimal import Decimal
from rest_framework import generics, filters
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import VenteFacilite
from .serializers import VenteFaciliteSerializer
from .filters import VenteFaciliteFilter
from django.core.cache import cache


from django.db.models import Count, Sum
from decimal import Decimal
from rest_framework import generics, filters
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import VenteFacilite
from .serializers import VenteFaciliteListSerializer, VenteFaciliteDetailSerializer
from .filters import VenteFaciliteFilter
from django.db import connection
import time


class VenteFaciliteCreateAPIView(generics.ListCreateAPIView):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = VenteFaciliteFilter

    search_fields = [
        'client__nom_famille_fr',
        'client__prenom_fr',
        'client__nom_famille_ar',
        'client__prenom_ar',
        'client__ccp',
        'client__cle'
    ]

    def get_serializer_class(self):
        """Use minimal serializer for list, full serializer for create"""
        if self.request.method == 'GET':
            return VenteFaciliteMinimalSerializer
        return VenteFaciliteSerializer  # ✅ Use the full serializer for POST

    def get_queryset(self):
        """Get only the fields needed for list view"""
        if self.request.method == 'GET':
            return VenteFacilite.objects.select_related(
                'client', 'utilisateur', 'magasin'
            ).only(
                'id', 'date_creation', 'montant_total', 'montant_verse',
                'montant_restant', 'montant_mensuel', 'nombre_mois',
                'client__id', 'client__nom_famille_ar', 'client__prenom_ar',
                'client__nom_famille_fr', 'client__prenom_fr',
                'utilisateur__id', 'utilisateur__username',
                'magasin__id', 'magasin__nom'
            ).order_by('-id')
        
        return VenteFacilite.objects.all()

    def list(self, request, *args, **kwargs):
        """Optimized list method"""
        import time
        start_time = time.time()
        
        queryset = self.filter_queryset(self.get_queryset())
        
        total_ventes = queryset.count()
        total_montant_total = queryset.aggregate(Sum('montant_total'))['montant_total__sum'] or 0
        total_montant_verse = queryset.aggregate(Sum('montant_verse'))['montant_verse__sum'] or 0
        total_montant_restant = queryset.aggregate(Sum('montant_restant'))['montant_restant__sum'] or 0
        
        page = self.paginate_queryset(queryset)
        
        execution_time = time.time() - start_time
        print(f"✅ Query + Serialization: {execution_time:.2f} seconds")
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = {
                "ventes": serializer.data,
                "total_ventes": total_ventes,
                "total_montant_total": total_montant_total,
                "total_montant_verse": total_montant_verse,
                "total_montant_restant": total_montant_restant,
            }
            return self.get_paginated_response(response_data)
        
        serializer = self.get_serializer(queryset, many=True)
        response_data = {
            "ventes": serializer.data,
            "total_ventes": total_ventes,
            "total_montant_total": total_montant_total,
            "total_montant_verse": total_montant_verse,
            "total_montant_restant": total_montant_restant,
        }
        
        return Response(response_data)
class VenteFaciliteDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Use separate serializer for detail view"""
    queryset = VenteFacilite.objects.all().select_related('client', 'utilisateur', 'magasin')
    serializer_class = VenteFaciliteDetailSerializer
# Optional: Simple stats endpoint (can be removed if not needed)
class VenteFaciliteSimpleStatsAPIView(generics.GenericAPIView):
    """Simple stats endpoint - returns only basic counts"""
    
    def get(self, request):
        """Return simple stats without heavy calculations"""
        
        # Basic counts - very fast
        total_ventes = VenteFacilite.objects.count()
        total_montant = VenteFacilite.objects.aggregate(Sum('montant_total'))['montant_total__sum'] or 0
        
        return Response({
            "total_ventes": total_ventes,
            "total_montant": total_montant,
        })
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from django.utils.timezone import now
from django.db.models import Sum


from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import VenteFacilite, PaiementVente
from .serializers import PaiementVenteSerializer


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.db.models import Sum
from decimal import Decimal
from django.utils.timezone import now
from .models import VenteFacilite, PaiementVente


class VentePaiementAPIView(APIView):
    """
    GET    -> Historique des ventes avec filtres (client, year, month_index, status)
    POST   -> Effectuer un paiement pour une vente
    PATCH  -> Changer le statut d’un paiement existant
    """

    def get(self, request, pk=None):
        client_id = request.query_params.get("client")
        year_filter = request.query_params.get("year")  # ex: 2025
        month_index_filter = request.query_params.get("month")  # 0-based
        status_filter = request.query_params.get("status")  # paid, unpaid, pending

        ventes = VenteFacilite.objects.all()

        if pk:
            ventes = ventes.filter(id=pk)
        elif client_id:
            ventes = ventes.filter(client_id=client_id)

        if not ventes.exists():
            return Response({"error": "Aucune vente trouvée."}, status=status.HTTP_404_NOT_FOUND)

        history = []

        for vente in ventes:
            paiements_qs = vente.paiements.all().order_by("date_paiement")

            # --- Apply filters on paiements ---
            if status_filter:
                paiements_qs = paiements_qs.filter(status=status_filter)
            if year_filter:
                paiements_qs = paiements_qs.filter(date_paiement__year=int(year_filter))
            if month_index_filter:
                paiements_qs = paiements_qs.filter(month_index=int(month_index_filter))

            if not paiements_qs.exists() and (status_filter or month_index_filter or year_filter):
                # Skip ventes that don't match filter
                continue

            mois_status = vente.mois_status or ["pending"] * vente.nombre_mois
            mois_status_filtered = mois_status[:]

            # --- If filtering by status, hide other months ---
            if status_filter:
                mois_status_filtered = [
                    s if s == status_filter else None for s in mois_status
                ]

            # --- If filtering by month index, hide other months ---
            if month_index_filter:
                month_index_filter = int(month_index_filter)
                mois_status_filtered = [
                    s if i == month_index_filter else None
                    for i, s in enumerate(mois_status_filtered)
                ]

            unpaid_count = vente.paiements.filter(status="pending").count()

            history.append({
                "vente_id": vente.id,
                "client_detail": {
                    "id": vente.client.id,
                    "nom_famille_ar": vente.client.nom_famille_ar,
                    "prenom_ar": vente.client.prenom_ar,
                    "nom_famille_fr": vente.client.nom_famille_fr,
                    "prenom_fr": vente.client.prenom_fr,
                    "ccp": vente.client.ccp,
                    "cle": vente.client.cle,
                    "telephones": vente.client.telephones or [],
                },
                "montant_mensuel": float(vente.montant_mensuel),
                "montant_par_mois": vente.montants_par_mois,
                "nombre_mois": vente.nombre_mois,
                "date_debut": vente.date_debut.strftime("%Y-%m-%d"),
                "mois_status": mois_status_filtered,
                "total_verse_effectif": float(vente.montant_paye_effectif),
                "reste_vente": float(vente.montant_restant),
                "reste_global": float(
                    VenteFacilite.objects.filter(client=vente.client)
                    .aggregate(total_restant=Sum('montant_restant'))['total_restant'] or 0
                ),
                "solde_regle": vente.montant_restant <= 0,
                "unpaid_count": unpaid_count,
                "paiements": [
                    {
                        "id": p.id,
                        "montant": float(p.montant),
                        "date_paiement": p.date_paiement.isoformat(),
                        "month_index": p.month_index,
                        "status": p.status
                    }
                    for p in paiements_qs
                ]
            })

        return Response(history, status=status.HTTP_200_OK)


    def patch(self, request, pk=None):
        """
        PATCH /vente/vente/payer/<paiement_id>/
        Body: {"status": "pending" | "paid" | "unpaid"}
        """
        paiement_id = pk
        new_status = request.data.get("status")

        if new_status not in ["pending", "paid", "unpaid"]:
            return Response(
                {"error": "Status invalide. Choisissez 'pending', 'paid' ou 'unpaid'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            paiement = PaiementVente.objects.select_related("vente").get(id=paiement_id)
        except PaiementVente.DoesNotExist:
            return Response({"error": "Paiement introuvable."}, status=status.HTTP_404_NOT_FOUND)

        old_status = paiement.status
        if old_status == new_status:
            return Response(
                {"message": "Aucune modification : le statut est identique."},
                status=status.HTTP_200_OK,
            )

        vente = paiement.vente

        with transaction.atomic():
            montant_change = paiement.montant

            # --- Mettre à jour montants ---
            if old_status == "paid" and new_status in ["pending", "unpaid"]:
                vente.montant_paye_effectif -= montant_change
                vente.montant_restant += montant_change
            elif old_status in ["pending", "unpaid"] and new_status == "paid":
                vente.montant_paye_effectif += montant_change
                vente.montant_restant -= montant_change

            # --- Mettre à jour mois_status ---
            if paiement.month_index is not None:
                mois_status = vente.mois_status or ["pending"] * vente.nombre_mois
                if 0 <= paiement.month_index < len(mois_status):
                    mois_status[paiement.month_index] = new_status
                    vente.mois_status = mois_status

            # --- Sauvegarder paiement ---
            paiement.status = new_status
            paiement.save(update_fields=["status"])

            # --- Vérifier si la vente est réglée ---
            vente.solde_regle = vente.montant_restant <= 0
            vente.save(update_fields=[
                "montant_paye_effectif",
                "montant_restant",
                "mois_status",
                "solde_regle"
            ])

        reste_global = (
            VenteFacilite.objects.filter(client=vente.client)
            .aggregate(total_restant=Sum("montant_restant"))["total_restant"] or 0
        )
        unpaid_count = vente.paiements.filter(status="pending").count()

        return Response({
            "message": f"Paiement #{paiement.id} passé de {old_status} à {new_status}.",
            "vente_id": vente.id,
            "total_verse_effectif": float(vente.montant_paye_effectif),
            "reste_vente": float(vente.montant_restant),
            "reste_global": float(reste_global),
            "solde_regle": vente.solde_regle,
            "unpaid_count": unpaid_count,
        }, status=status.HTTP_200_OK)

    def post(self, request, pk):
        """
        POST /vente/vente/payer/<vente_id>/
        Body: {"montant": 5000, "month": 0-11, "status": "pending|paid|unpaid"}
        """
        try:
            vente = VenteFacilite.objects.get(pk=pk)
        except VenteFacilite.DoesNotExist:
            return Response({"error": "Vente introuvable"}, status=status.HTTP_404_NOT_FOUND)

        montant = Decimal(request.data.get("montant", vente.montant_mensuel))
        calendar_month_index = int(request.data.get("month", 0))  # 0-based
        status_str = request.data.get("status", "pending")

        if vente.montant_restant <= 0:
            return Response({"message": "La dette est déjà réglée."}, status=status.HTTP_400_BAD_REQUEST)

        paiement = min(montant, vente.montant_restant)

        # ✅ Update vente
        vente.montant_restant -= paiement
        vente.montant_paye_effectif += paiement
        vente.last_payment_date = now().date()

        mois_status = vente.mois_status or ["pending"] * vente.nombre_mois
        if 0 <= calendar_month_index < len(mois_status):
            mois_status[calendar_month_index] = status_str

        vente.mois_status = mois_status
        vente.solde_regle = vente.montant_restant <= 0
        vente.save()

        # ✅ Save paiement
        PaiementVente.objects.create(
            vente=vente,
            montant=paiement,
            date_paiement=now(),
            month_index=calendar_month_index,
            status=status_str,
            year=now().year
        )

        return self.get(request, pk)
    
from collections import defaultdict
from decimal import Decimal
from django.utils.timezone import now
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.core.files.storage import default_storage
from ventes.models import Client, VenteFacilite, PaiementVente


from collections import defaultdict
from decimal import Decimal
from django.utils.timezone import now
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage

from ventes.models import Client, VenteFacilite, PaiementVente



import io
from collections import defaultdict
from decimal import Decimal
from django.db import transaction
from django.utils.timezone import now
from django.core.files.storage import default_storage
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ventes.models import Client, VenteFacilite, PaiementVente  # adjust import as needed

from datetime import datetime
from decimal import Decimal
from django.utils.timezone import make_aware
from collections import defaultdict
import io

class ImportPaiementsTxtAPIView(APIView):
    """
    POST /vente/import-paiements-txt/
    Body: { "file": <fichier.txt> }
    
    Format du fichier (positions fixes):
    00-01: Type d'enregistrement
    02-09: CCP (8 caractères)
    10-34: Nom (25 caractères)
    35-48: Montant (14 caractères, format 000000XXXXX.00)
    49-58: Date (10 caractères, format DD/MM/YYYY)
    59-62: Code banque
    63-68: Référence
    """
    
    def validate_line_format(self, line):
        """Validate the line has minimum required length"""
        # Nous avons besoin d'au moins 68 caractères pour toutes les données
        return len(line) >= 68
    
    def extract_fields(self, line):
        """Extract fields from a fixed-width line"""
        # Basé sur l'exemple: 0000189487M.BOUMEDIENE ABDELHADI     00000005700.0023/10/20250021027337011MUBHS062025033
        
        # Extraire avec les positions exactes
        record_type = line[0:2].strip()  # 00-01
        ccp = line[2:10].strip()  # 02-09 (8 chars)
        name = line[10:35].strip()  # 10-34 (25 chars)
        montant_str = line[41:51].strip()  # 35-48 (14 chars)
        date_str = line[51:61].strip()  # 49-58 (10 chars) - DD/MM/YYYY
        bank_code = line[59:63].strip()  # 59-62
        reference = line[63:68].strip()  # 63-67
        
        return {
            'record_type': record_type,
            'ccp': ccp,
            'name': name,
            'montant_str': montant_str,
            'date_str': date_str,
            'bank_code': bank_code,
            'reference': reference
        }
    
    def parse_date(self, date_str):
        """Parse date string DD/MM/YYYY and return datetime object"""
        try:
            date_str = date_str.strip()
            
            # Validation de base
            if len(date_str) != 10:
                raise ValueError(f"Longueur de date invalide: {date_str}")
            
            if date_str[2] != '/' or date_str[5] != '/':
                raise ValueError(f"Format de date invalide: {date_str}")
            
            # Extraire les parties
            day = int(date_str[0:2])
            month = int(date_str[3:5])
            year = int(date_str[6:10])
            
            # Validation des valeurs
            if not (1 <= month <= 12):
                raise ValueError(f"Mois invalide: {month}")
            
            if not (1 <= day <= 31):
                raise ValueError(f"Jour invalide: {day}")
            
            if not (2000 <= year <= 2100):
                raise ValueError(f"Année invalide: {year}")
            
            # Créer l'objet datetime
            date_obj = datetime(year, month, day)
            
            # Rendre aware pour Django
            aware_date = make_aware(date_obj)
            
            return {
                'datetime': aware_date,
                'month_index': month - 1,  # 0-based pour month_index
                'year': year,
                'day': day
            }
            
        except ValueError as e:
            raise ValueError(f"Erreur de parsing de date '{date_str}': {str(e)}")
        except Exception as e:
            raise ValueError(f"Erreur inattendue avec la date '{date_str}': {str(e)}")
    
    def parse_montant(self, montant_str):
        """Parse amount string to Decimal"""
        try:
            # Exemple: "00000005700.00" → "5700.00" → Decimal("5700")
            montant_str = montant_str.strip()
            
            # Supprimer les zéros en tête
            montant_str = montant_str.lstrip('0')
            
            # Si vide après suppression, c'est 0
            if not montant_str:
                return Decimal('0')
            
            # Si on a .00 à la fin, on peut l'enlever
            if montant_str.endswith('.00'):
                montant_str = montant_str[:-3]
                # Si vide après, c'est 0
                if not montant_str:
                    return Decimal('0')
            
            # Convertir en Decimal
            # On utilise quantize pour enlever les décimales si .00
            amount = Decimal(montant_str)
            
            # Si c'est un nombre entier (comme dans votre exemple), retourner comme integer
            if amount == amount.to_integral_value():
                return Decimal(int(amount))
            
            return amount
            
        except Exception as e:
            raise ValueError(f"Montant invalide '{montant_str}': {str(e)}")
    
    def handle_file(self, file_path):
        if not default_storage.exists(file_path):
            return {
                "paiements_effectues": [], 
                "erreurs": [{"error": "Fichier introuvable"}],
                "status": "error"
            }
        
        paiements_effectues = []
        erreurs = []
        line_number = 0
        
        # Grouper par (ccp + date) → montant total
        grouped_paiements = defaultdict(lambda: {'montant': Decimal('0'), 'date_info': None})
        
        with default_storage.open(file_path, "rb") as f:
            text_file = io.TextIOWrapper(f, encoding="utf-8")
            
            for line in text_file:
                line_number += 1
                original_line = line.rstrip('\n\r')
                
                # Ignorer les lignes vides
                if not original_line.strip():
                    continue
                
                try:
                    # Validation de la longueur
                    if not self.validate_line_format(original_line):
                        erreurs.append({
                            "ligne": line_number,
                            "error": f"Ligne trop courte ({len(original_line)} chars, minimum 68 requis)",
                            "extrait": original_line[:100] + "..." if len(original_line) > 100 else original_line
                        })
                        continue
                    
                    # Extraire les champs
                    fields = self.extract_fields(original_line)
                    
                    # Validation des champs requis
                    if not fields['ccp']:
                        erreurs.append({
                            "ligne": line_number,
                            "error": "CCP manquant ou vide",
                            "extrait": original_line[:50]
                        })
                        continue
                    
                    if not fields['montant_str']:
                        erreurs.append({
                            "ligne": line_number,
                            "error": "Montant manquant ou vide",
                            "ccp": fields['ccp']
                        })
                        continue
                    
                    if not fields['date_str']:
                        erreurs.append({
                            "ligne": line_number,
                            "error": "Date manquante ou vide",
                            "ccp": fields['ccp']
                        })
                        continue
                    
                    # Parser le montant
                    try:
                        montant = self.parse_montant(fields['montant_str'])
                    except ValueError as e:
                        erreurs.append({
                            "ligne": line_number,
                            "ccp": fields['ccp'],
                            "montant_str": fields['montant_str'],
                            "error": str(e)
                        })
                        continue
                    
                    # Parser la date
                    try:
                        date_info = self.parse_date(fields['date_str'])
                    except ValueError as e:
                        erreurs.append({
                            "ligne": line_number,
                            "ccp": fields['ccp'],
                            "date_str": fields['date_str'],
                            "error": str(e)
                        })
                        continue
                    
                    # Clé de regroupement: ccp + date complète
                    key = (fields['ccp'], date_info['datetime'].date())
                    
                    # Ajouter au groupe
                    if key not in grouped_paiements or grouped_paiements[key]['date_info'] is None:
                        grouped_paiements[key]['date_info'] = date_info
                    
                    grouped_paiements[key]['montant'] += montant
                    
                except Exception as e:
                    erreurs.append({
                        "ligne": line_number,
                        "extrait": original_line[:100],
                        "error": f"Erreur générale: {str(e)}"
                    })
        
        # Si trop d'erreurs, arrêter
        if erreurs and len(erreurs) > 20:
            return {
                "paiements_effectues": [],
                "erreurs": erreurs[:50],
                "status": "error",
                "message": f"Trop d'erreurs ({len(erreurs)}). Importation annulée."
            }
        
        # Appliquer les paiements groupés
        for (ccp, date_only), data in grouped_paiements.items():
            try:
                # 1️⃣ Trouver le client par CCP
                try:
                    client = Client.objects.get(ccp=ccp)
                except Client.DoesNotExist:
                    # Essayer avec des zéros ajoutés (format 8 chiffres)
                    ccp_8_digits = ccp.zfill(8)
                    client = Client.objects.filter(ccp=ccp_8_digits).first()
                    
                    if not client:
                        # Chercher par nom partiel (fallback)
                        # Note: Cette partie dépend de votre logique métier
                        raise Client.DoesNotExist(f"Client avec CCP {ccp} non trouvé")
                
                # 2️⃣ Trouver une vente active
                vente = VenteFacilite.objects.filter(client=client, solde_regle=False).first()
                if not vente:
                    erreurs.append({
                        "ccp": ccp,
                        "client": str(client),
                        "date": date_only.isoformat(),
                        "error": "Aucune vente active trouvée"
                    })
                    continue
                
                # 3️⃣ Vérifier si un paiement existe déjà pour cette date
                existing_payment = PaiementVente.objects.filter(
                    vente=vente,
                    date_paiement__date=date_only
                ).first()
                
                if existing_payment:
                    erreurs.append({
                        "ccp": ccp,
                        "client": str(client),
                        "date": date_only.isoformat(),
                        "error": f"Paiement existe déjà (ID: {existing_payment.id})"
                    })
                    continue
                
                # 4️⃣ Créer le paiement avec la date du fichier
                date_info = data['date_info']
                montant_total = data['montant']
                
                with transaction.atomic():
                    paiement = PaiementVente.objects.create(
                        vente=vente,
                        montant=montant_total,
                        date_paiement=date_info['datetime'],  # Date du fichier
                        month_index=date_info['month_index'],
                        status="paid",
                        year=date_info['year']  # Optionnel: stocker l'année
                    )
                    
                    # 5️⃣ Mettre à jour la vente
                    vente.montant_paye_effectif += montant_total
                    vente.montant_restant = max(Decimal('0'), vente.montant_restant - montant_total)
                    
                    if vente.montant_restant == 0:
                        vente.solde_regle = True
                    
                    vente.last_payment_date = date_only
                    vente.save()
                
                paiements_effectues.append({
                    "client": str(client),
                    "ccp": ccp,
                    "vente_id": vente.id,
                    "paiement_id": paiement.id,
                    "montant": float(montant_total),
                    "date_paiement": date_info['datetime'].isoformat(),
                    "month": date_info['month_index'] + 1,  # 1-based pour l'affichage
                    "year": date_info['year'],
                    "day": date_info['day']
                })
                
            except Client.DoesNotExist:
                erreurs.append({
                    "ccp": ccp,
                    "date": date_only.isoformat() if 'date_only' in locals() else "N/A",
                    "error": f"Client introuvable avec CCP: {ccp}"
                })
            except Exception as e:
                erreurs.append({
                    "ccp": ccp,
                    "date": date_only.isoformat() if 'date_only' in locals() else "N/A",
                    "error": f"Erreur lors du traitement: {str(e)}"
                })
        
        # Préparer la réponse
        result = {
            "paiements_effectues": paiements_effectues,
            "erreurs": erreurs,
            "statistics": {
                "total_lignes_lues": line_number,
                "paiements_crees": len(paiements_effectues),
                "erreurs_total": len(erreurs),
                "montant_total": float(sum(data['montant'] for data in grouped_paiements.values())),
                "clients_traites": len(set([p['ccp'] for p in paiements_effectues]))
            }
        }
        
        # Déterminer le statut
        if erreurs and not paiements_effectues:
            result["status"] = "error"
            result["message"] = "Aucun paiement importé"
        elif erreurs and paiements_effectues:
            result["status"] = "partial"
            result["message"] = f"{len(paiements_effectues)} paiements importés avec {len(erreurs)} erreurs"
        else:
            result["status"] = "success"
            result["message"] = f"Tous les {len(paiements_effectues)} paiements importés avec succès"
        
        return result
    
    def post(self, request, *args, **kwargs):
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"error": "Aucun fichier fourni", "status": "error"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier l'extension
        if not file.name.lower().endswith('.txt'):
            return Response(
                {"error": "Le fichier doit être un fichier .txt", "status": "error"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Limiter la taille du fichier (optionnel)
        if file.size > 10 * 1024 * 1024:  # 10MB
            return Response(
                {"error": "Fichier trop volumineux (max 10MB)", "status": "error"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file_path = default_storage.save(f"paiements_txt/{file.name}", file)
        
        try:
            result = self.handle_file(file_path)
            
            # Retourner le statut approprié
            if result.get("status") == "error":
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            elif result.get("status") == "partial":
                return Response(result, status=status.HTTP_207_MULTI_STATUS)
            else:
                return Response(result, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            import traceback
            return Response({
                "error": f"Erreur critique lors du traitement: {str(e)}",
                "traceback": traceback.format_exc(),
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            # Nettoyer le fichier temporaire
            if default_storage.exists(file_path):
                default_storage.delete(file_path)

# ventes/views.py - Fixed VenteFaciliteRetrieveUpdateDestroyAPIView

from django.db import transaction
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.conf import settings

from .models import VenteFacilite, LigneVenteFacilite, PaiementVente
from .serializers import VenteFaciliteDetailSerializer
from produits.models import Produit
from parametres.models import Magasin

from django.conf import settings
from django.db import transaction
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

class VenteFaciliteRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = VenteFacilite.objects.all()
    serializer_class = VenteFaciliteDetailSerializer
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        force_delete = str(request.query_params.get("force", "false")).lower() in (
            "1",
            "true",
            "yes",
        )

        restored_products = []
        failed_products = []

        try:
            lignes = list(
                instance.lignes.select_related("produit").all()
            )

            if not force_delete:

                from produits.models import Produit

                produit_ids = list(
                    {l.produit_id for l in lignes if l.produit_id}
                )

                produits_map = {
                    p.id: p
                    for p in Produit.objects.select_for_update().filter(
                        id__in=produit_ids
                    )
                }

                for ligne in lignes:

                    if (
                        not ligne.produit_id
                        or ligne.produit_id not in produits_map
                    ):
                        failed_products.append({
                            "line_id": ligne.id,
                            "error": "Product not found"
                        })
                        continue

                    produit = produits_map[ligne.produit_id]

                    snapshot = ligne.stock_snapshot

                    if not snapshot:
                        failed_products.append({
                            "produit_id": produit.id,
                            "produit_nom": produit.nom,
                            "error": "Stock snapshot missing"
                        })
                        continue

                    try:
                        produit.magasins = snapshot.get("magasins", [])

                        produit.save()

                        produit.refresh_from_db()

                        restored_products.append({
                            "id": produit.id,
                            "nom": produit.nom,
                            "quantite_restauree": produit.quantite_totale,
                            "barcodes_restaures": len(
                                snapshot.get("codes_barres", [])
                            ),
                        })

                    except Exception as e:
                        failed_products.append({
                            "produit_id": produit.id,
                            "produit_nom": produit.nom,
                            "error": str(e)
                        })

                if failed_products:
                    transaction.set_rollback(True)

                    return Response(
                        {
                            "success": False,
                            "error": f"{len(failed_products)} product(s) failed to restore",
                            "failed_products": failed_products,
                            "restored_products": restored_products,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            paiements_count = instance.paiements.count()

            instance.paiements.all().delete()

            self.perform_destroy(instance)

            return Response(
                {
                    "success": True,
                    "message": "Vente supprimée avec succès",
                    "restored_products": restored_products,
                    "total_restored": len(restored_products),
                    "paiements_supprimes": paiements_count,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            transaction.set_rollback(True)

            import traceback

            error_response = {
                "success": False,
                "error": str(e),
                "restored_products": restored_products,
                "failed_products": failed_products,
            }

            if settings.DEBUG:
                error_response["traceback"] = traceback.format_exc()

            return Response(
                error_response,
                status=status.HTTP_400_BAD_REQUEST,
            )



from django.db import transaction
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from .models import VenteCache
from .serializers import VenteCacheSerializer
from produits.models import Produit
from parametres.models import Magasin


class VenteCacheDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = VenteCache.objects.all()
    serializer_class = VenteCacheSerializer
    lookup_field = 'id'

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """
        Suppression d'une vente au comptant avec rollback automatique et restitution du stock.
        """
        instance = self.get_object()

        try:
            # Get the magasin from the sale record
            sale_magasin = instance.magasin
            
            if not sale_magasin:
                return Response(
                    {"error": "Le magasin n'est pas spécifié pour cette vente"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Restaurer le stock des produits
            for ligne in instance.lignes.all():
                produit = ligne.produit
                magasin_id = sale_magasin.id
                codes_to_restore = ligne.codes_barres_utilises or []
                
                if not codes_to_restore:
                    continue
                
                # Find if the product already has this magasin in its magasins array
                magasin_index = -1
                for i, mag in enumerate(produit.magasins or []):
                    if mag.get('id') == magasin_id:
                        magasin_index = i
                        break
                
                if magasin_index == -1:
                    # Create new magasin entry
                    produit.magasins.append({
                        'id': magasin_id,
                        'nom': sale_magasin.nom,
                        'adresse': getattr(sale_magasin, 'adresse', ''),
                        'codes_barres': codes_to_restore
                    })
                else:
                    # Add codes to existing magasin
                    current_codes = produit.magasins[magasin_index].get('codes_barres', [])
                    # Add restored codes to the beginning or end? 
                    # Adding to the beginning to maintain order
                    produit.magasins[magasin_index]['codes_barres'] = codes_to_restore + current_codes
                
                # Sync product to update global codes_barres
                produit._sync_quantite()
                produit.save()

            # Delete the sale (cascade will delete lines)
            self.perform_destroy(instance)

            return Response(
                {"success": "Vente supprimée avec succès et stock restauré"},
                status=status.HTTP_204_NO_CONTENT
            )

        except Exception as e:
            transaction.set_rollback(True)
            return Response(
                {"error": f"Suppression annulée : {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
class VenteCacheCreateAPIView(generics.CreateAPIView):
    queryset = VenteCache.objects.all()
    serializer_class = VenteCacheSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Get magasin_id from request data or query params
        magasin_id = self.request.data.get('magasin_id') or self.request.query_params.get('magasin_id')
        if magasin_id:
            context['magasin_id'] = magasin_id
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class VenteCacheListAPIView(generics.ListAPIView):
    queryset = VenteCache.objects.all().select_related('client', 'utilisateur', 'magasin')
    serializer_class = VenteCacheSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = VenteCacheFilter

    search_fields = [
        'client__nom_famille_fr',
        'client__prenom_fr',
        'client__nom_famille_ar',
        'client__prenom_ar',
        'client__ccp',
        'client__cle'
    ]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        total_montant = queryset.aggregate(Sum("montant_total"))["montant_total__sum"] or 0
        total_ventes = queryset.count()
        produit_id = request.query_params.get('produit')
        quantite_vendue = 0
        montant_total_produit = 0

        if produit_id:
            produit_stats = queryset.aggregate(
                quantite_vendue=Coalesce(
                    Sum(
                        'lignes__quantite',
                        filter=Q(lignes__produit_id=produit_id),
                        output_field=IntegerField()
                    ),
                    Value(0, output_field=IntegerField())
                ),
                montant_total_produit=Coalesce(
                    Sum(
                        'lignes__sous_total',
                        filter=Q(lignes__produit_id=produit_id),
                        output_field=DecimalField()
                    ),
                    Value(0, output_field=DecimalField())
                ),
            )

            quantite_vendue = produit_stats['quantite_vendue'] or 0
            montant_total_produit = produit_stats['montant_total_produit'] or 0

        return Response({
            "total_montant": total_montant,
            "nombre_de_ventes": total_ventes,
            "ventes": serializer.data,
            "quantite_vendue_produit": quantite_vendue,
            "montant_total_produit": montant_total_produit
        })   



from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

# class VenteCacheDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
#     queryset = VenteCache.objects.all()
#     serializer_class = VenteCacheSerializer
#     lookup_field = 'id'

#     @transaction.atomic
#     def destroy(self, request, *args, **kwargs):
#         """
#         Suppression d'une vente au comptant avec rollback automatique
#         et restauration du stock produit.
#         """
#         instance = self.get_object()

#         try:
#             # 🔄 Restaurer le stock des produits
#             for ligne in instance.lignes.all():
#                 produit = ligne.produit

#                 # Restituer la quantité
#                 produit.quantite += ligne.quantite

#                 # Restituer les codes-barres
#                 if ligne.codes_barres_utilises:
#                     produit.codes_barres = ligne.codes_barres_utilises + produit.codes_barres

#                 produit.save()

#             # Supprimer la vente (les lignes sont supprimées en cascade)
#             self.perform_destroy(instance)

#             return Response(
#                 {"success": "Vente supprimée avec succès et stock restauré"},
#                 status=status.HTTP_204_NO_CONTENT
#             )

#         except Exception as e:
#             transaction.set_rollback(True)
#             return Response(
#                 {"error": f"Suppression annulée : {str(e)}"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )



from docxtpl import DocxTemplate
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import VenteFacilite
from django.conf import settings
from pathlib import Path
from docxtpl import DocxTemplate

class VenteFaciliteActeWordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            vente = VenteFacilite.objects.prefetch_related('lignes', 'client').get(pk=pk)
        except VenteFacilite.DoesNotExist:
            return Response({"error": "Vente non trouvée"}, status=404)

        # Charger le template ACTE.docx
        template_path = Path(settings.BASE_DIR) / "templates_word" / "ACTE.docx" # chemin vers ton modèle
        doc = DocxTemplate(template_path)

        # Construire la liste des produits
        produits_list = []
        for ligne in vente.lignes.all():
            produits_list.append({
                "designation": ligne.produit.nom,
                "quantite": ligne.quantite,
                "prix": ligne.sous_total,
            })

        # Remplir le contexte
        context = {
            "vente_id": vente.id,
            "client_nom": vente.client.nom_famille_ar,
            "client_prenom": vente.client.prenom_ar,
            "client_date_naissance":vente.client.date_naissance,
            "client_lieu_naissance":vente.client.lieu_naissance,
            "nom_pere":vente.client.nom_pere,
            "nom_mere":vente.client.nom_mere,
            "ccp":vente.client.ccp,
            "cle":vente.client.cle,
            "numero_piece_identite":vente.client.numero_piece_identite,
            "date_emission_piece":vente.client.date_emission_piece,
            "lieu_emission_piece":vente.client.lieu_emission_piece,
            "client_adresse": vente.client.adresse,
            "client_telephone": " / ".join(vente.client.telephones or []),
            "produits": produits_list,
            "total": vente.montant_total,
            "montant_verse":vente.montant_verse,
            "montant_restant":vente.montant_restant,
            "nombre_mois":vente.nombre_mois,
            "montant_mensuel":vente.montant_mensuel,
        }

        # Rendre le document
        doc.render(context)

        # Envoyer la réponse HTTP
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename="Acte_{vente.id}.docx"'
        doc.save(response)
        return response

class VenteFaciliteBonWordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            vente = VenteFacilite.objects.prefetch_related('lignes', 'client','utilisateur').get(pk=pk)
        except VenteFacilite.DoesNotExist:
            return Response({"error": "Vente non trouvée"}, status=404)

        # Charger le template ACTE.docx
        template_path = Path(settings.BASE_DIR) / "templates_word" / "BON.docx" # chemin vers ton modèle
        doc = DocxTemplate(template_path)

        # Construire la liste des produits
        produits_list = []
        for ligne in vente.lignes.all():
            produits_list.append({
                "designation": ligne.produit.nom,
                "prix": ligne.sous_total,
            })

        # Remplir le contexte
        context = {
            "client_nom": vente.client.nom_famille_ar,
            "client_prenom": vente.client.prenom_ar,
            "client_date_naissance":vente.client.date_naissance,
            "client_lieu_naissance":vente.client.lieu_naissance,
            "adresse":vente.client.adresse,
            "utilisateur":vente.utilisateur.username,
            "produits": produits_list,
            "total": vente.montant_total,
            "montant_verse":vente.montant_verse,
            "montant_restant":vente.montant_restant,
            "nombre_mois":vente.nombre_mois,
            "montant_mensuel":vente.montant_mensuel,
            "date_debut":vente.date_debut,
            "date_fin":vente.date_fin,
            "date_creation": vente.date_creation.strftime("%d/%m/%Y"),
        }

        # Rendre le document
        doc.render(context)

        # Envoyer la réponse HTTP
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename="BON_{vente.id}.docx"'
        doc.save(response)
        return response

from pathlib import Path
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from docxtpl import DocxTemplate
from django.conf import settings
from .models import VenteCache

class VenteCashBonWordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            vente = (
                VenteCache.objects
                .select_related('client', 'utilisateur')
                .prefetch_related('lignes')
                .get(pk=pk)
            )
        except VenteCache.DoesNotExist:
            return Response({"error": "Vente non trouvée"}, status=404)

        # Load Word template
        template_path = Path(settings.BASE_DIR) / "templates_word" / "BON_CASH.docx"
        doc = DocxTemplate(template_path)

        # Build product list
        produits_list = [
            {"designation": ligne.produit.nom, "prix": f"{ligne.sous_total} DA"}
            for ligne in vente.lignes.all()
        ]

        # Fill context
        context = {
            "client_nom": vente.client.nom_famille_ar,
            "client_prenom": vente.client.prenom_ar,
            "client_date_naissance": vente.client.date_naissance.strftime("%d/%m/%Y") if vente.client.date_naissance else "",
            "client_lieu_naissance": vente.client.lieu_naissance or "",
            "adresse": vente.client.adresse or "",
            "utilisateur": vente.utilisateur.username if vente.utilisateur else "",
            "produits": produits_list,
            "total": f"{vente.montant_total} DA",
            "date_vente": vente.date_vente.strftime("%d/%m/%Y"),
        }

        # Render document
        doc.render(context)

        # Return as downloadable Word file
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename="BON_{vente.id}.docx"'
        doc.save(response)
        return response


class VenteFaciliteDepotWordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            vente = VenteFacilite.objects.prefetch_related('lignes', 'client', 'utilisateur', 'magasin').get(pk=pk)
        except VenteFacilite.DoesNotExist:
            return Response({"error": "Vente non trouvée"}, status=404)

        # Charger le template DEPOT.docx
        template_path = Path(settings.BASE_DIR) / "templates_word" / "DEPOT.docx"
        doc = DocxTemplate(template_path)

        # Construire la liste des produits avec le bon magasin
        produits_list = []
        for ligne in vente.lignes.all():
            # Get the magasin name from the sale's magasin if available, or from product's magasins
            magasin_nom = "N/A"
            
            # First try to get from the sale's magasin
            if vente.magasin:
                magasin_nom = vente.magasin.nom
            else:
                # If not, try to find from product's magasins list
                if hasattr(ligne.produit, 'magasins') and ligne.produit.magasins:
                    # magasins is a list of dicts like [{'id': 1, 'nom': 'Magasin Name', ...}]
                    if isinstance(ligne.produit.magasins, list) and len(ligne.produit.magasins) > 0:
                        magasin_nom = ligne.produit.magasins[0].get('nom', 'N/A')
            
            produits_list.append({
                "designation": ligne.produit.nom,
                "prix": ligne.sous_total,
                "magasin": magasin_nom,  # Fixed: Now using magasin_nom instead of ligne.produit.magasin.nom
            })
        
        # Collect all barcodes
        codes_barres_list = []
        for ligne in vente.lignes.all():
            if ligne.codes_barres_utilises:
                codes_barres_list.extend(ligne.codes_barres_utilises)

        # Remplir le contexte
        context = {
            "vente_id": vente.id,
            "client_nom": vente.client.nom_famille_ar,
            "client_prenom": vente.client.prenom_ar,
            "client_date_naissance": vente.client.date_naissance,
            "client_lieu_naissance": vente.client.lieu_naissance,
            "adresse": vente.client.adresse,
            "utilisateur": vente.utilisateur.username,
            "produits": produits_list,
            "codes_barres": "- ".join(codes_barres_list) if codes_barres_list else "Aucun code barres",
            "date_creation": vente.date_creation.strftime("%d/%m/%Y"),
        }

        # Rendre le document
        doc.render(context)

        # Envoyer la réponse HTTP
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename="DEPOT_{vente.id}.docx"'
        doc.save(response)
        return response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from django.http import HttpResponse
import io
from pathlib import Path
from docx import Document

from .models import VenteFacilite


from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from django.http import HttpResponse
import io
from pathlib import Path
from docx import Document

from .models import VenteFacilite


class VenteFaciliteCCPWordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            vente = (
                VenteFacilite.objects
                .select_related('client', 'utilisateur')
                .get(pk=pk)
            )
        except VenteFacilite.DoesNotExist:
            return Response({"error": "Vente non trouvée"}, status=404)

        prelevement = request.GET.get("prelevement")
        if not prelevement:
            return Response({"error": "Le paramètre 'prelevement' est requis"}, status=400)

        template_path = Path(settings.BASE_DIR) / "templates_word" / "ccp.docx"
        doc = Document(template_path)

        def remplir_ligne_cases(table, row_index, texte, is_ccp=False, cle="", align_right=False):
            texte = str(texte)
            cells = table.rows[row_index].cells
            total_cells = len(cells)

            # Clear row (except label column)
            for i in range(1, total_cells):
                for paragraph in cells[i].paragraphs:
                    for run in paragraph.runs:
                        run.text = ""

            # =========================
            # ✅ FIXED POSITIONING LOGIC
            # =========================
            if align_right and not is_ccp:
                chars = list(texte)

                # 🔥 Start from 3rd last cell
                start_col = total_cells - 3

                for i, char in enumerate(reversed(chars)):
                    col_index = start_col - i
                    if col_index >= 1:  # avoid first label column
                        cells[col_index].paragraphs[0].add_run(char)

                return  # VERY IMPORTANT → stop here

            # =========================
            # NORMAL LEFT → RIGHT
            # =========================
            if is_ccp:
                cle_cols = [total_cells - 2, total_cells - 1]
                data_cells = list(range(1, total_cells - 2))
            else:
                cle_cols = []
                data_cells = list(range(1, total_cells))

            letter_idx = 0
            for i in data_cells:
                if letter_idx < len(texte):
                    cells[i].paragraphs[0].add_run(texte[letter_idx])
                    letter_idx += 1

            # CCP key
            if is_ccp and cle:
                cle = cle.upper().ljust(2)[:2]
                for idx, col in enumerate(cle_cols):
                    if idx < len(cle):
                        cells[col].paragraphs[0].add_run(cle[idx])

        # Format months
        nb_mois = vente.nombre_mois or 0
        echeances = f"{nb_mois:02}"

        # CCP data
        ccp_number = str(vente.client.ccp or "")
        cle_number = str(vente.client.cle or "")

        # Format amount
        try:
            prelevement_float = float(prelevement)
            montant_formatted = f"{prelevement_float:.2f}".replace(".", ",")
        except:
            montant_formatted = f"{prelevement},00"

        # Fill tables
        for table in doc.tables[:2]:
            remplir_ligne_cases(table, 0, vente.client.nom_famille_fr or "")
            remplir_ligne_cases(table, 2, vente.client.prenom_fr or "")
            remplir_ligne_cases(table, 4, ccp_number, is_ccp=True, cle=cle_number)
            remplir_ligne_cases(table, 8, vente.date_debut.strftime("%d"))
            remplir_ligne_cases(table, 10, vente.date_debut.strftime("%d/%m/%Y"))

            # ✅ Correct amount placement
            remplir_ligne_cases(table, 12, montant_formatted, align_right=True)

            # ✅ Force "DA" and empty last cell
            cells = table.rows[12].cells
            total_cells = len(cells)

            if total_cells >= 2:
                # Clear last 2 cells
                for paragraph in cells[total_cells - 2].paragraphs:
                    for run in paragraph.runs:
                        run.text = ""

                for paragraph in cells[total_cells - 1].paragraphs:
                    for run in paragraph.runs:
                        run.text = ""

                # Put DA
                cells[total_cells - 2].paragraphs[0].add_run("DA")

                # Last cell remains empty

            remplir_ligne_cases(table, 14, echeances)

        # Generate Word
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename="ccp_{vente.id}.docx"'
        return response

class DashboardPaiementsAPIView(APIView):
    def _add_months(self, value, months):
        month = value.month - 1 + months
        year = value.year + month // 12
        month = month % 12 + 1
        day = min(value.day, 28)
        return value.replace(year=year, month=month, day=day)

    def _parse_int(self, value):
        try:
            return int(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None

    def get(self, request):
        year = self._parse_int(request.query_params.get("year"))
        month = self._parse_int(request.query_params.get("month"))
        status = request.query_params.get("status")

        ventes = VenteFacilite.objects.select_related("client").prefetch_related("paiements").all()
        data = []

        for vente in ventes:
            paiements_by_month = {}
            for paiement in vente.paiements.all():
                payment_year = paiement.year or paiement.date_paiement.year
                key = (payment_year, paiement.month_index)
                paiements_by_month[key] = paiement

            mois_status = vente.mois_status or []

            for index in range(vente.nombre_mois):
                due_date = self._add_months(vente.date_debut, index)
                due_year = due_date.year
                due_month_index = due_date.month - 1

                if year is not None and due_year != year:
                    continue
                if month is not None and due_month_index != month:
                    continue

                paiement = paiements_by_month.get((due_year, due_month_index))
                row_status = paiement.status if paiement else (
                    mois_status[index] if index < len(mois_status) else "pending"
                )

                if status and row_status != status:
                    continue

                data.append({
                    "name": f"{vente.client.nom_famille_ar} {vente.client.prenom_ar}",
                    "account": f"{vente.client.ccp}/{vente.client.cle}",
                    "date": paiement.date_paiement if paiement else due_date,
                    "amount": paiement.montant if paiement else vente.montant_mensuel,
                    "status": row_status,
                    "clientStatus": vente.client.statut,
                    "month_index": due_month_index,
                    "year": due_year,
                    "vente_id": vente.id,
                    "paiement_id": paiement.id if paiement else None,
                })

        return Response(data)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

# Assumons que vous avez ce modèle
from .models import PaiementVente

@api_view(['DELETE', 'POST'])  # Supporte DELETE et POST
@permission_classes([IsAuthenticated])
def delete_all_payments(request):
    """
    Supprime TOUS les paiements de la base de données
    """
    try:
        with transaction.atomic():
            # Compter avant suppression
            total_payments = PaiementVente.objects.count()
            
            # Supprimer tous les paiements
            deleted_count, _ = PaiementVente.objects.all().delete()
            
            return Response({
                'message': 'Tous les paiements ont été supprimés',
                'paiements_supprimes': deleted_count,
                'total_avant_suppression': total_payments,
                'action': 'Toutes les lignes ont été supprimées de la table PaiementVente'
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        return Response({
            'error': f'Erreur lors de la suppression: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reset_all_ventes_to_initial(request):
    """
    Réinitialise TOUTES les ventes à l'état initial
    """
    try:
        ventes = VenteFacilite.objects.all()
        results = []
        total_paiements_supprimes = 0
        
        for vente in ventes:
            # Sauvegarder ancien état
            ancien_verse = vente.montant_verse
            ancien_restant = vente.montant_restant
            
            # Réinitialiser
            vente.montant_verse = Decimal('0')
            vente.montant_restant = vente.montant_total
            
            if hasattr(vente, 'montant_paye_effectif'):
                vente.montant_paye_effectif = Decimal('0')
            
            if hasattr(vente, 'last_payment_date'):
                vente.last_payment_date = None
            
            if hasattr(vente, 'solde_regle'):
                vente.solde_regle = False
            
            vente.save()
            
            # Supprimer les paiements restants
            paiements = PaiementVente.objects.filter(vente=vente)
            paiements_count = paiements.count()
            paiements.delete()
            total_paiements_supprimes += paiements_count
            
            results.append({
                'vente_id': vente.id,
                'client': f"{vente.client.nom_famille_ar} {vente.client.prenom_ar}",
                'ancien_montant_verse': float(ancien_verse),
                'nouveau_montant_verse': 0,
                'montant_total': float(vente.montant_total),
                'montant_mensuel': float(vente.montant_mensuel)
            })
        
        # Calculer les totaux
        total_montant = sum(v.montant_total for v in ventes)
        total_mensuel = sum(v.montant_mensuel for v in ventes)
        
        return Response({
            'message': 'تمت إعادة تعيين جميع المبيعات',
            'ventes_traitees': len(results),
            'paiements_supprimes': total_paiements_supprimes,
            'totaux': {
                'المبلغ الإجمالي لجميع المبيعات': f'{total_montant} دج',
                'المبلغ المدفوع الكلي': '0 دج',
                'المبلغ المتبقي الكلي': f'{total_montant} دج',
                'مجموع الأقساط الشهرية': f'{total_mensuel} دج'
            },
            'details': results[:10]  # Limiter à 10 pour éviter une réponse trop grande
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Erreur: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
# ventes/views.py - Add this API view

class AppSettingsAPIView(APIView):
    """
    GET /vente/settings/
    POST /vente/settings/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get the 30% salary limit setting"""
        try:
            setting = AppSettings.objects.get(name='salary_limit_active')
            return Response({
                'name': setting.name,
                'value': setting.value,
                'description': setting.description
            })
        except AppSettings.DoesNotExist:
            # Create default setting
            setting = AppSettings.objects.create(
                name='salary_limit_active',
                value=False,
                description='تفعيل حد 30% من الراتب للبيع بالتقسيط'
            )
            return Response({
                'name': setting.name,
                'value': setting.value,
                'description': setting.description
            })
    
    def post(self, request):
        """Update the 30% salary limit setting"""
        if request.user.role != 'admin':
            return Response(
                {"error": "Seul un administrateur peut modifier ce paramètre"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        value = request.data.get('value')
        if value is None:
            return Response(
                {"error": "Le paramètre 'value' est requis"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            setting = AppSettings.objects.get(name='salary_limit_active')
            setting.value = value
            setting.updated_by = request.user
            setting.save()
        except AppSettings.DoesNotExist:
            setting = AppSettings.objects.create(
                name='salary_limit_active',
                value=value,
                description='تفعيل حد 30% من الراتب للبيع بالتقسيط',
                updated_by=request.user
            )
        
        return Response({
            'name': setting.name,
            'value': setting.value,
            'description': setting.description,
            'updated_at': setting.updated_at,
            'updated_by': setting.updated_by.username if setting.updated_by else None
        })
