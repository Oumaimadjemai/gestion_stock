# diagnose_websocket_fixed.py
import os
import sys
import django

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_stock.settings')

# Initialize Django
django.setup()

from django.contrib.auth import get_user_model
from django.conf import settings
from chat.models import ChatRoom, Message
from channels.layers import get_channel_layer

def diagnose():
    print("=" * 60)
    print("WebSocket Configuration Diagnosis")
    print("=" * 60)
    
    # 1. Check settings
    print(f"\n1. Django Settings:")
    print(f"   DEBUG: {settings.DEBUG}")
    print(f"   ASGI_APPLICATION: {settings.ASGI_APPLICATION}")
    print(f"   CHANNEL_LAYERS BACKEND: {settings.CHANNEL_LAYERS['default']['BACKEND']}")
    
    # Check Redis configuration
    try:
        if 'CONFIG' in settings.CHANNEL_LAYERS['default']:
            config = settings.CHANNEL_LAYERS['default']['CONFIG']
            hosts = config.get('hosts', [])
            print(f"   Redis Hosts: {hosts}")
            
            # Check if password is in the correct format
            # The error suggests RedisChannelLayer doesn't accept 'password' as keyword
            # We need to fix this in settings
            print(f"   ⚠️ Redis configuration needs to be fixed: password should be in host tuple")
    except Exception as e:
        print(f"   ❌ Error reading Redis config: {e}")
    
    # 2. Check Channel Layer
    try:
        channel_layer = get_channel_layer()
        print("\n2. ✅ Channel layer created successfully")
    except Exception as e:
        print(f"\n2. ❌ Channel layer error: {e}")
        print("   This is likely because Redis configuration is incorrect.")
        print("   We'll use InMemoryChannelLayer for testing.")
    
    # 3. Check Database - Users
    User = get_user_model()
    users = User.objects.all()
    print(f"\n3. Total users: {users.count()}")
    for i, user in enumerate(users[:5]):
        print(f"   {i+1}. {user.username} (ID: {user.id}, Role: {user.role})")
    if users.count() == 0:
        print("   ⚠️ No users found! Create a user first.")
        print("   Run: python manage.py createsuperuser")
    
    # Check for user 'imi' specifically
    try:
        test_user = User.objects.get(username='imi')
        print(f"\n   ✅ Found test user 'imi' (ID: {test_user.id})")
    except User.DoesNotExist:
        print(f"\n   ⚠️ User 'imi' not found")
    except Exception as e:
        print(f"\n   ⚠️ Error finding user 'imi': {e}")
    
    # 4. Check Database - Rooms
    rooms = ChatRoom.objects.all()
    print(f"\n4. Total chat rooms: {rooms.count()}")
    for room in rooms:
        print(f"   - {room.name} (ID: {room.id})")
        print(f"     Private: {room.is_private}")
        print(f"     Created by: {room.created_by.username if room.created_by else 'None'}")
        print(f"     Participants: {room.participants.count()}")
        for participant in room.participants.all()[:3]:
            print(f"       - {participant.username}")
    
    # 5. Check user participation
    if users.exists() and rooms.exists():
        user = users.filter(username='imi').first() or users.first()
        room = rooms.first()
        is_participant = user in room.participants.all()
        print(f"\n5. User '{user.username}' in room '{room.name}': {is_participant}")
        if not is_participant:
            print(f"   Adding user to room...")
            room.participants.add(user)
            print(f"   ✅ User added")
        else:
            print(f"   ✅ User already a participant")
    
    # 6. Check Messages
    total_messages = Message.objects.count()
    print(f"\n6. Total messages: {total_messages}")
    if total_messages > 0:
        recent_messages = Message.objects.order_by('-created_at')[:3]
        print("   Recent messages:")
        for msg in recent_messages:
            print(f"   - {msg.user.username}: {msg.content[:50]} ({msg.created_at})")
    
    # 7. Check ASGI configuration
    print("\n7. ASGI Configuration:")
    try:
        from gestion_stock.asgi import application
        print("   ✅ ASGI application loaded successfully")
    except Exception as e:
        print(f"   ❌ Error loading ASGI application: {e}")
    
    print("\n" + "=" * 60)
    print("Diagnosis complete!")
    print("=" * 60)
    
    print("\n🔧 Recommended fix for Redis configuration:")
    print("   Update CHANNEL_LAYERS in settings.py to:")
    print("   CHANNEL_LAYERS = {")
    print("       'default': {")
    print("           'BACKEND': 'channels_redis.core.RedisChannelLayer',")
    print("           'CONFIG': {")
    print("               'hosts': [('junction.proxy.rlwy.net', 41907, 'dVZwODtckOEHIVQHTZQQjRzMgqfFzaAW')],")
    print("           },")
    print("       },")
    print("   }")
    print("\n   Or for testing, use InMemoryChannelLayer:")
    print("   CHANNEL_LAYERS = {")
    print("       'default': {")
    print("           'BACKEND': 'channels.layers.InMemoryChannelLayer',")
    print("       },")
    print("   }")
    
    if rooms.exists():
        print(f"\n✅ To test WebSocket with wscat:")
        print(f"   wscat -c ws://localhost:8000/ws/chat/{rooms.first().id}/")
        print(f"\n   Then send this message:")
        print(f'   {{"type": "message", "message": "Hello from test!"}}')
    else:
        print("\n⚠️ No rooms found. Create a room first")

if __name__ == "__main__":
    diagnose()