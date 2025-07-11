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
        self._add_user_message(content)
        payload = self._create_request_payload()
        
        print(f"\n🤖 Sending message to {self.current_agent} agent: {content}")
        print("📡 Waiting for response...\n")
        
        try:
            await self._stream_agent_response(payload)
        except aiohttp.ClientError as e:
            print(f"❌ Connection error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    def _add_user_message(self, content: str) -> None:
        """Add user message to conversation history"""
        user_message = {
            "id": str(uuid4()),
            "role": "user",
            "content": content
        }
        self.messages.append(user_message)
    
    def _create_request_payload(self) -> Dict[str, Any]:
        """Create the request payload for the agent"""
        return {
            "thread_id": self.thread_id,
            "messages": self.messages,
            "tools": [],
            "state": self.state,
            "context": [],
            "forwardedProps": {},
            "agent_type": self.current_agent
        }
    
    async def _stream_agent_response(self, payload: Dict[str, Any]) -> None:
        """Handle the streaming response from the agent"""
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
                
                await self._process_event_stream(response)
    
    async def _process_event_stream(self, response) -> None:
        """Process the Server-Sent Events stream"""
        # Use a dict to hold mutable state
        stream_state = {
            'current_message': "",
            'message_id': None
        }
        
        async for line in response.content:
            if not (line_str := line.decode('utf-8').strip()) or line_str.startswith(':'):
                continue
                
            if not line_str.startswith('data: '):
                continue
                
            try:
                event_data = self._parse_sse_data(line_str)
                if not event_data:
                    continue
                    
                should_break = await self._handle_event(event_data, stream_state)
                if should_break:
                    break
                    
            except json.JSONDecodeError:
                print(f"⚠️ Failed to parse event: {line_str}")
                continue
            except Exception as e:
                print(f"⚠️ Error processing event: {e}")
                continue
    
    def _parse_sse_data(self, line_str: str) -> Dict[str, Any]:
        """Parse Server-Sent Event data"""
        json_part = line_str[6:]  # Remove "data: " prefix
        return json.loads(json_part)
    
    async def _handle_event(self, event_data: Dict[str, Any], stream_state: Dict[str, Any]) -> bool:
        """Handle a single event from the stream. Returns True if processing should stop."""
        event_type = event_data.get('type')
        
        if event_type == 'RUN_STARTED':
            print("🔄 Agent started processing...")
            
        elif event_type == 'TEXT_MESSAGE_START':
            stream_state['message_id'] = event_data.get('message_id')
            print("💬 Assistant: ", end='', flush=True)
            
        elif event_type == 'TEXT_MESSAGE_CONTENT':
            delta = event_data.get('delta', '')
            stream_state['current_message'] += delta
            print(delta, end='', flush=True)
            
        elif event_type == 'TEXT_MESSAGE_END':
            self._finalize_assistant_message(stream_state['current_message'], stream_state['message_id'])
            # Reset for next message
            stream_state['current_message'] = ""
            stream_state['message_id'] = None
            
        elif event_type == 'TOOL_CALL_START':
            self._handle_tool_call_start(event_data)
            
        elif event_type == 'TOOL_CALL_ARGS':
            self._handle_tool_call_args(event_data)
            
        elif event_type == 'TOOL_CALL_END':
            self._handle_tool_call_end(event_data)
            
        elif event_type == 'STATE_DELTA':
            self._handle_state_delta(event_data)
            
        elif event_type == 'STATE_SNAPSHOT':
            self._handle_state_snapshot(event_data)
            
        elif event_type == 'RUN_FINISHED':
            print("✅ Agent finished processing\n")
            return True
            
        return False
    
    def _finalize_assistant_message(self, current_message: str, message_id: str) -> None:
        """Add completed assistant message to history"""
        print()  # New line after message
        
        # Generate a fallback ID if message_id is None (defensive programming)
        if message_id is None:
            message_id = str(uuid4())
            print("⚠️ Warning: Message ID was None, generated fallback ID")
        
        assistant_message = {
            "id": message_id,
            "role": "assistant", 
            "content": current_message
        }
        self.messages.append(assistant_message)
    
    def _handle_tool_call_start(self, event_data: Dict[str, Any]) -> None:
        """Handle tool call start event"""
        tool_name = event_data.get('tool_call_name', 'unknown')
        tool_call_id = event_data.get('tool_call_id')
        print(f"🔧 Starting tool call: {tool_name} (ID: {tool_call_id})")
    
    def _handle_tool_call_args(self, event_data: Dict[str, Any]) -> None:
        """Handle tool call arguments event"""
        tool_call_id = event_data.get('tool_call_id')
        args = event_data.get('delta', '{}')
        
        try:
            parsed_args = json.loads(args)
            print(f"📋 Tool arguments: {parsed_args}")
        except json.JSONDecodeError:
            print(f"📋 Tool arguments: {args}")
    
    def _handle_tool_call_end(self, event_data: Dict[str, Any]) -> None:
        """Handle tool call end event"""
        tool_call_id = event_data.get('tool_call_id')
        print(f"✅ Tool call completed (ID: {tool_call_id})")
    
    def _handle_state_delta(self, event_data: Dict[str, Any]) -> None:
        """Handle state delta update event using JSON Patch format (RFC 6902)"""
        delta = event_data.get('delta', [])
        print(f"📊 State delta received: {delta}")
        
        # Apply JSON Patch operations
        for operation in delta:
            if not isinstance(operation, dict):
                continue
                
            op = operation.get('op')
            path = operation.get('path', '')
            value = operation.get('value')
            
            # Convert JSON Pointer path to key list
            path_parts = self._parse_json_pointer(path)
            
            try:
                if op == 'replace' or op == 'add':
                    self._apply_json_patch_operation(op, path_parts, value)
                elif op == 'remove':
                    self._remove_json_patch_path(path_parts)
                else:
                    print(f"⚠️ Unsupported JSON Patch operation: {op}")
            except Exception as e:
                print(f"⚠️ Failed to apply JSON Patch operation {op} at {path}: {e}")
        
        print(f"📋 Current state: {self.state}")
    
    def _parse_json_pointer(self, path: str) -> List[str]:
        """Parse JSON Pointer path (RFC 6901) into component parts"""
        if not path or path == '/':
            return []
        
        # Remove leading slash and split
        parts = path[1:].split('/') if path.startswith('/') else path.split('/')
        
        # Decode JSON Pointer special characters
        decoded_parts = []
        for part in parts:
            # Replace ~1 with / and ~0 with ~
            decoded_part = part.replace('~1', '/').replace('~0', '~')
            decoded_parts.append(decoded_part)
        
        return decoded_parts
    
    def _apply_json_patch_operation(self, op: str, path_parts: List[str], value: Any) -> None:
        """Apply a JSON Patch add or replace operation"""
        if not path_parts:
            # Replace entire state
            if isinstance(value, dict):
                self.state = value
            return
        
        # Navigate to parent object
        current = self.state
        for part in path_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Apply the operation
        final_key = path_parts[-1]
        
        # Handle array operations
        if final_key == '-':
            # Append to array
            if isinstance(current, list):
                current.append(value)
            else:
                print(f"⚠️ Cannot append to non-array at path {'/'.join(path_parts[:-1])}")
        elif final_key.isdigit() and isinstance(current, list):
            # Array index operation
            index = int(final_key)
            if op == 'add':
                current.insert(index, value)
            elif op == 'replace':
                if 0 <= index < len(current):
                    current[index] = value
                else:
                    print(f"⚠️ Array index {index} out of bounds")
        else:
            # Object property operation
            if isinstance(current, dict):
                current[final_key] = value
            else:
                print(f"⚠️ Cannot set property on non-object at path {'/'.join(path_parts[:-1])}")
    
    def _remove_json_patch_path(self, path_parts: List[str]) -> None:
        """Remove a path from the state using JSON Patch remove operation"""
        if not path_parts:
            self.state = {}
            return
        
        # Navigate to parent object
        current = self.state
        for part in path_parts[:-1]:
            if part not in current:
                return  # Path doesn't exist
            current = current[part]
        
        # Remove the final key
        final_key = path_parts[-1]
        
        if final_key.isdigit() and isinstance(current, list):
            # Array index removal
            index = int(final_key)
            if 0 <= index < len(current):
                current.pop(index)
        elif isinstance(current, dict) and final_key in current:
            # Object property removal
            del current[final_key]
    
    def _handle_state_snapshot(self, event_data: Dict[str, Any]) -> None:
        """Handle state snapshot event"""
        new_state = event_data.get('snapshot', {})
        print(f"📸 State snapshot: {new_state}")
        self.state = new_state
    
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
                    return await response.json() if response.status == 200 else {}
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

async def _initialize_client() -> AGUIClient:
    """Initialize client and check server health"""
    print("🤖 AG-UI Multi-Agent Client")
    print("=" * 70)
    
    client = AGUIClient()
    
    print("🔍 Checking server health...")
    if not await client.health_check():
        print("❌ Server is not available. Please start the server first:")
        print("   python server.py")
        return None
    
    return client

async def _show_startup_info(client: AGUIClient) -> None:
    """Display startup information and available agents"""
    print("\n🔍 Fetching available agents...")
    if agents := await client.get_available_agents():
        print("🤖 Available agents:")
        for agent_name, agent_info in agents.items():
            features = ", ".join(agent_info.get('features', []))
            print(f"  • {agent_name}: {agent_info.get('description', 'No description')} [{features}]")
    
    print(f"\n💬 Chat with AG-UI agents! Current agent: {client.current_agent}")
    print("Type '/help' for commands or '/quit' to exit")
    print("-" * 70)

async def _handle_user_command(client: AGUIClient, user_input: str) -> bool:
    """Handle a user command. Returns True if should exit."""
    command = user_input.lower()
    
    if command in ['/quit', '/exit', '/q']:
        print("👋 Goodbye!")
        return True
    
    if command in ['/help', '/h']:
        await show_help()
        return False
    
    if user_input.startswith('/agent '):
        agent_type = user_input[7:].strip()
        await client.switch_agent(agent_type)
        return False
    
    if command == '/agents':
        return await _handle_agents_command(client)
    
    if command == '/current':
        return await _handle_current_command(client)
    
    if command == '/state':
        await client.show_state()
        return False
    
    # Not a command, send as message
    if user_input:
        await client.send_message(user_input)
    
    return False

async def _handle_agents_command(client: AGUIClient) -> bool:
    """Handle the /agents command"""
    if agents := await client.get_available_agents():
        print("🤖 Available agents:")
        for agent_name, agent_info in agents.items():
            current = " (current)" if agent_name == client.current_agent else ""
            print(f"  • {agent_name}{current}: {agent_info.get('description', 'No description')}")
    return False

async def _handle_current_command(client: AGUIClient) -> bool:
    """Handle the /current command"""
    agents = await client.get_available_agents()
    if agents and client.current_agent in agents:
        agent_info = agents[client.current_agent]
        print(f"🤖 Current agent: {client.current_agent}")
        print(f"📋 Description: {agent_info.get('description', 'No description')}")
        print(f"🔧 Features: {', '.join(agent_info.get('features', []))}")
    return False

async def _run_main_loop(client: AGUIClient) -> None:
    """Run the main interaction loop"""
    while True:
        try:
            user_input = input(f"\n👤 You [{client.current_agent}]: ").strip()
            if await _handle_user_command(client, user_input):
                break
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Goodbye!")
            break

async def main():
    """Main CLI interface"""
    if client := await _initialize_client():
        await _show_startup_info(client)
        await _run_main_loop(client)

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