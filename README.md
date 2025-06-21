# AG-UI Multi-Agent Server and Client

A comprehensive implementation of the Agent User Interaction Protocol (AG-UI) featuring multiple specialized agents, tool calling capabilities, state management, and a full-featured CLI client.

## Features

- **AG-UI Protocol Compliant**: Implements the complete AG-UI protocol specification
- **Multi-Agent Architecture**: Three specialized agent types (Echo, Tool, State)
- **Real-time Streaming**: Character-by-character text streaming with full event support
- **Tool Calling**: Integrated tool calling with calculator, weather, and time tools
- **State Management**: Persistent user data and preferences across conversations
- **Enhanced CLI Client**: Full-featured command-line interface with agent switching
- **Comprehensive Demo**: Interactive demonstration of all AG-UI features
- **Health Monitoring**: Built-in health checks and server status monitoring

## Architecture

### Server Components

#### 1. Echo Agent (`EchoAgent`)
- Simple message echoing functionality
- Demonstrates basic text streaming
- Character-by-character response delivery
- Perfect for testing basic protocol compliance

#### 2. Tool Agent (`ToolAgent`)
- Advanced tool calling capabilities
- **Calculator Tool**: Safe mathematical expression evaluation
- **Weather Tool**: Simulated weather information
- **Time Tool**: Current time and date functionality
- Proper tool call event sequences (START → ARGS → END)

#### 3. State Agent (`StateAgent`)
- Persistent state management
- User profile storage (name, preferences)
- Conversation tracking and analytics
- State delta and snapshot event handling
- Memory operations (set, get, reset)

### Client Features

- **Multi-Agent Support**: Switch between different agent types
- **Complete Event Handling**: All AG-UI event types supported
- **Interactive Commands**: Built-in command system
- **Real-time Streaming**: Live response display
- **State Visualization**: Current state inspection
- **Health Monitoring**: Server connectivity checks

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Starting the Server

1. Start the AG-UI multi-agent server:
```bash
python server.py
```

The server will start on `http://localhost:8000` with the following endpoints:
- `POST /agent` - Main agent endpoint (supports `agent_type` parameter)
- `GET /health` - Health check endpoint
- `GET /agents` - List available agents and their capabilities

### Using the Interactive Client

1. In a new terminal, start the enhanced CLI client:
```bash
python client.py
```

2. The client supports these commands:
   - `/agent <type>` - Switch agent (echo, tool, state)
   - `/agents` - List available agents
   - `/current` - Show current agent
   - `/state` - Display current state
   - `/health` - Check server health
   - `/help` - Show help
   - `/quit` - Exit client

3. Type regular messages to chat with the current agent
4. Watch real-time streaming responses with full event handling

### Running the Comprehensive Demo

Experience all features at once:
```bash
python demo.py
```

The demo showcases:
- All three agent types in action
- Tool calling with different tools
- State management and persistence
- Agent switching capabilities
- Complete AG-UI event handling

## Agent Examples

### Echo Agent Example
```
👤 You [echo]: Hello, world!
🔄 Agent started processing...
💬 Assistant: Echo: Hello, world!
✅ Agent finished processing
```

### Tool Agent Example
```
👤 You [tool]: calculate 15 * 7 + 3
🔄 Agent started processing...
🔧 Starting tool call: calculator (ID: abc123)
📋 Tool arguments: {"expression": "15 * 7 + 3"}
✅ Tool call completed (ID: abc123)
💬 Assistant: Calculation result: 15 * 7 + 3 = 108
✅ Agent finished processing
```

### State Agent Example (Enhanced with JSON Patch)
```
👤 You [state]: my name is Alice
🔄 Agent started processing...
📊 State delta received: [{"op": "replace", "path": "/conversation_count", "value": 1}]
📊 State delta received: [{"op": "add", "path": "/user_name", "value": "Alice"}]
💬 Assistant: Nice to meet you, Alice! I'll remember your name for our future conversations.
✅ Agent finished processing

👤 You [state]: what do you know about me?
💬 Assistant: 📊 Here's what I know about you:
• Name: Alice
• Conversations: 2
• Preferences: None set
• Topics discussed: 0
```

