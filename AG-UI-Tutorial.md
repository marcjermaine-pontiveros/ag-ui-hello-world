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

#### State Event Sequence

```
1. STATE_SNAPSHOT → Complete state refresh (initial or reset)
2. STATE_DELTA    → Incremental state updates
```

#### Complete State Agent Implementation

```python
class StateAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        # Simple in-memory state storage (use proper storage in production)
        self.memory = {}
    
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Agent that demonstrates state management capabilities"""
        
        thread_id = input.thread_id
        run_id = input.run_id
        
        # Emit RUN_STARTED event
        yield self.encoder.encode(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=thread_id,
            run_id=run_id
        ))
        
        # Initialize thread-specific memory
        if thread_id not in self.memory:
            self.memory[thread_id] = {
                "user_name": None,
                "preferences": {},
                "conversation_count": 0,
                "topics": []
            }
            
            # Send initial state snapshot
            yield self.encoder.encode(StateSnapshotEvent(
                type=EventType.STATE_SNAPSHOT,
                snapshot=self.memory[thread_id]
            ))
        
        # Process user message
        user_messages = [msg for msg in input.messages if getattr(msg, 'role', None) == 'user']
        if user_messages:
            latest_message = user_messages[-1]
            content = getattr(latest_message, 'content', '').lower()
            
            # Update conversation count
            self.memory[thread_id]["conversation_count"] += 1
            yield self.encoder.encode(StateDeltaEvent(
                type=EventType.STATE_DELTA,
                delta=[{"path": ["conversation_count"], "value": self.memory[thread_id]["conversation_count"]}]
            ))
            
            # Handle different state operations
            if content.startswith('my name is'):
                await self._handle_name_setting(thread_id, content)
                
            elif 'prefer' in content:
                await self._handle_preference_setting(thread_id, content)
                
            elif 'remember' in content and 'name' in content:
                await self._handle_name_query(thread_id)
                
            elif 'what do you know about me' in content or 'my info' in content:
                await self._handle_info_query(thread_id)
                
            elif 'reset' in content and ('state' in content or 'memory' in content):
                await self._handle_state_reset(thread_id)
                
            else:
                await self._handle_general_conversation(thread_id, content)
        
        # Emit RUN_FINISHED event
        yield self.encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=thread_id,
            run_id=run_id
        ))
    
    async def _handle_name_setting(self, thread_id: str, content: str):
        """Handle name setting with state updates"""
        name = content.replace('my name is', '').strip().title()
        old_name = self.memory[thread_id]["user_name"]
        self.memory[thread_id]["user_name"] = name
        
        # Emit state delta
        yield self.encoder.encode(StateDeltaEvent(
            type=EventType.STATE_DELTA,
            delta=[{"path": ["user_name"], "value": name}]
        ))
        
        # Send response
        if old_name:
            response = f"I've updated your name from {old_name} to {name}!"
        else:
            response = f"Nice to meet you, {name}! I'll remember your name for our future conversations."
        
        async for event in self._send_text_message(response):
            yield event
    
    async def _handle_preference_setting(self, thread_id: str, content: str):
        """Handle preference setting with state updates"""
        if 'dark mode' in content:
            self.memory[thread_id]["preferences"]["theme"] = "dark"
            pref_key, pref_value = "theme", "dark"
            response = "I've noted that you prefer dark mode!"
        elif 'light mode' in content:
            self.memory[thread_id]["preferences"]["theme"] = "light"
            pref_key, pref_value = "theme", "light"
            response = "I've noted that you prefer light mode!"
        else:
            response = "I've updated your preferences!"
            pref_key, pref_value = "general", content
            self.memory[thread_id]["preferences"]["general"] = content
        
        # Emit state delta for preference change
        yield self.encoder.encode(StateDeltaEvent(
            type=EventType.STATE_DELTA,
            delta=[{"path": ["preferences", pref_key], "value": pref_value}]
        ))
        
        async for event in self._send_text_message(response):
            yield event
    
    async def _handle_name_query(self, thread_id: str):
        """Handle queries about remembered name"""
        user_name = self.memory[thread_id].get("user_name")
        if user_name:
            response = f"Yes, I remember! Your name is {user_name}. 😊"
        else:
            response = "I don't know your name yet. You can tell me by saying 'my name is [your name]'."
        
        async for event in self._send_text_message(response):
            yield event
    
    async def _handle_info_query(self, thread_id: str):
        """Handle requests for stored information"""
        memory = self.memory[thread_id]
        user_name = memory.get("user_name", "Unknown")
        conv_count = memory.get("conversation_count", 0)
        preferences = memory.get("preferences", {})
        topics = memory.get("topics", [])
        
        info = f"📊 Here's what I know about you:\n"
        info += f"• Name: {user_name}\n"
        info += f"• Conversations: {conv_count}\n"
        info += f"• Preferences: {preferences if preferences else 'None set'}\n"
        info += f"• Topics discussed: {len(topics)}"
        
        async for event in self._send_text_message(info):
            yield event
    
    async def _handle_state_reset(self, thread_id: str):
        """Handle state reset requests"""
        # Reset memory
        self.memory[thread_id] = {
            "user_name": None,
            "preferences": {},
            "conversation_count": 0,
            "topics": []
        }
        
        # Send complete state snapshot after reset
        yield self.encoder.encode(StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT,
            snapshot=self.memory[thread_id]
        ))
        
        response = "🔄 Memory has been reset! I've forgotten everything about our previous conversations."
        async for event in self._send_text_message(response):
            yield event
    
    async def _handle_general_conversation(self, thread_id: str, content: str):
        """Handle general conversation with topic tracking"""
        # Add topic to discussed topics
        topic = content[:30] + "..." if len(content) > 30 else content
        if topic not in self.memory[thread_id]["topics"]:
            self.memory[thread_id]["topics"].append(topic)
            
            # Emit state delta for new topic
            yield self.encoder.encode(StateDeltaEvent(
                type=EventType.STATE_DELTA,
                delta=[{"path": ["topics"], "value": self.memory[thread_id]["topics"]}]
            ))
        
        user_name = self.memory[thread_id].get("user_name")
        greeting = f"Hello {user_name}! " if user_name else "Hello! "
        
        response = greeting + f"I can remember information about you across our conversation. "
        response += f"Try saying 'my name is [name]', 'I prefer dark mode', or 'what do you know about me?'"
        
        async for event in self._send_text_message(response):
            yield event
```

