'use client'

import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AppShell } from '@/components/AppShell'
import { AgentList } from '@/components/chat/AgentList'
import { ChatPanel } from '@/components/chat/ChatPanel'
import { useVoiceContext } from '@/contexts/VoiceContext'
import { fetchAgents } from '@/lib/api'

export default function ChatPage() {
  const [selectedAgent, setSelectedAgent] = useState('')
  const [lastMessages, setLastMessages] = useState<Record<string, string>>({})
  const voice = useVoiceContext()

  const { data: agents = [] } = useQuery({ queryKey: ['agents'], queryFn: fetchAgents })

  useEffect(() => {
    if (agents.length > 0 && !selectedAgent) {
      setSelectedAgent(agents[0].id)
    }
  }, [agents, selectedAgent])

  useEffect(() => {
    voice.registerSelectAgent((name) => {
      const key = name.toLowerCase()
      const match = agents.find(a =>
        a.name.toLowerCase().includes(key) || key.includes(a.name.toLowerCase())
      )
      if (!match) return false
      setSelectedAgent(match.id)
      return true
    })
  }, [voice, agents])

  return (
    <AppShell>
      <div className="flex h-full">
        <AgentList
          selectedId={selectedAgent}
          onSelect={setSelectedAgent}
          lastMessages={lastMessages}
        />
        <div className="flex-1 min-w-0">
          {selectedAgent && (
            <ChatPanel
              key={selectedAgent}
              agentId={selectedAgent}
              onNewMessage={(text) =>
                setLastMessages(prev => ({ ...prev, [selectedAgent]: text }))
              }
            />
          )}
        </div>
      </div>
    </AppShell>
  )
}
