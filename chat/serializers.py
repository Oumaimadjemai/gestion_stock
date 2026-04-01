# chat/serializers.py
from rest_framework import serializers
from .models import ChatRoom, Message
from authentification.serializers import CustomUserSerializer


class MessageSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    file_url = serializers.URLField(read_only=True)
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'content', 'message_type', 'file_url', 'file_name',
            'emoji', 'created_at', 'updated_at', 'username', 'user_id', 
            'is_read', 'can_edit', 'can_delete', 'file_size'
        ]
        read_only_fields = ['created_at', 'updated_at', 'is_read', 'file_url', 'file_size']

    def get_can_edit(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False
    
    def get_can_delete(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user == request.user or obj.room.created_by == request.user
        return False


class ChatRoomSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    participants_detail = CustomUserSerializer(source='participants', many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    can_delete = serializers.SerializerMethodField()
    can_add_participants = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            'id', 'name', 'is_private',
            'participants', 'participants_detail',
            'created_by', 'created_by_name', 'created_at',
            'messages', 'last_message', 'unread_count',
            'can_delete', 'can_add_participants'
        ]

    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return MessageSerializer(last_msg, context=self.context).data
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_unread_count(request.user)
        return 0
    
    def get_can_delete(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.created_by == request.user
        return False
    
    def get_can_add_participants(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user in obj.participants.all()
        return False