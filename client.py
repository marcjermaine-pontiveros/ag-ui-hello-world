#!/usr/bin/env python3
"""
AG-UI CLI Client
A comprehensive command-line interface to interact with AG-UI servers supporting
text messages, tool calls, and state management.
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
        self.current_agent = "echo"
        
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
            "forwardedProps": {},
            "agent_type": self.current_agent
        }
        
        print(f"\n🤖 Sending message to {self.current_agent} agent: {content}")
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
                                    
                                elif event_type == 'TOOL_CALL_START':
                                    tool_name = event_data.get('toolCallName', 'unknown')
                                    tool_call_id = event_data.get('toolCallId')
                                    print(f"🔧 Starting tool call: {tool_name} (ID: {tool_call_id})")
                                    
                                elif event_type == 'TOOL_CALL_ARGS':
                                    tool_call_id = event_data.get('toolCallId')
                                    args = event_data.get('delta', '{}')
                                    try:
                                        parsed_args = json.loads(args)
                                        print(f"📋 Tool arguments: {parsed_args}")
                                    except json.JSONDecodeError:
                                        print(f"📋 Tool arguments: {args}")
                                    
                                elif event_type == 'TOOL_CALL_END':
                                    tool_call_id = event_data.get('toolCallId')
                                    print(f"✅ Tool call completed (ID: {tool_call_id})")
                                    
                                elif event_type == 'STATE_DELTA':
                                    delta = event_data.get('delta', {})
                                    print(f"📊 State updated: {delta}")
                                    # Validate/filter delta before applying
                                    validated_delta = {
                                        k: v for k, v in delta.items()
                                        if self.is_valid_state_key(k, v)
                                    }
                                    if validated_delta:
                                        self.state.update(validated_delta)
                                    else:
                                        print("⚠️ No valid state updates found in delta")
                                    
                                elif event_type == 'STATE_SNAPSHOT':
                                    new_state = event_data.get('snapshot', {})
                                    print(f"📸 State snapshot: {new_state}")
                                    # Replace entire state
                                    self.state = new_state
                                    
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
    
    async def switch_agent(self, agent_type: str) -> bool:
        """Switch to a different agent"""
        available_agents = await self.get_available_agents()
        if available_agents and agent_type in available_agents:
            self.current_agent = agent_type
            print(f"🔄 Switched to {agent_type} agent")
            
            # Show agent capabilities
            agent_info = available_agents[agent_type]
            print(f"📋 Description: {agent_info.get('description', 'No description')}")
            print(f"🔧 Features: {', '.join(agent_info.get('features', []))}")
            
            if 'tools' in agent_info:
                print(f"🛠️ Available tools: {', '.join(agent_info['tools'])}")
            if 'state_operations' in agent_info:
                print(f"💾 State operations: {', '.join(agent_info['state_operations'])}")
            
            return True
        else:
            print(f"❌ Agent '{agent_type}' not available")
            if available_agents:
                print(f"Available agents: {', '.join(available_agents.keys())}")
            return False
    
    async def get_available_agents(self) -> Dict[str, Any]:
        """Get list of available agents from server"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/agents") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {}
        except Exception as e:
            print(f"⚠️ Could not fetch agents: {e}")
            return {}
    
    async def show_state(self):
        """Display current state"""
        if self.state:
            print("📊 Current State:")
            for key, value in self.state.items():
                print(f"  • {key}: {value}")
        else:
            print("📊 No state data available")
    
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

    def is_valid_state_key(self, key: str, value) -> bool:
        """Validate state keys and values before applying them"""
        # Basic validation rules for state keys and values
        
        # Check key is a valid string
        if not isinstance(key, str) or not key:
            return False
        
        # Prevent keys that could be used maliciously
        dangerous_keys = ['__', 'eval', 'exec', 'import', 'open', 'file', 'system', 'subprocess']
        if any(dangerous in key.lower() for dangerous in dangerous_keys):
            return False
        
        # Limit key length to prevent abuse
        if len(key) > 100:
            return False
        
        # Check value types - only allow basic types
        allowed_types = (str, int, float, bool, type(None), list, dict)
        if not isinstance(value, allowed_types):
            return False
        
        # For strings, limit length and check for dangerous content
        if isinstance(value, str):
            if len(value) > 1000:  # Reasonable limit for state values
                return False
            # Prevent potentially dangerous string content
            if any(dangerous in value.lower() for dangerous in ['<script', 'javascript:', 'data:text/html']):
                return False
        
        # For lists and dicts, do recursive validation
        elif isinstance(value, list):
            if len(value) > 100:  # Limit list size
                return False
            return all(self.is_valid_state_key(f"{key}[{i}]", item) for i, item in enumerate(value))
        
        elif isinstance(value, dict):
            if len(value) > 50:  # Limit dict size
                return False
            return all(
                self.is_valid_state_key(f"{key}.{k}", v) 
                for k, v in value.items()
                if isinstance(k, str)
            )
        
        # For numbers, check for reasonable ranges
        elif isinstance(value, (int, float)):
            if abs(value) > 1e10:  # Prevent extremely large numbers
                return False
        
        return True

