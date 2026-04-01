# test_channels.py (place in project root)
import os
import sys
import django

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_stock.settings')

# Initialize Django
django.setup()

import asyncio
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from gestion_stock.asgi import application
from chat.models import ChatRoom, Message

async def test_websocket_connection():
    # Create test user if doesn't exist
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username='imi',
        defaults={
            
            'password': 'admin'
        }
    )
    
    if created:
        print(f"✅ Created test user: {user.username}")
    else:
        print(f"✅ Using existing user: {user.username}")
    
    # Create test room
    room, created = ChatRoom.objects.get_or_create(
        name='Test Room',
        defaults={'is_private': False}
    )
    
    if created:
        print(f"✅ Created test room: {room.name} (ID: {room.id})")
    else:
        print(f"✅ Using existing room: {room.name} (ID: {room.id})")
    
    # Add user to room
    if user not in room.participants.all():
        room.participants.add(user)
        print(f"✅ Added user to room")
    else:
        print(f"✅ User already in room")
    
    # Create communicator
    communicator = WebsocketCommunicator(
        application,
        f"/ws/chat/{room.id}/"
    )
    
    # Set scope user
    communicator.scope['user'] = user
    
    # Connect
    try:
        connected, _ = await communicator.connect()
        if connected:
            print("\n✅ WebSocket connected successfully!")
            
            # Send a message
            await communicator.send_json_to({
                'type': 'message',
                'message': 'Hello from test!'
            })
            print("✅ Message sent")
            
            # Try to receive response (might timeout if no response)
            try:
                response = await asyncio.wait_for(communicator.receive_json_from(), timeout=5.0)
                print(f"✅ Received: {response}")
            except asyncio.TimeoutError:
                print("⚠️ No response received (timeout) - this might be normal if server doesn't echo")
            
            # Disconnect
            await communicator.disconnect()
            print("✅ Disconnected")
        else:
            print("❌ WebSocket connection failed")
    except Exception as e:
        print(f"❌ Error during connection: {e}")
    
    return True

# Run the test
if __name__ == "__main__":
    print("=" * 50)
    print("Testing WebSocket Connection")
    print("=" * 50)
    asyncio.run(test_websocket_connection())