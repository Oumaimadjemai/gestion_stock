from import_export import resources
from .models import *

class ClientResource(resources.ModelResource):
    class Meta:
        model = Client
        fields = (
            'id', 'nom_famille_fr','nom_famille_ar', 'prenom_fr','nom_pere','nom_mere', 'ccp','cle',
            'nom_famille_ar', 'prenom_ar', 'adresse', 'telephones',
            'numero_national', 'profession', 'revenu', 
            'numero_piece_identite', 'type_piece_identite',
            'date_naissance', 'lieu_naissance','date_emission_piece','jour',
            'lieu_emission_piece','dette_initiale','note','recuperer_fichiers',
        )

    def dehydrate_telephones(self, client):
        """Convertir la liste en chaîne pour l'export Excel"""
        if client.telephones and len(client.telephones) > 0:
            return ', '.join(client.telephones)
        return ''
    
    def before_import_row(self, row, **kwargs):
        """Convertir la chaîne de téléphones en liste lors de l'import"""
        if 'telephones' in row and row['telephones']:
            # Si c'est une chaîne avec des virgules
            if isinstance(row['telephones'], str) and ',' in row['telephones']:
                row['telephones'] = [p.strip() for p in row['telephones'].split(',')]
            elif isinstance(row['telephones'], str):
                row['telephones'] = [row['telephones']]
        else:
            row['telephones'] = []
class FournisseurResource(resources.ModelResource):
    class Meta:
        model = Fournisseur
        fields = ('id', 'nom', 'adresse', 'telephone', 'wilaya','dettes_initiales')
