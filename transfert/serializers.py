# from rest_framework import serializers
# from .models import Transfert
# from produits.models import Produit
# from parametres.serializers import MagasinSerializer
# from authentification.serializers import CustomUserSerializer


# class TransfertSerializer(serializers.ModelSerializer):
#     produit_details = serializers.SerializerMethodField()
#     magasin_source_details = MagasinSerializer(source='magasin_source', read_only=True)
#     magasin_destination_details = MagasinSerializer(source='magasin_destination', read_only=True)
#     utilisateur_details = CustomUserSerializer(source='utilisateur', read_only=True)
#     warning = serializers.SerializerMethodField()
#     date_formatee = serializers.SerializerMethodField()
#     heure_formatee = serializers.SerializerMethodField()

#     class Meta:
#         model = Transfert
#         fields = '__all__'
#         read_only_fields = [
#             'magasin_source', 'utilisateur',
#             'codes_barres_transferes', 'date', 'heure',
#             'produit_supprime', 'warning'
#         ]

#     def get_date_formatee(self, obj):
#         return obj.date.strftime('%d/%m/%Y') if obj.date else None

#     def get_heure_formatee(self, obj):
#         return obj.heure.strftime('%H:%M') if obj.heure else None

#     def get_produit_details(self, obj):
#         return {
#             "id": obj.produit.id,
#             "nom": obj.produit.nom,
#             "quantite": obj.produit.quantite
#         }

#     def get_warning(self, obj):
#         return "Le produit source est marqué comme supprimé car le stock est épuisé." if obj.produit_supprime else None

#     def validate(self, data):
#         produit = data.get('produit')
#         quantite = data.get('quantite')
#         magasin_destination = data.get('magasin_destination')

#         if not produit or quantite is None:
#             return data

#         if quantite > produit.quantite:
#             raise serializers.ValidationError({
#                 'quantite': f"Stock insuffisant. Disponible: {produit.quantite}"
#             })

#         if magasin_destination and magasin_destination == produit.magasin:
#             raise serializers.ValidationError({
#                 'magasin_destination': "Le magasin de destination doit être différent du magasin source."
#             })

#         return data

#     def create(self, validated_data):
#         produit = validated_data['produit']
#         quantite = validated_data['quantite']
#         magasin_destination = validated_data['magasin_destination']
#         user = self.context['request'].user

#         # ✅ Codes-barres transférés
#         codes_transferes = produit.codes_barres[:quantite] if produit.codes_barres else []

#         # ✅ Mise à jour du produit source
#         produit.quantite -= quantite
#         if produit.quantite <= 0:
#             produit.est_supprime = True
#         if produit.codes_barres:
#             produit.codes_barres = produit.codes_barres[quantite:]
#         produit.save()

#         # ✅ Champs à copier intégralement
#         fields_to_copy = [
#             'taux_benefice_cache', 'prix_vente_cache',
#             'taux_benefice_3', 'taux_benefice_5',
#             'taux_benefice_8', 'taux_benefice_10',
#             'taux_benefice_6', 'taux_benefice_9',
#             'taux_benefice_12', 'taux_benefice_15',
#             'prix_vente_6', 'prix_vente_9',
#             'prix_vente_12', 'prix_vente_15',
#             'prix_vente_3', 'prix_vente_5',
#             'prix_vente_8', 'prix_vente_10'
#         ]

#         # ✅ Produit de destination : création ou réactivation
#         dest_produit, created = Produit.objects.get_or_create(
#             magasin=magasin_destination,
#             nom=produit.nom,
#             marque=produit.marque,
#             defaults={
#                 'reference': produit.reference,
#                 'famille': produit.famille,
#                 'prix_achat': produit.prix_achat,
#                 'codes_barres': codes_transferes,
#                 'quantite': quantite,
#                 'est_supprime': False,
#             }
#         )

#         # Copier les taux & prix même si déjà existant
#         for field in fields_to_copy:
#             setattr(dest_produit, field, getattr(produit, field))

#         if not created:
#             dest_produit.quantite += quantite
#             if codes_transferes:
#                 dest_produit.codes_barres = list(set(dest_produit.codes_barres + codes_transferes))
#             if dest_produit.est_supprime:
#                 dest_produit.est_supprime = False

#         dest_produit.save()

#         # ✅ Créer le transfert
#         transfert = Transfert.objects.create(
#             produit=produit,
#             magasin_source=produit.magasin,
#             magasin_destination=magasin_destination,
#             quantite=quantite,
#             codes_barres_transferes=codes_transferes,
#             utilisateur=user,
#             produit_supprime=produit.est_supprime
#         )

