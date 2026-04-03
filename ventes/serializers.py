from rest_framework import serializers
from .models import *
from produits.models import Produit
from produits.serializers import ProduitSerializer
from authentification.serializers import ClientSerializer
from parametres.serializers import MagasinSerializer
from datetime import timedelta
from rest_framework.exceptions import ValidationError
from django.utils.timezone import localtime
from authentification.serializers import CustomUserSerializer


class VenteFaciliteMinimalSerializer(serializers.ModelSerializer):
    """Ultra-lightweight serializer - no nested objects, only IDs and formatted strings"""
    
    client_name = serializers.SerializerMethodField()
    utilisateur_name = serializers.SerializerMethodField()
    magasin_name = serializers.SerializerMethodField()
    date_formatee = serializers.SerializerMethodField()

    class Meta:
        model = VenteFacilite
        fields = [
            'id', 
            'client_name',
            'utilisateur_name', 
            'magasin_name',
            'nombre_mois', 
            'montant_total', 
            'montant_verse', 
            'montant_restant',
            'montant_mensuel', 
            'date_formatee',
            'montants_par_mois'
        ]

    def get_client_name(self, obj):
        if obj.client_id and obj.client:
            client = obj.client
            if client.nom_famille_ar or client.prenom_ar:
                return f"{client.nom_famille_ar or ''} {client.prenom_ar or ''}".strip()
            elif client.nom_famille_fr or client.prenom_fr:
                return f"{client.nom_famille_fr or ''} {client.prenom_fr or ''}".strip()
        return 'غير معروف'

    def get_utilisateur_name(self, obj):
        if obj.utilisateur_id and obj.utilisateur:
            return obj.utilisateur.username
        return 'غير معروف'

    def get_magasin_name(self, obj):
        if obj.magasin_id and obj.magasin:
            return obj.magasin.nom
        return '-'

    def get_date_formatee(self, obj):
        if obj.date_creation:
            return localtime(obj.date_creation).strftime('%d/%m/%Y')
        return ''


class VenteFaciliteListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list view"""
    client_detail = serializers.SerializerMethodField()
    utilisateur_detail = serializers.SerializerMethodField()
    magasin_detail = serializers.SerializerMethodField()
    date_formatee = serializers.SerializerMethodField()

    class Meta:
        model = VenteFacilite
        fields = [
            'id', 'client', 'client_detail', 'utilisateur', 'utilisateur_detail',
            'magasin', 'magasin_detail',
            'nombre_mois', 'date_debut', 'date_fin', 'date_creation',
            'montant_total', 'montant_verse', 'montant_restant',
            'montant_mensuel', 'montant_paye_effectif', 'solde_regle',
            'date_formatee'
        ]

    def get_client_detail(self, obj):
        if obj.client:
            return {
                "id": obj.client.id,
                "nom_famille_ar": obj.client.nom_famille_ar,
                "prenom_ar": obj.client.prenom_ar,
                "nom_famille_fr": obj.client.nom_famille_fr,
                "prenom_fr": obj.client.prenom_fr,
                "ccp": obj.client.ccp,
                "cle": obj.client.cle,
            }
        return None

    def get_utilisateur_detail(self, obj):
        if obj.utilisateur:
            return {
                "id": obj.utilisateur.id,
                "username": obj.utilisateur.username,
            }
        return None

    def get_magasin_detail(self, obj):
        if obj.magasin:
            return {
                "id": obj.magasin.id,
                "nom": obj.magasin.nom,
            }
        return None

    def get_date_formatee(self, obj):
        return localtime(obj.date_creation).strftime('%d/%m/%Y')


class VenteFaciliteDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail view - includes lines and magasin"""
    client_detail = ClientSerializer(source='client', read_only=True)
    utilisateur_detail = serializers.SerializerMethodField()
    magasin = MagasinSerializer(read_only=True)  # ✅ This should already be there
    lignes_detail = serializers.SerializerMethodField()
    date_formatee = serializers.SerializerMethodField()

    class Meta:
        model = VenteFacilite
        fields = [
            'id', 'client', 'client_detail', 'utilisateur', 'utilisateur_detail',
            'nombre_mois', 'date_debut', 'date_fin', 'date_creation',
            'montant_total', 'montant_verse', 'montant_restant',
            'montant_mensuel', 'montants_par_mois', 'montant_paye_effectif',
            'last_payment_date', 'solde_regle', 'magasin',  # ✅ Ensure magasin is here
            'lignes_detail', 'date_formatee'
        ]

    def get_utilisateur_detail(self, obj):
        if obj.utilisateur:
            return {
                "id": obj.utilisateur.id,
                "username": obj.utilisateur.username,
            }
        return None

    def get_date_formatee(self, obj):
        return localtime(obj.date_creation).strftime('%d/%m/%Y') if obj.date_creation else ''

    def get_lignes_detail(self, obj):
        return LigneVenteFaciliteSerializer(obj.lignes.all(), many=True).data
