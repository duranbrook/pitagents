'use client'

import { useState } from 'react'
import { AgentList } from './AgentList'
import { ChatPanel } from './ChatPanel'

export function AppShell() {
  const [selectedAgent, setSelectedAgent] = useState('assistant')
  const [lastMessages, setLastMessages] = useState<Record<string, string>>({})

  return (
    <div className="flex h-screen bg-gray-950 overflow-hidden">
      {/* Icon rail */}
      <div className="w-11 bg-gray-950 border-r border-gray-800 flex flex-col items-center py-4 gap-4 flex-shrink-0">
        <div className="w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center">
          <span className="text-white text-xs font-bold">P</span>
        </div>
        <div className="w-px flex-1 bg-gray-800" />
        <a href="/dashboard" className="w-7 h-7 bg-gray-800 hover:bg-gray-700 rounded-lg flex items-center justify-center" title="Reports">
          <span className="text-gray-400 text-xs">≡</span>
        </a>
      </div>

      {/* Agent list */}
      <AgentList
        selectedId={selectedAgent}
        onSelect={setSelectedAgent}
        lastMessages={lastMessages}
      />

      {/* Chat panel */}
      <div className="flex-1 min-w-0">
        <ChatPanel
          key={selectedAgent}
          agentId={selectedAgent}
          onNewMessage={(text) =>
            setLastMessages(prev => ({ ...prev, [selectedAgent]: text }))
          }
        />
      </div>
    </div>
  )
}