#### State Management Best Practices

1. **Thread Isolation**: Keep state separate per thread_id
2. **Delta vs Snapshot**: Use deltas for small changes, snapshots for resets
3. **Structured Paths**: Use clear, hierarchical state structures
4. **Validation**: Validate state changes before applying
5. **Persistence**: In production, use proper databases for state storage

#### State Event Patterns

```python
# Pattern 1: Simple state delta (single field update)
yield self.encoder.encode(StateDeltaEvent(
    type=EventType.STATE_DELTA,
    delta=[{"path": ["user_name"], "value": "Alice"}]
))

# Pattern 2: Multiple field updates
yield self.encoder.encode(StateDeltaEvent(
    type=EventType.STATE_DELTA,
    delta=[
        {"path": ["user_name"], "value": "Alice"},
        {"path": ["last_seen"], "value": "2024-01-15"},
        {"path": ["preferences", "theme"], "value": "dark"}
    ]
))

# Pattern 3: Complete state replacement
yield self.encoder.encode(StateSnapshotEvent(
    type=EventType.STATE_SNAPSHOT,
    snapshot={
        "user_name": "Alice",
        "preferences": {"theme": "dark"},
        "conversation_count": 5,
        "topics": ["weather", "movies", "travel"]
    }
))

# Pattern 4: Array operations
# Add item to array
current_topics = state.get("topics", [])
current_topics.append("new_topic")
yield self.encoder.encode(StateDeltaEvent(
    type=EventType.STATE_DELTA,
    delta=[{"path": ["topics"], "value": current_topics}]
))

# Pattern 5: Nested object updates
yield self.encoder.encode(StateDeltaEvent(
    type=EventType.STATE_DELTA,
    delta=[{"path": ["user_profile", "settings", "notifications"], "value": True}]
))
```

#### Client-Side State Handling

