# Building AG-UI Servers and Clients: A Complete Guide

## Table of Contents
1. [Introduction to AG-UI Protocol](#introduction-to-ag-ui-protocol)
2. [Understanding the Architecture](#understanding-the-architecture)
3. [Building an AG-UI Server](#building-an-ag-ui-server)
4. [Building an AG-UI Client](#building-an-ag-ui-client)
5. [Protocol Compatibility](#protocol-compatibility)
6. [Advanced Features](#advanced-features)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

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
  |    TEXT_MESSAGE_CONTENT |
  |    ...                  |
  |    TEXT_MESSAGE_END     |
  |    RUN_FINISHED         |
```

### Event Types
According to the AG-UI protocol, the following events are used for communication:

- **`RUN_STARTED`**: Indicates agent has started processing
- **`TEXT_MESSAGE_START`**: Begins a new assistant message
- **`TEXT_MESSAGE_CONTENT`**: Streams message content (delta)
- **`TEXT_MESSAGE_END`**: Completes the assistant message
- **`RUN_FINISHED`**: Indicates agent has finished processing
- **`TOOL_CALL_START`**: Beginning of a tool call
- **`TOOL_CALL_ARGS`**: Tool call arguments
- **`TOOL_CALL_END`**: Tool call completion
- **`STATE_DELTA`**: Incremental state updates
- **`STATE_SNAPSHOT`**: Complete state refresh

---

## Building an AG-UI Server

### 1. Core Dependencies

```python
# requirements.txt
ag-ui-protocol
fastapi
uvicorn
sse-starlette
python-multipart
```

### 2. Server Implementation Structure

```python
import asyncio
from typing import AsyncGenerator, Dict, Any
from uuid import uuid4
from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse

# AG-UI imports
from ag_ui.core import (
    RunAgentInput, EventType,
    TextMessageStartEvent, TextMessageContentEvent, TextMessageEndEvent,
    RunStartedEvent, RunFinishedEvent
)
from ag_ui.encoder import EventEncoder
```

### 3. Agent Implementation

The core of your AG-UI server is the agent class:

```python
class EchoAgent:
    def __init__(self):
        self.encoder = EventEncoder()
    
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Main agent logic - yields encoded AG-UI events"""
        
        # 1. Start the run
        yield self.encoder.encode(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=input.thread_id,
            run_id=input.run_id
        ))
        
        # 2. Process messages and generate response
        user_messages = [msg for msg in input.messages if getattr(msg, 'role', None) == 'user']
        if user_messages:
            latest_message = user_messages[-1]
            content = getattr(latest_message, 'content', '')
            
            # 3. Stream the response
            message_id = str(uuid4())
            
            # Start message
            yield self.encoder.encode(TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=message_id,
                role="assistant"
            ))
            
            # Stream content character by character
            response = f"Echo: {content}"
            for char in response:
                yield self.encoder.encode(TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=message_id,
                    delta=char
                ))
                await asyncio.sleep(0.05)  # Streaming delay
            
            # End message
            yield self.encoder.encode(TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=message_id
            ))
        
        # 4. Finish the run
        yield self.encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=input.thread_id,
            run_id=input.run_id
        ))
```

### 4. FastAPI Endpoint

```python
app = FastAPI(title="AG-UI Server")
agent = EchoAgent()

class RunAgentRequest(BaseModel):
    thread_id: str
    messages: list
    tools: list = []
    state: Dict[str, Any] = {}
    context: list = []
    forwardedProps: dict = {}

@app.post("/agent")
async def run_agent(request: RunAgentRequest):
    """AG-UI compliant agent endpoint"""
    
    run_input = RunAgentInput(
        thread_id=request.thread_id,
        run_id=str(uuid4()),
        messages=request.messages,
        tools=request.tools,
        state=request.state,
        context=request.context,
        forwardedProps=request.forwardedProps
    )
    
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
```

---

## Building an AG-UI Client

### 1. Client Dependencies

```python
# Only need aiohttp for the client
import aiohttp
import asyncio
import json
```

### 2. Client Implementation

```python
class AGUIClient:
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.thread_id = str(uuid4())
        self.messages = []
        self.state = {}
        
    async def send_message(self, content: str) -> None:
        """Send message and process streaming response"""
        
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
            "forwardedProps": {}
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.server_url}/agent",
                json=payload,
                headers={"Accept": "text/event-stream"}
            ) as response:
                
                await self._process_event_stream(response)
    
    async def _process_event_stream(self, response):
        """Process Server-Sent Events from AG-UI server"""
        current_message = ""
        message_id = None
        
        async for line in response.content:
            line_str = line.decode('utf-8').strip()
            
            if line_str.startswith('data: '):
                # Handle double "data: " prefix from EventEncoder
                json_part = line_str[6:]
                if json_part.startswith('data: '):
                    json_part = json_part[6:]
                
                try:
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
                        print()  # New line
                        # Add to message history
                        self.messages.append({
                            "id": message_id,
                            "role": "assistant",
                            "content": current_message
                        })
                        current_message = ""
                        
                    elif event_type == 'RUN_FINISHED':
                        print("✅ Agent finished processing\n")
                        break
                        
                except json.JSONDecodeError:
                    continue
```

---

## Protocol Compatibility

### Universal Client Compatibility

**Yes, you are absolutely correct!** Your AG-UI client is designed to work with any AG-UI compliant server. Here's why:

#### 1. **Standardized Protocol**
The AG-UI protocol defines a standard set of events and message formats. As long as both client and server follow this protocol, they are interoperable.

#### 2. **Event-Driven Architecture**
All AG-UI servers emit the same core events:
- `RUN_STARTED` / `RUN_FINISHED` for run lifecycle
- `TEXT_MESSAGE_START` / `TEXT_MESSAGE_CONTENT` / `TEXT_MESSAGE_END` for messages
- `TOOL_CALL_*` events for tool interactions
- `STATE_*` events for state management

#### 3. **HTTP + SSE Transport**
The protocol uses standard HTTP POST requests with Server-Sent Events for streaming, making it universally compatible across different implementations.

#### 4. **Flexible Payload Structure**
The `RunAgentInput` structure is standardized:
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

### Testing Compatibility

You can test your client against different AG-UI servers:

```python
# Connect to different servers
client1 = AGUIClient("http://localhost:8000")      # Your echo server
client2 = AGUIClient("http://another-server:8001")  # Different AG-UI server
client3 = AGUIClient("https://production-ai.com")   # Production server

# Same client code works with all!
await client1.send_message("Hello")
await client2.send_message("Hello")
await client3.send_message("Hello")
```

---

## Advanced Features

### 1. Tool Integration

AG-UI supports sophisticated tool calling:

```python
# Server-side tool handling
elif event_type == 'TOOL_CALL_START':
    tool_id = event_data.get('toolCallId')
    yield self.encoder.encode(ToolCallStartEvent(
        type=EventType.TOOL_CALL_START,
        tool_call_id=tool_id
    ))

# Client-side tool execution
elif event_type == 'TOOL_CALL_START':
    # Execute the requested tool
    result = await self.execute_tool(event_data)
    # Send result back to server
```

### 2. State Management

```python
# Incremental state updates
yield self.encoder.encode(StateDeltaEvent(
    type=EventType.STATE_DELTA,
    delta={"user_preference": "dark_mode"}
))

# Complete state snapshots
yield self.encoder.encode(StateSnapshotEvent(
    type=EventType.STATE_SNAPSHOT,
    state=complete_state_object
))
```

### 3. Multi-Agent Workflows

```python
# Agent handoff
if specialized_task_detected:
    # Hand off to specialized agent
    specialist_response = await self.delegate_to_specialist(input)
    yield from specialist_response
```

---

## Best Practices

### Server Development

1. **Always follow event sequence**: `RUN_STARTED` → Message events → `RUN_FINISHED`
2. **Handle errors gracefully**: Send appropriate error events
3. **Implement proper streaming**: Use async generators for real-time responses
4. **Validate input**: Check `RunAgentInput` structure
5. **Add health checks**: Implement `/health` endpoint

### Client Development

1. **Parse events robustly**: Handle malformed or unexpected events
2. **Maintain message history**: Keep conversation context
3. **Implement reconnection**: Handle network failures
4. **Process tools properly**: Execute requested tools and return results
5. **Handle state updates**: Apply state changes from server

### Protocol Compliance

1. **Use standard event types**: Stick to defined AG-UI events
2. **Proper JSON encoding**: Ensure all data is JSON serializable
3. **Correct SSE format**: Follow Server-Sent Events specification
4. **Thread management**: Maintain proper thread and run IDs

---

## Troubleshooting

### Common Server Issues

**Event Parsing Errors**
```
Solution: Check EventEncoder usage and event structure
```

**Missing Required Fields**
```
Solution: Ensure RunAgentInput includes all required fields:
- thread_id, run_id, messages, tools, state, context, forwardedProps
```

**SSE Format Issues**
```
Solution: Use AG-UI EventEncoder for proper formatting
```

### Common Client Issues

**Double "data:" Prefix**
```python
# Handle both formats
json_part = line_str[6:]  # Remove first "data: "
if json_part.startswith('data: '):
    json_part = json_part[6:]  # Remove second "data: "
```

**Connection Timeouts**
```python
# Add timeout handling
timeout = aiohttp.ClientTimeout(total=30)
async with aiohttp.ClientSession(timeout=timeout) as session:
    # ... rest of code
```

**Method Not Allowed (405)**
```
Solution: Ensure client sends POST requests to /agent endpoint
```

---

## Conclusion

The AG-UI protocol provides a powerful foundation for building AI-powered applications with real-time streaming capabilities. Key takeaways:

1. **Universal Compatibility**: AG-UI clients work with any compliant server
2. **Standardized Events**: Consistent event types across implementations
3. **Real-time Streaming**: Character-by-character response streaming
4. **Tool Integration**: Support for human-in-the-loop workflows
5. **State Management**: Persistent conversation context

By following the AG-UI protocol specifications and implementing proper event handling, you can build sophisticated AI applications that are interoperable across different platforms and services.

### Next Steps

1. **Explore the AG-UI Dojo**: Test your implementation against reference examples
2. **Add Tool Support**: Implement tool calling and execution
3. **State Management**: Add persistent state handling
4. **Production Deployment**: Scale your server with proper infrastructure
5. **Multi-Agent Workflows**: Implement agent-to-agent collaboration

For more information, consult the official AG-UI documentation at [docs.ag-ui.com](https://docs.ag-ui.com/llms-full.txt).

---

*This tutorial demonstrates the power and flexibility of the AG-UI protocol for building next-generation AI applications.* 