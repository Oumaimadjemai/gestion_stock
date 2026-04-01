# inventaire/serializers.py
from rest_framework import serializers
from .models import (
    SessionInventaire, ProduitInventaire, 
    MouvementInventaire, EcartInventaire
)
from produits.models import Produit
from produits.serializers import ProduitSerializer


class ProduitInventaireSerializer(serializers.ModelSerializer):
    produit_details = ProduitSerializer(source='produit', read_only=True)
    
    class Meta:
        model = ProduitInventaire
        fields = [
            'id', 'produit', 'produit_details', 'quantite_attendue',
            'quantite_comptee', 'valeur_attendue', 'valeur_comptee',
            'quantite_ecart', 'valeur_ecart', 'est_verifie', 'notes'
        ]


class MouvementInventaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = MouvementInventaire
        fields = '__all__'


class EcartInventaireSerializer(serializers.ModelSerializer):
    produit_details = serializers.SerializerMethodField()
    
    class Meta:
        model = EcartInventaire
        fields = '__all__'
    
    def get_produit_details(self, obj):
        return {
            'id': obj.produit_inventaire.produit.id,
            'nom': obj.produit_inventaire.produit.nom,
            'reference': obj.produit_inventaire.produit.reference,
            'codes_barres': obj.produit_inventaire.produit.codes_barres
        }


class SessionInventaireSerializer(serializers.ModelSerializer):
    produits = ProduitInventaireSerializer(many=True, read_only=True)
    ecarts = serializers.SerializerMethodField()
    
    class Meta:
        model = SessionInventaire
        fields = [
            'id', 'magasin', 'date_debut', 'date_fin', 'est_termine',
            'est_annule', 'total_produits_attendus', 'total_produits_comptes',
            'total_produits_manquants', 'total_produits_excedents',
            'compteur_par', 'produits', 'ecarts', 'taux_avancement', 'duree'
        ]
        read_only_fields = ['date_debut', 'taux_avancement', 'duree']
    
    def get_ecarts(self, obj):
        ecarts = EcartInventaire.objects.filter(
            produit_inventaire__session=obj
        ).select_related('produit_inventaire__produit')
        return EcartInventaireSerializer(ecarts, many=True).data


class SessionInventaireDetailSerializer(SessionInventaireSerializer):
    mouvements = serializers.SerializerMethodField()
    
    class Meta(SessionInventaireSerializer.Meta):
        fields = SessionInventaireSerializer.Meta.fields + ['mouvements']
    
    def get_mouvements(self, obj):
        mouvements = MouvementInventaire.objects.filter(
            produit_inventaire__session=obj
        )
        return MouvementInventaireSerializer(mouvements, many=True).data


class ComptageBarreSerializer(serializers.Serializer):
    barcode = serializers.CharField(max_length=100)
    produit_id = serializers.IntegerField(required=False)
    
    def validate_barcode(self, value):
        # Verify barcode exists
        from produits.models import Produit
        
        produit = Produit.objects.filter(codes_barres__contains=[value]).first()
        if not produit:
            raise serializers.ValidationError("Code-barres non trouvé")
        
        return value