```python
class AGUIClient:
    def __init__(self):
        self.state = {}
    
    async def _process_state_events(self, event_data):
        """Handle state events from server"""
        event_type = event_data.get('type')
        
        if event_type == 'STATE_DELTA':
            # Apply incremental changes
            delta = event_data.get('delta', [])
            for change in delta:
                path = change.get('path', [])
                value = change.get('value')
                self._apply_state_change(path, value)
            print(f"📊 State updated: {delta}")
            
        elif event_type == 'STATE_SNAPSHOT':
            # Replace entire state
            new_state = event_data.get('snapshot', {})
            self.state = new_state
            print(f"📸 State snapshot: {new_state}")
    
    def _apply_state_change(self, path: list, value):
        """Apply a state change at the specified path"""
        current = self.state
        
        # Navigate to the parent object
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Set the final value
        if path:
            current[path[-1]] = value
```

### 2. Base Agent Architecture

Here's the actual base agent implementation from our working system:

```python
import asyncio
import json
from typing import AsyncGenerator, Dict, Any
from uuid import uuid4
from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse

# AG-UI imports (from working implementation)
from ag_ui.core import (
    RunAgentInput, EventType,
    TextMessageStartEvent, TextMessageContentEvent, TextMessageEndEvent,
    RunStartedEvent, RunFinishedEvent, StateDeltaEvent, StateSnapshotEvent,
    ToolCallStartEvent, ToolCallArgsEvent, ToolCallEndEvent,
    Message, UserMessage, AssistantMessage
)
from ag_ui.encoder import EventEncoder

class BaseAgent:
    """Base class for all AG-UI agents - from working implementation"""
    def __init__(self):
        self.encoder = EventEncoder()
    
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Override this method in concrete agent implementations"""
        raise NotImplementedError
    
    async def _send_text_message(self, content: str):
        """Helper method to send a streaming text message with realistic delays"""
        message_id = str(uuid4())
        
        # Start message
        yield self.encoder.encode(TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START,
            message_id=message_id,
            role="assistant"
        ))
        
        # Stream content character by character with slight delays
        for char in content:
            yield self.encoder.encode(TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id=message_id,
                delta=char
            ))
            await asyncio.sleep(0.05)  # Realistic streaming delay
        
        # End message
        yield self.encoder.encode(TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END,
            message_id=message_id
        ))
```

### 3. Echo Agent (Basic Text Messages)

This is the actual working echo agent implementation:

```python
class EchoAgent(BaseAgent):
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Echo agent that repeats user messages - production implementation"""
        
        thread_id = input.thread_id
        run_id = input.run_id
        
        # Emit RUN_STARTED event
        yield self.encoder.encode(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=thread_id,
            run_id=run_id
        ))
        
        # Find the latest user message using walrus operator for cleaner code
        if user_messages := [msg for msg in input.messages if getattr(msg, 'role', None) == 'user']:
            latest_message = user_messages[-1]
            content = getattr(latest_message, 'content', '')
            
            # Generate echo response
            echo_response = f"Echo: {content}"
            
            # Create message ID
            message_id = str(uuid4())
            
            # Emit TEXT_MESSAGE_START
            yield self.encoder.encode(TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=message_id,
                role="assistant"
            ))
            
            # Emit TEXT_MESSAGE_CONTENT (character by character for streaming effect)
            for char in echo_response:
                yield self.encoder.encode(TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=message_id,
                    delta=char
                ))
                await asyncio.sleep(0.05)  # Small delay for realistic streaming
            
            # Emit TEXT_MESSAGE_END
            yield self.encoder.encode(TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=message_id
            ))
        
        # Emit RUN_FINISHED event
        yield self.encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=thread_id,
            run_id=run_id
        ))
```

**Key Implementation Details:**
- Uses walrus operator (`:=`) for cleaner message filtering
- Explicit message ID generation for proper event correlation
- Realistic streaming delays (0.05s per character)
- Proper thread_id and run_id handling
- Defensive programming with `getattr()` for safe attribute access

### 4. Tool Agent (Demonstrates Tool Calling)

Tool calling is one of the most powerful features of AG-UI, allowing agents to request the client to execute functions on their behalf. This enables human-in-the-loop workflows and external integrations.

#### Tool Call Event Sequence

```
1. TOOL_CALL_START  → Announces tool call with name and ID
2. TOOL_CALL_ARGS   → Streams tool arguments (JSON)
3. TOOL_CALL_END    → Indicates tool call completion
```

