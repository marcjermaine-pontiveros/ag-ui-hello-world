import { NextRequest } from "next/server";

export const POST = async (req: NextRequest) => {
  try {
    const body = await req.json();
    
    // Check if this is a CopilotKit GraphQL request or direct AG-UI request
    const isGraphQL = body.query !== undefined || body.operationName !== undefined;
    
    if (isGraphQL) {
      console.log('CopilotKit GraphQL Operation:', body.operationName || 'undefined');
      return handleGraphQLRequest(body);
    } else {
      console.log('Direct AG-UI request:', body.agent_type);
      return handleDirectRequest(body);
    }
  } catch (error) {
    console.error('API Error:', error);
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    
    return new Response(JSON.stringify({
      error: `Server error: ${errorMessage}`
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  }
};

// Forward request to AG-UI Python server
async function forwardToAGUIServer(message: string, agentType: string, threadId: string): Promise<string> {
  try {
    const payload = {
      thread_id: threadId,
      messages: [
        {
          id: `msg-${Date.now()}`,
          role: 'user',
          content: message
        }
      ],
      tools: [],
      state: {},
      context: [],
      forwardedProps: {},
      agent_type: agentType
    };

    console.log('Forwarding to AG-UI Python server:', payload);

    const response = await fetch('http://localhost:8000/agent', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.body) {
      return `Error: No response from AG-UI server`;
    }

    // Process the AG-UI server's streaming response
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullResponse = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6));
            if (event.type === 'TEXT_MESSAGE_CONTENT') {
              fullResponse += event.delta;
            }
          } catch {
            // Skip invalid JSON
          }
        }
      }
    }

    return fullResponse || `${agentType} agent processed: ${message}`;
  } catch (error) {
    console.error('Error forwarding to AG-UI server:', error);
    return `Error connecting to AG-UI server: ${error}`;
  }
}

