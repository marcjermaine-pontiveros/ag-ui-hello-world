#!/usr/bin/env python3
"""
AG-UI WebSocket Server
Integrates with the existing AG-UI server to provide WebSocket communication
"""

import asyncio
import json
import websockets
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
import uuid

# Add the parent directory to the path so we can import from cli/
sys.path.append(str(Path(__file__).parent.parent / 'cli'))

from server import EchoAgent, ToolAgent, StateAgent, RunAgentInput

class WebSocketHandler:
    def __init__(self):
        self.agents = {
            'echo': EchoAgent(),
            'tool': ToolAgent(),
            'state': StateAgent()
        }
        self.default_agent = 'tool'  # Default to tool agent for rich features
        
    async def handle_client(self, websocket, path):
        """Handle a new WebSocket client connection"""
        client_id = str(uuid.uuid4())[:8]
        print(f"🔌 New WebSocket client connected: {client_id}")
        
        try:
            async for message in websocket:
                await self.process_message(websocket, message, client_id)
        except websockets.exceptions.ConnectionClosed:
            print(f"🔌 Client {client_id} disconnected")
        except Exception as e:
            print(f"❌ Error handling client {client_id}: {e}")
            await websocket.close(1011, f"Server error: {e}")

    async def process_message(self, websocket, message: str, client_id: str):
        """Process a message from the WebSocket client"""
        try:
            # Parse the incoming RunAgentInput
            data = json.loads(message)
            print(f"📨 Received from {client_id}: {data.get('messages', [{}])[-1].get('content', 'N/A')[:50]}...")
            
            # Create RunAgentInput from the received data
            run_input = self.create_run_input(data)
            
            # Determine which agent to use
            agent_type = data.get('agent_type', self.default_agent)
            if agent_type not in self.agents:
                agent_type = self.default_agent
            
            agent = self.agents[agent_type]
            print(f"🤖 Using {agent_type} agent for {client_id}")
            
            # Run the agent and stream events back via WebSocket
            async for event_data in agent.run(run_input):
                await websocket.send(event_data)
                
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON from {client_id}: {e}")
            await websocket.send(json.dumps({
                "type": "ERROR",
                "message": f"Invalid JSON: {e}"
            }))
        except Exception as e:
            print(f"❌ Error processing message from {client_id}: {e}")
            await websocket.send(json.dumps({
                "type": "ERROR", 
                "message": f"Processing error: {e}"
            }))

    def create_run_input(self, data: Dict[str, Any]) -> RunAgentInput:
        """Create a RunAgentInput from WebSocket data"""
        # Extract or generate required fields
        thread_id = data.get('thread_id', str(uuid.uuid4()))
        run_id = data.get('run_id', str(uuid.uuid4()))
        
        # Get messages or create a default
        messages = data.get('messages', [])
        if not messages:
            messages = [{"role": "user", "content": "Hello"}]
        
        # Create the RunAgentInput
        return RunAgentInput(
            thread_id=thread_id,
            run_id=run_id,
            messages=messages,
            tools=data.get('tools', []),
            state=data.get('state', {}),
            agent_type=data.get('agent_type', self.default_agent)
        )

async def main():
    """Start the WebSocket server"""
    handler = WebSocketHandler()
    
    # WebSocket server configuration
    host = "localhost"
    port = 8765
    
    print("🚀 Starting AG-UI WebSocket Server...")
    print(f"📡 Server will run on ws://{host}:{port}")
    print("🤖 Available agents: echo, tool, state")
    print("💡 Make sure to start the React frontend with: npm run dev")
    print("─" * 60)
    
    # Start the WebSocket server
    async with websockets.serve(handler.handle_client, host, port):
        print(f"✅ WebSocket server running on ws://{host}:{port}")
        print("Press Ctrl+C to stop the server")
        
        # Keep the server running
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1) 