#### Complete Tool Agent Implementation

```python
class ToolAgent(BaseAgent):
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Agent that demonstrates tool calling capabilities"""
        
        thread_id = input.thread_id
        run_id = input.run_id
        
        # Start the run
        yield self.encoder.encode(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=thread_id,
            run_id=run_id
        ))
        
        # Process user message
        user_messages = [msg for msg in input.messages if getattr(msg, 'role', None) == 'user']
        if user_messages:
            latest_message = user_messages[-1]
            content = getattr(latest_message, 'content', '').lower()
            
            # Determine which tool to use based on content
            if any(word in content for word in ['calculate', 'math', '+', '-', '*', '/', '=']):
                async for event in self._handle_calculator_tool(content):
                    yield event
            elif any(word in content for word in ['weather', 'temperature', 'forecast']):
                async for event in self._handle_weather_tool(content):
                    yield event
            elif any(word in content for word in ['time', 'clock', 'date']):
                async for event in self._handle_time_tool():
                    yield event
            else:
                # Default response with available tools
                response = "I can help with calculations, weather, or time. Try asking me to 'calculate 5+3' or 'what time is it?'"
                async for event in self._send_text_message(response):
                    yield event
        
        # Finish the run
        yield self.encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=thread_id,
            run_id=run_id
        ))
    
    async def _handle_calculator_tool(self, content: str):
        """Handle calculator tool calls"""
        tool_call_id = str(uuid4())
        
        # Extract mathematical expression
        expression = content
        for word in ['calculate', 'compute', 'what is', 'what\'s']:
            expression = expression.replace(word, '').strip()
        
        # Start tool call
        yield self.encoder.encode(ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            tool_call_name="calculator",
            tool_call_id=tool_call_id
        ))
        
        # Send tool arguments
        args = {"expression": expression}
        yield self.encoder.encode(ToolCallArgsEvent(
            type=EventType.TOOL_CALL_ARGS,
            tool_call_id=tool_call_id,
            delta=json.dumps(args)
        ))
        
        # End tool call
        yield self.encoder.encode(ToolCallEndEvent(
            type=EventType.TOOL_CALL_END,
            tool_call_id=tool_call_id
        ))
        
        # Simulate calculation result
        try:
            # WARNING: In production, use a safe math evaluator
            result = eval(expression.replace('x', '*'))
            response = f"Calculation result: {expression} = {result}"
        except:
            response = f"Sorry, I couldn't calculate '{expression}'. Please check the expression."
        
        # Send response
        async for event in self._send_text_message(response):
            yield event
    
    async def _handle_weather_tool(self, content: str):
        """Handle weather tool calls"""
        tool_call_id = str(uuid4())
        
        # Start tool call
        yield self.encoder.encode(ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            tool_call_name="weather",
            tool_call_id=tool_call_id
        ))
        
        # Send tool arguments
        args = {"location": "current_location", "units": "metric"}
        yield self.encoder.encode(ToolCallArgsEvent(
            type=EventType.TOOL_CALL_ARGS,
            tool_call_id=tool_call_id,
            delta=json.dumps(args)
        ))
        
        # End tool call
        yield self.encoder.encode(ToolCallEndEvent(
            type=EventType.TOOL_CALL_END,
            tool_call_id=tool_call_id
        ))
        
        # Simulate weather response
        response = "🌤️ Current weather: 22°C, partly cloudy with light winds"
        async for event in self._send_text_message(response):
            yield event
    
    async def _handle_time_tool(self):
        """Handle time tool calls"""
        tool_call_id = str(uuid4())
        
        # Start tool call
        yield self.encoder.encode(ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            tool_call_name="get_time",
            tool_call_id=tool_call_id
        ))
        
        # Send tool arguments
        args = {"timezone": "local"}
        yield self.encoder.encode(ToolCallArgsEvent(
            type=EventType.TOOL_CALL_ARGS,
            tool_call_id=tool_call_id,
            delta=json.dumps(args)
        ))
        
        # End tool call
        yield self.encoder.encode(ToolCallEndEvent(
            type=EventType.TOOL_CALL_END,
            tool_call_id=tool_call_id
        ))
        
        # Get current time
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        response = f"🕐 Current time: {current_time}"
        
        async for event in self._send_text_message(response):
            yield event
```

