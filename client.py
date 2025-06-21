#!/usr/bin/env python3
"""
AG-UI CLI Client
A simple command-line interface to interact with the AG-UI echo server.
"""

import asyncio
import json
import sys
from typing import Dict, Any, List
from uuid import uuid4
import aiohttp

class AGUIClient:
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.thread_id = str(uuid4())
        self.messages: List[Dict[str, Any]] = []
        self.state: Dict[str, Any] = {}
        
    async def send_message(self, content: str) -> None:
        """Send a message to the agent and stream the response"""
        
        # Add user message to history
        user_message = {
            "id": str(uuid4()),
            "role": "user",
            "content": content
        }
        self.messages.append(user_message)
        
        # Prepare request payload
        payload = {
            "thread_id": self.thread_id,
            "messages": self.messages,
            "tools": [],
            "state": self.state,
            "context": [],
            "forwardedProps": {}
        }
        
        print(f"\n🤖 Sending message: {content}")
        print("📡 Waiting for response...\n")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.server_url}/agent",
                    json=payload,
                    headers={
                        "Accept": "text/event-stream",
                        "Cache-Control": "no-cache"
                    }
                ) as response:
                    
                    if response.status != 200:
                        print(f"❌ Error: Server returned status {response.status}")
                        return
                    
                    current_message = ""
                    message_id = None
                    
                    # Process the Server-Sent Events stream
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        
                        # Skip empty lines and comments
                        if not line_str or line_str.startswith(':'):
                            continue
                            
                        # Parse SSE format: "data: {json}" or "data: data: {json}"
                        if line_str.startswith('data: '):
                            try:
                                # Remove the first "data: " prefix
                                json_part = line_str[6:]
                                
                                # Check if there's another "data: " prefix and remove it
                                if json_part.startswith('data: '):
                                    json_part = json_part[6:]
                                
                                event_data = json.loads(json_part)
                                event_type = event_data.get('type')
                                
                                if event_type == 'RUN_STARTED':
                                    print("🔄 Agent started processing...")
                                    
                                elif event_type == 'TEXT_MESSAGE_START':
                                    message_id = event_data.get('messageId')
                                    print("💬 Assistant: ", end='', flush=True)
                                    
                                elif event_type == 'TEXT_MESSAGE_CONTENT':
                                    delta = event_data.get('delta', '')
                                    current_message += delta
                                    print(delta, end='', flush=True)
                                    
                                elif event_type == 'TEXT_MESSAGE_END':
                                    print()  # New line after message
                                    
                                    # Add assistant message to history
                                    assistant_message = {
                                        "id": message_id,
                                        "role": "assistant", 
                                        "content": current_message
                                    }
                                    self.messages.append(assistant_message)
                                    current_message = ""
                                    
                                elif event_type == 'RUN_FINISHED':
                                    print("✅ Agent finished processing\n")
                                    break
                                    
                            except json.JSONDecodeError as e:
                                print(f"⚠️ Failed to parse event: {line_str}")
                                continue
                            except Exception as e:
                                print(f"⚠️ Error processing event: {e}")
                                continue

        except aiohttp.ClientError as e:
            print(f"❌ Connection error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    async def health_check(self) -> bool:
        """Check if the server is healthy"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Server health: {data}")
                        return True
                    else:
                        print(f"❌ Server health check failed: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False

async def main():
    """Main CLI interface"""
    
    print("🤖 AG-UI Echo Client")
    print("=" * 50)
    
    # Initialize client
    client = AGUIClient()
    
    # Check server health
    print("🔍 Checking server health...")
    if not await client.health_check():
        print("❌ Server is not available. Please start the server first:")
        print("   python server.py")
        return
    
    print("\n💬 Chat with the echo agent! (Type 'quit' to exit)")
    print("-" * 50)
    
    while True:
        try:
            # Get user input
            user_input = input("\n👤 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
                
            if not user_input:
                continue
                
            # Send message to agent
            await client.send_message(user_input)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except EOFError:
            print("\n👋 Goodbye!")
            break

if __name__ == "__main__":
    # Check for required packages
    try:
        import aiohttp
    except ImportError:
        print("❌ Missing required packages. Please install:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    
    # Run the client
    asyncio.run(main()) 