from rest_framework import serializers
from .models import *
from parametres.models import Magasin


# class CustomUserSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True)  # Important: write_only
    
#     class Meta:
#         model = CustomUser
#         fields = ['username', 'password', 'role','id','features']
#         extra_kwargs = {
#             'password': {'write_only': True}
#         }
    
#     def create(self, validated_data):
#         user = CustomUser.objects.create_user(
#             username=validated_data['username'],
#             password=validated_data['password'],
#             role=validated_data['role']
#         )
#         return user
class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    # 👉 écriture : id du magasin
    magasin = serializers.PrimaryKeyRelatedField(
        queryset=Magasin.objects.all(),
        required=False,
        allow_null=True
    )
    
    # 👉 écriture : ids des magasins accessibles
    magasins_acces = serializers.PrimaryKeyRelatedField(
        queryset=Magasin.objects.all(),
        many=True,
        required=False
    )

    # 👉 lecture : détails magasin
    magasin_detail = serializers.SerializerMethodField(read_only=True)
    magasins_acces_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'username',
            'password',
            'role',
            'magasin',
            'magasin_detail',
            'magasins_acces',
            'magasins_acces_detail',
            'magasin_access_type',
            'features'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def get_magasin_detail(self, obj):
        if obj.magasin:
            return {
                "id": obj.magasin.id,
                "nom": obj.magasin.nom,
                "adresse": obj.magasin.adresse,
            }
        return None
    
    def get_magasins_acces_detail(self, obj):
        return [
            {
                "id": mag.id,
                "nom": mag.nom,
                "adresse": mag.adresse,
            }
            for mag in obj.magasins_acces.all()
        ]

    def validate(self, attrs):
        role = attrs.get('role', getattr(self.instance, 'role', None))
        magasin = attrs.get('magasin', getattr(self.instance, 'magasin', None))
        magasin_access_type = attrs.get('magasin_access_type', getattr(self.instance, 'magasin_access_type', 'assigned_only'))
        magasins_acces = attrs.get('magasins_acces', [])

        if role != 'admin':
            # For non-admin users, they must have at least one magasin assigned
            if magasin_access_type == 'assigned_only' and not magasin:
                raise serializers.ValidationError(
                    "Un vendeur ou magasinier avec accès uniquement au magasin assigné doit avoir un magasin assigné."
                )
            if magasin_access_type == 'selected_magasins' and not magasins_acces:
                raise serializers.ValidationError(
                    "Un vendeur ou magasinier avec accès à des magasins sélectionnés doit avoir au moins un magasin sélectionné."
                )
        
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        magasins_acces = validated_data.pop('magasins_acces', [])
        
        user = CustomUser.objects.create_user(
            username=validated_data.get('username'),
            password=password,
            role=validated_data.get('role'),
            magasin=validated_data.get('magasin', None),
            magasin_access_type=validated_data.get('magasin_access_type', 'assigned_only'),
            features=validated_data.get('features', []),
            is_active=validated_data.get('is_active', True)
        )
        
        # Add accessible magasins
        if magasins_acces:
            user.magasins_acces.set(magasins_acces)
        
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        magasins_acces = validated_data.pop('magasins_acces', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)
        
        if magasins_acces is not None:
            instance.magasins_acces.set(magasins_acces)

        instance.save()
        return instance

from .models import FichierClient

class FichierClientSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = FichierClient
        fields = ['id', 'url', 'type', 'name']

    def get_url(self, obj):
        return obj.fichier.url if obj.fichier else None

    def get_name(self, obj):
        if not obj.fichier:
            return None
        # CloudinaryField => on peut récupérer public_id et format
        try:
            return obj.fichier.public_id.split('/')[-1] + '.' + obj.fichier.format
        except Exception:
            return obj.fichier.name.split('/')[-1]

    def get_type(self, obj):
        if not obj.fichier or not obj.fichier.format:
            return "other"
        fmt = obj.fichier.format.lower()
        if fmt in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            return "image"
        elif fmt == 'pdf':
            return "pdf"
        return "other"


# class ClientSerializer(serializers.ModelSerializer):
#     fichiers = FichierClientSerializer(many=True, read_only=True)
#     fichiers_upload = serializers.ListField(
#         child=serializers.FileField(max_length=100000, allow_empty_file=False),
#         write_only=True,
#         required=False
#     )

#     class Meta:
#         model = Client
#         fields = '__all__'
#         # extra_kwargs = {
#         #     'code': {'write_only': True},
#         #     'cle': {'write_only': True}
#         # }

#     def create(self, validated_data):
#         fichiers_data = validated_data.pop('fichiers_upload', [])
#         client = Client.objects.create(**validated_data)
        
#         for fichier_data in fichiers_data:
#             FichierClient.objects.create(
#                 client=client,
#                 fichier=fichier_data,
#             )
        
#         return client

#     def update(self, instance, validated_data):
#         fichiers_data = validated_data.pop('fichiers_upload', [])
#         instance = super().update(instance, validated_data)
        
#         for fichier_data in fichiers_data:
#             FichierClient.objects.create(
#                 client=instance,
#                 fichier=fichier_data,
#             )
        
#         return instance
    
class ClientSerializer(serializers.ModelSerializer):
    fichiers = FichierClientSerializer(many=True, read_only=True)

    # Ajout de nouveaux fichiers
    fichiers_upload = serializers.ListField(
        child=serializers.FileField(max_length=100000, allow_empty_file=False),
        write_only=True,
        required=False
    )

    # Mise à jour/remplacement de fichiers existants
    fichiers_update = serializers.ListField(
        child=serializers.DictField(),  # ex: {"id": 1, "fichier": <InMemoryUploadedFile>}
        write_only=True,
        required=False
    )

    class Meta:
        model = Client
        fields = '__all__'

    def create(self, validated_data):
        fichiers_data = validated_data.pop('fichiers_upload', [])
        client = Client.objects.create(**validated_data)

        # 🔹 Ajout des fichiers uploadés
        for fichier_data in fichiers_data:
            FichierClient.objects.create(client=client, fichier=fichier_data)

        return client

    def update(self, instance, validated_data):
        fichiers_data = validated_data.pop('fichiers_upload', [])
        fichiers_update_data = validated_data.pop('fichiers_update', [])

        # 🔹 Mise à jour des champs de base du client
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # 🔹 Ajout de nouveaux fichiers
        for fichier_data in fichiers_data:
            FichierClient.objects.create(client=instance, fichier=fichier_data)

        # 🔹 Mise à jour/remplacement des fichiers existants
        for fichier_dict in fichiers_update_data:
            fichier_id = fichier_dict.get("id")
            fichier_new = fichier_dict.get("fichier")

            if fichier_id and fichier_new:
                try:
                    fichier_obj = FichierClient.objects.get(id=fichier_id, client=instance)
                    fichier_obj.fichier.delete(save=False)  # supprime l'ancien fichier du stockage
                    fichier_obj.fichier = fichier_new
                    fichier_obj.save()
                except FichierClient.DoesNotExist:
                    continue  # ignore si le fichier n’existe pas

        return instance
 
class FournisseurSerializer(serializers.ModelSerializer):
    wilaya_display = serializers.CharField(source='get_wilaya_display', read_only=True)
    
    class Meta:
        model = Fournisseur
        fields = [
            'id',
            'nom',
            'adresse',
            'telephone',
            'wilaya',
            'wilaya_display',
            'dettes_initiales',
            'date_creation',
            'date_modification'
        ]
        extra_kwargs = {
            'date_creation': {'read_only': True},
            'date_modification': {'read_only': True},
        }