### Human-in-the-Loop (HITL) Agent Example
```
👤 You [hitl]: send email to team about meeting
🔄 Agent started processing...
📸 State snapshot: {"pending_actions": [], "user_preferences": {}, "interaction_mode": "human_in_the_loop"}
📊 State delta received: [{"op": "add", "path": "/pending_actions/-", "value": {...}}]
💬 Assistant: 🤔 **Action Requires Approval**

I want to send an email with the following details:
• Recipient: example@example.com
• Subject: Automated Email
• Content: to team about meeting

Do you approve this action? (yes/no)
✅ Agent finished processing

👤 You [hitl]: yes
🔄 Agent started processing...
📊 State delta received: [{"op": "remove", "path": "/pending_actions/0"}]
💬 Assistant: 📧 **Email Sent Successfully**

• To: example@example.com
• Subject: Automated Email
• Status: Delivered
• Time: Just now
✅ Agent finished processing
```

## AG-UI Protocol Events

The implementation handles all standard AG-UI events:

### Core Lifecycle Events
- **`RUN_STARTED`**: Agent processing begins
- **`RUN_FINISHED`**: Agent processing complete

### Text Message Events
- **`TEXT_MESSAGE_START`**: New assistant message begins
- **`TEXT_MESSAGE_CONTENT`**: Streaming message content (character deltas)
- **`TEXT_MESSAGE_END`**: Assistant message complete

### Tool Calling Events
- **`TOOL_CALL_START`**: Tool execution begins
- **`TOOL_CALL_ARGS`**: Tool arguments (JSON streamed)
- **`TOOL_CALL_END`**: Tool execution complete

### State Management Events
- **`STATE_DELTA`**: Incremental state updates
- **`STATE_SNAPSHOT`**: Complete state replacement

## Available Tools

### Calculator Tool
- **Function**: Safe mathematical expression evaluation
- **Usage**: "calculate 5 + 3 * 2", "math: 100 / 4"
- **Features**: Basic arithmetic, parentheses, power operations
- **Safety**: Protected against code injection

### Weather Tool
- **Function**: Weather information (simulated)
- **Usage**: "what's the weather?", "weather forecast"
- **Response**: Current conditions with temperature and description

### Time Tool
- **Function**: Current date and time
- **Usage**: "what time is it?", "current time"
- **Response**: Formatted timestamp

## State Management

The State Agent maintains persistent information using **JSON Patch format (RFC 6902)** as specified in the AG-UI protocol:

```python
{
    "user_name": "Alice",
    "preferences": {"theme": "dark", "language": "en"},
    "conversation_count": 15,
    "topics": ["weather", "math", "preferences"],
    "initialized": true
}
```

### State Operations
- **Name Setting**: "my name is [name]"
- **Preference Setting**: "I prefer [preference]"
- **Memory Recall**: "what do you know about me?"
- **State Reset**: "reset my memory"

### JSON Patch State Updates
The enhanced state management now uses proper JSON Patch format:

```python
# Add operation
{"op": "add", "path": "/user_name", "value": "Alice"}

# Replace operation  
{"op": "replace", "path": "/conversation_count", "value": 5}

# Remove operation
{"op": "remove", "path": "/preferences/theme"}

# Array append
{"op": "add", "path": "/topics/-", "value": "new_topic"}
```

## Human-in-the-Loop (HITL) Workflows

The HITL Agent demonstrates proper human-in-the-loop patterns as described in the AG-UI documentation:

### Key Features:
- **Action Approval**: Requests user approval before executing actions
- **Risk Assessment**: Different approval levels based on action risk
- **Trust Levels**: Adjustable trust levels (new_user, trusted, verified)
- **Pending Actions**: State tracking of actions awaiting approval
- **Transparency**: Full visibility into proposed actions

### HITL Actions:
- **Email Sending**: `send email to team about meeting`
- **Data Deletion**: `delete old files` (high risk)
- **Purchases**: `buy coffee` (medium risk)
- **Calculations**: `calculate 5+3` (low risk, auto-approved for trusted users)

