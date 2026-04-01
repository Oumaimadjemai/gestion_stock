

from rest_framework import serializers
from .models import Produit
import cloudinary.uploader

class ProduitSerializer(serializers.ModelSerializer):
    codebar_principal = serializers.SerializerMethodField()
    moyenne_pourcentage_facilite = serializers.SerializerMethodField()
    nouveaux_codes_barres = serializers.SerializerMethodField()
    image = serializers.ImageField(required=False, allow_null=True)
    quantite_totale = serializers.ReadOnlyField()
    tous_les_magasins = serializers.ReadOnlyField()
    magasin_principal_detail = serializers.SerializerMethodField()
    magasin_principal_quantite = serializers.IntegerField(read_only=True)

    class Meta:
        model = Produit
        fields = [
            'id', 'reference', 'codes_barres', 'codebar_principal', 'nom', 'famille',
            'marque', 'image', 'prix_achat', 'taux_benefice_cache', 'prix_vente_cache',
            'taux_benefice_3', 'taux_benefice_5', 'taux_benefice_8', 'taux_benefice_10',
            'taux_benefice_6', 'taux_benefice_9', 'taux_benefice_12', 'taux_benefice_15',
            'prix_vente_6', 'prix_vente_9', 'prix_vente_12', 'prix_vente_15',
            'prix_vente_3', 'prix_vente_5', 'prix_vente_8', 'prix_vente_10',
            'magasin_principal', 'magasin_principal_detail', 'magasin_principal_quantite',
            'magasins', 'tous_les_magasins', 'quantite_totale', 'date_creation',
            'date_modification', 'moyenne_pourcentage_facilite',
            'nouveaux_codes_barres', 'est_supprime',
        ]

    def get_magasin_principal_detail(self, obj):
        if obj.magasin_principal:
            return {
                'id': obj.magasin_principal.id,
                'nom': obj.magasin_principal.nom,
                'adresse': getattr(obj.magasin_principal, 'adresse', '')
            }
        return None

    def get_codebar_principal(self, obj):
        return obj.codebar_principal

    def get_moyenne_pourcentage_facilite(self, obj):
        return obj.moyenne_pourcentage_facilite

    def get_nouveaux_codes_barres(self, obj):
        return getattr(obj, 'nouveaux_codes_barres', [])

    def validate_magasins(self, value):
        """Validate magasins structure"""
        if not isinstance(value, list):
            raise serializers.ValidationError("magasins must be a list")
        for mag in value:
            if not isinstance(mag, dict):
                raise serializers.ValidationError("Each magasin must be an object")
            if 'id' not in mag or 'nom' not in mag:
                raise serializers.ValidationError("Each magasin must have id and nom")
        return value

    def validate_codes_barres(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Doit être une liste de codes-barres")
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Les codes-barres doivent être uniques")
        return value

    def create(self, validated_data):
        # Remove any fields that shouldn't be in create
        validated_data.pop('magasin_principal_quantite', None)
        
        produit = Produit.objects.create(**validated_data)
        return produit

    def update(self, instance, validated_data):
        # Handle clearing image
        if 'image' in validated_data:
            if validated_data['image'] in ["", None]:
                if instance.image:
                    public_id = str(instance.image.public_id)
                    if public_id:
                        cloudinary.uploader.destroy(public_id)
                validated_data['image'] = None
        
        return super().update(instance, validated_data)

class ProduitMiniSerializer(serializers.ModelSerializer):
    quantite_totale = serializers.ReadOnlyField()
    
    class Meta:
        model = Produit
        fields = ['id', 'reference', 'nom', 'codes_barres', 'quantite_totale', 'est_supprime']