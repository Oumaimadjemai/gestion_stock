# test_websocket.py - Fixed version
import asyncio
import websockets
import json

async def handler(websocket):
    print("✅ Connection received")
    await websocket.send(json.dumps({"message": "Connected to test server!"}))
    
    async for message in websocket:
        print(f"📨 Received: {message}")
        await websocket.send(json.dumps({"echo": message}))

async def main():
    async with websockets.serve(handler, "localhost", 8000):
        print("🚀 Test WebSocket server running on ws://localhost:8000")
        print("Press Ctrl+C to stop")
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Server stopped")