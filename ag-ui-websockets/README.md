# 🚀 AG-UI WebSocket Demo

A comprehensive demo showcasing real-time communication between a React frontend and a Python AG-UI server using WebSockets.

## ✨ Features

- **Real-time Communication**: WebSocket-based communication between React and Python
- **AG-UI Protocol**: Full implementation of the AG-UI protocol with streaming events
- **Multi-Agent Support**: Echo, Tool, and State agents with different capabilities
- **Modern React UI**: Beautiful, responsive interface built with `@ag-ui/react`
- **Tool Integration**: Calculator, weather, and time tools
- **State Management**: Persistent conversation state and user preferences
- **TypeScript Support**: Fully typed codebase for better development experience

## 🏗️ Architecture

```
┌─────────────────┐    WebSocket    ┌──────────────────┐
│   React Client  │ ◄─────────────► │  Python Server   │
│  (@ag-ui/react) │                 │   (AG-UI Core)   │
└─────────────────┘                 └──────────────────┘
        │                                    │
        ▼                                    ▼
┌─────────────────┐                 ┌──────────────────┐
│ WebSocketAgent  │                 │  Multi-Agents    │
│ (Custom Agent)  │                 │ • EchoAgent      │
│                 │                 │ • ToolAgent      │
│                 │                 │ • StateAgent     │
└─────────────────┘                 └──────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.8+
- Modern web browser with WebSocket support

### 1. Install Dependencies

```bash
# Install Python dependencies (from project root)
pip install -r requirements.txt
pip install websockets

# Install Node.js dependencies
cd ag-ui-websockets
npm install
```

### 2. Start the WebSocket Server

```bash
# From the ag-ui-websockets directory
python websocket_server.py
```

You should see:
```
🚀 Starting AG-UI WebSocket Server...
📡 Server will run on ws://localhost:8765
🤖 Available agents: echo, tool, state
✅ WebSocket server running on ws://localhost:8765
```

### 3. Start the React Frontend

```bash
# In a new terminal, from the ag-ui-websockets directory
npm run dev
```

The app will be available at: http://localhost:3000

## 💬 Using the Demo

### Basic Interaction

1. **Simple Messages**: Type "Hello!" to get an echo response
2. **Calculations**: Try "Calculate 15 * 7 + 3" to use the calculator tool
3. **Weather**: Ask "What's the weather like?" for weather information
4. **Time**: Ask "What time is it?" to get the current time

### Agent Types

The demo automatically uses the **Tool Agent** which provides the richest feature set:

- **Echo Agent**: Simple message echoing
- **Tool Agent**: Calculator, weather, and time tools
- **State Agent**: Persistent conversation state and user preferences

### Example Conversations

```
👤 You: Calculate the area of a circle with radius 5
🤖 Agent: Using the calculator tool...
🔧 Tool: calculator
📋 Args: {"expression": "3.14159 * 5 * 5"}
💬 Result: The area is approximately 78.54 square units.

👤 You: What's the weather like?
🤖 Agent: Checking weather conditions...
🔧 Tool: weather
💬 Result: Current weather: 72°F, partly cloudy with light winds.
```

## 🛠️ Development

### Project Structure

```
ag-ui-websockets/
├── src/
│   ├── agents/
│   │   └── WebSocketAgent.ts     # Custom WebSocket agent
│   ├── components/
│   │   └── AgentDemo.tsx         # Main React component
│   ├── App.tsx                   # App root component
│   ├── App.css                   # Styles
│   ├── main.tsx                  # React entry point
│   └── index.css                 # Global styles
├── websocket_server.py           # WebSocket server
├── package.json                  # Node.js dependencies
├── tsconfig.json                 # TypeScript config
├── vite.config.ts               # Vite config
└── index.html                   # HTML template
```

### WebSocket Agent Implementation

The `WebSocketAgent` extends `AbstractAgent` from `@ag-ui/client`:

```typescript
export class WebSocketAgent extends AbstractAgent {
  protected run(input: RunAgentInput): Observable<BaseEvent> {
    return new Observable<BaseEvent>((observer) => {
      // Connect to WebSocket server
      const ws = new WebSocket('ws://localhost:8765')
      
      // Send AG-UI input
      ws.send(JSON.stringify(input))
      
      // Stream events back to AG-UI
      ws.onmessage = (event) => {
        const agentEvent = JSON.parse(event.data) as BaseEvent
        observer.next(agentEvent)
      }
    })
  }
}
```

### Server Integration

The WebSocket server integrates with the existing AG-UI server:

```python
# Import existing agents
from server import EchoAgent, ToolAgent, StateAgent

