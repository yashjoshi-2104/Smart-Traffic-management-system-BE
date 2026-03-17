# backend/test_websocket.py
"""
Test WebSocket connection and real-time updates
"""

import asyncio
import websockets
import json


async def test_websocket():
    """Connect to WebSocket and receive real-time updates"""
    
    uri = "ws://localhost:8000/ws"
    
    print("🔌 Connecting to WebSocket...")
    
    async with websockets.connect(uri) as websocket:
        print("✅ Connected!")
        print("\n📡 Receiving updates (Ctrl+C to stop)...\n")
        
        try:
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                
                if data['type'] == 'state_update':
                    print(f"Step {data['step']:3d}: "
                          f"Baseline={data['baseline']['vehicle_count']:2d} vehicles, "
                          f"RL={data['rl']['vehicle_count']:2d} vehicles, "
                          f"Mode={data['rl_mode']}")
        
        except KeyboardInterrupt:
            print("\n\n✅ WebSocket test complete!")


if __name__ == "__main__":
    asyncio.run(test_websocket())
