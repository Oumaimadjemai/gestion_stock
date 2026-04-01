# test_websocket.py
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/chat/test-room/"
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")
            
            # Receive welcome message
            response = await websocket.recv()
            print(f"📨 Welcome: {response}")
            
            # Send a test message
            test_msg = {"message": "Hello from test!", "type": "message"}
            await websocket.send(json.dumps(test_msg))
            print(f"📤 Sent: {test_msg}")
            
            # Receive echo
            response = await websocket.recv()
            print(f"📨 Echo: {response}")
            
            # Keep connection open for a moment
            await asyncio.sleep(1)
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Failed to connect - Status code: {e.status_code}")
        if e.status_code == 500:
            print("   This is a server error - check your consumer code")
    except ConnectionRefusedError:
        print("❌ Connection refused - Is Daphne running on port 8000?")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())