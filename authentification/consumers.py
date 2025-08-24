# authentification/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"chat_{self.room_name}"
        self.username = self.scope['query_string'].decode().split("=")[1]

        # Join room
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Notify users
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "users.update", "users": [self.username]}
        )

    async def disconnect(self, close_code):
        # Leave room
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get("message")

        # Broadcast to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "chat.message", "message": message, "user": self.username}
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "message",
            "message": event["message"],
            "user": event["user"]
        }))

    async def users_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "users",
            "users": event["users"]
        }))