async def show_help():
    """Display help information"""
    help_text = """
🤖 AG-UI Client Commands:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 Basic Commands:
  • Type any message to chat with the current agent
  • /help or /h          - Show this help
  • /quit, /exit, or /q  - Exit the client
  
🔄 Agent Management:
  • /agent <type>        - Switch to different agent (echo, tool, state)
  • /agents              - List available agents
  • /current             - Show current agent info
  
📊 State Management (when using state agent):
  • /state               - Show current state
  • "my name is [name]"  - Set your name
  • "I prefer [option]"  - Set preferences
  • "what do you know about me?" - Show stored info
  • "reset state"        - Clear all state
  
🛠️ Tool Usage (when using tool agent):
  • "calculate 5 + 3"    - Use calculator tool
  • "what's the weather?" - Use weather tool
  • "what time is it?"   - Use time tool
  
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    print(help_text)

async def main():
    """Main CLI interface"""
    
    print("🤖 AG-UI Multi-Agent Client")
    print("=" * 70)
    
    # Initialize client
    client = AGUIClient()
    
    # Check server health
    print("🔍 Checking server health...")
    if not await client.health_check():
        print("❌ Server is not available. Please start the server first:")
        print("   python server.py")
        return
    
    # Show available agents
    print("\n🔍 Fetching available agents...")
    agents = await client.get_available_agents()
    if agents:
        print("🤖 Available agents:")
        for agent_name, agent_info in agents.items():
            features = ", ".join(agent_info.get('features', []))
            print(f"  • {agent_name}: {agent_info.get('description', 'No description')} [{features}]")
    
    print(f"\n💬 Chat with AG-UI agents! Current agent: {client.current_agent}")
    print("Type '/help' for commands or '/quit' to exit")
    print("-" * 70)
    
    while True:
        try:
            # Get user input
            user_input = input(f"\n👤 You [{client.current_agent}]: ").strip()
            
            # Handle commands
            if user_input.lower() in ['/quit', '/exit', '/q']:
                print("👋 Goodbye!")
                break
            elif user_input.lower() in ['/help', '/h']:
                await show_help()
                continue
            elif user_input.startswith('/agent '):
                agent_type = user_input[7:].strip()
                await client.switch_agent(agent_type)
                continue
            elif user_input.lower() == '/agents':
                agents = await client.get_available_agents()
                if agents:
                    print("🤖 Available agents:")
                    for agent_name, agent_info in agents.items():
                        current = " (current)" if agent_name == client.current_agent else ""
                        print(f"  • {agent_name}{current}: {agent_info.get('description', 'No description')}")
                continue
            elif user_input.lower() == '/current':
                agents = await client.get_available_agents()
                if agents and client.current_agent in agents:
                    agent_info = agents[client.current_agent]
                    print(f"🤖 Current agent: {client.current_agent}")
                    print(f"📋 Description: {agent_info.get('description', 'No description')}")
                    print(f"🔧 Features: {', '.join(agent_info.get('features', []))}")
                continue
            elif user_input.lower() == '/state':
                await client.show_state()
                continue
                
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