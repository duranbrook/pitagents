'use client'

import { useState } from 'react'
import { AppShell } from '@/components/AppShell'
import { AgentList } from '@/components/chat/AgentList'
import { ChatPanel } from '@/components/chat/ChatPanel'

export default function ChatPage() {
  const [selectedAgent, setSelectedAgent] = useState('assistant')
  const [lastMessages, setLastMessages] = useState<Record<string, string>>({})

  return (
    <AppShell>
      <div className="flex h-full">
        <AgentList
          selectedId={selectedAgent}
          onSelect={setSelectedAgent}
          lastMessages={lastMessages}
        />
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
    </AppShell>
  )
}
