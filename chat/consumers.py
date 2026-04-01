# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from urllib.parse import parse_qs
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.room_id = self.scope['url_route']['kwargs']['room_id']
            self.room_group_name = f'chat_{self.room_id}'
            
            # Get token from query string
            query_string = self.scope.get('query_string', b'').decode()
            query_params = parse_qs(query_string)
            token = query_params.get('token', [None])[0]
            
            print(f"🔌 [WS] Connecting to room {self.room_id}")
            
            # Get user from token
            if token:
                try:
                    access_token = AccessToken(token)
                    user_id = access_token['user_id']
                    self.user = await self.get_user(user_id)
                    if self.user:
                        print(f"✅ [WS] User authenticated: {self.user.username}")
                    else:
                        print(f"❌ [WS] User not found")
                        await self.close()
                        return
                except Exception as e:
                    print(f"❌ [WS] Token error: {e}")
                    await self.close()
                    return
            else:
                print(f"❌ [WS] No token provided")
                await self.close()
                return
            
            # Check if user is a participant
            is_participant = await self.is_participant(self.user, self.room_id)
            if not is_participant:
                print(f"❌ [WS] User {self.user.username} not a participant")
                await self.close()
                return
            
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            # Accept the connection
            await self.accept()
            print(f"✅ [WS] User {self.user.username} connected to room {self.room_id}")
            
            # Send connection confirmation
            await self.send(text_data=json.dumps({
                'type': 'connection',
                'message': f'Connected to room {self.room_id}',
                'room_id': self.room_id,
                'user': self.user.username
            }))
            
        except Exception as e:
            print(f"❌ [WS] Error in connect: {e}")
            import traceback
            traceback.print_exc()
            await self.close()
    
    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    
    @database_sync_to_async
    def is_participant(self, user, room_id):
        from .models import ChatRoom
        try:
            room = ChatRoom.objects.get(id=room_id)
            return user in room.participants.all()
        except ChatRoom.DoesNotExist:
            return False
    
    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            print(f"🔴 [WS] User disconnected from room {self.room_id}")
        except Exception as e:
            print(f"Error in disconnect: {e}")
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')
            
            print(f"📨 [WS] Received: {data}")
            
            if message_type == 'message':
                message = data.get('message', '')
                if message:
                    # Save message to database
                    saved_message = await self.save_message(message)
                    
                    # Send message to room group
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'chat_message',
                            'message': message,
                            'username': self.user.username,
                            'user_id': self.user.id,
                            'timestamp': timezone.now().isoformat(),
                            'message_id': saved_message.id if saved_message else None
                        }
                    )
            elif message_type == 'typing':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing',
                        'username': self.user.username,
                        'is_typing': data.get('is_typing', False)
                    }
                )
                
        except Exception as e:
            print(f"❌ [WS] Error in receive: {e}")
    
    @database_sync_to_async
    def save_message(self, content):
        from .models import ChatRoom, Message
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            message = Message.objects.create(
                room=room,
                user=self.user,
                content=content,
                message_type='text',
                created_at=timezone.now()
            )
            print(f"💾 [WS] Message saved: {message.id}")
            return message
        except Exception as e:
            print(f"❌ [WS] Error saving message: {e}")
            return None
    
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'username': event['username'],
            'user_id': event['user_id'],
            'timestamp': event['timestamp'],
            'message_id': event.get('message_id')
        }))
    
    async def typing(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'username': event['username'],
            'is_typing': event['is_typing']
        }))