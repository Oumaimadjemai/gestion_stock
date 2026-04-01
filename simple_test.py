# simple_test.py
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/chat/1/"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Wait for connection message
            response = await websocket.recv()
            print(f"📥 Received: {response}")
            
            # Send a message
            message = {"type": "message", "message": "Hello from Python test!"}
            await websocket.send(json.dumps(message))
            print(f"📤 Sent: {message}")
            
            # Wait for response
            response = await websocket.recv()
            print(f"📥 Received: {response}")
            
            # Send typing indicator
            typing_msg = {"type": "typing", "is_typing": True}
            await websocket.send(json.dumps(typing_msg))
            print(f"📤 Sent typing indicator")
            
            # Wait a bit
            await asyncio.sleep(2)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())