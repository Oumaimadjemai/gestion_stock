# inventaire/models.py
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from produits.models import Produit
from parametres.models import Magasin
from common.models import BaseModel
from common.managers import BaseManager
from decimal import Decimal
import json


class SessionInventaire(BaseModel):
    """
    Inventory counting session
    """
    magasin = models.ForeignKey(
        Magasin, 
        on_delete=models.CASCADE,
        related_name='sessions_inventaire'
    )
    date_debut = models.DateTimeField(auto_now_add=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    est_termine = models.BooleanField(default=False)
    est_annule = models.BooleanField(default=False)
    
    # Statistics
    total_produits_attendus = models.IntegerField(default=0)  # Total expected items
    total_produits_comptes = models.IntegerField(default=0)   # Total counted items
    total_produits_manquants = models.IntegerField(default=0)  # Missing items
    total_produits_excedents = models.IntegerField(default=0)  # Excess items
    
    # User who performed the inventory
    compteur_par = models.CharField(max_length=255, null=True, blank=True)
    
    objects = BaseManager()
    
    @property
    def taux_avancement(self):
        """Calculate completion rate"""
        if self.total_produits_attendus == 0:
            return 0
        return (self.total_produits_comptes / self.total_produits_attendus) * 100
    
    @property
    def duree(self):
        """Calculate session duration"""
        if self.date_fin:
            return (self.date_fin - self.date_debut).total_seconds() / 3600
        return (timezone.now() - self.date_debut).total_seconds() / 3600
    
    def terminer(self):
        """Mark session as completed"""
        self.est_termine = True
        self.date_fin = timezone.now()
        self.save()
    
    def annuler(self):
        """Cancel the inventory session"""
        self.est_annule = True
        self.date_fin = timezone.now()
        self.save()
    
    class Meta:
        db_table = 'inventaire_session'
        ordering = ['-date_debut']


class ProduitInventaire(models.Model):
    """
    Product inventory count details
    """
    session = models.ForeignKey(
        SessionInventaire,
        on_delete=models.CASCADE,
        related_name='produits_inventaire'
    )
    produit = models.ForeignKey(
        Produit,
        on_delete=models.CASCADE,
        related_name='inventaires'
    )
    
    # Expected values (from system)
    quantite_attendue = models.IntegerField(default=0)
    valeur_attendue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Counted values
    quantite_comptee = models.IntegerField(default=0)
    valeur_comptee = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Differences
    quantite_ecart = models.IntegerField(default=0)
    valeur_ecart = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Status
    est_verifie = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventaire_produit'
        unique_together = ['session', 'produit']
        indexes = [
            models.Index(fields=['session', 'est_verifie']),
            models.Index(fields=['produit']),
        ]
    
    def calculer_ecarts(self):
        """Calculate differences between expected and counted"""
        self.quantite_ecart = self.quantite_comptee - self.quantite_attendue
        
        # Calculate value difference
        prix_unitaire = self.produit.prix_achat or 0
        self.valeur_attendue = self.quantite_attendue * prix_unitaire
        self.valeur_comptee = self.quantite_comptee * prix_unitaire
        self.valeur_ecart = self.valeur_comptee - self.valeur_attendue
        
        self.save()
    
    def sauvegarder_comptage(self, quantite_comptee):
        """Save counted quantity and calculate differences"""
        self.quantite_comptee = quantite_comptee
        self.calculer_ecarts()
        
    def valider(self):
        """Mark as verified"""
        self.est_verifie = True
        self.save()


class MouvementInventaire(models.Model):
    """
    Track inventory movements during counting
    """
    TYPES_MOUVEMENT = [
        ('count', 'Comptage'),
        ('adjust', 'Ajustement'),
        ('verify', 'Vérification'),
        ('cancel', 'Annulation'),
    ]
    
    produit_inventaire = models.ForeignKey(
        ProduitInventaire,
        on_delete=models.CASCADE,
        related_name='mouvements'
    )
    type_mouvement = models.CharField(max_length=20, choices=TYPES_MOUVEMENT)
    ancienne_quantite = models.IntegerField(default=0)
    nouvelle_quantite = models.IntegerField(default=0)
    codes_barres_scannes = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True, null=True)
    effectue_par = models.CharField(max_length=255, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'inventaire_mouvement'
        ordering = ['-date_creation']


class EcartInventaire(models.Model):
    """
    Inventory discrepancies (missing or excess items)
    """
    TYPES_ECART = [
        ('missing', 'Manquant'),
        ('excess', 'Excédent'),
        ('damaged', 'Endommagé'),
        ('expired', 'Périmé'),
    ]
    
    STATUTS = [
        ('pending', 'En attente'),
        ('investigating', 'En investigation'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    ]
    
    produit_inventaire = models.ForeignKey(
        ProduitInventaire,
        on_delete=models.CASCADE,
        related_name='ecarts'
    )
    type_ecart = models.CharField(max_length=20, choices=TYPES_ECART)
    quantite = models.IntegerField()
    valeur = models.DecimalField(max_digits=15, decimal_places=2)
    statut = models.CharField(max_length=20, choices=STATUTS, default='pending')
    cause = models.TextField(blank=True)
    resolution = models.TextField(blank=True)
    
    # Who reported and who resolved
    declare_par = models.CharField(max_length=255, blank=True)
    resolue_par = models.CharField(max_length=255, blank=True, null=True)
    date_resolution = models.DateTimeField(null=True, blank=True)
    
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'inventaire_ecart'
        indexes = [
            models.Index(fields=['statut']),
            models.Index(fields=['type_ecart']),
        ]
    
    def resoudre(self, resolution, resolved_by):
        """Mark discrepancy as resolved"""
        self.resolution = resolution
        self.resolue_par = resolved_by
        self.date_resolution = timezone.now()
        self.statut = 'approved'
        self.save()
    
    def rejeter(self, reason):
        """Reject discrepancy"""
        self.resolution = reason
        self.statut = 'rejected'
        self.save()