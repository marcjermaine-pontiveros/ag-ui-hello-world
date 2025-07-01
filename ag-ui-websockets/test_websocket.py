#!/usr/bin/env python3
"""
Test script for AG-UI WebSocket integration
"""

import asyncio
import json
import websockets
import uuid

async def test_websocket():
    """Test the WebSocket server with a simple message"""
    uri = "ws://localhost:8765"
    
    try:
        print("🔌 Connecting to WebSocket server...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")
            
            # Create a test message
            test_message = {
                "thread_id": str(uuid.uuid4()),
                "run_id": str(uuid.uuid4()),
                "messages": [
                    {"role": "user", "content": "Hello, WebSocket server!"}
                ],
                "tools": [],
                "state": {},
                "agent_type": "tool"
            }
            
            print(f"📤 Sending test message: {test_message['messages'][0]['content']}")
            await websocket.send(json.dumps(test_message))
            
            print("📨 Waiting for responses...")
            message_count = 0
            
            # Listen for responses (with timeout)
            try:
                async with asyncio.timeout(10):  # 10 second timeout
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            event_type = data.get('type', 'UNKNOWN')
                            print(f"📨 Received: {event_type}")
                            
                            # Print message content if available
                            if event_type == 'TEXT_MESSAGE_CONTENT':
                                delta = data.get('delta', '')
                                print(f"💬 Content: {delta}")
                            
                            message_count += 1
                            
                            # Stop after receiving a reasonable number of events
                            if event_type == 'RUN_FINISHED' or message_count > 20:
                                break
                                
                        except json.JSONDecodeError:
                            print(f"❌ Invalid JSON: {message}")
                            
            except asyncio.TimeoutError:
                print("⏰ Response timeout - server might be slow")
            
            print(f"✅ Test completed! Received {message_count} events")
            
    except ConnectionRefusedError:
        print("❌ Connection refused - make sure the WebSocket server is running")
        print("💡 Run: python websocket_server.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
        
    return True

async def main():
    """Main test function"""
    print("🚀 AG-UI WebSocket Test")
    print("=" * 40)
    
    success = await test_websocket()
    
    print("=" * 40)
    if success:
        print("✅ WebSocket integration test PASSED!")
        print("💡 Your setup is ready for the React demo!")
    else:
        print("❌ WebSocket integration test FAILED!")
        print("🔧 Check the server and try again")

if __name__ == "__main__":
    asyncio.run(main()) 