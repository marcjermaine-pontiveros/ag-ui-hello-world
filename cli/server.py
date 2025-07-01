import asyncio
import json
import time
from typing import AsyncGenerator, Dict, Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

# AG-UI core imports
from ag_ui.core import (
    RunAgentInput, EventType,
    TextMessageStartEvent, TextMessageContentEvent, TextMessageEndEvent,
    RunStartedEvent, RunFinishedEvent, StateDeltaEvent, StateSnapshotEvent,
    ToolCallStartEvent, ToolCallArgsEvent, ToolCallEndEvent,
    Message, UserMessage, AssistantMessage
)

app = FastAPI(title="AG-UI Multi-Agent Server")

# Base Agent class
class BaseAgent:
    def __init__(self):
        pass  # Remove EventEncoder
    
    def _format_sse(self, event) -> str:
        """Format event as proper Server-Sent Event"""
        event_dict = event.model_dump()
        # Convert EventType enum to string
        if 'type' in event_dict:
            event_dict['type'] = event_dict['type'].value if hasattr(event_dict['type'], 'value') else str(event_dict['type'])
        
        json_data = json.dumps(event_dict)
        return f"data: {json_data}\n\n"

# 1. Simple Echo Agent (existing)
class EchoAgent(BaseAgent):
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Echo agent that repeats user messages"""
        
        thread_id = input.thread_id
        run_id = input.run_id
        
        # Emit RUN_STARTED event
        yield self._format_sse(RunStartedEvent(
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
            yield self._format_sse(TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=message_id,
                role="assistant"
            ))
            
            # Emit TEXT_MESSAGE_CONTENT (character by character for streaming effect)
            for char in echo_response:
                yield self._format_sse(TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=message_id,
                    delta=char
                ))
                await asyncio.sleep(0.05)  # Small delay for streaming effect
            
            # Emit TEXT_MESSAGE_END
            yield self._format_sse(TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=message_id
            ))
        
        # Emit RUN_FINISHED event
        yield self._format_sse(RunFinishedEvent(
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
        yield self._format_sse(RunStartedEvent(
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
        yield self._format_sse(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=thread_id,
            run_id=run_id
        ))
    
    async def _handle_calculator_tool(self, content: str):
        """Demonstrate calculator tool call"""
        tool_call_id = str(uuid4())
        
        # Start tool call
        yield self._format_sse(ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            tool_call_id=tool_call_id,
            tool_call_name="calculator"
        ))
        
        # Stream tool arguments
        args = {"expression": content.replace('calculate', '').strip()}
        yield self._format_sse(ToolCallArgsEvent(
            type=EventType.TOOL_CALL_ARGS,
            tool_call_id=tool_call_id,
            delta=json.dumps(args)
        ))
        
        # End tool call
        yield self._format_sse(ToolCallEndEvent(
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
        yield self._format_sse(ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            tool_call_id=tool_call_id,
            tool_call_name="weather"
        ))
        
        # Stream tool arguments
        args = {"location": "current"}
        yield self._format_sse(ToolCallArgsEvent(
            type=EventType.TOOL_CALL_ARGS,
            tool_call_id=tool_call_id,
            delta=json.dumps(args)
        ))
        
        # End tool call
        yield self._format_sse(ToolCallEndEvent(
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
        yield self._format_sse(ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            tool_call_id=tool_call_id,
            tool_call_name="get_time"
        ))
        
        # Stream tool arguments
        args = {"timezone": "local"}
        yield self._format_sse(ToolCallArgsEvent(
            type=EventType.TOOL_CALL_ARGS,
            tool_call_id=tool_call_id,
            delta=json.dumps(args)
        ))
        
        # End tool call
        yield self._format_sse(ToolCallEndEvent(
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
        yield self._format_sse(TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START,
            message_id=message_id,
            role="assistant"
        ))
        
        # Stream content
        for char in content:
            yield self._format_sse(TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id=message_id,
                delta=char
            ))
            await asyncio.sleep(0.03)
        
        # End message
        yield self._format_sse(TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END,
            message_id=message_id
        ))

# 3. State Management Agent (Enhanced with proper JSON Patch format)
class StateAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        # Simple in-memory state storage (in production, use proper storage)
        self.memory = {}
    
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Agent that demonstrates proper AG-UI state management with JSON Patch format"""
        yield self._format_sse(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=input.thread_id,
            run_id=input.run_id
        ))
        
        self._ensure_thread_memory(input.thread_id)
        
        # Send initial state snapshot (required by AG-UI protocol)
        if input.thread_id not in self.memory or not self.memory[input.thread_id].get("initialized"):
            yield self._format_sse(StateSnapshotEvent(
                type=EventType.STATE_SNAPSHOT,
                snapshot=self.memory[input.thread_id]
            ))
            self.memory[input.thread_id]["initialized"] = True
        
        if user_messages := [msg for msg in input.messages if getattr(msg, 'role', None) == 'user']:
            async for event in self._process_user_message(input.thread_id, user_messages[-1]):
                yield event
        
        yield self._format_sse(RunFinishedEvent(
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
                "topics": [],
                "initialized": False
            }
    
    async def _process_user_message(self, thread_id: str, message) -> AsyncGenerator[str, None]:
        """Process a user message and generate appropriate responses with proper state deltas"""
        content = getattr(message, 'content', '').lower()
        
        # Update conversation count using JSON Patch format
        old_count = self.memory[thread_id]["conversation_count"]
        self.memory[thread_id]["conversation_count"] += 1
        
        # Emit state delta in proper JSON Patch format (RFC 6902)
        yield self._format_sse(StateDeltaEvent(
            type=EventType.STATE_DELTA,
            delta=[{"op": "replace", "path": "/conversation_count", "value": self.memory[thread_id]["conversation_count"]}]
        ))
        
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
        """Handle setting user's name with proper JSON Patch format"""
        if name := content.replace('my name is', '').strip().title():
            old_name = self.memory[thread_id]["user_name"]
            self.memory[thread_id]["user_name"] = name
            
            # Emit state delta using JSON Patch format
            op = "replace" if old_name else "add"
            yield self._format_sse(StateDeltaEvent(
                type=EventType.STATE_DELTA,
                delta=[{"op": op, "path": "/user_name", "value": name}]
            ))
            
            if old_name:
                response = f"I've updated your name from {old_name} to {name}!"
            else:
                response = f"Nice to meet you, {name}! I'll remember your name for our future conversations."
            
            async for event in self._send_text_message(response):
                yield event
    
    async def _handle_preference_setting(self, thread_id: str, content: str) -> AsyncGenerator[str, None]:
        """Handle setting user preferences with proper JSON Patch format"""
        if 'dark mode' in content:
            self.memory[thread_id]["preferences"]["theme"] = "dark"
            response = "I've noted that you prefer dark mode!"
            pref_path = "/preferences/theme"
            pref_value = "dark"
        elif 'light mode' in content:
            self.memory[thread_id]["preferences"]["theme"] = "light" 
            response = "I've noted that you prefer light mode!"
            pref_path = "/preferences/theme"
            pref_value = "light"
        else:
            # Handle general preferences
            self.memory[thread_id]["preferences"]["general"] = content
            response = "I've updated your preferences!"
            pref_path = "/preferences/general"
            pref_value = content
        
        # Emit state delta using JSON Patch format for nested objects
        yield self._format_sse(StateDeltaEvent(
            type=EventType.STATE_DELTA,
            delta=[{"op": "add", "path": pref_path, "value": pref_value}]
        ))
        
        async for event in self._send_text_message(response):
            yield event
    
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
        """Handle memory/state reset requests with proper state snapshot"""
        # Reset memory
        self.memory[thread_id] = {
            "user_name": None,
            "preferences": {},
            "conversation_count": 0,
            "topics": [],
            "initialized": True
        }
        
        # Send complete state snapshot after reset (as per AG-UI spec)
        yield self._format_sse(StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT,
            snapshot=self.memory[thread_id]
        ))
        
        response = "🔄 Memory has been reset! I've forgotten everything about our previous conversations."
        async for event in self._send_text_message(response):
            yield event
    
    async def _handle_general_conversation(self, thread_id: str, content: str) -> AsyncGenerator[str, None]:
        """Handle general conversation and topic tracking with proper state deltas"""
        # Track conversation topics
        topic = f"{content[:30]}..." if len(content) > 30 else content
        if topic not in self.memory[thread_id]["topics"]:
            self.memory[thread_id]["topics"].append(topic)
            
            # Emit state delta for new topic using JSON Patch format
            yield self._format_sse(StateDeltaEvent(
                type=EventType.STATE_DELTA,
                delta=[{"op": "replace", "path": "/topics", "value": self.memory[thread_id]["topics"]}]
            ))
        
        response = self._build_general_response(thread_id)
        async for event in self._send_text_message(response):
            yield event
    
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
        yield self._format_sse(TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START,
            message_id=message_id,
            role="assistant"
        ))
        
        # Stream content
        for char in content:
            yield self._format_sse(TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id=message_id,
                delta=char
            ))
            await asyncio.sleep(0.03)
        
        # End message
        yield self._format_sse(TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END,
            message_id=message_id
        ))

