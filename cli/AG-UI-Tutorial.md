# Building AG-UI Servers and Clients: A Complete Guide

## Table of Contents
1. [Introduction to AG-UI Protocol](#introduction-to-ag-ui-protocol)
2. [Understanding the Architecture](#understanding-the-architecture)
3. [Building an AG-UI Server](#building-an-ag-ui-server)
4. [Building an AG-UI Client](#building-an-ag-ui-client)
5. [Protocol Compatibility](#protocol-compatibility)
6. [Advanced Features](#advanced-features)
7. [Real-World Implementation Examples](#real-world-implementation-examples)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

> **Note**: This tutorial includes practical examples from a working AG-UI multi-agent implementation. You can find the complete source code referenced throughout this guide in the accompanying files: `server.py`, `client.py`, and `demo.py`.

---

## Introduction to AG-UI Protocol

The **Agent User Interaction Protocol (AG-UI)** is a standardized protocol that establishes consistent communication between front-end applications and AI services. It provides a framework for building sophisticated AI-powered applications with real-time, event-driven interactions.

### Key Benefits
- **Standardized Communication**: Consistent interface regardless of underlying AI implementation
- **Real-time Streaming**: Character-by-character streaming responses
- **Tool Integration**: Support for human-in-the-loop workflows
- **State Management**: Persistent conversation context
- **Multi-Agent Support**: Agent-to-agent collaboration capabilities

### Core Concepts
- **Events**: Standardized messages for communication
- **Streaming**: Real-time data transmission via Server-Sent Events (SSE)
- **Tools**: Functions that agents can request clients to execute
- **State**: Structured data that persists across interactions
- **Messages**: Conversation history with user and assistant messages

---

## Understanding the Architecture

### Client-Server Communication Flow

```
Client                    Server
  |                         |
  |--- POST /agent -------->|  (JSON payload with messages, tools, state)
  |                         |
  |<-- SSE Stream ----------|  (Real-time events)
  |    RUN_STARTED          |
  |    TEXT_MESSAGE_START   |
  |    TEXT_MESSAGE_CONTENT |
  |    TOOL_CALL_START      |
  |    TOOL_CALL_ARGS       |
  |    TOOL_CALL_END        |
  |    STATE_DELTA          |
  |    TEXT_MESSAGE_END     |
  |    RUN_FINISHED         |
```

### Complete Event Types
The AG-UI protocol supports these standardized events:

#### Core Lifecycle Events
- **`RUN_STARTED`**: Indicates agent has started processing
- **`RUN_FINISHED`**: Indicates agent has finished processing

#### Text Message Events
- **`TEXT_MESSAGE_START`**: Begins a new assistant message
- **`TEXT_MESSAGE_CONTENT`**: Streams message content (delta)
- **`TEXT_MESSAGE_END`**: Completes the assistant message

#### Tool Calling Events
- **`TOOL_CALL_START`**: Beginning of a tool call
- **`TOOL_CALL_ARGS`**: Tool call arguments (streamed)
- **`TOOL_CALL_END`**: Tool call completion

#### State Management Events
- **`STATE_DELTA`**: Incremental state updates
- **`STATE_SNAPSHOT`**: Complete state refresh

#### Additional Events
- **`CUSTOM_EVENT`**: Custom agent-specific events
- **`STEP_STARTED`**: Multi-step process tracking
- **`STEP_FINISHED`**: Step completion

---

## Building an AG-UI Server

### 1. Core Dependencies

Based on our working implementation, you'll need these dependencies:

```python
# requirements.txt (from actual working implementation)
ag-ui-protocol
fastapi
uvicorn
sse-starlette
python-multipart
aiohttp
```

**Installation:**
```bash
pip install -r requirements.txt
```

### 5. State Agent (Demonstrates State Management)

State management allows agents to maintain persistent information across conversations. AG-UI provides two types of state events: `STATE_DELTA` for incremental updates and `STATE_SNAPSHOT` for complete state replacement.

**Important**: AG-UI state deltas use **JSON Patch format (RFC 6902)** for standardized, interoperable state updates.

#### State Event Sequence

```
1. STATE_SNAPSHOT → Complete state refresh (initial or reset)
2. STATE_DELTA    → Incremental state updates (JSON Patch format)
```

#### JSON Patch Format Overview

AG-UI uses JSON Patch (RFC 6902) for state deltas, providing standardized operations:

```python
# Basic JSON Patch operations
{
    "op": "add",        # Add a new value
    "path": "/user_name", # JSON Pointer to target location
    "value": "Alice"    # Value to add
}

{
    "op": "replace",    # Replace existing value
    "path": "/conversation_count",
    "value": 5
}

{
    "op": "remove",     # Remove a value
    "path": "/temporary_data"
}

{
    "op": "add",        # Append to array
    "path": "/topics/-", # "-" means append
    "value": "new_topic"
}
```

#### Complete Enhanced State Agent Implementation

```python
class StateAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        # Simple in-memory state storage (use proper storage in production)
        self.memory = {}
    
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Agent demonstrating proper AG-UI state management with JSON Patch"""
        
        thread_id = input.thread_id
        run_id = input.run_id
        
        # Emit RUN_STARTED event
        yield self._format_sse(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=thread_id,
            run_id=run_id
        ))
        
        # Initialize thread-specific memory
        self._ensure_thread_memory(thread_id)
        
        # Send initial state snapshot (required by AG-UI protocol)
        if not self.memory[thread_id].get("initialized"):
            yield self._format_sse(StateSnapshotEvent(
                type=EventType.STATE_SNAPSHOT,
                snapshot=self.memory[thread_id]
            ))
            self.memory[thread_id]["initialized"] = True
        
        # Process user message with proper state updates
        if user_messages := [msg for msg in input.messages if getattr(msg, 'role', None) == 'user']:
            async for event in self._process_user_message(thread_id, user_messages[-1]):
                yield event
        
        # Emit RUN_FINISHED event
        yield self._format_sse(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=thread_id,
            run_id=run_id
        ))
    
    def _ensure_thread_memory(self, thread_id: str) -> None:
        """Initialize thread memory if needed"""
        if thread_id not in self.memory:
            self.memory[thread_id] = {
                "user_name": None,
                "preferences": {},
                "conversation_count": 0,
                "topics": [],
                "initialized": False
            }
    
    async def _process_user_message(self, thread_id: str, message) -> AsyncGenerator[str, None]:
        """Process user message with JSON Patch state updates"""
        content = getattr(message, 'content', '').lower()
        
        # Update conversation count using JSON Patch format
        self.memory[thread_id]["conversation_count"] += 1
        
        # Emit state delta in proper JSON Patch format (RFC 6902)
        yield self._format_sse(StateDeltaEvent(
            type=EventType.STATE_DELTA,
            delta=[{"op": "replace", "path": "/conversation_count", "value": self.memory[thread_id]["conversation_count"]}]
        ))
        
        # Route to appropriate handler
        if content.startswith('my name is'):
            async for event in self._handle_name_setting(thread_id, content):
                yield event
        elif 'prefer' in content:
            async for event in self._handle_preference_setting(thread_id, content):
                yield event
        # ... other handlers
    
    async def _handle_name_setting(self, thread_id: str, content: str) -> AsyncGenerator[str, None]:
        """Handle name setting with proper JSON Patch format"""
        if name := content.replace('my name is', '').strip().title():
            old_name = self.memory[thread_id]["user_name"]
            self.memory[thread_id]["user_name"] = name
            
            # Emit state delta using JSON Patch format
            op = "replace" if old_name else "add"
            yield self._format_sse(StateDeltaEvent(
                type=EventType.STATE_DELTA,
                delta=[{"op": op, "path": "/user_name", "value": name}]
            ))
            
            # Send response...
    
    async def _handle_preference_setting(self, thread_id: str, content: str) -> AsyncGenerator[str, None]:
        """Handle preferences with nested JSON Patch operations"""
        if 'dark mode' in content:
            self.memory[thread_id]["preferences"]["theme"] = "dark"
            pref_path = "/preferences/theme"
            pref_value = "dark"
        # ... handle other preferences
        
        # Emit state delta using JSON Patch format for nested objects
        yield self._format_sse(StateDeltaEvent(
            type=EventType.STATE_DELTA,
            delta=[{"op": "add", "path": pref_path, "value": pref_value}]
        ))
        
        # Send response...
```

#### Advanced State Management Patterns

##### Pattern 1: Nested Object Updates
```python
# Update nested preference
yield self._format_sse(StateDeltaEvent(
    type=EventType.STATE_DELTA,
    delta=[{"op": "add", "path": "/preferences/ui/theme", "value": "dark"}]
))
```

##### Pattern 2: Array Operations
```python
# Append to array
yield self._format_sse(StateDeltaEvent(
    type=EventType.STATE_DELTA,
    delta=[{"op": "add", "path": "/topics/-", "value": "new_topic"}]
))

# Insert at specific position
yield self._format_sse(StateDeltaEvent(
    type=EventType.STATE_DELTA,
    delta=[{"op": "add", "path": "/topics/0", "value": "first_topic"}]
))

# Remove array item
yield self._format_sse(StateDeltaEvent(
    type=EventType.STATE_DELTA,
    delta=[{"op": "remove", "path": "/topics/2"}]
))
```

##### Pattern 3: Complex State Operations
```python
# Multiple simultaneous updates
yield self._format_sse(StateDeltaEvent(
    type=EventType.STATE_DELTA,
    delta=[
        {"op": "replace", "path": "/user_name", "value": "Alice"},
        {"op": "add", "path": "/preferences/language", "value": "en"},
        {"op": "replace", "path": "/last_seen", "value": "2024-01-15T10:30:00Z"},
        {"op": "add", "path": "/capabilities/-", "value": "advanced_user"}
    ]
))
```

##### Pattern 4: State Reset with Snapshot
```python
# Complete state replacement
yield self._format_sse(StateSnapshotEvent(
    type=EventType.STATE_SNAPSHOT,
    snapshot={
        "user_name": None,
        "preferences": {},
        "conversation_count": 0,
        "topics": [],
        "initialized": True
    }
))
```

#### Client-Side JSON Patch Processing

The client must properly handle JSON Patch operations:

```python
class AGUIClient:
    def _handle_state_delta(self, event_data: Dict[str, Any]) -> None:
        """Handle state delta using JSON Patch format (RFC 6902)"""
        delta = event_data.get('delta', [])
        
        # Apply JSON Patch operations
        for operation in delta:
            op = operation.get('op')
            path = operation.get('path', '')
            value = operation.get('value')
            
            # Convert JSON Pointer path to key list
            path_parts = self._parse_json_pointer(path)
            
            if op == 'replace' or op == 'add':
                self._apply_json_patch_operation(op, path_parts, value)
            elif op == 'remove':
                self._remove_json_patch_path(path_parts)
    
    def _parse_json_pointer(self, path: str) -> List[str]:
        """Parse JSON Pointer path (RFC 6901) into component parts"""
        if not path or path == '/':
            return []
        
        # Remove leading slash and split
        parts = path[1:].split('/') if path.startswith('/') else path.split('/')
        
        # Decode JSON Pointer special characters (~1 -> /, ~0 -> ~)
        return [part.replace('~1', '/').replace('~0', '~') for part in parts]
    
    def _apply_json_patch_operation(self, op: str, path_parts: List[str], value: Any) -> None:
        """Apply JSON Patch add or replace operation"""
        if not path_parts:
            if isinstance(value, dict):
                self.state = value
            return
        
        # Navigate to parent and apply operation
        current = self.state
        for part in path_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        final_key = path_parts[-1]
        
        # Handle array append (-)
        if final_key == '-' and isinstance(current, list):
            current.append(value)
        # Handle array index
        elif final_key.isdigit() and isinstance(current, list):
            index = int(final_key)
            if op == 'add':
                current.insert(index, value)
            elif op == 'replace' and 0 <= index < len(current):
                current[index] = value
        # Handle object property
        elif isinstance(current, dict):
            current[final_key] = value
```

### 6. Human-in-the-Loop (HITL) Agent

The HITL Agent demonstrates how to implement proper human-in-the-loop workflows as emphasized in the AG-UI documentation. This pattern enables collaborative decision-making between humans and AI agents.

#### Core HITL Principles

1. **Real-time Visibility**: Users can observe the agent's thought process
2. **Contextual Awareness**: Agent accesses user actions and preferences  
3. **Collaborative Decision-making**: Both human and AI contribute to state
4. **Feedback Loops**: Humans can correct or guide agent behavior

#### Complete HITL Agent Implementation

```python
class HitlAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        # Store pending actions for user approval
        self.pending_actions = {}
        # Store user context and state
        self.memory = {}
    
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Agent implementing Human-in-the-Loop workflows"""
        yield self._format_sse(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=input.thread_id,
            run_id=input.run_id
        ))
        
        self._ensure_thread_memory(input.thread_id)
        
        # Send state snapshot showing current HITL context
        yield self._format_sse(StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT,
            snapshot={
                "pending_actions": self.pending_actions.get(input.thread_id, []),
                "user_preferences": self.memory[input.thread_id].get("preferences", {}),
                "interaction_mode": "human_in_the_loop",
                "trust_level": self.memory[input.thread_id].get("trust_level", "new_user")
            }
        ))
        
        if user_messages := [msg for msg in input.messages if getattr(msg, 'role', None) == 'user']:
            async for event in self._process_hitl_message(input.thread_id, user_messages[-1]):
                yield event
        
        yield self._format_sse(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=input.thread_id,
            run_id=input.run_id
        ))
    
    def _ensure_thread_memory(self, thread_id: str) -> None:
        """Initialize HITL-specific thread memory"""
        if thread_id not in self.memory:
            self.memory[thread_id] = {
                "preferences": {},
                "interaction_history": [],
                "trust_level": "new_user"  # new_user, trusted, verified
            }
        if thread_id not in self.pending_actions:
            self.pending_actions[thread_id] = []
```

#### HITL Workflow Patterns

##### Pattern 1: Action Proposal with Approval
```python
async def _propose_email_action(self, thread_id: str, content: str) -> AsyncGenerator[str, None]:
    """Propose an action and request user approval"""
    # Create proposed action
    proposed_action = {
        "id": str(uuid4()),
        "type": "send_email",
        "details": {
            "recipient": "team@company.com",
            "subject": "Meeting Update",
            "content": content.replace('send email', '').strip()
        },
        "risk_level": "medium",
        "requires_approval": True
    }
    
    # Add to pending actions
    self.pending_actions[thread_id].append(proposed_action)
    
    # Update state with pending action
    yield self._format_sse(StateDeltaEvent(
        type=EventType.STATE_DELTA,
        delta=[{"op": "add", "path": "/pending_actions/-", "value": proposed_action}]
    ))
    
    # Ask for user approval
    approval_message = (
        f"🤔 **Action Requires Approval**\n\n"
        f"I want to send an email:\n"
        f"• To: {proposed_action['details']['recipient']}\n"
        f"• Subject: {proposed_action['details']['subject']}\n"
        f"• Content: {proposed_action['details']['content']}\n\n"
        f"Do you approve? (yes/no)"
    )
    
    async for event in self._send_text_message(approval_message):
        yield event
```

##### Pattern 2: Risk-Based Approval
```python
async def _propose_deletion_action(self, thread_id: str, content: str) -> AsyncGenerator[str, None]:
    """High-risk actions require explicit confirmation"""
    proposed_action = {
        "id": str(uuid4()),
        "type": "delete_data",
        "details": {"target": content.replace('delete', '').strip()},
        "risk_level": "high",
        "requires_approval": True
    }
    
    # High-risk actions get special treatment
    approval_message = (
        f"⚠️ **HIGH RISK ACTION**\n\n"
        f"You want to delete: {proposed_action['details']['target']}\n"
        f"This action is PERMANENT and cannot be undone.\n\n"
        f"Are you absolutely sure? (yes/no)"
    )
    
    # Add to state and request approval...
```

##### Pattern 3: Trust-Based Automation
```python
async def _propose_calculation_action(self, thread_id: str, content: str) -> AsyncGenerator[str, None]:
    """Low-risk actions can be auto-approved for trusted users"""
    expression = content.replace('calculate', '').strip()
    trust_level = self.memory[thread_id].get("trust_level", "new_user")
    
    if trust_level == "new_user":
        # Request approval for new users
        proposed_action = {
            "type": "calculation",
            "details": {"expression": expression},
            "risk_level": "low",
            "requires_approval": True
        }
        
        # Add to pending actions and request approval...
    else:
        # Auto-approve for trusted users
        async for event in self._execute_calculation(thread_id, expression):
            yield event
```

##### Pattern 4: Approval Processing
```python
async def _handle_approval(self, thread_id: str) -> AsyncGenerator[str, None]:
    """Process user approval of pending actions"""
    if not self.pending_actions[thread_id]:
        async for event in self._send_text_message("No pending actions to approve."):
            yield event
        return
    
    # Get and remove approved action
    action = self.pending_actions[thread_id].pop(0)
    
    # Update state to remove pending action
    yield self._format_sse(StateDeltaEvent(
        type=EventType.STATE_DELTA,
        delta=[{"op": "remove", "path": "/pending_actions/0"}]
    ))
    
    # Execute the approved action
    if action["type"] == "send_email":
        async for event in self._execute_email_action(thread_id, action):
            yield event
    elif action["type"] == "delete_data":
        async for event in self._execute_deletion_action(thread_id, action):
            yield event
    # ... handle other action types
```

#### HITL State Integration

HITL workflows generate rich state information:

```python
# Track interaction history
self.memory[thread_id]["interaction_history"].append({
    "action": "email_sent",
    "timestamp": datetime.now().isoformat(),
    "user_approved": True,
    "details": action["details"]
})

# Update trust level based on interactions
successful_actions = len([h for h in self.memory[thread_id]["interaction_history"] 
                         if h.get("user_approved")])
if successful_actions > 10:
    self.memory[thread_id]["trust_level"] = "trusted"
    
    # Emit state update
    yield self._format_sse(StateDeltaEvent(
        type=EventType.STATE_DELTA,
        delta=[{"op": "replace", "path": "/user_preferences/trust_level", "value": "trusted"}]
    ))
```

#### Advanced HITL Patterns

##### Contextual Decision Making
```python
# Agent uses state to make informed proposals
user_preferences = self.memory[thread_id].get("preferences", {})
if user_preferences.get("email_notifications") == "minimal":
    # Propose batch email instead of individual emails
    # ...

# Agent learns from user feedback
rejection_count = len([h for h in self.memory[thread_id]["interaction_history"] 
                      if not h.get("user_approved")])
if rejection_count > 5:
    # Increase approval threshold for this user
    self.memory[thread_id]["trust_level"] = "cautious"
```

##### Collaborative State Building
```python
# Human and agent collaboratively build state
async def _handle_preference_learning(self, thread_id: str, feedback: str):
    """Learn from user feedback to improve future proposals"""
    if "too many emails" in feedback:
        self.memory[thread_id]["preferences"]["email_frequency"] = "low"
    elif "need more details" in feedback:
        self.memory[thread_id]["preferences"]["detail_level"] = "high"
    
    # Update state with learned preferences
    yield self._format_sse(StateDeltaEvent(
        type=EventType.STATE_DELTA,
        delta=[{"op": "replace", "path": "/preferences", "value": self.memory[thread_id]["preferences"]}]
    ))
```

### State Management Best Practices

1. **Use JSON Patch**: Always use RFC 6902 JSON Patch format for state deltas
2. **Thread Isolation**: Keep state separate per thread_id  
3. **Delta vs Snapshot**: Use deltas for incremental changes, snapshots for resets
4. **Structured Paths**: Use clear JSON Pointer paths (/user/preferences/theme)
5. **Validation**: Validate state changes before applying
6. **HITL Integration**: Use state to enable collaborative decision-making
7. **Persistence**: In production, use proper databases for state storage
8. **Security**: Validate and sanitize all state data

### Advanced State Management Considerations

#### Production State Storage
```python
# Example with database integration
class PersistentStateAgent(BaseAgent):
    def __init__(self, db_connection):
        super().__init__()
        self.db = db_connection
    
    async def _save_state(self, thread_id: str, state: dict):
        """Save state to persistent storage"""
        await self.db.upsert_state(thread_id, state)
    
    async def _load_state(self, thread_id: str) -> dict:
        """Load state from persistent storage"""
        return await self.db.get_state(thread_id) or {}
```

#### State Synchronization Conflict Resolution
```python
async def _handle_state_conflict(self, local_state: dict, server_state: dict) -> dict:
    """Resolve conflicts between local and server state"""
    # Implement merge strategy (last-write-wins, user-preference, etc.)
    resolved_state = {}
    
    # Example: User preferences take precedence
    resolved_state.update(server_state)
    if "user_preferences" in local_state:
        resolved_state["user_preferences"] = local_state["user_preferences"]
    
    return resolved_state
```

This comprehensive state management system provides the foundation for sophisticated AI applications that combine the best of human intuition and AI capabilities through the AG-UI protocol.

---

## Building an AG-UI Client

### 1. Complete Client Implementation

```python
import asyncio
import json
import aiohttp
from typing import Dict, Any, List
from uuid import uuid4

class AGUIClient:
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.thread_id = str(uuid4())
        self.messages: List[Dict[str, Any]] = []
        self.state: Dict[str, Any] = {}
        self.current_agent = "echo"
        
    async def send_message(self, content: str) -> None:
        """Send message and process all event types"""
        
        # Add user message to history
        user_message = {
            "id": str(uuid4()),
            "role": "user",
            "content": content
        }
        self.messages.append(user_message)
        
        # Prepare AG-UI compliant payload
        payload = {
            "thread_id": self.thread_id,
            "messages": self.messages,
            "tools": [],
            "state": self.state,
            "context": [],
            "forwardedProps": {},
            "agent_type": self.current_agent
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.server_url}/agent",
                json=payload,
                headers={"Accept": "text/event-stream"}
            ) as response:
                
                await self._process_event_stream(response)
    
    async def _process_event_stream(self, response):
        """Process all AG-UI event types"""
        current_message = ""
        message_id = None
        
        async for line in response.content:
            line_str = line.decode('utf-8').strip()
            
            if line_str.startswith('data: '):
                json_part = line_str[6:]  # Remove "data: " prefix
                
                try:
                    event_data = json.loads(json_part)
                    event_type = event_data.get('type')
                    
                    # Core lifecycle events
                    if event_type == 'RUN_STARTED':
                        print("🔄 Agent started processing...")
                        
                    elif event_type == 'RUN_FINISHED':
                        print("✅ Agent finished processing\n")
                        break
                    
                    # Text message events
                    elif event_type == 'TEXT_MESSAGE_START':
                        message_id = event_data.get('message_id')
                        print("💬 Assistant: ", end='', flush=True)
                        
                    elif event_type == 'TEXT_MESSAGE_CONTENT':
                        delta = event_data.get('delta', '')
                        current_message += delta
                        print(delta, end='', flush=True)
                        
                    elif event_type == 'TEXT_MESSAGE_END':
                        print()  # New line
                        # Add to message history
                        self.messages.append({
                            "id": message_id,
                            "role": "assistant",
                            "content": current_message
                        })
                        current_message = ""
                    
                    # Tool calling events
                    elif event_type == 'TOOL_CALL_START':
                        tool_name = event_data.get('tool_call_name', 'unknown')
                        tool_call_id = event_data.get('tool_call_id')
                        print(f"🔧 Tool call: {tool_name} (ID: {tool_call_id})")
                        
                    elif event_type == 'TOOL_CALL_ARGS':
                        args = event_data.get('delta', '{}')
                        try:
                            parsed_args = json.loads(args)
                            print(f"📋 Arguments: {parsed_args}")
                        except json.JSONDecodeError:
                            print(f"📋 Arguments: {args}")
                            
                    elif event_type == 'TOOL_CALL_END':
                        tool_call_id = event_data.get('tool_call_id')
                        print("✅ Tool call completed")
                    
                    # State management events
                    elif event_type == 'STATE_DELTA':
                        delta = event_data.get('delta', {})
                        print(f"📊 State updated: {delta}")
                        self.state.update(delta)
                        
                    elif event_type == 'STATE_SNAPSHOT':
                        new_state = event_data.get('snapshot', {})
                        print(f"📸 State snapshot: {new_state}")
                        self.state = new_state
                        
                except json.JSONDecodeError:
                    continue
    
    async def switch_agent(self, agent_type: str):
        """Switch to a different agent"""
        agents = await self._get_available_agents()
        if agents and agent_type in agents:
            self.current_agent = agent_type
            print(f"🔄 Switched to {agent_type} agent")
            return True
        return False
    
    async def _get_available_agents(self):
        """Get available agents from server"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/agents") as response:
                    if response.status == 200:
                        return await response.json()
        except:
            pass
        return {}
```

### 2. CLI Interface with Command Support

```python
async def main():
    """Complete CLI with all features"""
    
    client = AGUIClient()
    
    print("🤖 AG-UI Multi-Agent Client")
    print("Available commands:")
    print("  /agent <type>  - Switch agent (echo, tool, state)")
    print("  /help          - Show help")
    print("  /quit          - Exit")
    
    while True:
        user_input = input(f"\n👤 You [{client.current_agent}]: ").strip()
        
        if user_input.startswith('/agent '):
            agent_type = user_input[7:].strip()
            await client.switch_agent(agent_type)
        elif user_input == '/quit':
            break
        elif user_input == '/help':
            print("Help: Use /agent to switch, type messages to chat")
        else:
            await client.send_message(user_input)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Protocol Compatibility

### Universal Client Compatibility

**Yes, your AG-UI client works with ANY AG-UI compliant server!** Here's why:

#### 1. **Standardized Events**
All AG-UI servers emit the same core events:
- `RUN_STARTED` / `RUN_FINISHED` for lifecycle
- `TEXT_MESSAGE_*` for text responses
- `TOOL_CALL_*` for tool interactions
- `STATE_*` for state management

#### 2. **Consistent Transport**
- HTTP POST requests with JSON payloads
- Server-Sent Events for real-time streaming
- Standard headers and content types

#### 3. **Flexible Payload Structure**
```json
{
  "thread_id": "uuid",
  "messages": [...],
  "tools": [...],
  "state": {...},
  "context": [...],
  "forwardedProps": {...}
}
```

### Cross-Platform Testing

```python
# Test with different servers
servers = [
    "http://localhost:8000",      # Your local server
    "http://another-ai.com",      # Different implementation
    "https://production.ai"       # Production server
]

for server_url in servers:
    client = AGUIClient(server_url)
    await client.send_message("Hello!")  # Same code works everywhere!
```

### 6. Advanced Integration: Tools + State

Combining tool calling with state management creates powerful, context-aware agents that can perform complex workflows while maintaining conversation history.

#### Hybrid Agent Example

```python
class HybridAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.memory = {}
        self.tool_history = {}
    
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Agent that combines tool calling with state management"""
        
        thread_id = input.thread_id
        run_id = input.run_id
        
        # Initialize state
        if thread_id not in self.memory:
            self.memory[thread_id] = {
                "user_name": None,
                "tool_usage_count": 0,
                "calculation_history": [],
                "preferences": {}
            }
            
            # Send initial state
            yield self.encoder.encode(StateSnapshotEvent(
                type=EventType.STATE_SNAPSHOT,
                snapshot=self.memory[thread_id]
            ))
        
        yield self.encoder.encode(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=thread_id,
            run_id=run_id
        ))
        
        # Process user message
        user_messages = [msg for msg in input.messages if getattr(msg, 'role', None) == 'user']
        if user_messages:
            latest_message = user_messages[-1]
            content = getattr(latest_message, 'content', '')
            
            # Determine action based on content and state
            if 'calculate' in content.lower() or any(op in content for op in ['+', '-', '*', '/']):
                await self._handle_stateful_calculation(thread_id, content)
            elif 'my calculation history' in content.lower():
                await self._show_calculation_history(thread_id)
            elif 'my name is' in content.lower():
                await self._handle_name_with_tool_context(thread_id, content)
            else:
                await self._handle_contextual_response(thread_id, content)
        
        yield self.encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=thread_id,
            run_id=run_id
        ))
    
    async def _handle_stateful_calculation(self, thread_id: str, content: str):
        """Perform calculation while updating state"""
        
        # Extract expression
        expression = content.lower().replace('calculate', '').strip()
        tool_call_id = str(uuid4())
        
        # Call calculator tool
        yield self.encoder.encode(ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            tool_call_name="calculator",
            tool_call_id=tool_call_id
        ))
        
        args = {"expression": expression}
        yield self.encoder.encode(ToolCallArgsEvent(
            type=EventType.TOOL_CALL_ARGS,
            tool_call_id=tool_call_id,
            delta=json.dumps(args)
        ))
        
        yield self.encoder.encode(ToolCallEndEvent(
            type=EventType.TOOL_CALL_END,
            tool_call_id=tool_call_id
        ))
        
        # Perform calculation
        try:
            result = eval(expression.replace('x', '*'))
            calculation_record = {
                "expression": expression,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
            # Update state
            self.memory[thread_id]["tool_usage_count"] += 1
            self.memory[thread_id]["calculation_history"].append(calculation_record)
            
            # Emit state updates
            yield self.encoder.encode(StateDeltaEvent(
                type=EventType.STATE_DELTA,
                delta=[
                    {"path": ["tool_usage_count"], "value": self.memory[thread_id]["tool_usage_count"]},
                    {"path": ["calculation_history"], "value": self.memory[thread_id]["calculation_history"]}
                ]
            ))
            
            # Contextual response
            user_name = self.memory[thread_id].get("user_name", "")
            greeting = f"{user_name}, " if user_name else ""
            response = f"{greeting}calculation result: {expression} = {result}. "
            response += f"This is your {self.memory[thread_id]['tool_usage_count']} calculation with me!"
            
        except Exception as e:
            response = f"Sorry, I couldn't calculate '{expression}'. Error: {str(e)}"
        
        async for event in self._send_text_message(response):
            yield event
    
    async def _show_calculation_history(self, thread_id: str):
        """Show user's calculation history"""
        history = self.memory[thread_id]["calculation_history"]
        
        if not history:
            response = "You haven't done any calculations with me yet!"
        else:
            response = f"📊 Your calculation history ({len(history)} calculations):\n"
            for i, calc in enumerate(history[-5:], 1):  # Show last 5
                response += f"{i}. {calc['expression']} = {calc['result']}\n"
            
            if len(history) > 5:
                response += f"... and {len(history) - 5} more calculations"
        
        async for event in self._send_text_message(response):
            yield event
    
    async def _handle_name_with_tool_context(self, thread_id: str, content: str):
        """Handle name setting with tool usage context"""
        name = content.replace('my name is', '').strip().title()
        old_name = self.memory[thread_id]["user_name"]
        self.memory[thread_id]["user_name"] = name
        
        # Update state
        yield self.encoder.encode(StateDeltaEvent(
            type=EventType.STATE_DELTA,
            delta=[{"path": ["user_name"], "value": name}]
        ))
        
        # Contextual response based on tool usage
        tool_count = self.memory[thread_id]["tool_usage_count"]
        if tool_count > 0:
            response = f"Nice to meet you, {name}! I see you've already used {tool_count} tools with me. "
            response += "I'll remember your name for all future calculations and interactions!"
        else:
            response = f"Hello {name}! I'm excited to help you with calculations and other tasks."
        
        async for event in self._send_text_message(response):
            yield event
    
    async def _handle_contextual_response(self, thread_id: str, content: str):
        """Provide contextual responses based on state"""
        user_name = self.memory[thread_id].get("user_name")
        tool_count = self.memory[thread_id]["tool_usage_count"]
        calc_count = len(self.memory[thread_id]["calculation_history"])
        
        # Build contextual response
        if user_name:
            greeting = f"Hi {user_name}! "
        else:
            greeting = "Hello! "
        
        if tool_count > 0:
            context = f"I see you've used {tool_count} tools with me"
            if calc_count > 0:
                context += f", including {calc_count} calculations"
            context += ". "
        else:
            context = "I can help you with calculations, remember information about you, and more. "
        
        response = greeting + context + "What would you like to do today?"
        
        async for event in self._send_text_message(response):
            yield event
```

---

## Advanced Features

### 1. Multi-Agent Workflows

```python
class OrchestrationAgent(BaseAgent):
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Agent that coordinates with other agents"""
        
        yield self.encoder.encode(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=input.thread_id,
            run_id=input.run_id
        ))
        
        # Analyze request and delegate to appropriate agent
        user_message = self._get_latest_user_message(input.messages)
        
        if 'calculate' in user_message.lower():
            # Delegate to tool agent
            async for event in self._delegate_to_agent('tool', input):
                yield event
        elif 'remember' in user_message.lower():
            # Delegate to state agent
            async for event in self._delegate_to_agent('state', input):
                yield event
        else:
            # Handle with echo agent
            async for event in self._delegate_to_agent('echo', input):
                yield event
        
        yield self.encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=input.thread_id,
            run_id=input.run_id
        ))
```

### 2. Custom Events

```python
from ag_ui.core import CustomEvent

class AnalyticsAgent(BaseAgent):
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Agent that emits custom analytics events"""
        
        # Emit custom event for analytics
        yield self.encoder.encode(CustomEvent(
            type="ANALYTICS_EVENT",
            data={
                "user_sentiment": "positive",
                "topic_category": "general",
                "response_time_ms": 150
            }
        ))
        
        # Continue with regular response...
```

### 3. Error Handling

```python
from ag_ui.core import RunErrorEvent

class RobustAgent(BaseAgent):
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Agent with comprehensive error handling"""
        
        try:
            yield self.encoder.encode(RunStartedEvent(
                type=EventType.RUN_STARTED,
                thread_id=input.thread_id,
                run_id=input.run_id
            ))
            
            # Agent logic here...
            
        except Exception as e:
            # Emit error event
            yield self.encoder.encode(RunErrorEvent(
                type=EventType.RUN_ERROR,
                error=str(e),
                thread_id=input.thread_id,
                run_id=input.run_id
            ))
        
        finally:
            yield self.encoder.encode(RunFinishedEvent(
                type=EventType.RUN_FINISHED,
                thread_id=input.thread_id,
                run_id=input.run_id
            ))
```

---

## Real-World Implementation Examples

> **These examples are from the actual working implementation included with this tutorial**

### Example 1: Running the Complete Multi-Agent System

**Starting the Server:**
```bash
python server.py
```

**Using the Interactive Client:**
```bash
python client.py

# Interactive session with real output:
🤖 AG-UI Multi-Agent Client
Available commands:
  /agent <type>  - Switch agent (echo, tool, state)
  /help          - Show help  
  /quit          - Exit

👤 You [echo]: Hello, world!
🤖 Sending message to echo agent: Hello, world!
📡 Waiting for response...

🔄 Agent started processing...
💬 Assistant: Echo: Hello, world!
✅ Agent finished processing

👤 You [echo]: /agent tool
🔄 Switched to tool agent

👤 You [tool]: calculate 15 * 7 + 3
🤖 Sending message to tool agent: calculate 15 * 7 + 3
📡 Waiting for response...

🔄 Agent started processing...
🔧 Starting tool call: calculator (ID: abc123)
📋 Tool arguments: {"expression": "15 * 7 + 3"}
✅ Tool call completed (ID: abc123)
💬 Assistant: Calculation result: 15 * 7 + 3 = 108
✅ Agent finished processing
```

**Running the Comprehensive Demo:**
```bash
python demo.py

# Output shows all agent types in action:
🚀 AG-UI Multi-Agent Comprehensive Demo
🔸 DEMO 1: ECHO AGENT
🔸 DEMO 2: TOOL AGENT (calculator, weather, time)
🔸 DEMO 3: STATE AGENT (user data, preferences)
🔸 DEMO 4: AGENT SWITCHING
✅ DEMO COMPLETE - All AG-UI features demonstrated!
```

### Example 2: State Management in Action

**Real State Agent Usage:**
```bash
👤 You [state]: my name is Alice
🔄 Agent started processing...
📊 State updated: [{"path": ["user_name"], "value": "Alice"}]
💬 Assistant: Nice to meet you, Alice! I'll remember your name.
✅ Agent finished processing

👤 You [state]: I prefer dark mode  
🔄 Agent started processing...
📊 State updated: [{"path": ["user_preferences", "theme"], "value": "dark"}]
💬 Assistant: I've noted that you prefer dark mode!
✅ Agent finished processing

👤 You [state]: what do you know about me?
💬 Assistant: 📊 Here's what I know about you:
• Name: Alice
• Conversations: 3
• Preferences: {'theme': 'dark'}
• Topics discussed: 2
```

### Example 3: Tool Agent Features

**Calculator Tool:**
```bash
👤 You [tool]: calculate (15 + 5) * 2 - 3
🔧 Starting tool call: calculator (ID: def456)
📋 Tool arguments: {"expression": "(15 + 5) * 2 - 3"}
✅ Tool call completed (ID: def456)
💬 Assistant: Calculation result: (15 + 5) * 2 - 3 = 37
```

**Weather Tool:**
```bash
👤 You [tool]: what's the weather?
🔧 Starting tool call: weather (ID: ghi789)
📋 Tool arguments: {"location": "current"}
✅ Tool call completed (ID: ghi789)
💬 Assistant: 🌤️ Current weather: 72°F, partly cloudy with light winds. (This is a simulated response)
```

**Time Tool:**
```bash
👤 You [tool]: what time is it?
🔧 Starting tool call: get_time (ID: jkl012)
📋 Tool arguments: {"timezone": "local"}
✅ Tool call completed (ID: jkl012)
💬 Assistant: 🕐 Current time: 2024-01-15 14:30:25
```

### Example 3: Multi-Feature Agent

```python
class AdvancedAgent(BaseAgent):
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Agent combining all features"""
        
        yield self.encoder.encode(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=input.thread_id,
            run_id=input.run_id
        ))
        
        # Get user message
        user_message = self._get_latest_user_message(input.messages)
        content = user_message.lower()
        
        # Update state
        current_state = input.state or {"interactions": 0}
        current_state["interactions"] += 1
        current_state["last_message"] = content
        
        yield self.encoder.encode(StateDeltaEvent(
            type=EventType.STATE_DELTA,
            delta={"interactions": current_state["interactions"]}
        ))
        
        # Handle different request types
        if 'calculate' in content:
            # Use calculator tool
            async for event in self._handle_calculator_tool(content):
                yield event
        elif 'weather' in content:
            # Use weather tool
            async for event in self._handle_weather_tool():
                yield event
        else:
            # Regular text response
            response = f"I've processed {current_state['interactions']} interactions with you."
            async for event in self._send_text_message(response):
                yield event
        
        yield self.encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=input.thread_id,
            run_id=input.run_id
        ))
```

---

## Best Practices

### Server Development

1. **Event Sequence**: Always emit `RUN_STARTED` → Content Events → `RUN_FINISHED`
2. **Error Handling**: Wrap agent logic in try-catch and emit error events
3. **State Consistency**: Use deltas for incremental updates, snapshots for resets
4. **Tool Safety**: Validate tool arguments and handle execution errors
5. **Performance**: Use async generators for memory-efficient streaming

### Client Development

1. **Event Processing**: Handle all event types gracefully
2. **State Synchronization**: Apply deltas and snapshots correctly
3. **Connection Management**: Implement reconnection logic
4. **User Experience**: Provide visual feedback for different event types
5. **Error Recovery**: Handle malformed events and network issues

### Protocol Compliance

1. **Standard Events**: Use only defined AG-UI event types
2. **JSON Format**: Ensure all data is JSON serializable
3. **SSE Format**: Follow Server-Sent Events specification
4. **Thread Safety**: Maintain proper thread and run IDs
5. **Backwards Compatibility**: Support older protocol versions

---

## Troubleshooting

### Common Server Issues

**Missing Event Imports**
```python
# Fix: Import all required event types
from ag_ui.core import (
    RunStartedEvent, RunFinishedEvent,
    TextMessageStartEvent, TextMessageContentEvent, TextMessageEndEvent,
    ToolCallStartEvent, ToolCallArgsEvent, ToolCallEndEvent,
    StateDeltaEvent, StateSnapshotEvent
)
```

**Async Generator Issues**
```python
# Wrong: Regular function
def run(self, input):
    return self.encoder.encode(event)

# Correct: Async generator
async def run(self, input) -> AsyncGenerator[str, None]:
    yield self.encoder.encode(event)
```

**State Management Errors**
```python
# Wrong: Modifying input state directly
input.state["key"] = "value"

# Correct: Creating new state and emitting events
new_state = input.state.copy()
new_state["key"] = "value"
yield self.encoder.encode(StateDeltaEvent(
    type=EventType.STATE_DELTA,
    delta={"key": "value"}
))
```

### Common Client Issues

**Event Processing Errors**
```python
# Add robust error handling
try:
    event_data = json.loads(json_part)
    event_type = event_data.get('type')
    # Process event...
except json.JSONDecodeError:
    print(f"⚠️ Failed to parse: {line_str}")
    continue
except Exception as e:
    print(f"⚠️ Error processing event: {e}")
    continue
```

**State Synchronization Issues**
```python
# Handle both delta and snapshot events
if event_type == 'STATE_DELTA':
    delta = event_data.get('delta', {})
    self.state.update(delta)  # Merge changes
elif event_type == 'STATE_SNAPSHOT':
    new_state = event_data.get('snapshot', {})
    self.state = new_state  # Replace entirely
```

**Connection Timeout Handling**
```python
# Add timeout and retry logic
timeout = aiohttp.ClientTimeout(total=30)
async with aiohttp.ClientSession(timeout=timeout) as session:
    try:
        async with session.post(...) as response:
            # Process events...
    except asyncio.TimeoutError:
        print("⚠️ Connection timed out, retrying...")
        # Implement retry logic
```

---

## Conclusion

This tutorial provided a complete guide to the AG-UI protocol using real, working examples. The AG-UI protocol enables sophisticated AI applications with:

1. **Universal Compatibility**: Your clients work with ANY compliant AG-UI server
2. **Rich Feature Set**: Text streaming, tool calling, state management, and custom events  
3. **Real-time Streaming**: Character-by-character response delivery with full event support
4. **Multi-Agent Architecture**: Specialized agents for different capabilities
5. **Production Ready**: Robust error handling, safe tool execution, and scalable patterns

**What You've Learned:**
- Complete AG-UI server implementation with multiple agent types
- Full-featured client with interactive commands and real-time streaming
- Tool calling with calculator, weather, and time tools
- State management with persistent user data and preferences
- Protocol-compliant event handling for all AG-UI event types

### Key Takeaways

- **Standardized Events**: Consistent communication across all implementations
- **Advanced Tool Integration**: Powerful human-in-the-loop capabilities with structured arguments
- **Sophisticated State Management**: Persistent context with delta updates and snapshots
- **Multi-Agent Workflows**: Specialized agents for different tasks and use cases
- **Hybrid Capabilities**: Seamless integration of tools and state for complex workflows
- **Extensible Design**: Custom events and patterns for specific requirements

### Tool Calling Mastery

You now understand how to:
- Implement structured tool calls with proper event sequences
- Handle tool arguments with streaming support
- Integrate tool results with conversational responses
- Build reusable tool patterns for common operations
- Handle tool errors gracefully with user feedback

### State Management Expertise

You've learned to:
- Maintain persistent state across conversations
- Use delta updates for efficient state synchronization
- Implement state snapshots for complete refreshes
- Handle complex nested state structures
- Combine state with tool usage for context-aware agents

### Advanced Integration Patterns

The tutorial covered:
- Hybrid agents that combine tools and state seamlessly
- Context-aware tool selection based on user preferences
- Tool usage analytics with state correlation
- Cross-session learning from user interactions
- Sophisticated client-side event processing

### Production Considerations

For production deployments:
1. **Security**: Validate all tool inputs and sanitize state data
2. **Persistence**: Use proper databases instead of in-memory storage
3. **Monitoring**: Track tool usage, state changes, and performance metrics
4. **Scaling**: Implement proper load balancing and state distribution
5. **Testing**: Create comprehensive test suites for all event types

### Next Steps

1. **Try the Working Examples**: Run `python server.py` and `python client.py` to experience the full system
2. **Run the Demo**: Execute `python demo.py` to see all features in action
3. **Build Your Own Agents**: Create specialized agents for your specific use cases
4. **Extend the Tool Set**: Add new tools to the ToolAgent for your domain
5. **Advanced State Management**: Enhance the StateAgent with persistent storage
6. **Multi-Agent Workflows**: Implement agent coordination and handoffs
7. **Performance Optimization**: Profile and optimize for high-throughput scenarios

**Ready-to-Use Files:**
- `server.py` - Complete multi-agent server implementation
- `client.py` - Full-featured interactive client
- `demo.py` - Comprehensive feature demonstration
- `requirements.txt` - All necessary dependencies

For more information and examples, visit the [AG-UI Dojo](https://github.com/ag-ui-protocol/dojo) and consult the official documentation at [docs.ag-ui.com](https://docs.ag-ui.com/llms-full.txt).

---

*This tutorial demonstrates the power and flexibility of the AG-UI protocol for building next-generation AI applications.* 