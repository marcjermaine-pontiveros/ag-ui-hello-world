import React, { useState, useEffect, useRef } from 'react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  isStreaming?: boolean
}

interface ChatInterfaceProps {
  websocketUrl?: string
}

export default function ChatInterface({ websocketUrl = 'ws://localhost:8765' }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected')
  
  const websocketRef = useRef<WebSocket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const currentStreamingMessageRef = useRef<string>('')

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const connectWebSocket = () => {
    setConnectionStatus('connecting')
    
    const ws = new WebSocket(websocketUrl)
    websocketRef.current = ws

    ws.onopen = () => {
      console.log('Connected to WebSocket')
      setIsConnected(true)
      setConnectionStatus('connected')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleWebSocketMessage(data)
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }

    ws.onclose = () => {
      console.log('WebSocket connection closed')
      setIsConnected(false)
      setConnectionStatus('disconnected')
      setIsTyping(false)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      setConnectionStatus('disconnected')
      setIsTyping(false)
    }
  }

  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'RUN_STARTED':
        setIsTyping(true)
        currentStreamingMessageRef.current = ''
        break

      case 'TEXT_MESSAGE_START':
        // Start a new assistant message
        const newMessage: Message = {
          id: data.message_id || Date.now().toString(),
          role: 'assistant',
          content: '',
          timestamp: new Date(),
          isStreaming: true
        }
        setMessages(prev => [...prev, newMessage])
        break

      case 'TEXT_MESSAGE_CONTENT':
        // Append character to the streaming message
        const delta = data.delta || ''
        currentStreamingMessageRef.current += delta
        
        setMessages(prev => 
          prev.map(msg => 
            msg.isStreaming && msg.role === 'assistant' 
              ? { ...msg, content: currentStreamingMessageRef.current }
              : msg
          )
        )
        break

      case 'TEXT_MESSAGE_END':
        // Finish the streaming message
        setMessages(prev =>
          prev.map(msg =>
            msg.isStreaming && msg.role === 'assistant'
              ? { ...msg, isStreaming: false }
              : msg
          )
        )
        break

      case 'RUN_FINISHED':
        setIsTyping(false)
        currentStreamingMessageRef.current = ''
        break

      case 'ERROR':
        console.error('Server error:', data.message)
        setIsTyping(false)
        break

      default:
        console.log('Unknown message type:', data.type)
    }
  }

  const sendMessage = () => {
    if (!input.trim() || !isConnected || isTyping) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])

    // Send message to WebSocket server
    if (websocketRef.current) {
      const messageData = {
        thread_id: Date.now().toString(),
        run_id: Date.now().toString(),
        messages: [{ role: 'user', content: input.trim() }],
        tools: [],
        state: {}
      }
      
      websocketRef.current.send(JSON.stringify(messageData))
    }

    setInput('')
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    sendMessage()
  }

  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  useEffect(() => {
    connectWebSocket()
    
    return () => {
      if (websocketRef.current) {
        websocketRef.current.close()
      }
    }
  }, [websocketUrl])

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h2>🚀 React WebSocket Chat</h2>
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
            <h3>Welcome to WebSocket Chat! 💬</h3>
            <p>This demo showcases real-time communication between React and a Python WebSocket server.</p>
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
                {message.role === 'user' ? '👤 You' : '🤖 Assistant'}
              </span>
              <span className="timestamp">
                {formatTimestamp(message.timestamp)}
              </span>
            </div>
            <div className="message-content">
              {message.content}
              {message.isStreaming && <span className="cursor">|</span>}
            </div>
          </div>
        ))}

        {isTyping && messages.filter(m => m.isStreaming).length === 0 && (
          <div className="message assistant">
            <div className="message-header">
              <span className="role">🤖 Assistant</span>
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
        
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="input-form">
        <div className="input-container">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isConnected ? "Type your message..." : "Connecting..."}
            disabled={!isConnected || isTyping}
            className="message-input"
          />
          <button 
            type="submit" 
            disabled={!isConnected || !input.trim() || isTyping}
            className="send-button"
          >
            {isTyping ? '⏳' : '📤'}
          </button>
        </div>
        {!isConnected && (
          <div className="connection-help">
            <button 
              type="button" 
              onClick={connectWebSocket}
              className="reconnect-button"
            >
              🔌 Reconnect
            </button>
            <span>Make sure the WebSocket server is running on {websocketUrl}</span>
          </div>
        )}
      </form>
    </div>
  )
} 