#!/usr/bin/env python3
"""
AG-UI Multi-Agent Demo
Demonstrates all three agent types: Echo, Tool, and State agents
"""

import asyncio
from client import AGUIClient

async def demo_echo_agent(client):
    """Demonstrate echo agent functionality"""
    print("\n" + "="*60)
    print("🔸 DEMO 1: ECHO AGENT")
    print("="*60)
    
    await client.switch_agent("echo")
    await client.send_message("Hello, echo agent!")
    await asyncio.sleep(1)
    await client.send_message("This is a test message")

async def demo_tool_agent(client):
    """Demonstrate tool agent functionality"""
    print("\n" + "="*60)
    print("🔸 DEMO 2: TOOL AGENT")
    print("="*60)
    
    await client.switch_agent("tool")
    await asyncio.sleep(1)
    
    print("\n🧮 Testing Calculator Tool:")
    await client.send_message("calculate 15 * 7 + 3")
    await asyncio.sleep(2)
    
    print("\n🌤️ Testing Weather Tool:")
    await client.send_message("what's the weather?")
    await asyncio.sleep(2)
    
    print("\n🕐 Testing Time Tool:")
    await client.send_message("what time is it?")
    await asyncio.sleep(2)
    
    print("\n❓ Testing Help Response:")
    await client.send_message("what can you do?")

async def demo_state_agent(client):
    """Demonstrate state agent functionality"""
    print("\n" + "="*60)
    print("🔸 DEMO 3: STATE AGENT")
    print("="*60)
    
    await client.switch_agent("state")
    await asyncio.sleep(1)
    
    print("\n👋 Setting user name:")
    await client.send_message("my name is Alice")
    await asyncio.sleep(2)
    
    print("\n⚙️ Setting preferences:")
    await client.send_message("I prefer dark mode")
    await asyncio.sleep(2)
    
    print("\n❓ Checking stored information:")
    await client.send_message("what do you know about me?")
    await asyncio.sleep(2)
    
    print("\n💬 Regular conversation:")
    await client.send_message("How are you today?")
    await asyncio.sleep(2)
    
    print("\n📊 Checking state again:")
    await client.send_message("my info")

async def demo_agent_switching(client):
    """Demonstrate switching between agents"""
    print("\n" + "="*60)
    print("🔸 DEMO 4: AGENT SWITCHING")
    print("="*60)
    
    print("\n🔄 Switching to echo agent:")
    await client.switch_agent("echo")
    await client.send_message("I'm talking to echo now")
    await asyncio.sleep(1)
    
    print("\n🔄 Switching to tool agent:")
    await client.switch_agent("tool")
    await client.send_message("calculate 100 / 4")
    await asyncio.sleep(2)
    
    print("\n🔄 Switching back to state agent:")
    await client.switch_agent("state")
    await client.send_message("Do you still remember my name?")

async def main():
    """Run comprehensive demo of all AG-UI features"""
    
    print("🚀 AG-UI Multi-Agent Comprehensive Demo")
    print("This demo showcases all AG-UI protocol features:")
    print("• Text message streaming")
    print("• Tool calling with different tools")
    print("• State management and persistence")
    print("• Multi-agent switching")
    print("• Complete event handling")
    
    # Initialize client
    client = AGUIClient()
    
    # Check server health
    if not await client.health_check():
        print("❌ Server not available. Please start the server first:")
        print("   python server.py")
        return
    
    try:
        # Run all demos
        await demo_echo_agent(client)
        await asyncio.sleep(1)
        
        await demo_tool_agent(client)
        await asyncio.sleep(1)
        
        await demo_state_agent(client)
        await asyncio.sleep(1)
        
        await demo_agent_switching(client)
        
        print("\n" + "="*60)
        print("✅ DEMO COMPLETE")
        print("="*60)
        print("🎉 All AG-UI features demonstrated successfully!")
        print("📚 Features showcased:")
        print("  ✓ Text message streaming (character-by-character)")
        print("  ✓ Tool calling (calculator, weather, time)")
        print("  ✓ State management (user data, preferences)")
        print("  ✓ Event handling (RUN_STARTED, TEXT_MESSAGE_*, TOOL_CALL_*, STATE_*, RUN_FINISHED)")
        print("  ✓ Agent switching (echo → tool → state)")
        print("  ✓ Protocol compliance (AG-UI standard events)")
        
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 