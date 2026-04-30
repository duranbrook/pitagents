'use client'

import { useEffect, useState } from 'react'
import { AppShell } from '@/components/AppShell'
import { AgentList } from '@/components/chat/AgentList'
import { ChatPanel } from '@/components/chat/ChatPanel'
import { useVoiceContext } from '@/contexts/VoiceContext'

const AGENT_IDS: Record<string, string> = {
  assistant: 'assistant',
  tom: 'tom',
}

export default function ChatPage() {
  const [selectedAgent, setSelectedAgent] = useState('assistant')
  const [lastMessages, setLastMessages] = useState<Record<string, string>>({})
  const voice = useVoiceContext()

  useEffect(() => {
    voice.registerSelectAgent((name) => {
      const key = name.toLowerCase()
      const id = Object.keys(AGENT_IDS).find(agentId =>
        agentId.includes(key) || key.includes(agentId)
      )
      if (!id) return false
      setSelectedAgent(id)
      return true
    })
  }, [voice])

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
