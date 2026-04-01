from django.core.management.base import BaseCommand
from django.db import connection, models
from django.apps import apps

class Command(BaseCommand):
    help = 'Create database indexes for all models'

    def handle(self, *args, **options):
        self.stdout.write("Creating database indexes...")
        
        # Define indexes for each model
        indexes = {
            'authentification.CustomUser': [
                models.Index(fields=['email']),
                models.Index(fields=['-date_joined']),
            ],
            'produits.Produit': [
                models.Index(fields=['nom']),
                models.Index(fields=['reference']),
                models.Index(fields=['famille']),
                models.Index(fields=['-date_creation']),
                models.Index(fields=['magasin_principal']),
            ],
            'ventes.Vente': [
                models.Index(fields=['-date_vente']),
                models.Index(fields=['utilisateur', '-date_vente']),
                models.Index(fields=['client', '-date_vente']),
            ],
            'achats.AchatGroupe': [
                models.Index(fields=['-date']),
                models.Index(fields=['fournisseur', '-date']),
            ],
            'depenses.Depense': [
                models.Index(fields=['-date']),
                models.Index(fields=['categorie', '-date']),
            ],
            'ventes.LigneVente': [
                models.Index(fields=['vente']),
                models.Index(fields=['produit']),
                models.Index(fields=['vente', 'produit']),
            ],
        }
        
        # Execute index creation
        for model_path, model_indexes in indexes.items():
            try:
                app_label, model_name = model_path.split('.')
                model = apps.get_model(app_label, model_name)
                
                self.stdout.write(f"Creating indexes for {model_path}...")
                
                # Create indexes via Django's schema editor
                with connection.schema_editor() as schema_editor:
                    for index in model_indexes:
                        try:
                            schema_editor.add_index(model, index)
                            self.stdout.write(f"  Created index: {index.fields}")
                        except Exception as e:
                            self.stdout.write(f"  Index already exists or error: {e}")
                            
            except Exception as e:
                self.stdout.write(f"Error with {model_path}: {e}")
        
        self.stdout.write(self.style.SUCCESS("Indexes created successfully!"))