#         return transfert
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
            'utilisateur', 'codes_barres_transferes', 
            'date', 'heure', 'produit_supprime', 'warning'
        ]

    def get_date_formatee(self, obj):
        return obj.date.strftime('%d/%m/%Y') if obj.date else None

    def get_heure_formatee(self, obj):
        return obj.heure.strftime('%H:%M') if obj.heure else None

    def get_produit_details(self, obj):
        # Get quantity in source magasin
        source_quantity = 0
        for mag in obj.produit.magasins or []:
            if mag.get('id') == obj.magasin_source.id:
                source_quantity = len(mag.get('codes_barres', []))
                break
        
        return {
            "id": obj.produit.id,
            "nom": obj.produit.nom,
            "reference": obj.produit.reference,
            "quantite_source": source_quantity,
            "quantite_totale": obj.produit.quantite_totale
        }

    def get_warning(self, obj):
        return "Le produit source est épuisé dans ce magasin." if obj.produit_supprime else None

    def validate(self, data):
        produit = data.get('produit')
        quantite = data.get('quantite')
        magasin_source = data.get('magasin_source')
        magasin_destination = data.get('magasin_destination')

        if not produit or quantite is None:
            return data

        # Check if source and destination are the same
        if magasin_source and magasin_destination and magasin_source.id == magasin_destination.id:
            raise serializers.ValidationError({
                'magasin_destination': "Le magasin de destination doit être différent du magasin source."
            })

        # Get source quantity from magasins array
        source_quantity = 0
        for mag in produit.magasins or []:
            if mag.get('id') == magasin_source.id:
                source_quantity = len(mag.get('codes_barres', []))
                break

        if quantite > source_quantity:
            raise serializers.ValidationError({
                'quantite': f"Stock insuffisant dans le magasin source. Disponible: {source_quantity}"
            })

        return data

    def create(self, validated_data):
        produit = validated_data['produit']
        quantite = validated_data['quantite']
        magasin_source = validated_data['magasin_source']
        magasin_destination = validated_data['magasin_destination']
        user = self.context['request'].user

        # Find source magasin and get its codes
        source_magasin_index = -1
        source_codes = []
        
        for i, mag in enumerate(produit.magasins or []):
            if mag.get('id') == magasin_source.id:
                source_magasin_index = i
                source_codes = mag.get('codes_barres', [])
                break
        
        if source_magasin_index == -1:
            raise serializers.ValidationError("Magasin source non trouvé dans le produit")
        
        # Get the barcodes to transfer (take from the end for latest first)
        codes_to_transfer = source_codes[-quantite:] if quantite > 0 else []
        
        if len(codes_to_transfer) < quantite:
            raise serializers.ValidationError("Nombre de codes-barres insuffisant")
        
        # Update source magasin - remove transferred barcodes
        updated_source_codes = source_codes[:-quantite] if quantite > 0 else source_codes
        
        # Update the magasins array
        updated_magasins = produit.magasins.copy()
        if updated_source_codes:
            updated_magasins[source_magasin_index]['codes_barres'] = updated_source_codes
        else:
            # Remove magasin if empty
            updated_magasins.pop(source_magasin_index)
        
        # Find or create destination magasin entry
        dest_magasin_index = -1
        for i, mag in enumerate(updated_magasins):
            if mag.get('id') == magasin_destination.id:
                dest_magasin_index = i
                break
        
        if dest_magasin_index == -1:
            # Create new magasin entry
            updated_magasins.append({
                'id': magasin_destination.id,
                'nom': magasin_destination.nom,
                'adresse': getattr(magasin_destination, 'adresse', ''),
                'codes_barres': codes_to_transfer
            })
        else:
            # Add to existing magasin
            current_codes = updated_magasins[dest_magasin_index].get('codes_barres', [])
            updated_magasins[dest_magasin_index]['codes_barres'] = current_codes + codes_to_transfer
        
        # Update the product
        produit.magasins = updated_magasins
        produit._sync_quantite()  # Sync global codes_barres
        produit.save()
        
        # Check if source magasin is now empty
        source_empty = len(updated_source_codes) == 0
        
        # Create transfer record
        transfert = Transfert.objects.create(
            produit=produit,
            magasin_source=magasin_source,
            magasin_destination=magasin_destination,
            quantite=quantite,
            codes_barres_transferes=codes_to_transfer,
            utilisateur=user,
            produit_supprime=source_empty
        )
        
        return transfert