#### Tool Call Best Practices

1. **Unique Tool Call IDs**: Always generate unique UUIDs for each tool call
2. **Descriptive Tool Names**: Use clear, consistent naming conventions
3. **Structured Arguments**: Pass well-formed JSON objects
4. **Error Handling**: Gracefully handle tool execution failures
5. **Security**: Validate and sanitize all tool inputs

#### Common Tool Patterns

```python
# Pattern 1: Simple tool with static arguments
async def _call_simple_tool(self, tool_name: str, args: dict):
    tool_call_id = str(uuid4())
    
    yield self.encoder.encode(ToolCallStartEvent(
        type=EventType.TOOL_CALL_START,
        tool_call_name=tool_name,
        tool_call_id=tool_call_id
    ))
    
    yield self.encoder.encode(ToolCallArgsEvent(
        type=EventType.TOOL_CALL_ARGS,
        tool_call_id=tool_call_id,
        delta=json.dumps(args)
    ))
    
    yield self.encoder.encode(ToolCallEndEvent(
        type=EventType.TOOL_CALL_END,
        tool_call_id=tool_call_id
    ))

# Pattern 2: Tool with streaming arguments
async def _call_streaming_tool(self, tool_name: str, large_args: dict):
    tool_call_id = str(uuid4())
    
    yield self.encoder.encode(ToolCallStartEvent(
        type=EventType.TOOL_CALL_START,
        tool_call_name=tool_name,
        tool_call_id=tool_call_id
    ))
    
    # Stream arguments in chunks
    args_json = json.dumps(large_args)
    chunk_size = 100
    for i in range(0, len(args_json), chunk_size):
        chunk = args_json[i:i+chunk_size]
        yield self.encoder.encode(ToolCallArgsEvent(
            type=EventType.TOOL_CALL_ARGS,
            tool_call_id=tool_call_id,
            delta=chunk
        ))
        await asyncio.sleep(0.01)
    
    yield self.encoder.encode(ToolCallEndEvent(
        type=EventType.TOOL_CALL_END,
        tool_call_id=tool_call_id
    ))
```
            content = getattr(latest_message, 'content', '').lower()
            
            # Route to appropriate tool
            if 'calculate' in content or 'math' in content:
                async for event in self._handle_calculator_tool(content):
                    yield event
            elif 'weather' in content:
                async for event in self._handle_weather_tool(content):
                    yield event
            elif 'time' in content:
                async for event in self._handle_time_tool():
                    yield event
            else:
                async for event in self._send_text_message(
                    "I can help with calculations, weather, or time. Try 'calculate 5 + 3'!"
                ):
                    yield event
        
        # Finish the run
        yield self.encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=input.thread_id,
            run_id=input.run_id
        ))
    
    async def _handle_calculator_tool(self, content: str):
        """Demonstrate calculator tool call"""
        tool_call_id = str(uuid4())
        
        # Start tool call
        yield self.encoder.encode(ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            tool_call_id=tool_call_id,
            tool_name="calculator"
        ))
        
        # Stream tool arguments
        expression = content.replace('calculate', '').strip()
        args = {"expression": expression}
        yield self.encoder.encode(ToolCallArgsEvent(
            type=EventType.TOOL_CALL_ARGS,
            tool_call_id=tool_call_id,
            args=json.dumps(args)
        ))
        
        # End tool call
        yield self.encoder.encode(ToolCallEndEvent(
            type=EventType.TOOL_CALL_END,
            tool_call_id=tool_call_id
        ))
        
        # Execute tool and send result
        try:
            # Simple math evaluation (use safe evaluation in production!)
            result = eval(expression.replace('x', '*').replace('÷', '/'))
            async for event in self._send_text_message(f"Result: {expression} = {result}"):
                yield event
        except:
            async for event in self._send_text_message("Sorry, couldn't calculate that."):
                yield event
