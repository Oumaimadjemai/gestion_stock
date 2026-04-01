# test_redis.py
import redis
import os

# Redis configuration from your settings
REDIS_HOST = 'junction.proxy.rlwy.net'
REDIS_PORT = 41907
REDIS_PASSWORD = 'dVZwODtckOEHIVQHTZQQjRzMgqfFzaAW'

try:
    # Test connection to Redis
    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    
    # Ping Redis
    response = r.ping()
    print(f"✅ Redis connection successful: {response}")
    
    # Test set/get
    r.set('test_key', 'test_value')
    value = r.get('test_key')
    print(f"✅ Redis read/write successful: {value}")
    
except Exception as e:
    print(f"❌ Redis connection failed: {e}")