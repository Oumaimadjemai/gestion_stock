# authentification/migrations/0019_auto_20241215_1200.py

from django.db import migrations, models

def copy_telephone_to_telephones(apps, schema_editor):
    """Copier les données de l'ancien champ telephone vers telephones"""
    Client = apps.get_model('authentification', 'Client')
    
    for client in Client.objects.all():
        # Vérifier si l'ancien champ telephone a une valeur
        if client.telephone and str(client.telephone).strip():
            client.telephones = [str(client.telephone).strip()]
            print(f"Client {client.id}: {client.telephone} -> {client.telephones}")
        else:
            client.telephones = []
        client.save(update_fields=['telephones'])

def reverse_copy(apps, schema_editor):
    """Restaurer l'ancien champ à partir du premier téléphone (rollback)"""
    Client = apps.get_model('authentification', 'Client')
    
    for client in Client.objects.all():
        if client.telephones and len(client.telephones) > 0:
            client.telephone = client.telephones[0]
        else:
            client.telephone = None
        client.save(update_fields=['telephone'])

class Migration(migrations.Migration):
    dependencies = [
        ('authentification', '0018_customuser_magasin_access_type_and_more'),
    ]

    operations = [
        # 1. Ajouter le nouveau champ
        migrations.AddField(
            model_name='client',
            name='telephones',
            field=models.JSONField(blank=True, default=list, help_text='Liste des numéros de téléphone', verbose_name='أرقام الهاتف / Téléphones'),
        ),
        
        # 2. Copier les données de l'ancien vers le nouveau
        migrations.RunPython(copy_telephone_to_telephones, reverse_copy),
        
        # 3. Supprimer l'ancien champ
        migrations.RemoveField(
            model_name='client',
            name='telephone',
        ),
    ]