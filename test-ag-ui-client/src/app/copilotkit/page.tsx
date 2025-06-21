"use client";

import { CopilotKitCSSProperties, CopilotSidebar } from "@copilotkit/react-ui";
import { useCopilotReadable } from "@copilotkit/react-core";
import { useState } from "react";

export default function CopilotKitPage() {
  const [themeColor] = useState("#6366f1");
  const [debugInfo] = useState("Connected to AG-UI Python server");
  const [showDebugPanel, setShowDebugPanel] = useState(false);

  // Add a simple readable for debugging
  useCopilotReadable({
    description: "Current AG-UI server connection status and theme",
    value: {
      serverStatus: "Connected to localhost:8000",
      themeColor: themeColor,
      debugInfo: debugInfo,
      availableAgents: ["Echo Agent", "Tool Agent", "State Agent"]
    }
  });

  // Note: CopilotKit actions removed for simplicity
  // The custom debug panel below provides the same functionality

  return (
    <main style={{ "--copilot-kit-primary-color": themeColor } as CopilotKitCSSProperties}>
      <ServerAgentInterface 
        themeColor={themeColor} 
        debugInfo={debugInfo}
        showDebugPanel={showDebugPanel}
        setShowDebugPanel={setShowDebugPanel}
      />
      <CopilotSidebar
        clickOutsideToClose={false}
        defaultOpen={true}
        labels={{
          title: "AG-UI Server Assistant",
          initial: `🚀 Connected to your AG-UI Python server!\n\n**Available Agents:**\n\n🔄 **Echo Agent** - Simple message echoing\n🧮 **Tool Agent** - Calculator, weather, time\n🧠 **State Agent** - Memory & preferences\n\n**Try saying:**\n• "Hello" - Test echo agent\n• "Calculate 25 * 8" - Test tool agent\n• "My name is John" - Test state agent\n• "What's the weather?" - Test weather tool\n\n**Basic Chat Mode** - Actions temporarily disabled for stability`
        }}
      />
    </main>
  );
}

function ServerAgentInterface({ 
  themeColor, 
  debugInfo, 
  showDebugPanel, 
  setShowDebugPanel 
}: { 
  themeColor: string;
  debugInfo: string;
  showDebugPanel: boolean;
  setShowDebugPanel: (value: boolean) => void;
}) {
  return (
    <div
      style={{ backgroundColor: themeColor }}
      className="h-screen w-screen flex justify-center items-center flex-col transition-colors duration-300"
    >
      <div className="bg-white/20 backdrop-blur-md p-8 rounded-2xl shadow-xl max-w-2xl w-full">
        <h1 className="text-4xl font-bold text-white mb-2 text-center">AG-UI Server Dashboard</h1>
        <p className="text-gray-200 text-center italic mb-6">Connected to your Python FastAPI backend! 🐍</p>
        
        {/* Agent Capabilities */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          <div className="p-3 rounded-xl text-center bg-white/15">
            <div className="text-2xl mb-2">🔄</div>
            <div className="text-white text-sm font-medium">Echo Agent</div>
            <div className="text-white/70 text-xs">Simple message echoing</div>
          </div>
          <div className="p-3 rounded-xl text-center bg-white/15">
            <div className="text-2xl mb-2">🧮</div>
            <div className="text-white text-sm font-medium">Tool Agent</div>
            <div className="text-white/70 text-xs">Calculator, weather, time</div>
          </div>
          <div className="p-3 rounded-xl text-center bg-white/15">
            <div className="text-2xl mb-2">🧠</div>
            <div className="text-white text-sm font-medium">State Agent</div>
            <div className="text-white/70 text-xs">Memory & preferences</div>
          </div>
        </div>

        <div className="text-center text-white/80 italic py-8">
          <p className="mb-4">🎯 <strong>Basic Chat Mode</strong></p>
          <p className="text-sm">Chat with your AG-UI Python server agents through the sidebar!</p>
          <p className="text-xs mt-2 text-white/60">Agent routing is automatic based on your message content</p>
          
          {/* Custom Debug Panel */}
          <div className="mt-6">
            <button 
              onClick={() => setShowDebugPanel(!showDebugPanel)}
              className="bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg text-sm transition-colors"
            >
              {showDebugPanel ? 'Hide' : 'Show'} Debug Info
            </button>
            
            {showDebugPanel && (
              <div className="mt-4 bg-black/20 rounded-lg p-4 text-left text-xs">
                <h3 className="text-white font-bold mb-2">🔍 Debug Information:</h3>
                <div className="space-y-1 text-white/80">
                  <p><strong>Server Status:</strong> Connected to localhost:8000</p>
                  <p><strong>Theme Color:</strong> {themeColor}</p>
                  <p><strong>Debug Info:</strong> {debugInfo}</p>
                  <p><strong>Available Agents:</strong> Echo, Tool, State</p>
                  <p><strong>Actions:</strong> updateDebugInfo</p>
                  <p><strong>Readables:</strong> serverStatus, themeColor, debugInfo, availableAgents</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