class WebSocketHandler:
    def __init__(self):
        self.agents = {
            'echo': EchoAgent(),
            'tool': ToolAgent(),
            'state': StateAgent()
        }
```

## 🔧 Configuration

### Changing the WebSocket URL

Update the WebSocket URL in `src/components/AgentDemo.tsx`:

```typescript
const [agent] = useState(() => new WebSocketAgent('ws://your-server:8765'))
```

### Adding New Agents

1. Create a new agent in the main server (`cli/server.py`)
2. Add it to the WebSocket handler:

```python
class WebSocketHandler:
    def __init__(self):
        self.agents = {
            'echo': EchoAgent(),
            'tool': ToolAgent(),
            'state': StateAgent(),
            'custom': YourCustomAgent(),  # Add here
        }
```

### Customizing the UI

Edit `src/App.css` to customize the appearance. The design uses:
- CSS Grid and Flexbox for layout
- CSS Custom Properties for theming
- Smooth animations and transitions
- Responsive design for mobile devices

## 📚 AG-UI Protocol Events

The demo handles all standard AG-UI events:

- **`RUN_STARTED`**: Agent processing begins
- **`RUN_FINISHED`**: Agent processing complete
- **`TEXT_MESSAGE_START`**: New message starts
- **`TEXT_MESSAGE_CONTENT`**: Streaming message content
- **`TEXT_MESSAGE_END`**: Message complete
- **`TOOL_CALL_START`**: Tool execution begins
- **`TOOL_CALL_ARGS`**: Tool arguments
- **`TOOL_CALL_END`**: Tool execution complete
- **`STATE_DELTA`**: State updates
- **`STATE_SNAPSHOT`**: Complete state

## 🐛 Troubleshooting

### WebSocket Connection Issues

1. **Server not running**: Make sure `python websocket_server.py` is running
2. **Port conflicts**: Change the port in both server and client if 8765 is in use
3. **Firewall issues**: Ensure port 8765 is open for local connections

### React Development Issues

1. **Dependencies**: Run `npm install` to ensure all packages are installed
2. **TypeScript errors**: The demo uses strict TypeScript settings
3. **Build issues**: Try `npm run build` to check for production build errors

### Python Server Issues

1. **Import errors**: Make sure you're running from the correct directory
2. **Dependencies**: Install required packages with `pip install -r requirements.txt websockets`
3. **Agent errors**: Check the server logs for detailed error messages

## 🌟 Next Steps

### Enhancements

1. **Authentication**: Add user authentication and authorization
2. **Multiple Connections**: Support multiple concurrent WebSocket connections
3. **Message History**: Persist conversation history across sessions
4. **Custom Tools**: Add more sophisticated tools and integrations
5. **Real-time Collaboration**: Multiple users in the same conversation

### Production Deployment

1. **Security**: Add proper WebSocket security (WSS, authentication)
2. **Scaling**: Use a proper WebSocket server like Socket.IO for production
3. **Monitoring**: Add logging, metrics, and health monitoring
4. **Error Handling**: Implement comprehensive error handling and recovery

## 📖 Learn More

- [AG-UI Protocol Documentation](https://ag-ui.dev)
- [React WebSocket Integration](https://reactjs.org)
- [Python WebSockets](https://websockets.readthedocs.io/)
- [AG-UI React Package](https://www.npmjs.com/package/@ag-ui/react)

## 🤝 Contributing

This demo is part of a larger AG-UI implementation. Feel free to:
- Report bugs and issues
- Suggest new features
- Submit pull requests
- Improve documentation

---

**Happy coding! 🚀** 