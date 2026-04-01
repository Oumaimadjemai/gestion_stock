# chat/views.py
from datetime import time

from rest_framework import generics, permissions, status, parsers
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .models import ChatRoom, Message
from .serializers import ChatRoomSerializer, MessageSerializer
from django.contrib.auth import get_user_model
from rest_framework.parsers import MultiPartParser, FormParser
import cloudinary.uploader
import cloudinary
import os

User = get_user_model()


# chat/views.py
class ChatRoomListCreateView(generics.ListCreateAPIView):
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatRoom.objects.filter(
            Q(participants=self.request.user) | Q(is_private=False)
        ).distinct()

    def perform_create(self, serializer):
        print(f"📝 Creating room with data: {serializer.validated_data}")
        room = serializer.save(created_by=self.request.user)
        room.participants.add(self.request.user)
        print(f"✅ Room created: {room.id} - {room.name}")

        participants = self.request.data.get('participants', [])
        for user_id in participants:
            try:
                user = User.objects.get(id=user_id)
                room.participants.add(user)
                print(f"  Added participant: {user.username}")
            except User.DoesNotExist:
                print(f"  User {user_id} not found")
                pass

class ChatRoomDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ChatRoom.objects.all()
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        room = self.get_object()
        # Only creator can delete the room
        if room.created_by != request.user:
            return Response(
                {'error': 'Only the room creator can delete this room'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class AddParticipantsToRoomView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, room_id):
        room = get_object_or_404(ChatRoom, id=room_id)
        
        # Check if user is a participant
        if request.user not in room.participants.all():
            return Response(
                {'error': 'You are not a participant in this room'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get user IDs to add
        user_ids = request.data.get('user_ids', [])
        if not user_ids:
            return Response(
                {'error': 'No user IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        added_users = []
        for user_id in user_ids:
            try:
                user = User.objects.get(id=user_id)
                if user not in room.participants.all():
                    room.participants.add(user)
                    added_users.append(user.username)
            except User.DoesNotExist:
                pass
        
        return Response({
            'message': f'Added users: {", ".join(added_users)}',
            'added_count': len(added_users)
        })


class RemoveParticipantFromRoomView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, room_id):
        room = get_object_or_404(ChatRoom, id=room_id)
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if the requesting user is the creator or the user themselves
        if request.user != room.created_by and request.user != user:
            return Response(
                {'error': 'Only the room creator or the user themselves can remove participants'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Cannot remove the creator if they are the only admin
        if user == room.created_by and room.participants.count() == 1:
            return Response(
                {'error': 'Cannot remove the last participant. Delete the room instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user in room.participants.all():
            room.participants.remove(user)
            return Response({'message': f'User {user.username} removed from room'})
        
        return Response(
            {'error': 'User is not a participant'},
            status=status.HTTP_400_BAD_REQUEST
        )


class LeaveRoomView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, room_id):
        room = get_object_or_404(ChatRoom, id=room_id)
        
        if request.user not in room.participants.all():
            return Response(
                {'error': 'You are not a participant in this room'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # If user is the creator and there are other participants, transfer ownership
        if request.user == room.created_by and room.participants.count() > 1:
            # Find another participant to be the new creator
            new_creator = room.participants.exclude(id=request.user.id).first()
            if new_creator:
                room.created_by = new_creator
                room.save()
        
        # Remove user from participants
        room.participants.remove(request.user)
        
        # If room has no participants, delete it
        if room.participants.count() == 0:
            room.delete()
            return Response({'message': 'Room deleted as no participants remain'})
        
        return Response({'message': 'You have left the room'})


class MessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Message.objects.filter(room__participants=self.request.user)

    def update(self, request, *args, **kwargs):
        message = self.get_object()
        # Only the message author can edit
        if message.user != request.user:
            return Response(
                {'error': 'You can only edit your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        message = self.get_object()
        # Only the message author or room creator can delete
        if message.user != request.user and message.room.created_by != request.user:
            return Response(
                {'error': 'You can only delete your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        room = get_object_or_404(ChatRoom, id=self.kwargs['room_id'])

        if self.request.user not in room.participants.all():
            return Message.objects.none()

        return Message.objects.filter(room=room).order_by('created_at')


class MessageCreateView(generics.CreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        room = get_object_or_404(ChatRoom, id=self.kwargs['room_id'])

        if self.request.user not in room.participants.all():
            raise permissions.PermissionDenied("Not allowed")

        serializer.save(
            user=self.request.user,
            room=room,
            message_type='text'
        )


class MarkMessagesReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, room_id):
        room = get_object_or_404(ChatRoom, id=room_id)
        
        # Only mark messages that are not from the current user
        updated_count = Message.objects.filter(
            room=room
        ).exclude(
            user=request.user
        ).update(
            is_read=True
        )
        
        return Response({
            'status': 'ok',
            'marked_count': updated_count
        })


class MarkSingleMessageReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, message_id):
        message = get_object_or_404(Message, id=message_id)
        
        # Can't mark your own message as read
        if message.user == request.user:
            return Response(
                {'error': 'Cannot mark your own message as read'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message.is_read = True
        message.save()
        
        return Response({'status': 'ok', 'message_id': message_id})


# chat/views.py
from rest_framework import generics, permissions, status, parsers
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .models import ChatRoom, Message
from .serializers import ChatRoomSerializer, MessageSerializer
from .b2_storage import b2_storage
from django.contrib.auth import get_user_model
from rest_framework.parsers import MultiPartParser, FormParser
import os

User = get_user_model()



class FileUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # Import here to avoid initialization issues
        from .b2_storage import b2_storage
        
        file_obj = request.data.get('file')
        room_id = request.data.get('room_id')
        
        if not file_obj:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not room_id:
            return Response({'error': 'room_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            room = ChatRoom.objects.get(id=room_id)
        except ChatRoom.DoesNotExist:
            return Response({'error': 'Room not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if request.user not in room.participants.all():
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        # Upload file to Backblaze B2
        result = b2_storage.upload_file(file_obj, room.id, request.user.id)
        
        if not result['success']:
            return Response({'error': result['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Create message with file
        message = Message.objects.create(
            room=room,
            user=request.user,
            content=f"File: {result['file_name']}",
            message_type='file',
            file_url=result['file_url'],
            file_path=result['file_path'],
            file_name=result['file_name'],
            file_size=result['file_size']
        )
        
        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class MessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Message.objects.filter(room__participants=self.request.user)

    def update(self, request, *args, **kwargs):
        message = self.get_object()
        if message.user != request.user:
            return Response(
                {'error': 'You can only edit your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        message = self.get_object()
        
        # Check permissions
        if message.user != request.user and message.room.created_by != request.user:
            return Response(
                {'error': 'You can only delete your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Delete file from Backblaze B2 if it's a file message
        if message.message_type == 'file' and message.file_path:
            b2_storage.delete_file(message.file_path)
        
        return super().destroy(request, *args, **kwargs)

# ... (keep all your other views)

class UnreadMessagesView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        unread_count = Message.objects.filter(
            room__participants=request.user
        ).exclude(
            user=request.user
        ).filter(
            is_read=False
        ).count()
        
        return Response({'unread_count': unread_count})
    
# chat/views.py
from django.http import HttpResponse
import requests
import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from .models import ChatRoom, Message
from .serializers import MessageSerializer
from rest_framework.permissions import IsAuthenticated 
# chat/views.py - DownloadFileView remains the same
class DownloadFileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, message_id):
        print(f"📥 Download request for message ID: {message_id}")
        
        try:
            # Get the message
            message = Message.objects.get(id=message_id)
            print(f"✅ Found message: {message.id} - {message.file_name}")
            
            # Check if user has access to this room
            if request.user not in message.room.participants.all():
                print(f"❌ User {request.user.username} not a participant")
                return Response({'error': 'You are not a participant in this room'}, status=403)
            
            # Check if there's a file URL
            if not message.file_url:
                print(f"❌ No file URL for message {message_id}")
                return Response({'error': 'No file associated with this message'}, status=404)
            
            print(f"📡 Fetching from: {message.file_url}")
            
            # Fetch the file from Backblaze
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = requests.get(message.file_url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    file_content = response.content
                    print(f"✅ File downloaded, size: {len(file_content)} bytes")
                    
                    http_response = HttpResponse(
                        file_content,
                        content_type='application/octet-stream'
                    )
                    http_response['Content-Disposition'] = f'attachment; filename="{message.file_name}"'
                    http_response['Content-Length'] = len(file_content)
                    http_response['Access-Control-Allow-Origin'] = '*'
                    
                    return http_response
                else:
                    print(f"❌ Backblaze returned status {response.status_code}")
                    return Response({'error': f'File server error: {response.status_code}'}, status=404)
                    
            except requests.exceptions.Timeout:
                print("❌ Request timeout")
                return Response({'error': 'Request timeout'}, status=504)
            except requests.exceptions.ConnectionError:
                print("❌ Connection error")
                return Response({'error': 'Cannot connect to file server'}, status=502)
            except Exception as e:
                print(f"❌ Request error: {e}")
                return Response({'error': f'Failed to fetch file: {str(e)}'}, status=500)
                
        except Message.DoesNotExist:
            print(f"❌ Message {message_id} not found")
            return Response({'error': 'Message not found'}, status=404)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)