'use client';

import { useState } from 'react';

interface Message {
  id: string;
  role: string;
  content: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [agentType, setAgentType] = useState('echo');

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { 
      id: `msg_${Date.now()}`, 
      role: 'user', 
      content: input 
    };
    setMessages(prev => [...prev, userMessage]);
    setLoading(true);
    setInput('');

    try {
      // Send request to our API route which forwards to your Python AG-UI server
      const response = await fetch('/api/copilotkit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          threadId: 'test-thread',
          messages: [...messages.map(msg => ({
            id: msg.id || `msg_${Date.now()}_${Math.random()}`,
            role: msg.role,
            content: msg.content
          })), userMessage],
          tools: [],
          state: {},
          context: [],
          forwardedProps: {},
          agent_type: agentType
        }),
      });

      if (!response.body) {
        throw new Error('No response body');
      }

      // Process Server-Sent Events from your Python AG-UI server
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const jsonData = line.slice(6); // Remove "data: " prefix
              
              if (!jsonData.trim()) continue; // Skip empty lines
              
              const event = JSON.parse(jsonData);
              
              console.log('Received AG-UI event:', event.type, event);
              
              if (event.type === 'TEXT_MESSAGE_CONTENT') {
                assistantMessage += event.delta;
                // Update the last message in real-time
                setMessages(prev => {
                  const newMessages = [...prev];
                  if (newMessages[newMessages.length - 1]?.role === 'assistant') {
                    newMessages[newMessages.length - 1].content = assistantMessage;
                  } else {
                    newMessages.push({ 
                      id: event.messageId || `assist_${Date.now()}`,
                      role: 'assistant', 
                      content: assistantMessage 
                    });
                  }
                  return newMessages;
                });
              } else if (event.type === 'TEXT_MESSAGE_START') {
                assistantMessage = '';
                setMessages(prev => [...prev, { 
                  id: event.message_id || `assist_${Date.now()}`, 
                  role: 'assistant', 
                  content: '' 
                }]);
              } else if (event.type === 'TOOL_CALL_START') {
                console.log('🔧 Tool call started:', event.tool_call_name);
              } else if (event.type === 'STATE_DELTA') {
                console.log('📊 State updated:', event.delta);
              }
            } catch (e) {
              // Ignore parse errors for partial JSON
              console.debug('Parse error for partial JSON:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { 
        id: `error_${Date.now()}`, 
        role: 'assistant', 
        content: 'Error connecting to server' 
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-center mb-8">
          AG-UI Python Server Test Client
        </h1>
        
        {/* Agent Selector */}
        <div className="mb-6 bg-white rounded-lg p-4 shadow">
          <label className="block text-sm font-medium mb-2">Select Agent Type:</label>
          <select 
            value={agentType} 
            onChange={(e) => setAgentType(e.target.value)}
            className="border rounded px-3 py-2 w-full"
          >
            <option value="echo">Echo Agent (repeats messages)</option>
            <option value="tool">Tool Agent (calculator, weather, time)</option>
            <option value="state">State Agent (remembers user data)</option>
          </select>
        </div>

        {/* Chat Messages */}
        <div className="bg-white rounded-lg shadow mb-6 h-96 overflow-y-auto p-4">
          {messages.length === 0 ? (
            <div className="text-gray-500 text-center py-8">
              <p>No messages yet. Try sending a message to test your Python AG-UI server!</p>
              <div className="mt-4 text-sm">
                <p><strong>Echo Agent:</strong> "Hello, world!"</p>
                <p><strong>Tool Agent:</strong> "calculate 5 + 3" or "what's the weather?"</p>
                <p><strong>State Agent:</strong> "my name is Alice" or "what do you know about me?"</p>
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <div key={index} className={`mb-4 ${message.role === 'user' ? 'text-right' : 'text-left'}`}>
                <div className={`inline-block p-3 rounded-lg max-w-[80%] ${
                  message.role === 'user' 
                    ? 'bg-blue-500 text-white' 
                    : 'bg-gray-200 text-gray-800'
                }`}>
                  <div className="text-xs font-medium mb-1">
                    {message.role === 'user' ? 'You' : `Assistant (${agentType})`}
                  </div>
                  <div className="whitespace-pre-wrap">{message.content}</div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Input */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Type your message..."
              className="flex-1 border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={loading}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600 disabled:opacity-50"
            >
              {loading ? 'Sending...' : 'Send'}
            </button>
          </div>
        </div>

        {/* Status */}
        <div className="text-center mt-4 text-sm text-gray-600">
          <p>Connected to Python AG-UI server at localhost:8000</p>
          <p>Current agent: <span className="font-medium">{agentType}</span></p>
        </div>
      </div>
    </div>
  );
}
