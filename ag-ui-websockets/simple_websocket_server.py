#!/usr/bin/env python3
"""
Simple WebSocket Server for React Chat Demo
No complex AG-UI validation - just works!
"""

import asyncio
import json
import websockets
import uuid
from datetime import datetime

class SimpleChatServer:
    def __init__(self):
        self.clients = set()

    async def handle_client(self, websocket, path):
        """Handle a new WebSocket client connection"""
        client_id = str(uuid.uuid4())[:8]
        self.clients.add(websocket)
        print(f"🔌 Client {client_id} connected (Total: {len(self.clients)})")
        
        try:
            async for message in websocket:
                await self.process_message(websocket, message, client_id)
        except websockets.exceptions.ConnectionClosed:
            print(f"🔌 Client {client_id} disconnected")
        except Exception as e:
            print(f"❌ Error with client {client_id}: {e}")
        finally:
            self.clients.discard(websocket)

    async def process_message(self, websocket, message: str, client_id: str):
        """Process incoming messages and send responses"""
        try:
            data = json.loads(message)
            user_message = data.get('messages', [{}])[-1].get('content', 'Hello')
            
            print(f"📨 {client_id}: {user_message[:50]}...")
            
            # Generate unique IDs
            thread_id = data.get('thread_id', str(uuid.uuid4()))
            run_id = data.get('run_id', str(uuid.uuid4()))
            message_id = str(uuid.uuid4())
            
            # Send RUN_STARTED event
            await self.send_event(websocket, {
                "type": "RUN_STARTED",
                "thread_id": thread_id,
                "run_id": run_id
            })
            
            # Send TEXT_MESSAGE_START event
            await self.send_event(websocket, {
                "type": "TEXT_MESSAGE_START",
                "message_id": message_id,
                "role": "assistant"
            })
            
            # Generate response based on user input
            response = self.generate_response(user_message)
            
            # Stream response character by character
            for char in response:
                await self.send_event(websocket, {
                    "type": "TEXT_MESSAGE_CONTENT",
                    "message_id": message_id,
                    "delta": char
                })
                await asyncio.sleep(0.03)  # Small delay for realistic streaming
            
            # Send TEXT_MESSAGE_END event
            await self.send_event(websocket, {
                "type": "TEXT_MESSAGE_END",
                "message_id": message_id
            })
            
            # Send RUN_FINISHED event
            await self.send_event(websocket, {
                "type": "RUN_FINISHED",
                "thread_id": thread_id,
                "run_id": run_id
            })
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON from {client_id}: {e}")
            await self.send_event(websocket, {
                "type": "ERROR",
                "message": f"Invalid JSON: {e}"
            })
        except Exception as e:
            print(f"❌ Error processing message from {client_id}: {e}")
            await self.send_event(websocket, {
                "type": "ERROR",
                "message": f"Processing error: {e}"
            })

    async def send_event(self, websocket, event_data):
        """Send an event to the WebSocket client"""
        try:
            await websocket.send(json.dumps(event_data))
        except Exception as e:
            print(f"❌ Error sending event: {e}")

    def generate_response(self, user_message: str) -> str:
        """Generate appropriate responses based on user input"""
        message_lower = user_message.lower()
        
        if 'calculate' in message_lower or 'math' in message_lower:
            # Try to extract numbers and do simple math
            if '+' in user_message:
                return "🧮 I can help with calculations! For more complex math, try asking like 'calculate 5 + 3 * 2'"
            elif '*' in user_message or 'x' in user_message:
                return "🧮 Multiplication detected! For a real calculator, I'd need more sophisticated parsing."
            else:
                return "🧮 I see you want to do math! Try asking 'calculate 15 + 7' or similar expressions."
                
        elif 'weather' in message_lower:
            weather_conditions = [
                "🌤️ Current weather: 72°F (22°C), partly cloudy with light winds. Perfect coding weather!",
                "☀️ It's sunny and 75°F (24°C) outside. Great day for a walk!",
                "🌧️ Light rain, 65°F (18°C). Perfect weather to stay inside and code!",
                "❄️ Chilly at 45°F (7°C) with overcast skies. Time for hot coffee!",
                "🌈 Partly cloudy, 70°F (21°C) - beautiful day ahead!"
            ]
            import random
            return random.choice(weather_conditions)
            
        elif 'time' in message_lower:
            current_time = datetime.now()
            return f"🕐 Current time: {current_time.strftime('%H:%M:%S')} on {current_time.strftime('%A, %B %d, %Y')}"
            
        elif 'hello' in message_lower or 'hi' in message_lower:
            greetings = [
                "👋 Hello there! I'm your friendly WebSocket chat assistant.",
                "🤖 Hi! I'm here to help with calculations, weather, time, and general chat.",
                "👋 Hey! Great to meet you. What would you like to talk about?",
                "🚀 Hello! Welcome to our real-time WebSocket chat demo!"
            ]
            import random
            return random.choice(greetings)
            
        elif 'how are you' in message_lower:
            return "🤖 I'm doing great! Running smoothly on WebSockets and ready to chat. How are you doing?"
            
        elif 'help' in message_lower:
            return """🔧 I can help you with:
• 🧮 Math: Ask me to calculate things
• 🌤️ Weather: Ask about the weather  
• 🕐 Time: Ask what time it is
• 💬 Chat: Just talk to me about anything!

Try saying 'calculate 5 + 3', 'what's the weather?', or 'what time is it?'"""
            
        else:
            # Echo with some flair
            return f"💬 You said: \"{user_message}\"\n\nI'm a simple chat bot! Try asking me about calculations, weather, time, or just say hello! 🚀"

async def main():
    """Start the WebSocket server"""
    server = SimpleChatServer()
    
    host = "localhost"
    port = 8765
    
    print("🚀 Starting Simple WebSocket Chat Server")
    print("=" * 50)
    print(f"📡 Server: ws://{host}:{port}")
    print("💬 Features: Chat, Math, Weather, Time")
    print("🎯 Compatible with React frontend")
    print("=" * 50)
    
    # Start the WebSocket server
    async with websockets.serve(server.handle_client, host, port):
        print(f"✅ Server running on ws://{host}:{port}")
        print("🚀 Start your React app with: npm run dev")
        print("🌐 Then visit: http://localhost:3000")
        print("=" * 50)
        print("Press Ctrl+C to stop the server")
        
        # Keep the server running
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Server error: {e}")
        import sys
        sys.exit(1) 