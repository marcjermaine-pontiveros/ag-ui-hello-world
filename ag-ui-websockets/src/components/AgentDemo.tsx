import React, { useState, useEffect } from 'react'
import { AgentProvider, useAgent, useChatHistory } from '@ag-ui/react'
import { WebSocketAgent } from '../agents/WebSocketAgent'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

function ChatInterface() {
  const { submitMessage, isRunning } = useAgent()
  const { messages } = useChatHistory()
  const [input, setInput] = useState('')
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isRunning) return

    try {
      await submitMessage(input.trim())
      setInput('')
    } catch (error) {
      console.error('Error submitting message:', error)
    }
  }

  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h2>🚀 AG-UI WebSocket Demo</h2>
        <div className={`connection-status ${connectionStatus}`}>
          <span className="status-dot"></span>
          {connectionStatus === 'connected' && 'Connected'}
          {connectionStatus === 'connecting' && 'Connecting...'}
          {connectionStatus === 'disconnected' && 'Disconnected'}
        </div>
      </div>

      <div className="messages-container">
        {messages.length === 0 && (
          <div className="welcome-message">
            <h3>Welcome to AG-UI WebSocket Demo!</h3>
            <p>This demo showcases real-time communication between a React frontend and a Python AG-UI server via WebSockets.</p>
            <p>Try asking:</p>
            <ul>
              <li>"Hello, how are you?"</li>
              <li>"Calculate 15 * 7 + 3"</li>
              <li>"What's the weather like?"</li>
              <li>"What time is it?"</li>
            </ul>
          </div>
        )}

        {messages.map((message) => (
          <div key={message.id} className={`message ${message.role}`}>
            <div className="message-header">
              <span className="role">
                {message.role === 'user' ? '👤 You' : '🤖 Agent'}
              </span>
              <span className="timestamp">
                {formatTimestamp(message.timestamp)}
              </span>
            </div>
            <div className="message-content">
              {message.content}
            </div>
          </div>
        ))}

        {isRunning && (
          <div className="message assistant">
            <div className="message-header">
              <span className="role">🤖 Agent</span>
              <span className="timestamp">now</span>
            </div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="input-form">
        <div className="input-container">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            disabled={isRunning}
            className="message-input"
          />
          <button 
            type="submit" 
            disabled={isRunning || !input.trim()}
            className="send-button"
          >
            {isRunning ? '⏳' : '📤'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default function AgentDemo() {
  const [agent] = useState(() => new WebSocketAgent('ws://localhost:8765'))
  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    // Check if WebSocket server is available
    const checkConnection = async () => {
      try {
        const testWs = new WebSocket('ws://localhost:8765')
        testWs.onopen = () => {
          setIsReady(true)
          testWs.close()
        }
        testWs.onerror = () => {
          setIsReady(false)
        }
      } catch (error) {
        setIsReady(false)
      }
    }

    checkConnection()
    const interval = setInterval(checkConnection, 5000)
    
    return () => clearInterval(interval)
  }, [])

  if (!isReady) {
    return (
      <div className="loading-container">
        <div className="loading-content">
          <h2>🔌 Starting WebSocket Server...</h2>
          <p>Make sure to run the WebSocket server:</p>
          <pre><code>python websocket_server.py</code></pre>
          <div className="loading-spinner"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      <AgentProvider agent={agent}>
        <ChatInterface />
      </AgentProvider>
    </div>
  )
} 