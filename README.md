# AG-UI Echo Server and Client

A simple implementation of the Agent User Interaction Protocol (AG-UI) with a server that echoes back user messages and a CLI client for interaction.

## Features

- **AG-UI Protocol Compliant**: Implements the standard AG-UI protocol for agent-client communication
- **Real-time Streaming**: Responses are streamed character-by-character for immediate feedback
- **Simple Echo Agent**: Server agent that echoes back any message sent by the client
- **CLI Client**: Easy-to-use command-line interface for testing
- **Health Checks**: Built-in health monitoring for the server

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Starting the Server

1. Start the AG-UI echo server:
```bash
python server.py
```

The server will start on `http://localhost:8000` with the following endpoints:
- `POST /agent` - Main agent endpoint for processing messages
- `GET /health` - Health check endpoint

### Using the Client

1. In a new terminal, start the CLI client:
```bash
python client.py
```

2. The client will automatically check server health and connect to the agent
3. Type your messages and press Enter to send them
4. Watch the agent echo back your messages in real-time
5. Type `quit`, `exit`, or `q` to exit the client

### Example Session

```
🤖 AG-UI Echo Client
==================================================
🔍 Checking server health...
✅ Server health: {'status': 'healthy', 'agent': 'echo'}

💬 Chat with the echo agent! (Type 'quit' to exit)
--------------------------------------------------

👤 You: Hello, world!

🤖 Sending message: Hello, world!
📡 Waiting for response...

🔄 Agent started processing...
💬 Assistant: Echo: Hello, world!
✅ Agent finished processing

👤 You: How are you today?

🤖 Sending message: How are you today?
📡 Waiting for response...

🔄 Agent started processing...
💬 Assistant: Echo: How are you today?
✅ Agent finished processing

👤 You: quit
👋 Goodbye!
```

## Architecture

### Server (`server.py`)

The server implements:
- **EchoAgent**: A simple agent that extends `AbstractAgent` and echoes back user messages
- **FastAPI Application**: HTTP server with SSE (Server-Sent Events) support
- **Event Streaming**: Proper AG-UI event emission (RUN_STARTED → TEXT_MESSAGE_* → RUN_FINISHED)
- **Message History**: Maintains conversation context across interactions

### Client (`client.py`)

The client implements:
- **AGUIClient**: Handles communication with the AG-UI server
- **SSE Processing**: Parses and handles Server-Sent Events
- **Real-time Display**: Shows streaming responses as they arrive
- **Message History**: Maintains conversation state locally

## AG-UI Protocol Events

The implementation follows the AG-UI protocol by emitting these events in sequence:

1. **RUN_STARTED**: Indicates the agent has started processing
2. **TEXT_MESSAGE_START**: Begins a new assistant message
3. **TEXT_MESSAGE_CONTENT**: Streams message content character by character
4. **TEXT_MESSAGE_END**: Completes the assistant message
5. **RUN_FINISHED**: Indicates the agent has finished processing

## Development

### Adding New Features

To extend this implementation:

1. **Custom Agents**: Create new agent classes extending `AbstractAgent`
2. **Tool Support**: Implement tool calling and execution
3. **State Management**: Add persistent state across conversations
4. **Multi-Agent**: Support agent-to-agent handoffs

### Testing

The server includes a health check endpoint for monitoring:
```bash
curl http://localhost:8000/health
```

## Troubleshooting

### Common Issues

1. **Server not starting**: Check if port 8000 is available
2. **Client connection errors**: Ensure the server is running before starting the client
3. **Import errors**: Verify all dependencies are installed with `pip install -r requirements.txt`

### Debug Mode

For debugging, you can add logging to both server and client by modifying the respective files.

## License

This implementation is provided as an educational example of the AG-UI protocol. 