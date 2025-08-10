from rest_framework import serializers
from .models import Transfert
from produits.models import Produit
from parametres.serializers import MagasinSerializer
from authentification.serializers import CustomUserSerializer

class TransfertSerializer(serializers.ModelSerializer):
    produit_details = serializers.SerializerMethodField()
    magasin_source_details = MagasinSerializer(source='magasin_source', read_only=True)
    magasin_destination_details = MagasinSerializer(source='magasin_destination', read_only=True)
    utilisateur_details = CustomUserSerializer(source='utilisateur', read_only=True)
    warning = serializers.SerializerMethodField()
    date_formatee = serializers.SerializerMethodField()
    heure_formatee = serializers.SerializerMethodField()

    class Meta:
        model = Transfert
        fields = '__all__'
        read_only_fields = [
            'magasin_source', 'utilisateur',
            'codes_barres_transferes', 'date', 'heure',
            'produit_supprime', 'warning'
        ]
        
    def get_date_formatee(self, obj):
        return obj.date.strftime('%d/%m/%Y') if obj.date else None

    def get_heure_formatee(self, obj):
        return obj.heure.strftime('%H:%M') if obj.heure else None

    def get_produit_details(self, obj):
        return {
            "id": obj.produit.id,
            "nom": obj.produit.nom,
            "quantite": obj.produit.quantite
        }

    def get_warning(self, obj):
        return "Le produit source est marqué comme supprimé car le stock est épuisé." if obj.produit_supprime else None

    def validate(self, data):
     produit = data.get('produit')
     quantite = data.get('quantite')
     magasin_destination = data.get('magasin_destination')

     if not produit or quantite is None:
         return data

     if quantite > produit.quantite:
        raise serializers.ValidationError({
            'quantite': f"Stock insuffisant. Disponible: {produit.quantite}"
        })

     if magasin_destination and magasin_destination == produit.magasin:
        raise serializers.ValidationError({
            'magasin_destination': "Le magasin de destination doit être différent du magasin source."
        })

     return data


    def create(self, validated_data):
      produit = validated_data['produit']
      quantite = validated_data['quantite']
      magasin_destination = validated_data['magasin_destination']
      user = self.context['request'].user

    # Préparer les codes_barres à transférer
      codes_transferes = produit.codes_barres[:quantite] if produit.codes_barres else []

    # Mettre à jour produit source
      produit.quantite -= quantite
      if produit.quantite <= 0:
        produit.est_supprime = True

      if produit.codes_barres:
        produit.codes_barres = produit.codes_barres[quantite:]

      produit.save()

    # Produit destination : chercher s’il existe déjà
      dest_produit, created = Produit.objects.get_or_create(
        magasin=magasin_destination,
        nom=produit.nom,
        marque=produit.marque,
        defaults={
           'reference':produit.reference,
            'famille': produit.famille,
            'prix_achat': produit.prix_achat,
            'prix_vente_cache': produit.prix_vente_cache,
            'prix_vente_3': produit.prix_vente_3,
            'prix_vente_5': produit.prix_vente_5,
            'prix_vente_6': produit.prix_vente_6,
            'prix_vente_8': produit.prix_vente_8,
            'prix_vente_9': produit.prix_vente_9,
            'prix_vente_10': produit.prix_vente_10,
            'prix_vente_12': produit.prix_vente_12,
            'prix_vente_15': produit.prix_vente_15,
            'image': produit.image,
            'codes_barres': codes_transferes,
            'quantite': quantite,
        }
    )

      if not created:
        # Mise à jour produit existant
        dest_produit.quantite += quantite

        if codes_transferes:
            dest_produit.codes_barres = list(set(dest_produit.codes_barres + codes_transferes))

        if dest_produit.est_supprime:
            dest_produit.est_supprime = False

        dest_produit.save()

    # Créer transfert
      transfert = Transfert.objects.create(
        produit=produit,
        magasin_source=produit.magasin,
        magasin_destination=magasin_destination,
        quantite=quantite,
        codes_barres_transferes=codes_transferes,
        utilisateur=user,
        produit_supprime=produit.est_supprime
    )

      return transfert
