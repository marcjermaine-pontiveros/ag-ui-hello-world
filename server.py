import asyncio
import json
import time
from typing import AsyncGenerator, Dict, Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

# AG-UI core imports
from ag_ui.core import (
    RunAgentInput, EventType,
    TextMessageStartEvent, TextMessageContentEvent, TextMessageEndEvent,
    RunStartedEvent, RunFinishedEvent, StateDeltaEvent, StateSnapshotEvent,
    ToolCallStartEvent, ToolCallArgsEvent, ToolCallEndEvent,
    Message, UserMessage, AssistantMessage
)
from ag_ui.encoder import EventEncoder

app = FastAPI(title="AG-UI Multi-Agent Server")

# Base Agent class
class BaseAgent:
    def __init__(self):
        self.encoder = EventEncoder()

# 1. Simple Echo Agent (existing)
class EchoAgent(BaseAgent):
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Echo agent that repeats user messages"""
        
        thread_id = input.thread_id
        run_id = input.run_id
        
        # Emit RUN_STARTED event
        yield self.encoder.encode(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=thread_id,
            run_id=run_id
        ))
        
        # Find the latest user message
        user_messages = [msg for msg in input.messages if getattr(msg, 'role', None) == 'user']
        if user_messages:
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
                await asyncio.sleep(0.05)  # Small delay for streaming effect
            
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

# 2. Tool-calling Agent
class ToolAgent(BaseAgent):
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Agent that demonstrates tool calling capabilities"""
        
        thread_id = input.thread_id
        run_id = input.run_id
        
        # Emit RUN_STARTED event
        yield self.encoder.encode(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=thread_id,
            run_id=run_id
        ))
        
        # Find the latest user message
        user_messages = [msg for msg in input.messages if getattr(msg, 'role', None) == 'user']
        if user_messages:
            latest_message = user_messages[-1]
            content = getattr(latest_message, 'content', '').lower()
            
            # Check if user wants to use a tool
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
                # Regular text response
                async for event in self._send_text_message("I can help you with calculations, weather, or time. Try asking 'calculate 5 + 3' or 'what's the weather?'"):
                    yield event
        
        # Emit RUN_FINISHED event
        yield self.encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=thread_id,
            run_id=run_id
        ))
    
    async def _handle_calculator_tool(self, content: str):
        """Demonstrate calculator tool call"""
        tool_call_id = str(uuid4())
        
        # Start tool call
        yield self.encoder.encode(ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            tool_call_id=tool_call_id,
            tool_call_name="calculator"
        ))
        
        # Stream tool arguments
        args = {"expression": content.replace('calculate', '').strip()}
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
        
        # Simulate tool execution and send result
        try:
            expression = args["expression"].replace('x', '*').replace('÷', '/')
            result = self._safe_calculate(expression) if expression else "Invalid expression"
            async for event in self._send_text_message(f"Calculation result: {expression} = {result}"):
                yield event
        except Exception as e:
            async for event in self._send_text_message(f"Sorry, I couldn't calculate that expression: {str(e)}"):
                yield event
    
    async def _handle_weather_tool(self, content: str):
        """Demonstrate weather tool call"""
        tool_call_id = str(uuid4())
        
        # Start tool call
        yield self.encoder.encode(ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            tool_call_id=tool_call_id,
            tool_call_name="weather"
        ))
        
        # Stream tool arguments
        args = {"location": "current"}
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
        
        # Simulate weather API response
        async for event in self._send_text_message("🌤️ Current weather: 72°F, partly cloudy with light winds. (This is a simulated response)"):
            yield event
    
    async def _handle_time_tool(self):
        """Demonstrate time tool call"""
        tool_call_id = str(uuid4())
        
        # Start tool call
        yield self.encoder.encode(ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            tool_call_id=tool_call_id,
            tool_call_name="get_time"
        ))
        
        # Stream tool arguments
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
        
        # Get actual current time
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        async for event in self._send_text_message(f"🕐 Current time: {current_time}"):
            yield event
    
    def _safe_calculate(self, expression: str) -> str:
        """Safely evaluate mathematical expressions without using eval()"""
        import re
        import operator
        
        # Define allowed operators
        ops = {
            '+': operator.add,
            '-': operator.sub,
            '*': operator.mul,
            '/': operator.truediv,
            '//': operator.floordiv,
            '%': operator.mod,
            '**': operator.pow,
            '^': operator.pow,  # Alternative power operator
        }
        
        try:
            # Remove whitespace
            expression = expression.replace(' ', '')
            
            # Check for invalid characters (only allow numbers, operators, parentheses, and decimal points)
            if not re.match(r'^[0-9+\-*/().%^*]+$', expression):
                return "Invalid characters in expression"
            
            # Simple validation to prevent obvious malicious patterns
            if any(dangerous in expression.lower() for dangerous in ['import', 'exec', 'eval', '__', 'open', 'file']):
                return "Invalid expression"
            
            # For now, use a simple recursive descent parser for basic arithmetic
            result = self._parse_expression(expression)
            
            # Format result nicely
            if isinstance(result, float):
                if result.is_integer():
                    return str(int(result))
                else:
                    return f"{result:.6f}".rstrip('0').rstrip('.')
            return str(result)
            
        except ZeroDivisionError:
            return "Division by zero error"
        except Exception as e:
            return f"Calculation error: {str(e)}"
    
    def _parse_expression(self, expression: str) -> float:
        """Simple expression parser for basic arithmetic"""
        # This is a simplified parser for basic arithmetic expressions
        # In production, consider using a proper math expression library like simpleeval
        
        # Remove outer parentheses if they wrap the entire expression
        while expression.startswith('(') and expression.endswith(')'):
            # Check if parentheses are balanced
            count = 0
            for i, char in enumerate(expression):
                if char == '(':
                    count += 1
                elif char == ')':
                    count -= 1
                    if count == 0 and i < len(expression) - 1:
                        break
            else:
                expression = expression[1:-1]
        
        # Handle simple cases first
        if expression.replace('.', '').replace('-', '').isdigit():
            return float(expression)
        
        # Find the last + or - (lowest precedence)
        paren_count = 0
        for i in range(len(expression) - 1, -1, -1):
            char = expression[i]
            if char == ')':
                paren_count += 1
            elif char == '(':
                paren_count -= 1
            elif paren_count == 0 and char in '+-' and i > 0:
                left = self._parse_expression(expression[:i])
                right = self._parse_expression(expression[i+1:])
                return left + right if char == '+' else left - right
        
        # Find the last * or / (higher precedence)
        paren_count = 0
        for i in range(len(expression) - 1, -1, -1):
            char = expression[i]
            if char == ')':
                paren_count += 1
            elif char == '(':
                paren_count -= 1
            elif paren_count == 0 and char in '*/':
                left = self._parse_expression(expression[:i])
                right = self._parse_expression(expression[i+1:])
                if char == '*':
                    return left * right
                else:
                    if right == 0:
                        raise ZeroDivisionError("Division by zero")
                    return left / right
        
        # Handle ** or ^ (power) - search from left to right for right associativity
        paren_count = 0
        for i in range(len(expression)):
            char = expression[i]
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif paren_count == 0:
                if i < len(expression) - 1 and expression[i:i+2] == '**':
                    left = self._parse_expression(expression[:i])
                    right = self._parse_expression(expression[i+2:])
                    return left ** right
                elif char == '^':
                    left = self._parse_expression(expression[:i])
                    right = self._parse_expression(expression[i+1:])
                    return left ** right
        
        # If we get here, try to parse as a number
        return float(expression)
    
    async def _send_text_message(self, content: str):
        """Helper method to send a text message"""
        message_id = str(uuid4())
        
        # Start message
        yield self.encoder.encode(TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START,
            message_id=message_id,
            role="assistant"
        ))
        
        # Stream content
        for char in content:
            yield self.encoder.encode(TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id=message_id,
                delta=char
            ))
            await asyncio.sleep(0.03)
        
        # End message
        yield self.encoder.encode(TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END,
            message_id=message_id
        ))

