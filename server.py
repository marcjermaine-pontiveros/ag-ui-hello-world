import asyncio
import json
import time
from typing import AsyncGenerator, Dict, Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
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
        if user_messages := [msg for msg in input.messages if getattr(msg, 'role', None) == 'user']:
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
            return self._format_calculation_result(result)
            
        except ZeroDivisionError:
            return "Division by zero error"
        except Exception as e:
            return f"Calculation error: {str(e)}"
    
    def _format_calculation_result(self, result: float | int | str) -> str:
        """Format calculation result with proper precision and type conversion"""
        if isinstance(result, float):
            return str(int(result)) if result.is_integer() else f"{result:.6f}".rstrip('0').rstrip('.')
        return str(result)
    
    def _parse_expression(self, expression: str) -> float:
        """Simple expression parser for basic arithmetic"""
        # Remove outer parentheses and handle simple numeric cases
        expression = self._remove_outer_parentheses(expression)
        
        if self._is_simple_number(expression):
            return float(expression)
        
        # Parse operators by precedence (lowest to highest)
        if result := self._parse_addition_subtraction(expression):
            return result
        
        if result := self._parse_multiplication_division(expression):
            return result
            
        if result := self._parse_power_operations(expression):
            return result
        
        # Final fallback to direct number parsing
        return float(expression)
    
    def _remove_outer_parentheses(self, expression: str) -> str:
        """Remove outer parentheses if they wrap the entire expression"""
        while expression.startswith('(') and expression.endswith(')'):
            if not self._parentheses_wrap_entire_expression(expression):
                break
            expression = expression[1:-1]
        return expression
    
    def _parentheses_wrap_entire_expression(self, expression: str) -> bool:
        """Check if parentheses wrap the entire expression"""
        count = 0
        for i, char in enumerate(expression):
            if char == '(':
                count += 1
            elif char == ')':
                count -= 1
                if count == 0 and i < len(expression) - 1:
                    return False
        return True
    
    def _is_simple_number(self, expression: str) -> bool:
        """Check if expression is a simple number"""
        return expression.replace('.', '').replace('-', '').isdigit()
    
    def _find_operator_outside_parentheses(self, expression: str, operators: str, reverse: bool = True) -> int:
        """Find the position of an operator outside parentheses"""
        paren_count = 0
        range_func = range(len(expression) - 1, -1, -1) if reverse else range(len(expression))
        
        for i in range_func:
            char = expression[i]
            if char == ')':
                paren_count += 1
            elif char == '(':
                paren_count -= 1
            elif paren_count == 0 and char in operators:
                if operators == '+-' and i > 0:  # Don't treat leading minus as operator
                    return i
                elif operators != '+-':
                    return i
        return -1
    
    def _parse_addition_subtraction(self, expression: str) -> float | None:
        """Parse addition and subtraction operations (lowest precedence)"""
        pos = self._find_operator_outside_parentheses(expression, '+-')
        if pos == -1:
            return None
            
        operator = expression[pos]
        left_expr = expression[:pos].strip()
        right_expr = expression[pos+1:].strip()
        
        if not (left_expr and right_expr):
            return None
            
        left = self._parse_expression(left_expr)
        right = self._parse_expression(right_expr)
        
        return left + right if operator == '+' else left - right
    
    def _parse_multiplication_division(self, expression: str) -> float | None:
        """Parse multiplication and division operations (higher precedence)"""
        # Skip ** operators by checking for double * 
        paren_count = 0
        for i in range(len(expression) - 1, -1, -1):
            char = expression[i]
            if char == ')':
                paren_count += 1
            elif char == '(':
                paren_count -= 1
            elif paren_count == 0 and char in '*/':
                # Skip if this is part of **
                if char == '*' and i > 0 and expression[i-1] == '*':
                    continue
                if char == '*' and i < len(expression) - 1 and expression[i+1] == '*':
                    continue
                    
                left_expr = expression[:i].strip()
                right_expr = expression[i+1:].strip()
                
                if not (left_expr and right_expr):
                    continue
                    
                left = self._parse_expression(left_expr)
                right = self._parse_expression(right_expr)
                
                if char == '*':
                    return left * right
                
                if right == 0:
                    raise ZeroDivisionError("Division by zero")
                return left / right
        
        return None
    
    def _parse_power_operations(self, expression: str) -> float | None:
        """Parse power operations (highest precedence, right associative)"""
        # Check for ** operator (search from left to right for right associativity)
        paren_count = 0
        for i in range(len(expression) - 1):
            char = expression[i]
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif paren_count == 0 and expression[i:i+2] == '**':
                left_expr = expression[:i].strip()
                right_expr = expression[i+2:].strip()
                if left_expr and right_expr:  # Ensure both parts are non-empty
                    left = self._parse_expression(left_expr)
                    right = self._parse_expression(right_expr)
                    return left ** right
        
        # Check for ^ operator
        pos = self._find_operator_outside_parentheses(expression, '^', reverse=False)
        if pos == -1:
            return None
            
        left_expr = expression[:pos].strip()
        right_expr = expression[pos+1:].strip()
        if left_expr and right_expr:  # Ensure both parts are non-empty
            left = self._parse_expression(left_expr)
            right = self._parse_expression(right_expr)
            return left ** right
        
        return None

    
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
        yield self.encoder.encode(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=input.thread_id,
            run_id=input.run_id
        ))
        
        self._ensure_thread_memory(input.thread_id)
        
        if user_messages := [msg for msg in input.messages if getattr(msg, 'role', None) == 'user']:
            async for event in self._process_user_message(input.thread_id, user_messages[-1]):
                yield event
        
        yield self.encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=input.thread_id,
            run_id=input.run_id
        ))
    
    def _ensure_thread_memory(self, thread_id: str) -> None:
        """Ensure thread-specific memory exists"""
        if thread_id not in self.memory:
            self.memory[thread_id] = {
                "user_name": None,
                "preferences": {},
                "conversation_count": 0,
                "topics": []
            }
    
    async def _process_user_message(self, thread_id: str, message) -> AsyncGenerator[str, None]:
        """Process a user message and generate appropriate responses"""
        content = getattr(message, 'content', '').lower()
        self.memory[thread_id]["conversation_count"] += 1
        
        # Route to appropriate handler based on content
        if content.startswith('my name is'):
            async for event in self._handle_name_setting(thread_id, content):
                yield event
        elif 'prefer' in content:
            async for event in self._handle_preference_setting(thread_id, content):
                yield event
        elif 'remember' in content and 'name' in content:
            async for event in self._handle_name_recall(thread_id):
                yield event
        elif 'what do you know about me' in content or 'my info' in content:
            async for event in self._handle_info_request(thread_id):
                yield event
        elif 'reset' in content and ('state' in content or 'memory' in content):
            async for event in self._handle_memory_reset(thread_id):
                yield event
        else:
            async for event in self._handle_general_conversation(thread_id, content):
                yield event
    
    async def _handle_name_setting(self, thread_id: str, content: str) -> AsyncGenerator[str, None]:
        """Handle setting user's name"""
        if name := content.replace('my name is', '').strip().title():
            self.memory[thread_id]["user_name"] = name
            response = f"Nice to meet you, {name}! I'll remember your name for our future conversations."
            async for event in self._send_text_message(response):
                yield event
    
    async def _handle_preference_setting(self, thread_id: str, content: str) -> AsyncGenerator[str, None]:
        """Handle setting user preferences"""
        response = self._determine_preference_response(thread_id, content)
        async for event in self._send_text_message(response):
            yield event
    
    def _determine_preference_response(self, thread_id: str, content: str) -> str:
        """Determine the appropriate response for preference setting"""
        if 'dark mode' in content:
            self.memory[thread_id]["preferences"]["theme"] = "dark"
            return "I've noted that you prefer dark mode!"
        elif 'light mode' in content:
            self.memory[thread_id]["preferences"]["theme"] = "light"
            return "I've noted that you prefer light mode!"
        else:
            return "I've updated your preferences!"
    
    async def _handle_name_recall(self, thread_id: str) -> AsyncGenerator[str, None]:
        """Handle questions about remembering the user's name"""
        if user_name := self.memory[thread_id].get("user_name"):
            response = f"Yes, I remember! Your name is {user_name}. 😊"
        else:
            response = "I don't know your name yet. You can tell me by saying 'my name is [your name]'."
        
        async for event in self._send_text_message(response):
            yield event
    
    async def _handle_info_request(self, thread_id: str) -> AsyncGenerator[str, None]:
        """Handle requests for user information summary"""
        info = self._build_user_info_summary(thread_id)
        async for event in self._send_text_message(info):
            yield event
    
    def _build_user_info_summary(self, thread_id: str) -> str:
        """Build a summary of what we know about the user"""
        memory = self.memory[thread_id]
        user_name = memory.get("user_name", "Unknown")
        conv_count = memory.get("conversation_count", 0)
        preferences = memory.get("preferences", {})
        topics = memory.get("topics", [])
        
        return (
            f"📊 Here's what I know about you:\n"
            f"• Name: {user_name}\n"
            f"• Conversations: {conv_count}\n"
            f"• Preferences: {preferences or 'None set'}\n"
            f"• Topics discussed: {len(topics)}"
        )
    
    async def _handle_memory_reset(self, thread_id: str) -> AsyncGenerator[str, None]:
        """Handle memory/state reset requests"""
        self.memory[thread_id] = {
            "user_name": None,
            "preferences": {},
            "conversation_count": 0,
            "topics": []
        }
        
        response = "🔄 Memory has been reset! I've forgotten everything about our previous conversations."
        async for event in self._send_text_message(response):
            yield event
    
    async def _handle_general_conversation(self, thread_id: str, content: str) -> AsyncGenerator[str, None]:
        """Handle general conversation and topic tracking"""
        self._track_conversation_topic(thread_id, content)
        response = self._build_general_response(thread_id)
        
        async for event in self._send_text_message(response):
            yield event
    
    def _track_conversation_topic(self, thread_id: str, content: str) -> None:
        """Track conversation topics"""
        topic = f"{content[:30]}..." if len(content) > 30 else content
        if topic not in self.memory[thread_id]["topics"]:
            self.memory[thread_id]["topics"].append(topic)
    
    def _build_general_response(self, thread_id: str) -> str:
        """Build a general conversation response"""
        if user_name := self.memory[thread_id].get("user_name"):
            greeting = f"Hello {user_name}! "
        else:
            greeting = "Hello! "
        
        return (
            f"{greeting}I can remember information about you across our conversation. "
            f"Try saying 'my name is [name]', 'I prefer dark mode', or 'what do you know about me?'"
        )
    
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
    if request.agent_type not in agents:
        return JSONResponse(
            status_code=400,
            content={"error": f"Unknown agent_type '{request.agent_type}'. Valid types are: {list(agents.keys())}."}
        )
    agent = agents[request.agent_type]
    
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