```

### 5. State Agent (Demonstrates State Management)

```python
class StateAgent(BaseAgent):
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Agent that demonstrates state management"""
        
        # Start the run
        yield self.encoder.encode(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=input.thread_id,
            run_id=input.run_id
        ))
        
        # Initialize or get current state
        current_state = input.state or {}
        if not current_state:
            current_state = {
                "user_preferences": {},
                "conversation_count": 0,
                "topics_discussed": [],
                "user_name": None
            }
            
            # Send initial state snapshot
            yield self.encoder.encode(StateSnapshotEvent(
                type=EventType.STATE_SNAPSHOT,
                state=current_state
            ))
        
        # Process user message
        user_messages = [msg for msg in input.messages if getattr(msg, 'role', None) == 'user']
        if user_messages:
            latest_message = user_messages[-1]
            content = getattr(latest_message, 'content', '').lower()
            
            # Update conversation count
            current_state["conversation_count"] += 1
            
            # Handle state operations
            if content.startswith('my name is'):
                name = content.replace('my name is', '').strip()
                current_state["user_name"] = name
                
                # Send state delta
                yield self.encoder.encode(StateDeltaEvent(
                    type=EventType.STATE_DELTA,
                    delta={"user_name": name}
                ))
                
                async for event in self._send_text_message(f"Nice to meet you, {name}!"):
                    yield event
                    
            elif 'prefer' in content:
                # Handle preferences
                if 'dark mode' in content:
                    current_state["user_preferences"]["theme"] = "dark"
                elif 'light mode' in content:
                    current_state["user_preferences"]["theme"] = "light"
                
                # Send state delta
                yield self.encoder.encode(StateDeltaEvent(
                    type=EventType.STATE_DELTA,
                    delta={"user_preferences": current_state["user_preferences"]}
                ))
                
                async for event in self._send_text_message("Preferences updated!"):
                    yield event
                    
            elif 'what do you know about me' in content:
                # Show current state
                user_name = current_state.get("user_name", "Unknown")
                conv_count = current_state.get("conversation_count", 0)
                preferences = current_state.get("user_preferences", {})
                
                info = f"Name: {user_name}, Conversations: {conv_count}, Preferences: {preferences}"
                async for event in self._send_text_message(info):
                    yield event
                    
            else:
                # Regular conversation
                user_name = current_state.get("user_name")
                greeting = f"Hello {user_name}! " if user_name else "Hello! "
                response = greeting + "I can remember your name and preferences."
                
                async for event in self._send_text_message(response):
                    yield event
            
            # Always update conversation count
            yield self.encoder.encode(StateDeltaEvent(
                type=EventType.STATE_DELTA,
                delta={"conversation_count": current_state["conversation_count"]}
            ))
        
        # Finish the run
        yield self.encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=input.thread_id,
            run_id=input.run_id
        ))
```

### 6. FastAPI Server Setup

```python
app = FastAPI(title="AG-UI Multi-Agent Server")

# Agent instances
agents = {
    "echo": EchoAgent(),
    "tool": ToolAgent(),
    "state": StateAgent()
}

class RunAgentRequest(BaseModel):
    thread_id: str
    messages: list
    tools: list = []
    state: Dict[str, Any] = {}
    context: list = []
    forwardedProps: dict = {}
    agent_type: str = "echo"  # Agent selection

@app.post("/agent")
async def run_agent(request: RunAgentRequest):
    """Run the specified agent"""
    
    # Select agent
    agent = agents.get(request.agent_type, agents["echo"])
    
    # Create run input
    run_input = RunAgentInput(
        thread_id=request.thread_id,
        run_id=str(uuid4()),
        messages=request.messages,
        tools=request.tools,
        state=request.state,
        context=request.context,
        forwardedProps=request.forwardedProps
    )
    
    # Return streaming response
    return EventSourceResponse(
        agent.run(run_input),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.get("/agents")
async def list_agents():
    """List available agents"""
    return {
        "echo": {
            "description": "Simple echo agent",
            "features": ["text_messages"]
        },
        "tool": {
            "description": "Tool-calling agent",
            "features": ["text_messages", "tool_calls"],
            "tools": ["calculator", "weather", "get_time"]
        },
        "state": {
            "description": "State management agent",
            "features": ["text_messages", "state_management"]
        }
    }
```

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

#### Integration Patterns

```python
# Pattern 1: Tool result affects state
async def _tool_with_state_update(self, thread_id: str, tool_name: str, result: Any):
    # Update state based on tool result
    self.memory[thread_id]["last_tool_result"] = result
    self.memory[thread_id]["tool_history"].append({
        "name": tool_name,
        "result": result,
        "timestamp": datetime.now().isoformat()
    })
    
    # Emit state update
    yield self.encoder.encode(StateDeltaEvent(
        type=EventType.STATE_DELTA,
        delta=[
            {"path": ["last_tool_result"], "value": result},
            {"path": ["tool_history"], "value": self.memory[thread_id]["tool_history"]}
        ]
    ))

# Pattern 2: State influences tool selection
async def _smart_tool_selection(self, thread_id: str, content: str):
    user_preferences = self.memory[thread_id].get("preferences", {})
    
    # Choose tool based on user preferences
    if "calculation" in content:
        if user_preferences.get("calculator_mode") == "advanced":
            await self._call_advanced_calculator(content)
        else:
            await self._call_basic_calculator(content)
    elif "weather" in content:
        preferred_units = user_preferences.get("weather_units", "metric")
        await self._call_weather_tool(content, units=preferred_units)

# Pattern 3: Cross-session state with tool context
async def _persistent_tool_learning(self, thread_id: str):
    # Learn from tool usage patterns
    tool_history = self.memory[thread_id].get("tool_history", [])
    
    # Analyze most used tools
    tool_usage = {}
    for entry in tool_history:
        tool_name = entry["name"]
        tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
    
    # Update user preferences based on usage
    if tool_usage:
        most_used = max(tool_usage, key=tool_usage.get)
        self.memory[thread_id]["preferences"]["favorite_tool"] = most_used
        
        yield self.encoder.encode(StateDeltaEvent(
            type=EventType.STATE_DELTA,
            delta=[{"path": ["preferences", "favorite_tool"], "value": most_used}]
        ))
```

#### Advanced Client Handling

```python
class AdvancedAGUIClient(AGUIClient):
    def __init__(self):
        super().__init__()
        self.tool_results = {}
        self.current_tool_call = None
    
    async def _process_events(self, line: str):
        """Enhanced event processing for tool + state integration"""
        # ... existing event processing ...
        
        elif event_type == 'TOOL_CALL_START':
            tool_name = event_data.get('tool_call_name')
            tool_call_id = event_data.get('tool_call_id')
            self.current_tool_call = {
                "id": tool_call_id,
                "name": tool_name,
                "args": "",
                "start_time": datetime.now()
            }
            print(f"🔧 Starting {tool_name} (ID: {tool_call_id})")
            
        elif event_type == 'TOOL_CALL_ARGS':
            if self.current_tool_call:
                args_delta = event_data.get('delta', '')
                self.current_tool_call["args"] += args_delta
                
        elif event_type == 'TOOL_CALL_END':
            if self.current_tool_call:
                tool_call_id = event_data.get('tool_call_id')
                
                # Store tool result with state context
                self.tool_results[tool_call_id] = {
                    "name": self.current_tool_call["name"],
                    "args": self.current_tool_call["args"],
                    "duration": (datetime.now() - self.current_tool_call["start_time"]).total_seconds(),
                    "state_at_time": self.state.copy()
                }
                
                print(f"✅ Tool {self.current_tool_call['name']} completed")
                self.current_tool_call = None
        
        elif event_type == 'STATE_DELTA':
            # Enhanced state processing with tool context
            delta = event_data.get('delta', [])
            
            # Check if state change is related to recent tool usage
            if self.current_tool_call:
                print(f"📊 State updated during {self.current_tool_call['name']}: {delta}")
            else:
                print(f"📊 State updated: {delta}")
            
            # Apply state changes
            for change in delta:
                path = change.get('path', [])
                value = change.get('value')
                self._apply_state_change(path, value)
    
    async def show_tool_analytics(self):
        """Display tool usage analytics with state correlation"""
        print("\n🔧 Tool Usage Analytics:")
        print("-" * 40)
        
        for tool_id, result in self.tool_results.items():
            print(f"Tool: {result['name']}")
            print(f"Duration: {result['duration']:.2f}s")
            print(f"State at time: {result['state_at_time']}")
            print("-" * 20)
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
    new_state = event_data.get('state', {})
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