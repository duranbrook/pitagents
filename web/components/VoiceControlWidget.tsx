'use client'
import { useMemo, useState, useRef, startTransition } from 'react'
import { useRouter } from 'next/navigation'
import { useVoiceControl } from '@/lib/voice/useVoiceControl'
import { createVoiceTools } from '@/lib/voice/tools'
import { useVoiceContext } from '@/contexts/VoiceContext'
import type { ActivationMode } from '@/lib/voice/types'

const INSTRUCTIONS = `You are a voice control assistant for an auto shop management web app.
Use the registered tools to control the UI. When the user says to navigate, select, or send — call the matching tool immediately.
Do not chat. If a required argument is unclear, ask one brief question.`

export function VoiceControlWidget() {
  const router = useRouter()
  const context = useVoiceContext()
  const [activationMode, setActivationMode] = useState<ActivationMode>('push-to-talk')

  const tools = useMemo(() => createVoiceTools({
    navigate: path => startTransition(() => router.push(path)),
    selectAgent: name => context.selectAgent(name),
    sendMessage: text => context.sendMessage(text),
    selectCustomer: name => startTransition(() => router.push(`/customers?voice_select=${encodeURIComponent(name)}`)),
    selectReport: query => startTransition(() => router.push(`/reports?voice_select=${encodeURIComponent(query)}`)),
    editLine: (service, field, value) => context.editLine(service, field, value),
    addLine: (service, hours, rate, parts) => context.addLine(service, hours, rate, parts),
  }), [context, router])

  const controller = useVoiceControl({
    auth: { sessionEndpoint: '/api/session' },
    tools,
    instructions: INSTRUCTIONS,
    model: 'gpt-4o-mini-realtime-preview',
    activationMode,
    outputMode: 'tool-only',
  })

  const { status, connect, disconnect, startCapture, stopCapture } = controller
  const isConnected = status !== 'idle' && status !== 'error' && status !== 'connecting'
  const mouseDownAt = useRef(0)

  const ringStyle = {
    idle: '0 0 0 2px rgba(255,255,255,0.12)',
    connecting: '0 0 0 2px var(--accent)',
    ready: '0 0 0 2px rgba(74,222,128,0.5)',
    listening: '0 0 0 2px rgba(74,222,128,0.9)',
    processing: '0 0 0 2px var(--accent)',
    error: '0 0 0 2px rgba(239,68,68,0.9)',
  }[status] ?? '0 0 0 2px rgba(255,255,255,0.12)'

  function handleClick() {
    if (status === 'idle' || status === 'error') { connect(); return }
    if (activationMode === 'vad') { disconnect(); return }
    if (activationMode === 'push-to-talk' && isConnected) {
      // Suppress disconnect when the click fires after a PTT hold (> 300ms).
      // Short tap (< 300ms) = intentional disconnect.
      if (Date.now() - mouseDownAt.current > 300) return
      disconnect(); return
    }
  }

  return (
    <div className="flex items-center gap-1.5">
      <button
        onClick={handleClick}
        onMouseDown={activationMode === 'push-to-talk' && isConnected ? () => { mouseDownAt.current = Date.now(); startCapture() } : undefined}
        onMouseUp={activationMode === 'push-to-talk' && isConnected ? () => stopCapture() : undefined}
        onTouchStart={activationMode === 'push-to-talk' && isConnected ? (e) => { e.preventDefault(); startCapture() } : undefined}
        onTouchEnd={activationMode === 'push-to-talk' && isConnected ? () => stopCapture() : undefined}
        title={
          status === 'idle' ? 'Enable voice control'
          : status === 'error' ? 'Voice error — click to retry'
          : status === 'connecting' ? 'Connecting…'
          : status === 'listening' ? (activationMode === 'push-to-talk' ? 'Hold to speak' : 'Listening…')
          : status === 'processing' ? 'Processing…'
          : 'Click to disconnect'
        }
        className="w-7 h-7 rounded-full flex items-center justify-center transition-all select-none"
        style={{ background: 'rgba(255,255,255,0.06)', boxShadow: ringStyle }}
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

      {isConnected && (
        <button
          onClick={() => setActivationMode(m => m === 'vad' ? 'push-to-talk' : 'vad')}
          title={activationMode === 'vad' ? 'Switch to push-to-talk' : 'Switch to always-listening'}
          className="text-[9px] px-1.5 py-0.5 rounded transition-colors select-none"
          style={{
            background: activationMode === 'push-to-talk' ? 'var(--accent)' : 'rgba(255,255,255,0.07)',
            color: activationMode === 'push-to-talk' ? '#fff' : 'rgba(255,255,255,0.3)',
          }}
        >
          PTT
        </button>
      )}
    </div>
  )
}