# 4. Human-in-the-Loop Agent (Demonstrates HITL workflows)
class HitlAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        # Store pending actions for user approval
        self.pending_actions = {}
        # Store user context and state
        self.memory = {}
    
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Agent that implements proper Human-in-the-Loop workflows"""
        yield self._format_sse(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=input.thread_id,
            run_id=input.run_id
        ))
        
        self._ensure_thread_memory(input.thread_id)
        
        # Send initial state snapshot showing pending actions
        yield self._format_sse(StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT,
            snapshot={
                "pending_actions": self.pending_actions.get(input.thread_id, []),
                "user_preferences": self.memory[input.thread_id].get("preferences", {}),
                "interaction_mode": "human_in_the_loop"
            }
        ))
        
        if user_messages := [msg for msg in input.messages if getattr(msg, 'role', None) == 'user']:
            async for event in self._process_hitl_message(input.thread_id, user_messages[-1]):
                yield event
        
        yield self._format_sse(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=input.thread_id,
            run_id=input.run_id
        ))
    
    def _ensure_thread_memory(self, thread_id: str) -> None:
        """Initialize thread memory for HITL workflows"""
        if thread_id not in self.memory:
            self.memory[thread_id] = {
                "preferences": {},
                "interaction_history": [],
                "trust_level": "new_user"  # new_user, trusted, verified
            }
        if thread_id not in self.pending_actions:
            self.pending_actions[thread_id] = []
    
    async def _process_hitl_message(self, thread_id: str, message) -> AsyncGenerator[str, None]:
        """Process messages with human-in-the-loop approval patterns"""
        content = getattr(message, 'content', '').lower()
        
        # Handle approval/rejection of pending actions
        if content in ['yes', 'approve', 'confirm', 'y']:
            async for event in self._handle_approval(thread_id):
                yield event
        elif content in ['no', 'reject', 'cancel', 'n']:
            async for event in self._handle_rejection(thread_id):
                yield event
        
        # Handle action requests that require approval
        elif 'send email' in content:
            async for event in self._propose_email_action(thread_id, content):
                yield event
        elif 'delete' in content or 'remove' in content:
            async for event in self._propose_deletion_action(thread_id, content):
                yield event
        elif 'purchase' in content or 'buy' in content:
            async for event in self._propose_purchase_action(thread_id, content):
                yield event
        elif 'calculate' in content:
            async for event in self._propose_calculation_action(thread_id, content):
                yield event
        
        # Handle preference setting for HITL behavior
        elif 'trust level' in content:
            async for event in self._handle_trust_level_setting(thread_id, content):
                yield event
        
        else:
            async for event in self._handle_general_hitl_conversation(thread_id, content):
                yield event
    
    async def _propose_email_action(self, thread_id: str, content: str) -> AsyncGenerator[str, None]:
        """Propose sending an email and ask for user approval"""
        # Extract email details (simplified)
        action_id = str(uuid4())
        proposed_action = {
            "id": action_id,
            "type": "send_email",
            "details": {
                "recipient": "example@example.com",  # Would extract from content
                "subject": "Automated Email",
                "content": content.replace('send email', '').strip()
            },
            "risk_level": "medium",
            "requires_approval": True
        }
        
        # Add to pending actions
        self.pending_actions[thread_id].append(proposed_action)
        
        # Update state with pending action
        yield self._format_sse(StateDeltaEvent(
            type=EventType.STATE_DELTA,
            delta=[{"op": "add", "path": "/pending_actions/-", "value": proposed_action}]
        ))
        
        # Ask for user approval
        approval_message = (
            f"🤔 **Action Requires Approval**\n\n"
            f"I want to send an email with the following details:\n"
            f"• Recipient: {proposed_action['details']['recipient']}\n"
            f"• Subject: {proposed_action['details']['subject']}\n"
            f"• Content: {proposed_action['details']['content']}\n\n"
            f"Do you approve this action? (yes/no)"
        )
        
        async for event in self._send_text_message(approval_message):
            yield event
    
    async def _propose_deletion_action(self, thread_id: str, content: str) -> AsyncGenerator[str, None]:
        """Propose a deletion action and ask for user approval"""
        action_id = str(uuid4())
        proposed_action = {
            "id": action_id,
            "type": "delete_data",
            "details": {
                "target": content.replace('delete', '').replace('remove', '').strip(),
                "permanent": True
            },
            "risk_level": "high",
            "requires_approval": True
        }
        
        self.pending_actions[thread_id].append(proposed_action)
        
        # Update state
        yield self._format_sse(StateDeltaEvent(
            type=EventType.STATE_DELTA,
            delta=[{"op": "add", "path": "/pending_actions/-", "value": proposed_action}]
        ))
        
        approval_message = (
            f"⚠️ **HIGH RISK ACTION - Approval Required**\n\n"
            f"You want to delete: {proposed_action['details']['target']}\n"
            f"This action is PERMANENT and cannot be undone.\n\n"
            f"Are you absolutely sure? (yes/no)"
        )
        
        async for event in self._send_text_message(approval_message):
            yield event
    
    async def _propose_purchase_action(self, thread_id: str, content: str) -> AsyncGenerator[str, None]:
        """Propose a purchase and ask for user approval"""
        action_id = str(uuid4())
        proposed_action = {
            "id": action_id,
            "type": "make_purchase",
            "details": {
                "item": content.replace('purchase', '').replace('buy', '').strip(),
                "estimated_cost": "$50.00",  # Would calculate from content
                "vendor": "Example Store"
            },
            "risk_level": "medium",
            "requires_approval": True
        }
        
        self.pending_actions[thread_id].append(proposed_action)
        
        # Update state
        yield self._format_sse(StateDeltaEvent(
            type=EventType.STATE_DELTA,
            delta=[{"op": "add", "path": "/pending_actions/-", "value": proposed_action}]
        ))
        
        approval_message = (
            f"💳 **Purchase Approval Required**\n\n"
            f"Item: {proposed_action['details']['item']}\n"
            f"Estimated Cost: {proposed_action['details']['estimated_cost']}\n"
            f"Vendor: {proposed_action['details']['vendor']}\n\n"
            f"Proceed with purchase? (yes/no)"
        )
        
        async for event in self._send_text_message(approval_message):
            yield event
    
    async def _propose_calculation_action(self, thread_id: str, content: str) -> AsyncGenerator[str, None]:
        """Even simple calculations can be part of HITL workflow for transparency"""
        expression = content.replace('calculate', '').strip()
        action_id = str(uuid4())
        
        proposed_action = {
            "id": action_id,
            "type": "calculation",
            "details": {
                "expression": expression,
                "estimated_result": "will be calculated"
            },
            "risk_level": "low",
            "requires_approval": False  # Could be auto-approved for trusted users
        }
        
        # Check user trust level
        trust_level = self.memory[thread_id].get("trust_level", "new_user")
        if trust_level == "new_user":
            proposed_action["requires_approval"] = True
            self.pending_actions[thread_id].append(proposed_action)
            
            # Update state
            yield self._format_sse(StateDeltaEvent(
                type=EventType.STATE_DELTA,
                delta=[{"op": "add", "path": "/pending_actions/-", "value": proposed_action}]
            ))
            
            approval_message = (
                f"🧮 **Calculation Request**\n\n"
                f"Expression: {expression}\n"
                f"Since you're a new user, I'll ask for approval on calculations.\n\n"
                f"Proceed with calculation? (yes/no)"
            )
            
            async for event in self._send_text_message(approval_message):
                yield event
        else:
            # Trusted user - execute immediately but show transparency
            async for event in self._execute_calculation(thread_id, expression):
                yield event
    
    async def _handle_approval(self, thread_id: str) -> AsyncGenerator[str, None]:
        """Handle user approval of pending actions"""
        if not self.pending_actions[thread_id]:
            async for event in self._send_text_message("No pending actions to approve."):
                yield event
            return
        
        # Get the most recent pending action
        action = self.pending_actions[thread_id].pop(0)
        
        # Update state to remove pending action
        yield self._format_sse(StateDeltaEvent(
            type=EventType.STATE_DELTA,
            delta=[{"op": "remove", "path": "/pending_actions/0"}]
        ))
        
        # Execute the approved action
        if action["type"] == "send_email":
            async for event in self._execute_email_action(thread_id, action):
                yield event
        elif action["type"] == "delete_data":
            async for event in self._execute_deletion_action(thread_id, action):
                yield event
        elif action["type"] == "make_purchase":
            async for event in self._execute_purchase_action(thread_id, action):
                yield event
        elif action["type"] == "calculation":
            async for event in self._execute_calculation(thread_id, action["details"]["expression"]):
                yield event
    
    async def _handle_rejection(self, thread_id: str) -> AsyncGenerator[str, None]:
        """Handle user rejection of pending actions"""
        if not self.pending_actions[thread_id]:
            async for event in self._send_text_message("No pending actions to reject."):
                yield event
            return
        
        # Remove the rejected action
        action = self.pending_actions[thread_id].pop(0)
        
        # Update state
        yield self._format_sse(StateDeltaEvent(
            type=EventType.STATE_DELTA,
            delta=[{"op": "remove", "path": "/pending_actions/0"}]
        ))
        
        response = f"✅ Action rejected: {action['type']}. I will not proceed with this action."
        async for event in self._send_text_message(response):
            yield event
    
    async def _execute_email_action(self, thread_id: str, action: dict) -> AsyncGenerator[str, None]:
        """Execute approved email action (simulated)"""
        # Simulate sending email
        response = (
            f"📧 **Email Sent Successfully**\n\n"
            f"• To: {action['details']['recipient']}\n"
            f"• Subject: {action['details']['subject']}\n"
            f"• Status: Delivered\n"
            f"• Time: Just now"
        )
        
        # Log the action in user history
        self.memory[thread_id]["interaction_history"].append({
            "action": "email_sent",
            "timestamp": "2024-01-15T10:30:00Z",
            "details": action["details"]
        })
        
        async for event in self._send_text_message(response):
            yield event
    
    async def _execute_deletion_action(self, thread_id: str, action: dict) -> AsyncGenerator[str, None]:
        """Execute approved deletion action (simulated)"""
        response = f"🗑️ **Deletion Completed**: {action['details']['target']} has been permanently removed."
        
        # Log the action
        self.memory[thread_id]["interaction_history"].append({
            "action": "data_deleted",
            "timestamp": "2024-01-15T10:30:00Z",
            "details": action["details"]
        })
        
        async for event in self._send_text_message(response):
            yield event
    
    async def _execute_purchase_action(self, thread_id: str, action: dict) -> AsyncGenerator[str, None]:
        """Execute approved purchase action (simulated)"""
        response = (
            f"💳 **Purchase Completed**\n\n"
            f"• Item: {action['details']['item']}\n"
            f"• Cost: {action['details']['estimated_cost']}\n"
            f"• Vendor: {action['details']['vendor']}\n"
            f"• Status: Order confirmed\n"
            f"• Order ID: #12345"
        )
        
        async for event in self._send_text_message(response):
            yield event
    
    async def _execute_calculation(self, thread_id: str, expression: str) -> AsyncGenerator[str, None]:
        """Execute calculation with tool calling for transparency"""
        tool_call_id = str(uuid4())
        
        # Start tool call
        yield self._format_sse(ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            tool_call_name="calculator",
            tool_call_id=tool_call_id
        ))
        
        # Send tool arguments
        args = {"expression": expression}
        yield self._format_sse(ToolCallArgsEvent(
            type=EventType.TOOL_CALL_ARGS,
            tool_call_id=tool_call_id,
            delta=json.dumps(args)
        ))
        
        # End tool call
        yield self._format_sse(ToolCallEndEvent(
            type=EventType.TOOL_CALL_END,
            tool_call_id=tool_call_id
        ))
        
        # Perform calculation (simplified)
        try:
            result = eval(expression.replace('x', '*'))
            response = f"🧮 Calculation approved and completed: {expression} = {result}"
        except:
            response = f"❌ Calculation failed: Invalid expression '{expression}'"
        
        async for event in self._send_text_message(response):
            yield event
    
    async def _handle_trust_level_setting(self, thread_id: str, content: str) -> AsyncGenerator[str, None]:
        """Allow users to set their trust level for HITL interactions"""
        if 'trusted' in content:
            new_level = "trusted"
        elif 'verified' in content:
            new_level = "verified"
        else:
            new_level = "new_user"
        
        old_level = self.memory[thread_id].get("trust_level", "new_user")
        self.memory[thread_id]["trust_level"] = new_level
        
        # Update state
        yield self._format_sse(StateDeltaEvent(
            type=EventType.STATE_DELTA,
            delta=[{"op": "replace", "path": "/user_preferences/trust_level", "value": new_level}]
        ))
        
        response = (
            f"🔐 **Trust Level Updated**\n\n"
            f"Previous: {old_level}\n"
            f"New: {new_level}\n\n"
            f"This affects how much approval I'll request for actions."
        )
        
        async for event in self._send_text_message(response):
            yield event
    
    async def _handle_general_hitl_conversation(self, thread_id: str, content: str) -> AsyncGenerator[str, None]:
        """Handle general conversation while maintaining HITL transparency"""
        pending_count = len(self.pending_actions[thread_id])
        trust_level = self.memory[thread_id].get("trust_level", "new_user")
        
        response = (
            f"👋 Hello! I'm your Human-in-the-Loop assistant.\n\n"
            f"Current status:\n"
            f"• Trust level: {trust_level}\n"
            f"• Pending actions: {pending_count}\n\n"
            f"I can help with emails, calculations, purchases, and more. "
            f"I'll ask for your approval before taking actions that affect your data or cost money.\n\n"
            f"Try: 'send email', 'calculate 5+3', 'purchase coffee', or 'delete old files'"
        )
        
        async for event in self._send_text_message(response):
            yield event
    
    async def _send_text_message(self, content: str):
        """Helper method to send a text message"""
        message_id = str(uuid4())
        
        # Start message
        yield self._format_sse(TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START,
            message_id=message_id,
            role="assistant"
        ))
        
        # Stream content
        for char in content:
            yield self._format_sse(TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id=message_id,
                delta=char
            ))
            await asyncio.sleep(0.02)
        
        # End message
        yield self._format_sse(TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END,
            message_id=message_id
        ))

# Agent Registry
agents = {
    "echo": EchoAgent(),
    "tool": ToolAgent(),
    "state": StateAgent(),
    "hitl": HitlAgent()
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
    return StreamingResponse(
        event_generator,
        media_type="text/plain",  # Use plain to avoid auto SSE formatting
        headers={
            "Content-Type": "text/event-stream",  # Set SSE content type manually
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
        "features": ["streaming", "tools", "state"]
    }

@app.get("/agents")
async def list_agents():
    """List available agents with their capabilities"""
    return {
        "echo": {
            "description": "Simple echo agent that repeats messages",
            "features": ["text_messages"],
            "use_case": "Testing basic AG-UI functionality"
        },
        "tool": {
            "description": "Tool-calling agent with multiple tools",
            "features": ["text_messages", "tool_calls"],
            "tools": ["calculator", "weather", "get_time"],
            "use_case": "Demonstrations of tool calling workflows"
        },
        "state": {
            "description": "Enhanced state management agent with JSON Patch",
            "features": ["text_messages", "state_management", "json_patch"],
            "use_case": "Persistent user data and preferences (RFC 6902 compliant)"
        },
        "hitl": {
            "description": "Human-in-the-Loop agent for collaborative workflows",
            "features": ["text_messages", "state_management", "approval_workflows", "trust_management"],
            "use_case": "Actions requiring human approval and collaborative decision-making"
        }
    }



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 