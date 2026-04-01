# chat/signals.py - Optional, you can keep it or remove it
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import Message
import cloudinary.uploader

@receiver(pre_delete, sender=Message)
def delete_cloudinary_file(sender, instance, **kwargs):
    """Delete file from Cloudinary when message is deleted"""
    # Check if the instance has the file_public_id attribute
    if hasattr(instance, 'file_public_id') and instance.file_public_id:
        try:
            # Determine resource type based on file extension
            file_ext = instance.file_name.split('.')[-1].lower() if instance.file_name else ''
            resource_type = 'auto'
            if file_ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']:
                resource_type = 'image'
            elif file_ext in ['mp4', 'mov', 'avi', 'mkv', 'webm']:
                resource_type = 'video'
            else:
                resource_type = 'raw'
            
            cloudinary.uploader.destroy(instance.file_public_id, resource_type=resource_type)
            print(f"✅ Deleted file from Cloudinary: {instance.file_public_id}")
        except Exception as e:
            print(f"Error deleting file from Cloudinary: {e}")