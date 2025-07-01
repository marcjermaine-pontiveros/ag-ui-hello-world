#!/usr/bin/env python3
"""
AG-UI WebSocket Demo Launcher
Comprehensive script to set up and run the WebSocket demo
"""

import asyncio
import subprocess
import sys
import os
import json
import time
from pathlib import Path

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    # Check Python dependencies
    required_python = ['websockets', 'fastapi', 'uvicorn']
    missing_python = []
    
    for pkg in required_python:
        try:
            __import__(pkg)
            print(f"✅ Python: {pkg}")
        except ImportError:
            missing_python.append(pkg)
            print(f"❌ Python: {pkg} (missing)")
    
    # Check Node.js dependencies
    package_json_path = Path(__file__).parent / 'package.json'
    node_modules_path = Path(__file__).parent / 'node_modules'
    
    if package_json_path.exists() and node_modules_path.exists():
        print("✅ Node.js: dependencies installed")
    else:
        print("❌ Node.js: dependencies not installed")
        print("💡 Run: npm install")
    
    return len(missing_python) == 0

def install_python_dependencies():
    """Install missing Python dependencies"""
    print("📦 Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'websockets'], check=True)
        print("✅ Python dependencies installed")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install Python dependencies")
        return False

def create_simple_websocket_server():
    """Create a simplified WebSocket server for demo purposes"""
    server_code = '''#!/usr/bin/env python3
"""
Simplified AG-UI WebSocket Server for Demo
"""

import asyncio
import json
import websockets
import uuid
from datetime import datetime

class SimpleWebSocketHandler:
    async def handle_client(self, websocket, path):
        """Handle WebSocket client connections"""
        client_id = str(uuid.uuid4())[:8]
        print(f"🔌 Client {client_id} connected")
        
        try:
            async for message in websocket:
                await self.process_message(websocket, message, client_id)
        except websockets.exceptions.ConnectionClosed:
            print(f"🔌 Client {client_id} disconnected")
        except Exception as e:
            print(f"❌ Error with client {client_id}: {e}")

    async def process_message(self, websocket, message: str, client_id: str):
        """Process incoming messages and send AG-UI compliant responses"""
        try:
            data = json.loads(message)
            user_message = data.get('messages', [{}])[-1].get('content', 'Hello')
            
            print(f"📨 {client_id}: {user_message[:50]}...")
            
            # Generate AG-UI events
            thread_id = data.get('thread_id', str(uuid.uuid4()))
            run_id = data.get('run_id', str(uuid.uuid4()))
            message_id = str(uuid.uuid4())
            
            # RUN_STARTED
            await websocket.send(json.dumps({
                "type": "RUN_STARTED",
                "thread_id": thread_id,
                "run_id": run_id
            }))
            
            # TEXT_MESSAGE_START
            await websocket.send(json.dumps({
                "type": "TEXT_MESSAGE_START",
                "message_id": message_id,
                "role": "assistant"
            }))
            
            # Generate response based on content
            response = self.generate_response(user_message)
            
            # Stream response character by character
            for char in response:
                await websocket.send(json.dumps({
                    "type": "TEXT_MESSAGE_CONTENT",
                    "message_id": message_id,
                    "delta": char
                }))
                await asyncio.sleep(0.05)  # Small delay for realistic streaming
            
            # TEXT_MESSAGE_END
            await websocket.send(json.dumps({
                "type": "TEXT_MESSAGE_END",
                "message_id": message_id
            }))
            
            # RUN_FINISHED
            await websocket.send(json.dumps({
                "type": "RUN_FINISHED",
                "thread_id": thread_id,
                "run_id": run_id
            }))
            
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            await websocket.send(json.dumps({
                "type": "ERROR",
                "message": str(e)
            }))

    def generate_response(self, user_message: str) -> str:
        """Generate appropriate responses based on user input"""
        message_lower = user_message.lower()
        
        if 'calculate' in message_lower or 'math' in message_lower:
            return "🧮 I can help with calculations! Try asking me to 'calculate 5 + 3' or similar math problems."
        elif 'weather' in message_lower:
            return f"🌤️ Current weather: 72°F (22°C), partly cloudy with light winds. Perfect day for coding!"
        elif 'time' in message_lower:
            return f"🕐 Current time: {datetime.now().strftime('%H:%M:%S')} on {datetime.now().strftime('%Y-%m-%d')}"
        elif 'hello' in message_lower or 'hi' in message_lower:
            return "👋 Hello! I'm your AG-UI WebSocket agent. I can help with calculations, weather, time, and general conversation. What would you like to know?"
        else:
            return f"💬 Echo: {user_message}\\n\\nTry asking me about calculations, weather, or the current time!"

async def main():
    handler = SimpleWebSocketHandler()
    host = "localhost"
    port = 8765
    
    print("🚀 Starting Simple AG-UI WebSocket Server...")
    print(f"📡 Server: ws://{host}:{port}")
    print("🤖 Features: Echo, Math, Weather, Time")
    print("─" * 50)
    
    async with websockets.serve(handler.handle_client, host, port):
        print(f"✅ Server running on ws://{host}:{port}")
        print("Press Ctrl+C to stop")
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Server stopped")
'''
    
    # Write the server file
    with open('simple_websocket_server.py', 'w') as f:
        f.write(server_code)
    
    print("✅ Created simple WebSocket server")

def main():
    """Main demo launcher"""
    print("🚀 AG-UI WebSocket Demo Launcher")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        print("\n🔧 Installing missing dependencies...")
        if not install_python_dependencies():
            print("❌ Failed to install dependencies. Please install manually:")
            print("   pip install websockets")
            return
    
    # Create simple server if the complex one has issues
 