### Trust Level Management:
```
👤 You [hitl]: set trust level to trusted
💬 Assistant: 🔐 Trust Level Updated
Previous: new_user
New: trusted
This affects how much approval I'll request for actions.
```

### State Management in HITL
The HITL agent uses sophisticated state management to track:
- Pending actions requiring approval
- User interaction history
- Trust levels and preferences
- Action execution logs

This implementation follows the AG-UI protocol's emphasis on **collaborative decision-making** and **real-time visibility** into agent processes.

## Development

### Adding New Agents

```python
class CustomAgent(BaseAgent):
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        # Emit RUN_STARTED
        yield self.encoder.encode(RunStartedEvent(...))
        
        # Your agent logic here
        async for event in self._send_text_message("Custom response"):
            yield event
            
        # Emit RUN_FINISHED  
        yield self.encoder.encode(RunFinishedEvent(...))
```

### Adding New Tools

```python
async def _handle_custom_tool(self, content: str):
    tool_call_id = str(uuid4())
    
    # Start tool call
    yield self.encoder.encode(ToolCallStartEvent(...))
    
    # Send arguments
    yield self.encoder.encode(ToolCallArgsEvent(...))
    
    # End tool call
    yield self.encoder.encode(ToolCallEndEvent(...))
    
    # Process result and respond
    async for event in self._send_text_message(result):
        yield event
```

## API Endpoints

### POST /agent
Main agent interaction endpoint supporting:
- `thread_id`: Conversation thread identifier
- `messages`: Conversation history
- `tools`: Available tools list
- `state`: Current conversation state
- `agent_type`: Agent selection (echo, tool, state)

### GET /agents
Returns available agents and their capabilities:
```json
{
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

### GET /health
Health check with agent status:
```json
{
  "status": "healthy",
  "agents": ["echo", "tool", "state"],
  "features": ["streaming", "tools", "state"]
}
```

## Testing

### Manual Testing
```bash
# Test individual agents
python client.py
/agent echo
Hello, world!

/agent tool  
calculate 5 + 3

/agent state
my name is Alice
```

### Automated Demo
```bash
# Run comprehensive feature demo
python demo.py
```

### Health Checks
```bash
# Check server status
curl http://localhost:8000/health

# List available agents
curl http://localhost:8000/agents
```

## Troubleshooting

### Common Issues

1. **Server not starting**: 
   - Check if port 8000 is available
   - Verify all dependencies are installed: `pip install -r requirements.txt`

2. **Client connection errors**: 
   - Ensure server is running before starting client
   - Check server health: `curl http://localhost:8000/health`

3. **Agent switching failures**:
   - Verify agent type exists: `/agents` command
   - Check server logs for errors

4. **Tool execution errors**:
   - Tool agents validate input expressions
   - Check calculation syntax for math operations

5. **State persistence issues**:
   - State is maintained per thread_id
   - Use `/state` command to inspect current state

### Debug Mode

Add logging for detailed debugging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Protocol Compatibility

This implementation is fully compatible with the AG-UI protocol specification:
- ✅ Standard event types
- ✅ Server-Sent Events transport
- ✅ JSON message format
- ✅ Tool calling specification
- ✅ State management patterns
- ✅ Multi-agent architecture

**Your AG-UI clients will work with ANY compliant AG-UI server!**

## Technical Implementation Notes

### Server-Sent Events Format
The server uses proper SSE format with single `data: ` prefixes:
```
data: {"type":"RUN_STARTED","thread_id":"123","run_id":"456"}

data: {"type":"TEXT_MESSAGE_START","message_id":"789","role":"assistant"}

data: {"type":"TEXT_MESSAGE_CONTENT","message_id":"789","delta":"H"}

```

### Custom SSE Formatting
Instead of using external libraries that might double-encode, we use custom SSE formatting:
```python
def _format_sse(self, event) -> str:
    event_dict = event.model_dump()
    if 'type' in event_dict:
        event_dict['type'] = event_dict['type'].value
    json_data = json.dumps(event_dict)
    return f"data: {json_data}\n\n"
```

## License

This implementation is provided as an educational example of the AG-UI protocol with advanced multi-agent capabilities.