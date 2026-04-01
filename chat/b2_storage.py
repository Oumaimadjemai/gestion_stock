# chat/b2_storage.py
import os
import uuid
from b2sdk.v2 import *
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class BackblazeStorage:
    def __init__(self):
        self.bucket = None
        self.b2_api = None
        self.info = None
        self._initialized = False
        
    def _initialize(self):
        """Initialize Backblaze connection only when needed"""
        if self._initialized:
            return
        
        try:
            # Initialize B2
            self.info = InMemoryAccountInfo()
            self.b2_api = B2Api(self.info)
            
            # Authorize with your credentials
            self.b2_api.authorize_account(
                "production", 
                settings.B2_ACCOUNT_ID, 
                settings.B2_APPLICATION_KEY
            )
            
            # Get bucket
            try:
                self.bucket = self.b2_api.get_bucket_by_name(settings.B2_BUCKET_NAME)
                logger.info(f"✅ Connected to bucket: {settings.B2_BUCKET_NAME}")
                self._initialized = True
            except Exception as e:
                logger.error(f"❌ Bucket not found: {e}")
                self.bucket = None
                
        except Exception as e:
            logger.error(f"❌ Backblaze authorization failed: {e}")
            self.bucket = None
    
    def upload_file(self, file_obj, room_id, user_id):
        """Upload file to Backblaze B2"""
        self._initialize()
        
        if not self.bucket:
            return {
                'success': False,
                'error': 'Backblaze storage not available'
            }
        
        try:
            # Generate unique filename
            file_extension = os.path.splitext(file_obj.name)[1]
            unique_filename = f"{uuid.uuid4()}_{file_obj.name}"
            file_path = f"rooms/{room_id}/user_{user_id}/{unique_filename}"
            
            # Read file content
            file_content = file_obj.read()
            
            # Upload to B2
            uploaded_file = self.bucket.upload_bytes(
                file_content,
                file_path,
                content_type=file_obj.content_type
            )
            
            # Get download URL
            download_url = self.bucket.get_download_url(file_path)
            
            logger.info(f"✅ File uploaded to B2: {file_path}")
            
            return {
                'success': True,
                'file_url': download_url,
                'file_path': file_path,
                'file_name': file_obj.name,
                'file_size': len(file_content)
            }
            
        except Exception as e:
            logger.error(f"❌ Upload error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_download_url(self, file_path):
        """Get download URL for a file"""
        self._initialize()
        if self.bucket:
            return self.bucket.get_download_url(file_path)
        return None
    
    def delete_file(self, file_path):
        """Delete file from Backblaze B2"""
        self._initialize()
        if not self.bucket:
            return False
            
        try:
            file_version = self.bucket.get_file_info_by_name(file_path)
            if file_version:
                self.bucket.delete_file_version(
                    file_version.id_,
                    file_version.file_name
                )
                logger.info(f"✅ Deleted file from B2: {file_path}")
                return True
        except Exception as e:
            logger.error(f"❌ Error deleting file: {e}")
        return False


# Create a singleton instance
b2_storage = BackblazeStorage()