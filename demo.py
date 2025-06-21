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

async def demo_hitl_agent(client):
    """Demonstrate Human-in-the-Loop (HITL) agent functionality"""
    print("\n" + "="*60)
    print("🔸 DEMO 4: HUMAN-IN-THE-LOOP (HITL) AGENT")
    print("="*60)
    
    await client.switch_agent("hitl")
    await asyncio.sleep(1)
    
    print("\n👋 Initial HITL introduction:")
    await client.send_message("Hello")
    await asyncio.sleep(3)
    
    print("\n📧 Testing email approval workflow:")
    await client.send_message("send email to team about meeting tomorrow")
    await asyncio.sleep(3)
    
    print("\n✅ Approving the email action:")
    await client.send_message("yes")
    await asyncio.sleep(3)
    
    print("\n💳 Testing purchase approval workflow:")
    await client.send_message("buy a new coffee machine")
    await asyncio.sleep(3)
    
    print("\n❌ Rejecting the purchase:")
    await client.send_message("no")
    await asyncio.sleep(3)
    
    print("\n⚠️ Testing high-risk deletion workflow:")
    await client.send_message("delete all old project files")
    await asyncio.sleep(3)
    
    print("\n❌ Rejecting the dangerous deletion:")
    await client.send_message("no")
    await asyncio.sleep(3)
    
    print("\n🔐 Setting trust level to trusted:")
    await client.send_message("set trust level to trusted")
    await asyncio.sleep(3)
    
    print("\n🧮 Testing calculation with trusted status:")
    await client.send_message("calculate 25 * 4 + 10")
    await asyncio.sleep(3)
    
    print("\n📊 Checking final HITL state:")
    await client.send_message("what's my current status?")

async def demo_enhanced_state_management(client):
    """Demonstrate enhanced state management with JSON Patch"""
    print("\n" + "="*60)
    print("🔸 DEMO 5: ENHANCED STATE MANAGEMENT (JSON PATCH)")
    print("="*60)
    
    await client.switch_agent("state")
    await asyncio.sleep(1)
    
    print("\n📸 Initial state snapshot:")
    await client.send_message("Hello, I'm new here")
    await asyncio.sleep(2)
    
    print("\n👤 Setting user identity (add operation):")
    await client.send_message("my name is David Chen")
    await asyncio.sleep(2)
    
    print("\n🎨 Setting theme preference (nested add):")
    await client.send_message("I prefer dark mode")
    await asyncio.sleep(2)
    
    print("\n🌐 Adding language preference:")
    await client.send_message("I prefer English language")
    await asyncio.sleep(2)
    
    print("\n💬 Generating topics (array operations):")
    await client.send_message("I love discussing AI and machine learning")
    await asyncio.sleep(2)
    await client.send_message("I'm also interested in web development")
    await asyncio.sleep(2)
    
    print("\n📊 Checking accumulated state:")
    await client.send_message("what do you know about me?")
    await asyncio.sleep(2)
    
    print("\n🔄 Testing state reset (snapshot replacement):")
    await client.send_message("reset my memory")
    await asyncio.sleep(2)
    
    print("\n✅ Confirming state reset:")
    await client.send_message("what do you know about me now?")

async def demo_agent_switching(client):
    """Demonstrate switching between agents"""
    print("\n" + "="*60)
    print("🔸 DEMO 6: MULTI-AGENT SWITCHING")
    print("="*60)
    
    print("\n🔄 Switching to echo agent:")
    await client.switch_agent("echo")
    await client.send_message("I'm talking to echo now")
    await asyncio.sleep(1)
    
    print("\n🔄 Switching to tool agent:")
    await client.switch_agent("tool")
    await client.send_message("calculate 100 / 4")
    await asyncio.sleep(2)
    
    print("\n🔄 Switching to state agent:")
    await client.switch_agent("state")
    await client.send_message("my name is Test User")
    await asyncio.sleep(2)
    
    print("\n🔄 Switching to HITL agent:")
    await client.switch_agent("hitl")
    await client.send_message("send email")
    await asyncio.sleep(2)
    await client.send_message("no")

async def main():
    """Run comprehensive demo of all AG-UI features"""
    
    print("🚀 AG-UI Multi-Agent Comprehensive Demo")
    print("This demo showcases all AG-UI protocol features:")
    print("• Text message streaming")
    print("• Tool calling with different tools")
    print("• Enhanced state management with JSON Patch")
    print("• Human-in-the-Loop (HITL) workflows")
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
        
        await demo_hitl_agent(client)
        await asyncio.sleep(1)
        
        await demo_enhanced_state_management(client)
        await asyncio.sleep(1)
        
        await demo_agent_switching(client)
        
        print("\n" + "="*60)
        print("✅ DEMO COMPLETE")
        print("="*60)
        print("🎉 All AG-UI features demonstrated successfully!")
        print("📚 Features showcased:")
        print("  ✓ Text message streaming (character-by-character)")
        print("  ✓ Tool calling (calculator, weather, time)")
        print("  ✓ Enhanced state management (JSON Patch RFC 6902)")
        print("  ✓ Human-in-the-Loop workflows (approval patterns)")
        print("  ✓ Event handling (RUN_STARTED, TEXT_MESSAGE_*, TOOL_CALL_*, STATE_*, RUN_FINISHED)")
        print("  ✓ Agent switching (echo → tool → state → hitl)")
        print("  ✓ Protocol compliance (AG-UI standard events)")
        print("  ✓ HITL approval workflows (email, purchase, deletion)")
        print("  ✓ Trust level management (new_user → trusted)")
        print("  ✓ JSON Patch state operations (add, replace, remove)")
        
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 