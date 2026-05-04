'use client'

import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { getChatHistory, clearChatHistory, streamChatMessage, rateFeedback, ChatHistoryItem, ToolCallRecord } from '@/lib/api'
import { MessageBubble } from './MessageBubble'
import { VoiceButton } from './VoiceButton'
import { ImageAttach } from './ImageAttach'
import { QuoteSummary } from './QuoteSummary'
import { useVoiceContext } from '@/contexts/VoiceContext'
import type { ShopAgent } from '@/lib/types'

interface StreamingMessage {
  text: string
  toolCalls: ToolCallRecord[]
}


const ASSISTANT_CAPABILITIES = [
  {
    icon: '🔍',
    title: 'VIN Lookup',
    description: 'Identify any vehicle by VIN number or photo',
    prompt: 'Look up VIN 1HGBH41JXMN109186',
  },
  {
    icon: '💰',
    title: 'Repair Quote',
    description: 'Build a line-item estimate for any repair job',
    prompt: 'I need a quote for a brake job on a 2019 Honda Civic',
  },
]

interface Props {
  agentId: string
  agent?: ShopAgent
  onNewMessage: (text: string) => void
}

export function ChatPanel({ agentId, agent, onNewMessage }: Props) {
  const router = useRouter()
  const qc = useQueryClient()
  const bottomRef = useRef<HTMLDivElement>(null)
  const [input, setInput] = useState('')
  const [pendingImageUrl, setPendingImageUrl] = useState<string | undefined>()
  const [streaming, setStreaming] = useState<StreamingMessage | null>(null)
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState('')
  const [optimisticUserMsg, setOptimisticUserMsg] = useState<string | null>(null)
  const [ratings, setRatings] = useState<Record<string, 1 | -1>>({})
  const [quoteId, setQuoteId] = useState<string | null>(null)
  const [reportId, setReportId] = useState<string | null>(null)
  const [drawerToken, setDrawerToken] = useState<string | null>(null)
  const [clearing, setClearing] = useState(false)
  const sendingRef = useRef(false)
  const voice = useVoiceContext()

  const [voiceMode] = useState<'hold' | 'toggle'>(() => {
    if (typeof window === 'undefined') return 'hold'
    return (localStorage.getItem('voice_mode') as 'hold' | 'toggle') ?? 'hold'
  })

  const { data: history = [] } = useQuery<ChatHistoryItem[]>({
    queryKey: ['chat', agentId],
    queryFn: () => getChatHistory(agentId),
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history, streaming, optimisticUserMsg])

  useEffect(() => {
    if (agentId !== 'assistant' || quoteId) return
    for (let i = history.length - 1; i >= 0; i--) {
      const msg = history[i]
      if (msg.tool_calls) {
        const hit = msg.tool_calls.find(
          tc => tc.name === 'create_quote' && typeof tc.output?.quote_id === 'string'
        )
        if (hit) {
          setQuoteId(hit.output.quote_id as string)
          break
        }
      }
    }
  }, [history, agentId, quoteId])

  useEffect(() => {
    if (agentId !== 'assistant') return
    for (let i = history.length - 1; i >= 0; i--) {
      const msg = history[i]
      if (msg.tool_calls) {
        const hit = msg.tool_calls.find(tc => typeof tc.output?.report_id === 'string')
        if (hit) {
          setReportId(hit.output.report_id as string)
          return
        }
      }
    }
  }, [history, agentId])

  useEffect(() => {
    voice.registerSendMessage((text) => {
      handleSend(text)
    })
  }, [voice]) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleRate(messageId: string, rating: 1 | -1) {
    setRatings(prev => ({ ...prev, [messageId]: rating }))
    try {
      await rateFeedback(agentId, messageId, rating)
    } catch {
      // silent
    }
  }

  async function handleClear() {
    if (clearing || sending) return
    setClearing(true)
    try {
      await clearChatHistory(agentId)
      setQuoteId(null)
      setReportId(null)
      await qc.invalidateQueries({ queryKey: ['chat', agentId] })
    } finally {
      setClearing(false)
    }
  }

  async function handleSend(overrideText?: string) {
    const text = (overrideText ?? input).trim()
    if (!text || sendingRef.current) return
    sendingRef.current = true
    setInput('')
    setSendError('')
    setSending(true)
    setOptimisticUserMsg(text)
    setStreaming({ text: '', toolCalls: [] })

    try {
      let accumulated = ''
      for await (const event of streamChatMessage(agentId, text, pendingImageUrl)) {
        if (event.type === 'token') {
          accumulated += (event as { type: 'token'; content: string }).content
          setStreaming(prev => prev ? { ...prev, text: accumulated } : null)
        } else if (event.type === 'tool_end') {
          const te = event as { type: 'tool_end'; tool: string; input: Record<string, unknown>; output: Record<string, unknown> }
          setStreaming(prev => prev
            ? { ...prev, toolCalls: [...prev.toolCalls, { name: te.tool, input: te.input, output: te.output }] }
            : null)
          if (te.output && typeof te.output.quote_id === 'string') {
            setQuoteId(te.output.quote_id)
          }
          if (te.output && typeof te.output.report_id === 'string') {
            setReportId(te.output.report_id)
          }
        } else if (event.type === 'done') {
          onNewMessage(accumulated.slice(0, 60))
        } else if (event.type === 'error') {
          const errMsg = (event as { type: 'error'; message?: string }).message ?? 'Something went wrong.'
          setSendError(errMsg)
          if (!overrideText) setInput(text)
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      if (msg.includes('401')) {
        router.replace('/login')
      } else {
        setSendError('Failed to send message. Please try again.')
      }
      if (!overrideText) setInput(text)
    } finally {
      sendingRef.current = false
      setStreaming(null)
      setSending(false)
      setPendingImageUrl(undefined)
      await qc.invalidateQueries({ queryKey: ['chat', agentId] })
      setOptimisticUserMsg(null)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const isEmpty = history.length === 0 && !streaming && !optimisticUserMsg

  // Collapse header for consecutive same-role messages
  type MsgWithHeader = ChatHistoryItem & { showHeader: boolean }
  const historyWithHeaders: MsgWithHeader[] = history.map((msg, i) => ({
    ...msg,
    showHeader: i === 0 || history[i - 1].role !== msg.role,
  }))

  return (
    <div className="flex h-full">
      <div className="flex flex-col flex-1 min-w-0" style={{ background: '#ffffff' }}>
        {/* Header */}
        <div
          className="flex-shrink-0 px-5 py-3 flex items-center gap-2.5"
          style={{ borderBottom: '1px solid #e5e7eb' }}
        >
          {agent?.accent_color && (
            <div
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ background: agent.accent_color }}
            />
          )}
          <div className="flex flex-col min-w-0 flex-1">
            <span className="font-semibold text-sm text-gray-900 leading-tight">
              {agent?.persona_name ?? agent?.name ?? agentId}
            </span>
            {agent?.role_tagline && (
              <span className="text-[10px] leading-tight text-gray-400">
                {agent.role_tagline}
              </span>
            )}
          </div>
          <span
            className="text-[10px] px-1.5 py-0.5 rounded-full flex-shrink-0"
            style={{ background: '#f3f4f6', color: '#9ca3af' }}
          >
            AI
          </span>
          {!isEmpty && (
            <button
              onClick={handleClear}
              disabled={clearing || sending}
              title="New session"
              className="flex-shrink-0 text-[10px] px-2 py-0.5 rounded-full transition-colors disabled:opacity-40"
              style={{ background: '#f3f4f6', color: '#9ca3af', border: '1px solid #e5e7eb' }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#374151' }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = '#9ca3af' }}
            >
              {clearing ? '…' : '+ New'}
            </button>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {isEmpty && agentId === 'assistant' ? (
            <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
              <p className="text-sm text-gray-400">What would you like to do?</p>
              <div className="grid grid-cols-2 gap-3 w-full max-w-sm">
                {ASSISTANT_CAPABILITIES.map(cap => (
                  <button
                    key={cap.title}
                    onClick={() => handleSend(cap.prompt)}
                    className="flex flex-col items-start gap-1.5 p-4 rounded-xl text-left transition-all"
                    style={{ background: '#f9fafb', border: '1px solid #e5e7eb' }}
                    onMouseEnter={e => {
                      const el = e.currentTarget as HTMLElement
                      el.style.borderColor = 'var(--accent)'
                      el.style.background = '#fff7ed'
                    }}
                    onMouseLeave={e => {
                      const el = e.currentTarget as HTMLElement
                      el.style.borderColor = '#e5e7eb'
                      el.style.background = '#f9fafb'
                    }}
                  >
                    <span className="text-xl">{cap.icon}</span>
                    <span className="text-sm font-medium text-gray-900">{cap.title}</span>
                    <span className="text-xs leading-relaxed text-gray-500">{cap.description}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {historyWithHeaders.map(msg => (
                <div key={msg.id}>
                  <MessageBubble
                    role={msg.role}
                    content={msg.content}
                    toolCalls={msg.tool_calls}
                    showHeader={msg.showHeader}
                    timestamp={msg.created_at}
                    onReportLink={setDrawerToken}
                  />
                  {msg.role === 'assistant' && (
                    <div className="flex gap-2 pl-9 pb-0.5">
                      <button
                        onClick={() => handleRate(msg.id, 1)}
                        title="Good response"
                        className={`text-xs px-1 py-0.5 rounded transition-colors ${
                          ratings[msg.id] === 1 ? 'text-green-400' : 'text-gray-700 hover:text-green-400'
                        }`}
                      >👍</button>
                      <button
                        onClick={() => handleRate(msg.id, -1)}
                        title="Bad response"
                        className={`text-xs px-1 py-0.5 rounded transition-colors ${
                          ratings[msg.id] === -1 ? 'text-red-400' : 'text-gray-700 hover:text-red-400'
                        }`}
                      >👎</button>
                    </div>
                  )}
                </div>
              ))}
              {optimisticUserMsg && (
                <MessageBubble
                  role="user"
                  content={[{ type: 'text', text: optimisticUserMsg }]}
                  toolCalls={null}
                  showHeader
                />
              )}
              {streaming !== null && (
                <MessageBubble
                  role="assistant"
                  content={[{ type: 'text', text: streaming.text }]}
                  toolCalls={streaming.toolCalls.length > 0 ? streaming.toolCalls : null}
                  streaming
                  showHeader
                  onReportLink={setDrawerToken}
                />
              )}
            </>
          )}
          <div ref={bottomRef} />
        </div>

        {sendError && (
          <div className="px-5 pb-1">
            <p className="text-xs text-red-400">{sendError}</p>
          </div>
        )}

        {pendingImageUrl && (
          <div className="px-5 pb-1 flex items-center gap-2">
            <span className="text-xs" style={{ color: 'var(--accent)' }}>📎 Photo attached</span>
            <button onClick={() => setPendingImageUrl(undefined)} className="text-xs text-gray-500 hover:text-red-400">✕</button>
          </div>
        )}

        {reportId && (
          <div className="px-5 pb-3">
            <a
              href={`/reports?id=${reportId}`}
              className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full transition-colors"
              style={{ background: 'color-mix(in srgb, var(--accent) 12%, transparent)', color: 'var(--accent)', border: '1px solid color-mix(in srgb, var(--accent) 30%, transparent)' }}
            >
              📋 View Report →
            </a>
          </div>
        )}

        {/* Glass input bar */}
        <div className="px-4 pb-4 pt-2">
          <div
            className="flex items-center gap-2 rounded-2xl px-3 py-2"
            style={{ background: '#f3f4f6', border: '1px solid #e5e7eb' }}
          >
            <ImageAttach onImageUrl={setPendingImageUrl} disabled={sending} />
            <VoiceButton
              mode={voiceMode}
              onTranscript={text => setInput(prev => prev ? `${prev} ${text}` : text)}
              disabled={sending}
            />
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything…"
              rows={1}
              className="flex-1 bg-transparent text-sm resize-none focus:outline-none text-gray-900 placeholder-gray-400"
              style={{
                caretColor: 'var(--accent)',
                maxHeight: '120px',
              }}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || sending}
              className="rounded-lg p-1.5 transition-opacity flex-shrink-0 disabled:opacity-25"
              style={{ background: 'var(--accent)' }}
            >
              <svg className="w-3.5 h-3.5" fill="white" viewBox="0 0 20 20">
                <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {agentId === 'assistant' && <QuoteSummary quoteId={quoteId} />}

      {/* Report slide-in drawer */}
      {drawerToken && (
        <>
          <div
            className="fixed inset-0 z-40"
            style={{ background: 'rgba(0,0,0,0.25)' }}
            onClick={() => setDrawerToken(null)}
          />
          <div
            className="fixed top-0 right-0 h-full z-50 flex flex-col"
            style={{
              width: 480,
              background: '#fff',
              boxShadow: '-4px 0 32px rgba(0,0,0,0.12)',
              animation: 'slideInRight 0.25s ease',
            }}
          >
            <div
              className="flex items-center justify-between px-4 py-3 flex-shrink-0"
              style={{ borderBottom: '1px solid #e5e7eb' }}
            >
              <span className="text-sm font-semibold text-gray-900">Inspection Report</span>
              <button
                onClick={() => setDrawerToken(null)}
                className="text-gray-400 hover:text-gray-700 text-lg leading-none px-1"
              >
                ✕
              </button>
            </div>
            <iframe
              src={`/r/${drawerToken}`}
              className="flex-1 border-none"
              title="Inspection Report"
            />
          </div>
          <style>{`
            @keyframes slideInRight {
              from { transform: translateX(100%); }
              to   { transform: translateX(0); }
            }
          `}</style>
        </>
      )}
    </div>
  )
}
