# chat/consumers_minimal.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class MinimalConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print("=" * 60)
        print("🚀 MinimalConsumer: connect() called")
        print(f"   Path: {self.scope.get('path')}")
        print(f"   Headers: {self.scope.get('headers')}")
        print("=" * 60)
        
        # Accept the connection immediately
        await self.accept()
        print("✅ Connection accepted")
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'Connected to Django WebSocket!'
        }))
        print("📤 Welcome message sent")
    
    async def receive(self, text_data):
        print(f"📨 Received: {text_data}")
        
        # Echo back
        await self.send(text_data=json.dumps({
            'type': 'echo',
            'data': text_data
        }))
        print(f"📤 Echo sent")
    
    async def disconnect(self, close_code):
        print(f"🔴 Disconnected, code: {close_code}")