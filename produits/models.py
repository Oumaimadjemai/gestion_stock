


from django.db import models
from parametres.models import Magasin
from django.core.exceptions import ValidationError
import random
from cloudinary.models import CloudinaryField
from common.models import BaseModel
from common.managers import BaseManager


# ================= BARCODE =================
def compute_ean13_checksum(code12):
    pairs = [int(d) for d in code12]
    total = sum(pairs[i] if i % 2 == 0 else pairs[i] * 3 for i in range(12))
    return str((10 - total % 10) % 10)


def generer_codes_barres_uniques(existants, nombre):
    from produits.models import Produit

    existants_set = set(existants or [])
    for codes in Produit.objects.values_list("codes_barres", flat=True):
        if codes:
            existants_set.update(codes)

    nouveaux = set()
    while len(nouveaux) < nombre:
        base = ''.join(str(random.randint(0, 9)) for _ in range(12))
        code = base + compute_ean13_checksum(base)

        if code not in existants_set:
            nouveaux.add(code)

    return list(nouveaux)


# ================= MODEL =================
class Produit(BaseModel):
    reference = models.CharField(max_length=100, null=True, blank=True)
    nom = models.CharField(max_length=100)
    famille = models.CharField(max_length=100)
    marque = models.CharField(max_length=100, blank=True)

    codes_barres = models.JSONField(default=list, blank=True, null=True)

    image = CloudinaryField(blank=True, null=True)

    magasin_principal = models.ForeignKey(
        Magasin,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # 🔥 MAIN STRUCTURE
    magasins = models.JSONField(default=list, null=True, blank=True)
    """
    [
        {
            "id": 1,
            "nom": "Magasin A",
            "adresse": "...",
            "codes_barres": ["123", "456"]
        }
    ]
    """

    # ================= PRICE FIELDS =================
    prix_achat = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Cash price
    prix_vente_cache = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Installment prices for different durations
    prix_vente_3 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prix_vente_5 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prix_vente_6 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prix_vente_8 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prix_vente_9 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prix_vente_10 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prix_vente_12 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prix_vente_15 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # ================= PROFIT RATE FIELDS =================
    taux_benefice_cache = models.FloatField(null=True, blank=True)
    taux_benefice_3 = models.FloatField(null=True, blank=True)
    taux_benefice_5 = models.FloatField(null=True, blank=True)
    taux_benefice_6 = models.FloatField(null=True, blank=True)
    taux_benefice_8 = models.FloatField(null=True, blank=True)
    taux_benefice_9 = models.FloatField(null=True, blank=True)
    taux_benefice_10 = models.FloatField(null=True, blank=True)
    taux_benefice_12 = models.FloatField(null=True, blank=True)
    taux_benefice_15 = models.FloatField(null=True, blank=True)

    # ================= TIMESTAMP FIELDS =================
    date_creation = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    date_modification = models.DateTimeField(auto_now=True, null=True, blank=True)

    est_supprime = models.BooleanField(default=False)

    objects = BaseManager()

    # ================= PROPERTIES =================
    
    @property
    def codebar_principal(self):
        return self.codes_barres[0] if self.codes_barres else None
    
    @property
    def magasin_principal_quantite(self):
        """Get quantity in principal magasin"""
        if not self.magasin_principal:
            return 0
        
        # Check if principal magasin exists in magasins array
        for mag in self.magasins:
            if mag.get('id') == self.magasin_principal.id:
                return len(mag.get('codes_barres', []))
        return 0
    
    @property
    def moyenne_pourcentage_facilite(self):
        """Calculate average profit percentage for installment sales"""
        taux = [
            self.taux_benefice_3, self.taux_benefice_5, self.taux_benefice_6,
            self.taux_benefice_8, self.taux_benefice_9, self.taux_benefice_10,
            self.taux_benefice_12, self.taux_benefice_15
        ]
        taux_valides = [t for t in taux if t is not None]
        if not taux_valides:
            return 0
        moyenne = sum(taux_valides) / len(taux_valides)
        return float(round(moyenne, 2))
    
    @property
    def quantite_totale(self):
        return sum(len(mag.get('codes_barres', [])) for mag in self.magasins)

    @property
    def tous_les_magasins(self):
        return [
            {
                "id": mag["id"],
                "nom": mag["nom"],
                "adresse": mag.get("adresse"),
                "quantite": len(mag.get("codes_barres", [])),
                "codes_barres": mag.get("codes_barres", [])
            }
            for mag in self.magasins
        ]

    # ================= CORE LOGIC =================
    
    def _sync_quantite(self):
        """Always sync quantite with barcode count"""
        for mag in self.magasins:
            mag['quantite'] = len(mag.get('codes_barres', []))

        # global list
        self.codes_barres = list({
            code for mag in self.magasins
            for code in mag.get('codes_barres', [])
        })

    def get_quantite_par_magasin(self, magasin_id):
        for mag in self.magasins or []:
            if mag["id"] == magasin_id:
                return len(mag.get("codes_barres", []))
        return 0

    def set_principal_quantite(self, quantite):
        """Set quantity for principal magasin"""
        if not self.magasin_principal:
            return
        
        magasin_id = self.magasin_principal.id
        magasin_nom = self.magasin_principal.nom
        magasin_adresse = getattr(self.magasin_principal, 'adresse', '')
        
        # Generate codes for the quantity
        if quantite > 0:
            # Get current codes
            current_codes = []
            for mag in self.magasins:
                if mag.get('id') == magasin_id:
                    current_codes = mag.get('codes_barres', [])
                    break
            
            # Generate new codes if needed
            if len(current_codes) < quantite:
                needed = quantite - len(current_codes)
                nouveaux_codes = generer_codes_barres_uniques(self.codes_barres or [], needed)
            else:
                nouveaux_codes = []
            
            # Check if principal magasin exists in magasins array
            magasin_found = False
            for i, mag in enumerate(self.magasins):
                if mag.get('id') == magasin_id:
                    magasin_found = True
                    if quantite == 0:
                        self.magasins.pop(i)
                    else:
                        current_codes = mag.get('codes_barres', [])
                        # Keep only up to quantite codes
                        if len(current_codes) > quantite:
                            mag['codes_barres'] = current_codes[:quantite]
                        elif len(current_codes) < quantite:
                            mag['codes_barres'] = current_codes + nouveaux_codes
                    break
            
            # Add principal magasin if not found
            if not magasin_found and quantite > 0:
                self.magasins.append({
                    'id': magasin_id,
                    'nom': magasin_nom,
                    'adresse': magasin_adresse,
                    'codes_barres': nouveaux_codes
                })
            
            self._sync_quantite()
            self.save()

    # ================= STOCK METHODS =================

    def increment_stock(self, magasin: Magasin, quantite: int):
        nouveaux_codes = generer_codes_barres_uniques(self.codes_barres, quantite)

        for mag in self.magasins:
            if mag['id'] == magasin.id:
                mag.setdefault('codes_barres', [])
                mag['codes_barres'].extend(nouveaux_codes)
                self._sync_quantite()
                self.save()
                return nouveaux_codes

        # new magasin
        self.magasins.append({
            "id": magasin.id,
            "nom": magasin.nom,
            "adresse": getattr(magasin, 'adresse', ''),
            "codes_barres": nouveaux_codes
        })

        self._sync_quantite()
        self.save()

        return nouveaux_codes

    def decrement_stock(self, magasin: Magasin, quantite: int):
        for mag in self.magasins:
            if mag['id'] == magasin.id:
                codes = mag.get('codes_barres', [])

                if len(codes) < quantite:
                    raise ValueError("Stock insuffisant")

                removed = codes[:quantite]
                mag['codes_barres'] = codes[quantite:]

                if not mag['codes_barres']:
                    self.magasins.remove(mag)

                self._sync_quantite()
                self.save()

                return removed

        raise ValueError("Magasin non trouvé")

    def transfer_stock(self, from_magasin: Magasin, to_magasin: Magasin, quantite: int):
        codes = self.decrement_stock(from_magasin, quantite)

        for mag in self.magasins:
            if mag['id'] == to_magasin.id:
                mag['codes_barres'].extend(codes)
                self._sync_quantite()
                self.save()
                return

        self.magasins.append({
            "id": to_magasin.id,
            "nom": to_magasin.nom,
            "adresse": getattr(to_magasin, 'adresse', ''),
            "codes_barres": codes
        })

        self._sync_quantite()
        self.save()

    # ================= NEW STOCK METHODS FOR ACHATS =================
    
    def increment_quantite_par_magasin(self, magasin_id, magasin_nom, quantite):
        """Increment quantity for a specific magasin"""
        # Find or create magasin entry in magasins list
        magasin_found = False
        for mag in self.magasins:
            if mag.get('id') == magasin_id:
                mag.setdefault('codes_barres', [])
                # Generate new barcodes for this quantity
                nouveaux_codes = generer_codes_barres_uniques(self.codes_barres or [], quantite)
                mag['codes_barres'].extend(nouveaux_codes)
                magasin_found = True
                break
        
        if not magasin_found:
            # Create new magasin entry
            nouveaux_codes = generer_codes_barres_uniques(self.codes_barres or [], quantite)
            self.magasins.append({
                'id': magasin_id,
                'nom': magasin_nom,
                'adresse': '',
                'codes_barres': nouveaux_codes
            })
        
        self._sync_quantite()
        self.save()

    def decrement_quantite_par_magasin(self, magasin_id, quantite):
        """Decrement quantity for a specific magasin"""
        for mag in self.magasins:
            if mag.get('id') == magasin_id:
                codes = mag.get('codes_barres', [])
                if len(codes) < quantite:
                    raise ValueError(f"Stock insuffisant dans le magasin {magasin_id}")
                
                # Remove the barcodes (remove from the end for latest first)
                removed_codes = codes[-quantite:] if quantite > 0 else []
                mag['codes_barres'] = codes[:-quantite] if quantite > 0 else codes
                
                # Remove magasin entry if empty
                if not mag['codes_barres']:
                    self.magasins.remove(mag)
                
                self._sync_quantite()
                self.save()
                return removed_codes
        
        raise ValueError(f"Magasin {magasin_id} non trouvé")

    # ================= LEGACY METHODS (for compatibility) =================
    
    def incrementer_quantite(self, quantite):
        """Legacy method for compatibility"""
        if self.magasin_principal:
            self.increment_stock(self.magasin_principal, quantite)

    def decrementer_quantite(self, quantite):
        """Legacy method for compatibility"""
        if self.magasin_principal:
            self.decrement_stock(self.magasin_principal, quantite)

    # ================= SAVE METHOD =================

    def save(self, *args, **kwargs):
        self._sync_quantite()

        # check global uniqueness
        autres = Produit.objects.exclude(pk=self.pk)
        for p in autres:
            if set(self.codes_barres or []) & set(p.codes_barres or []):
                raise ValidationError("Code-barres déjà utilisé")

        super().save(*args, **kwargs)

    class Meta(BaseModel.Meta):
        db_table = 'produits_produit'
        indexes = BaseModel.Meta.indexes + [
            models.Index(fields=['nom']),
            models.Index(fields=['reference']),
            models.Index(fields=['famille']),
        ]