class LigneVenteFaciliteSerializer(serializers.ModelSerializer):
    """Serializer for sale lines"""
    produit_detail = serializers.SerializerMethodField()

    class Meta:
        model = LigneVenteFacilite
        fields = [
            'id', 'produit', 'produit_detail', 'quantite',
            'prix_unitaire', 'sous_total', 'codes_barres_utilises'
        ]

    def get_produit_detail(self, obj):
        if obj.produit:
            return {
                "id": obj.produit.id,
                "nom": obj.produit.nom,
                "reference": obj.produit.reference,
            }
        return None
import copy

class VenteFaciliteSerializer(serializers.ModelSerializer):
    client_detail = ClientSerializer(source='client', read_only=True)
    utilisateur_detail = serializers.SerializerMethodField()
    date_formatee = serializers.SerializerMethodField()
    magasin = MagasinSerializer(read_only=True)
    magasin_id = serializers.IntegerField(write_only=True, required=True)
    lignes = serializers.ListField(write_only=True, required=True, child=serializers.DictField())

    class Meta:
        model = VenteFacilite
        fields = [
            'id', 'client', 'client_detail', 'utilisateur', 'utilisateur_detail',
            'nombre_mois', 'date_debut', 'date_fin', 'date_creation',
            'montant_total', 'montant_verse', 'montant_restant',
            'montant_mensuel', 'montants_par_mois', 'montant_paye_effectif',
            'last_payment_date', 'solde_regle', 'date_formatee', 'magasin',
            'magasin_id', 'lignes'
        ]
        read_only_fields = [
            'date_creation', 'utilisateur', 'last_payment_date', 
            'montant_paye_effectif', 'magasin'
        ]

    def get_utilisateur_detail(self, obj):
        if obj.utilisateur:
            return {
                "id": obj.utilisateur.id,
                "username": obj.utilisateur.username,
            }
        return None

    def get_date_formatee(self, obj):
        return localtime(obj.date_creation).strftime('%d/%m/%Y') if obj.date_creation else ''

    def validate(self, data):
        """Validate that all required data is present"""
        if not data.get('lignes'):
            raise serializers.ValidationError({"lignes": "Au moins un produit est requis"})
        
        if not data.get('magasin_id'):
            raise serializers.ValidationError({"magasin_id": "Le magasin est requis"})
        
        # Validate each line has barcodes if provided
        for ligne in data.get('lignes', []):
            if 'codes_barres' in ligne and ligne['codes_barres']:
                # If barcodes are provided, validate they exist in the magasin
                pass
        
        return data

    def create(self, validated_data):
        lignes_data = validated_data.pop('lignes', [])
        magasin_id = validated_data.pop('magasin_id', None)
        
        request = self.context.get('request')
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['utilisateur'] = request.user
        
        # Get the magasin object and save it to the sale
        magasin = None
        if magasin_id:
            from parametres.models import Magasin
            try:
                magasin = Magasin.objects.get(id=magasin_id)
                validated_data['magasin'] = magasin
            except Magasin.DoesNotExist:
                raise serializers.ValidationError(f"Magasin with id {magasin_id} does not exist")

        # Create the sale
        vente = VenteFacilite.objects.create(**validated_data)
        nombre_mois = vente.nombre_mois

        prix_mapping_field = {
            3: 'prix_vente_3',
            5: 'prix_vente_5',
            6: 'prix_vente_6',
            8: 'prix_vente_8',
            9: 'prix_vente_9',
            10: 'prix_vente_10',
            12: 'prix_vente_12',
            15: 'prix_vente_15',
        }

        # Process each line
        for ligne_data in lignes_data:
            produit_id = ligne_data.get('produit') or ligne_data.get('product')
            if not produit_id:
                raise serializers.ValidationError(f"Produit ID manquant dans la ligne: {ligne_data}")
            
            quantite = ligne_data.get('quantite')
            if not quantite:
                raise serializers.ValidationError(f"Quantité manquante dans la ligne: {ligne_data}")
            
            # Get manually provided barcodes (optional)
            codes_barres_manuels = ligne_data.get('codes_barres', [])
            
            try:
                produit = Produit.objects.get(id=produit_id)
                
                # Take snapshot before stock change
                snapshot = copy.deepcopy({
                    "magasins": produit.magasins,
                    "codes_barres": produit.codes_barres,
                    "quantite_totale": produit.quantite_totale,
                })
            except Produit.DoesNotExist:
                raise serializers.ValidationError(f"Produit with ID {produit_id} does not exist")
            
            # Get the magasins list
            magasins_list = produit.magasins if produit.magasins is not None else []
            
            # Find the magasin in the product's magasins array
            magasin_index = -1
            magasin_codes = []
            
            for i, mag in enumerate(magasins_list):
                if mag.get('id') == magasin_id:
                    magasin_index = i
                    magasin_codes = mag.get('codes_barres', [])
                    break
            
            if magasin_index == -1:
                raise serializers.ValidationError(
                    f"Le produit '{produit.nom}' n'est pas disponible dans le magasin sélectionné. "
                    f"ID magasin: {magasin_id}. Magasins disponibles: {[m.get('id') for m in magasins_list]}"
                )
            
            # Determine which barcodes to use
            codes_utilises = []
            
            if codes_barres_manuels and len(codes_barres_manuels) > 0:
                # Use manually provided barcodes
                codes_utilises = codes_barres_manuels
                
                # Validate that all manually provided barcodes exist in the magasin
                for code in codes_utilises:
                    if code not in magasin_codes:
                        raise serializers.ValidationError(
                            f"Le code barres '{code}' n'existe pas dans le magasin pour le produit '{produit.nom}'. "
                            f"Codes disponibles: {magasin_codes}"
                        )
                
                # Validate quantity matches number of barcodes
                if len(codes_utilises) != quantite:
                    raise serializers.ValidationError(
                        f"Le nombre de codes barres fournis ({len(codes_utilises)}) ne correspond pas à la quantité ({quantite}) "
                        f"pour le produit '{produit.nom}'"
                    )
                
                # Remove the used barcodes from magasin_codes
                for code in codes_utilises:
                    if code in magasin_codes:
                        magasin_codes.remove(code)
            else:
                # Auto-select barcodes (take from the beginning of the list)
                if len(magasin_codes) < quantite:
                    raise serializers.ValidationError(
                        f"Stock insuffisant pour {produit.nom} dans le magasin sélectionné. "
                        f"Disponible: {len(magasin_codes)}, demandé: {quantite}"
                    )
                codes_utilises = magasin_codes[:quantite]
                magasin_codes = magasin_codes[quantite:]

            # Get price based on number of months
            prix_field = prix_mapping_field.get(nombre_mois)
            if not prix_field:
                raise serializers.ValidationError(f"Aucun prix défini pour {nombre_mois} mois pour {produit.nom}.")

            prix_unitaire = getattr(produit, prix_field)
            if prix_unitaire is None:
                raise serializers.ValidationError(f"Le prix pour {nombre_mois} mois n'est pas défini pour {produit.nom}.")
            
            sous_total = prix_unitaire * quantite
            
            # Update the magasin's codes (remove used barcodes)
            updated_magasins = magasins_list.copy()
            
            if magasin_index < len(updated_magasins):
                if magasin_codes:
                    # Update with remaining codes
                    updated_magasins[magasin_index]['codes_barres'] = magasin_codes
                else:
                    # Remove the magasin entry if empty
                    updated_magasins.pop(magasin_index)
            
            # Update product
            produit.magasins = updated_magasins
            produit._sync_quantite()
            produit.save()

            # Create line with barcodes used
            LigneVenteFacilite.objects.create(
                vente=vente,
                produit=produit,
                quantite=quantite,
                prix_unitaire=prix_unitaire,
                sous_total=sous_total,
                codes_barres_utilises=codes_utilises,
                stock_snapshot=snapshot
            )

        return vente

class PaiementVenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaiementVente
        fields = ["id", "montant", "date_paiement", "month_index", "status", "year"]


class LigneVenteCacheReadSerializer(serializers.ModelSerializer):
    produit_nom = serializers.CharField(source='produit.nom', read_only=True)
    produit_reference = serializers.CharField(source='produit.reference', read_only=True)
    magasin_detail = serializers.SerializerMethodField()
    codes_barres_utilises = serializers.ListField(read_only=True)

    class Meta:
        model = LigneVenteCache
        fields = ['id', 'produit', 'produit_nom', 'produit_reference', 'quantite', 
                  'prix_unitaire', 'sous_total', 'magasin_detail', 'codes_barres_utilises']
    
    def get_magasin_detail(self, obj):
        if obj.vente and obj.vente.magasin:
            return {
                "id": obj.vente.magasin.id,
                "nom": obj.vente.magasin.nom,
                "adresse": getattr(obj.vente.magasin, 'adresse', '')
            }
        return {"id": None, "nom": "N/A", "adresse": ""}


class LigneVenteCacheCreateSerializer(serializers.Serializer):
    produit = serializers.IntegerField()
    quantite = serializers.IntegerField(min_value=1)


class VenteCacheSerializer(serializers.ModelSerializer):
    lignes = LigneVenteCacheCreateSerializer(many=True, write_only=True)
    lignes_detail = LigneVenteCacheReadSerializer(many=True, read_only=True, source='lignes')
    client_detail = ClientSerializer(source='client', read_only=True)
    utilisateur_detail = serializers.SerializerMethodField()
    date_formatee = serializers.SerializerMethodField()
    magasin_id = serializers.IntegerField(write_only=True, required=True)

    class Meta:
        model = VenteCache
        fields = [
            'id', 'client', 'client_detail', 'utilisateur', 'utilisateur_detail',
            'lignes', 'lignes_detail', 'montant_total', 'date_vente', 'date_formatee',
            'magasin_id', 'magasin'
        ]
        read_only_fields = [
            'montant_total', 'date_vente', 'lignes_detail',
            'client_detail', 'utilisateur', 'utilisateur_detail', 'date_formatee', 'magasin'
        ]

    def get_utilisateur_detail(self, obj):
        if obj.utilisateur:
            return {
                "id": obj.utilisateur.id,
                "username": obj.utilisateur.username,
            }
        return None

    def get_date_formatee(self, obj):
        return localtime(obj.date_vente).strftime('%d/%m/%Y')

    def create(self, validated_data):
        lignes_data = validated_data.pop('lignes')
        magasin_id = validated_data.pop('magasin_id')
        request = self.context.get('request')
        utilisateur = request.user if request and request.user.is_authenticated else None
        
        try:
            from parametres.models import Magasin
            magasin = Magasin.objects.get(id=magasin_id)
        except Magasin.DoesNotExist:
            raise ValidationError(f"Magasin avec ID {magasin_id} introuvable.")

        vente = VenteCache.objects.create(utilisateur=utilisateur, magasin=magasin, **validated_data)
        montant_total = 0

        for ligne in lignes_data:
            produit_id = ligne['produit']
            quantite = ligne['quantite']

            try:
                produit = Produit.objects.get(id=produit_id)
            except Produit.DoesNotExist:
                raise ValidationError(f"Produit avec ID {produit_id} introuvable.")

            # Find the magasin in product
            magasin_index = -1
            magasin_codes = []
            
            for i, mag in enumerate(produit.magasins or []):
                if mag.get('id') == magasin_id:
                    magasin_index = i
                    magasin_codes = mag.get('codes_barres', [])
                    break
            
            if magasin_index == -1:
                raise ValidationError(
                    f"Le produit '{produit.nom}' n'est pas disponible dans le magasin sélectionné."
                )

            if len(magasin_codes) < quantite:
                raise ValidationError(
                    f"Quantité insuffisante pour le produit '{produit.nom}'. "
                    f"Disponible: {len(magasin_codes)}, demandé: {quantite}."
                )

            codes_utilises = magasin_codes[:quantite]
            
            # Update product
            updated_magasins = produit.magasins.copy()
            updated_magasins[magasin_index]['codes_barres'] = magasin_codes[quantite:]
            
            if not updated_magasins[magasin_index]['codes_barres']:
                updated_magasins.pop(magasin_index)
            
            prix_unitaire = float(produit.prix_vente_cache)
            sous_total = prix_unitaire * quantite

            LigneVenteCache.objects.create(
                vente=vente,
                produit=produit,
                quantite=quantite,
                prix_unitaire=prix_unitaire,
                sous_total=sous_total,
                codes_barres_utilises=codes_utilises
            )

            produit.magasins = updated_magasins
            produit._sync_quantite()
            produit.save()

            montant_total += sous_total

        vente.montant_total = montant_total
        vente.save()
        return vente