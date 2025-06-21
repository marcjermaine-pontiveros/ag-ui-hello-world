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
    RunStartedEvent, RunFinishedEvent, StateDeltaEvent, Message, UserMessage, AssistantMessage
)
from ag_ui.encoder import EventEncoder

app = FastAPI(title="AG-UI Echo Server")

# Simple echo agent implementation
class EchoAgent:
    def __init__(self):
        self.encoder = EventEncoder()
    
    async def run(self, input: RunAgentInput) -> AsyncGenerator[str, None]:
        """Run the echo agent and yield encoded events"""
        
        thread_id = input.thread_id
        run_id = input.run_id
        
        # Emit RUN_STARTED event
        run_started = RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=thread_id,
            run_id=run_id
        )
        yield self.encoder.encode(run_started)
        
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
            message_start = TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=message_id,
                role="assistant"
            )
            yield self.encoder.encode(message_start)
            
            # Emit TEXT_MESSAGE_CONTENT (character by character for streaming effect)
            for char in echo_response:
                message_content = TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=message_id,
                    delta=char
                )
                yield self.encoder.encode(message_content)
                await asyncio.sleep(0.05)  # Small delay for streaming effect
            
            # Emit TEXT_MESSAGE_END
            message_end = TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=message_id
            )
            yield self.encoder.encode(message_end)
        
        # Emit RUN_FINISHED event
        run_finished = RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=thread_id,
            run_id=run_id
        )
        yield self.encoder.encode(run_finished)

# Global agent instance
echo_agent = EchoAgent()

# Request/Response models
class RunAgentRequest(BaseModel):
    thread_id: str
    messages: list
    tools: list = []
    state: Dict[str, Any] = {}
    context: list = []
    forwardedProps: dict = {}

@app.post("/agent")
async def run_agent(request: RunAgentRequest):
    """Run the echo agent with the provided input"""
    
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
    event_generator = echo_agent.run(run_input)
    
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
    return {"status": "healthy", "agent": "echo"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 