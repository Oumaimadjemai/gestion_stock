from rest_framework import serializers
from .models import *

# class CustomUserSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = CustomUser
#         fields = ('username','role')

class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)  # Important: write_only
    
    class Meta:
        model = CustomUser
        fields = ['username', 'password', 'role','id']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            role=validated_data['role']
        )
        return user

# class FichierClientSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = FichierClient
#         fields = ['id', 'fichier']
from rest_framework import serializers
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


class ClientSerializer(serializers.ModelSerializer):
    fichiers = FichierClientSerializer(many=True, read_only=True)
    fichiers_upload = serializers.ListField(
        child=serializers.FileField(max_length=100000, allow_empty_file=False),
        write_only=True,
        required=False
    )

    class Meta:
        model = Client
        fields = '__all__'
        # extra_kwargs = {
        #     'code': {'write_only': True},
        #     'cle': {'write_only': True}
        # }

    def create(self, validated_data):
        fichiers_data = validated_data.pop('fichiers_upload', [])
        client = Client.objects.create(**validated_data)
        
        for fichier_data in fichiers_data:
            FichierClient.objects.create(
                client=client,
                fichier=fichier_data,
            )
        
        return client

    def update(self, instance, validated_data):
        fichiers_data = validated_data.pop('fichiers_upload', [])
        instance = super().update(instance, validated_data)
        
        for fichier_data in fichiers_data:
            FichierClient.objects.create(
                client=instance,
                fichier=fichier_data,
            )
        
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
