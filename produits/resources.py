from import_export import resources
from .models import Produit

class ProduitResource(resources.ModelResource):
    class Meta:
        model = Produit
        fields = (
            'id', 
            'reference', 
            'nom', 
            'famille', 
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
        export_order = (
            'id', 
            'reference', 
            'nom', 
            'famille', 
            'marque',
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
            'taux_benefice_cache',
            'taux_benefice_3', 
            'taux_benefice_5', 
            'taux_benefice_6',
            'taux_benefice_8', 
            'taux_benefice_9', 
            'taux_benefice_10',
            'taux_benefice_12', 
            'taux_benefice_15',
            'codes_barres',
            'date_creation',
            'date_modification',
            'est_supprime',
        )
    
    def dehydrate_codes_barres(self, produit):
        """Convert codes_barres list to string for Excel"""
        if produit.codes_barres:
            return ', '.join(produit.codes_barres)
        return ''
    
    def dehydrate_magasins(self, produit):
        """Convert magasins JSON to string for Excel"""
        if produit.magasins:
            return '; '.join([f"{m.get('nom')}: {m.get('quantite')}" for m in produit.magasins])
        return ''
    
    def dehydrate_quantite_totale(self, produit):
        """Export total quantity"""
        return produit.quantite_totale