// Handle CopilotKit GraphQL requests
// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function handleGraphQLRequest(body: any) {
  // Handle unknown/undefined operations (CopilotKit sometimes sends these)
  if (!body.operationName || body.operationName === 'undefined') {
    return new Response(JSON.stringify({
      data: {},
      errors: [{ message: "No operation specified" }]
    }), {
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  }

  // Handle CopilotKit's generateCopilotResponse mutation
  if (body.operationName === 'generateCopilotResponse') {
    const messages = body.variables?.data?.messages || [];
    const lastMessage = messages[messages.length - 1];
    
    // Log available actions for debugging
    const actions = body.variables?.data?.frontend?.actions || [];
    console.log('CopilotKit request with actions:', actions.length > 0 ? actions.map((a: {name: string}) => a.name) : 'none');
    
    // Debug: Log the full request to see what CopilotKit is sending
    console.log('CopilotKit Full Request:', JSON.stringify(body, null, 2));
    console.log('Messages array:', messages);
    console.log('Last message:', lastMessage);
    
    // Extract content properly - CopilotKit sends it in textMessage.content
    let messageContent = 'Hello';
    if (lastMessage) {
      // CopilotKit format: { textMessage: { content: "...", role: "user" } }
      if (lastMessage.textMessage && lastMessage.textMessage.content) {
        messageContent = lastMessage.textMessage.content;
      }
      // Fallback to direct content field
      else if (Array.isArray(lastMessage.content)) {
        messageContent = lastMessage.content.join(' ');
      } else if (typeof lastMessage.content === 'string') {
        messageContent = lastMessage.content;
      }
    }
    
    console.log('Extracted message content:', messageContent);
    
    // Determine agent based on message content
    let agentType: 'echo' | 'tool' | 'state' = 'echo';
    const content = messageContent.toLowerCase();
    
    if (content.includes('calculate') || content.includes('weather') || content.includes('time')) {
      agentType = 'tool';
    } else if (content.includes('name') || content.includes('prefer') || content.includes('remember') || 
               content.includes('know about me') || content.includes('what do you know') || 
               content.includes('about me') || content.includes('my preference') || 
               content.includes('memory') || content.includes('information about me')) {
      agentType = 'state';
    }
    
    console.log(`Routing to ${agentType} agent for message: "${messageContent}"`);
    
    const threadId = body.variables?.data?.metadata?.threadId || `thread-${Date.now()}`;
    const runId = `run-${Date.now()}`;
    const messageId = `msg-${Date.now()}`;
    
    // Forward to actual AG-UI Python server
    const agServerResponse = await forwardToAGUIServer(messageContent, agentType, threadId);
    const responseText = agServerResponse;
    
    // Return proper GraphQL response format with content as array (simplified)
    const graphqlResponse = {
      data: {
        generateCopilotResponse: {
          threadId,
          runId,
          extensions: null,
          status: {
            code: "SUCCESS",
            __typename: "BaseResponseStatus"
          },
          messages: [
            {
              __typename: "TextMessageOutput",
              id: messageId,
              createdAt: new Date().toISOString(),
              content: [responseText], // Content as array
              role: "assistant",
              parentMessageId: null,
              status: {
                code: "SUCCESS",
                __typename: "SuccessMessageStatus"
              }
            }
          ],
          metaEvents: [],
          __typename: "CopilotResponse"
        }
      }
    };
    
    return new Response(JSON.stringify(graphqlResponse), {
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  }
  
  // Handle availableAgents query
  if (body.operationName === 'availableAgents') {
    const graphqlResponse = {
      data: {
        availableAgents: {
          agents: [
            {
              name: 'Echo Agent',
              id: 'echo',
              description: 'Simple message echoing from your AG-UI server',
              __typename: 'Agent'
            },
            {
              name: 'Tool Agent',
              id: 'tool',
              description: 'Calculator, weather, and time tools from your AG-UI server',
              __typename: 'Agent'
            },
            {
              name: 'State Agent',
              id: 'state',
              description: 'Memory and preferences management from your AG-UI server',
              __typename: 'Agent'
            }
          ],
          __typename: 'AvailableAgents'
        }
      }
    };
    
    return new Response(JSON.stringify(graphqlResponse), {
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  }
  
  // Handle other/unknown operations
  console.log('Unhandled GraphQL operation:', body.operationName);
  
  return new Response(JSON.stringify({
    data: null,
    errors: [{ message: `Operation ${body.operationName} not implemented` }]
  }), {
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
  });
}

// Handle direct AG-UI requests (for the root page client)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function handleDirectRequest(body: any) {
  const messages = body.messages || [];
  const lastMessage = messages[messages.length - 1]?.content || 'Hello';
  const agentType = body.agent_type || 'echo';
  
  console.log(`Direct AG-UI: Routing to ${agentType} agent for message: "${lastMessage}"`);
  
  // Forward to actual AG-UI Python server
  const agServerResponse = await forwardToAGUIServer(lastMessage, agentType, body.threadId || `thread-${Date.now()}`);
  const responseText = agServerResponse;
  
  // Return AG-UI Server-Sent Events format
  const messageId = `msg-${Date.now()}`;
  const threadId = body.threadId || `thread-${Date.now()}`;
  const runId = `run-${Date.now()}`;
  
  // Create streaming response in AG-UI format
  const stream = new ReadableStream({
    start(controller) {
      const encoder = new TextEncoder();
      
      // Start events
      controller.enqueue(encoder.encode(`data: {"type": "RUN_STARTED", "thread_id": "${threadId}", "run_id": "${runId}"}\n\n`));
      controller.enqueue(encoder.encode(`data: {"type": "TEXT_MESSAGE_START", "message_id": "${messageId}", "role": "assistant"}\n\n`));
      
      // Stream content character by character
      let index = 0;
      const streamContent = () => {
        if (index < responseText.length) {
          const char = responseText[index];
          controller.enqueue(encoder.encode(`data: {"type": "TEXT_MESSAGE_CONTENT", "message_id": "${messageId}", "delta": "${char}"}\n\n`));
          index++;
          setTimeout(streamContent, 50);
        } else {
          // End events
          controller.enqueue(encoder.encode(`data: {"type": "TEXT_MESSAGE_END", "message_id": "${messageId}"}\n\n`));
          controller.enqueue(encoder.encode(`data: {"type": "RUN_FINISHED", "thread_id": "${threadId}", "run_id": "${runId}"}\n\n`));
          controller.close();
        }
      };
      
      setTimeout(streamContent, 100);
    }
  });
  
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': '*',
    },
  });
}

export const GET = async () => {
  return new Response('Multi-format API Bridge: CopilotKit GraphQL + Direct AG-UI', { status: 200 });
};