# 3. State Management Agent (Simplified - Text Only)
class StateAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        # Simple in-memory state storage (in production, use proper storage)
        self.memory = {}
    
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Agent that demonstrates state management capabilities using text responses"""
        
        thread_id = input.thread_id
        run_id = input.run_id
        
        # Emit RUN_STARTED event
        yield self.encoder.encode(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=thread_id,
            run_id=run_id
        ))
        
        # Get thread-specific memory
        if thread_id not in self.memory:
            self.memory[thread_id] = {
                "user_name": None,
                "preferences": {},
                "conversation_count": 0,
                "topics": []
            }
        
        # Find the latest user message
        user_messages = [msg for msg in input.messages if getattr(msg, 'role', None) == 'user']
        if user_messages:
            latest_message = user_messages[-1]
            content = getattr(latest_message, 'content', '').lower()
            
            # Update conversation count
            self.memory[thread_id]["conversation_count"] += 1
            
            # Handle different state operations
            if content.startswith('my name is'):
                name = content.replace('my name is', '').strip().title()
                self.memory[thread_id]["user_name"] = name
                
                response = f"Nice to meet you, {name}! I'll remember your name for our future conversations."
                async for event in self._send_text_message(response):
                    yield event
                    
            elif 'prefer' in content:
                # Handle preference setting
                if 'dark mode' in content:
                    self.memory[thread_id]["preferences"]["theme"] = "dark"
                    response = "I've noted that you prefer dark mode!"
                elif 'light mode' in content:
                    self.memory[thread_id]["preferences"]["theme"] = "light"
                    response = "I've noted that you prefer light mode!"
                else:
                    response = "I've updated your preferences!"
                
                async for event in self._send_text_message(response):
                    yield event
                    
            elif 'remember' in content and 'name' in content:
                # Handle questions about remembering the name
                user_name = self.memory[thread_id].get("user_name")
                if user_name:
                    response = f"Yes, I remember! Your name is {user_name}. 😊"
                else:
                    response = "I don't know your name yet. You can tell me by saying 'my name is [your name]'."
                
                async for event in self._send_text_message(response):
                    yield event
                    
            elif 'what do you know about me' in content or 'my info' in content:
                # Show current state
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
                    
            elif 'reset' in content and ('state' in content or 'memory' in content):
                # Reset state
                self.memory[thread_id] = {
                    "user_name": None,
                    "preferences": {},
                    "conversation_count": 0,
                    "topics": []
                }
                
                async for event in self._send_text_message("🔄 Memory has been reset! I've forgotten everything about our previous conversations."):
                    yield event
                    
            else:
                # Add topic to discussed topics
                topic = content[:30] + "..." if len(content) > 30 else content
                if topic not in self.memory[thread_id]["topics"]:
                    self.memory[thread_id]["topics"].append(topic)
                
                user_name = self.memory[thread_id].get("user_name")
                greeting = f"Hello {user_name}! " if user_name else "Hello! "
                
                response = greeting + f"I can remember information about you across our conversation. "
                response += f"Try saying 'my name is [name]', 'I prefer dark mode', or 'what do you know about me?'"
                
                async for event in self._send_text_message(response):
                    yield event
        
        # Emit RUN_FINISHED event
        yield self.encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=thread_id,
            run_id=run_id
        ))
    
    async def _send_text_message(self, content: str):
        """Helper method to send a text message"""
        message_id = str(uuid4())
        
        # Start message
        yield self.encoder.encode(TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START,
            message_id=message_id,
            role="assistant"
        ))
        
        # Stream content
        for char in content:
            yield self.encoder.encode(TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id=message_id,
                delta=char
            ))
            await asyncio.sleep(0.03)
        
        # End message
        yield self.encoder.encode(TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END,
            message_id=message_id
        ))

# Agent instances
agents = {
    "echo": EchoAgent(),
    "tool": ToolAgent(),
    "state": StateAgent()
}

# Request/Response models
class RunAgentRequest(BaseModel):
    thread_id: str
    messages: list
    tools: list = []
    state: Dict[str, Any] = {}
    context: list = []
    forwardedProps: dict = {}
    agent_type: str = "echo"  # New field to select agent

@app.post("/agent")
async def run_agent(request: RunAgentRequest):
    """Run the specified agent with the provided input"""
    
    # Select agent based on request
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
    
    # Get the agent's event generator
    event_generator = agent.run(run_input)
    
    # Return streaming response
    return EventSourceResponse(
        event_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "agents": list(agents.keys()),
        "features": ["text_messages", "tool_calls", "state_management"]
    }

@app.get("/agents")
async def list_agents():
    """List available agents and their capabilities"""
    return {
        "echo": {
            "description": "Simple echo agent that repeats user messages",
            "features": ["text_messages"]
        },
        "tool": {
            "description": "Agent that demonstrates tool calling capabilities",
            "features": ["text_messages", "tool_calls"],
            "tools": ["calculator", "weather", "get_time"]
        },
        "state": {
            "description": "Agent that demonstrates state management",
            "features": ["text_messages", "state_management"],
            "state_operations": ["user_preferences", "conversation_tracking", "state_reset"]
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 