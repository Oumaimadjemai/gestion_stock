# authentification/migrations/0020_drop_old_telephone.py

from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('authentification', '0019_client_telephones'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE authentification_client DROP COLUMN IF EXISTS telephone;",
            reverse_sql="ALTER TABLE authentification_client ADD COLUMN telephone varchar(20) NULL;"
        ),
    ]