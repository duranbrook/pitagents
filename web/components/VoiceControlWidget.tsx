'use client'
import { useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { useVoiceControl } from '@/lib/voice/useVoiceControl'
import { createVoiceTools } from '@/lib/voice/tools'
import { useVoiceContext } from '@/contexts/VoiceContext'
import { fetchAgents } from '@/lib/api'

const STATIC_INSTRUCTIONS = `You are a voice navigator for an auto shop management app. You control the UI by calling tools. That is your only capability — you cannot answer questions from memory.

Always call a tool. Never respond with text.

Interpret commands broadly:
- "go to reports / customers / inspect / chat" → navigate_to_tab
- "show me / find / do you have [customer name]" → select_customer
- "show me / find / do you have a report for [vehicle or name]" → select_report
- "scroll down / up" → scroll
- "send message / ask [text]" → send_message

If genuinely unsure which tool to use, ask one brief clarifying question.`

export function VoiceControlWidget() {
  const router = useRouter()
  const context = useVoiceContext()
  const { data: agents } = useQuery({ queryKey: ['agents'], queryFn: fetchAgents })

  const { instructions, agentNames } = useMemo(() => {
    if (!agents?.length) return { instructions: STATIC_INSTRUCTIONS, agentNames: [] as string[] }
    const names: string[] = []
    const rosterLines = agents.map(a => {
      const display = a.persona_name ?? a.name
      names.push(a.name)
      if (a.persona_name) names.push(a.persona_name)
      return `- ${display} (${a.name}) — ${a.role_tagline}`
    })
    const rosterBlock = [
      'Your team members are:',
      ...rosterLines,
      '',
      `When the user addresses any team member by name — "Tom, are you there?", "Hey ${agents[0].persona_name ?? agents[0].name}", or similar — call select_agent with that name immediately, before responding.`,
    ].join('\n')
    return { instructions: `${STATIC_INSTRUCTIONS}\n\n${rosterBlock}`, agentNames: names }
  }, [agents])

  const tools = useMemo(() => createVoiceTools({
    navigate: path => router.push(path),
    selectAgent: name => context.selectAgent(name),
    sendMessage: text => context.sendMessage(text),
    selectCustomer: name => router.push(`/customers?voice_select=${encodeURIComponent(name)}`),
    selectReport: query => router.push(`/reports?voice_select=${encodeURIComponent(query)}`),
    editLine: (service, field, value) => context.editLine(service, field, value),
    addLine: (service, hours, rate, parts) => context.addLine(service, hours, rate, parts),
    agentNames,
  }), [context, router, agentNames])

  const voiceOptions = useMemo(() => ({
    auth: { sessionEndpoint: '/api/session' },
    tools,
    instructions,
    model: 'gpt-4o-realtime-preview',
    activationMode: 'vad' as const,
    outputMode: 'tool-only' as const,
    toolChoice: 'auto' as const,
    postToolResponse: false,
    autoConnect: true,
    audio: {
      input: {
        turnDetection: {
          type: 'server_vad' as const,
          threshold: 0.6,
          silenceDurationMs: 700,
          prefixPaddingMs: 300,
        },
      },
    },
  }), [tools, instructions])

  const controller = useVoiceControl(voiceOptions)

  const { status, connect, disconnect } = controller
  const isListening = status === 'listening'
  const isConnected = status !== 'idle' && status !== 'error' && status !== 'connecting'

  const ringColor = {
    idle: 'rgba(255,255,255,0.12)',
    connecting: 'var(--accent)',
    ready: 'rgba(74,222,128,0.5)',
    listening: 'rgba(74,222,128,0.9)',
    processing: 'var(--accent)',
    error: 'rgba(239,68,68,0.9)',
  }[status] ?? 'rgba(255,255,255,0.12)'

  function handleClick() {
    if (status === 'error') { connect(); return }
    if (isConnected) { disconnect(); return }
  }

  return (
    <button
      onClick={handleClick}
      title={
        status === 'connecting' ? 'Connecting…'
        : status === 'error' ? 'Voice error — click to retry'
        : isListening ? 'Listening — click to turn off'
        : status === 'processing' ? 'Processing…'
        : 'Voice off — click to turn on'
      }
      className="w-7 h-7 rounded-full flex items-center justify-center transition-all select-none"
      style={{ background: 'rgba(255,255,255,0.06)', boxShadow: `0 0 0 2px ${ringColor}` }}
    >
      {status === 'connecting' ? (
        <div className="w-2.5 h-2.5 rounded-full animate-pulse" style={{ background: 'var(--accent)' }} />
      ) : (
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
          stroke={isConnected ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.35)'}
          strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" y1="19" x2="12" y2="22"/>
        </svg>
      )}
    </button>
  )
}
