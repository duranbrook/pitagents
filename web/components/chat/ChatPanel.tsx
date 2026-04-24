'use client'

import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { getChatHistory, streamChatMessage, ChatHistoryItem, ToolCallRecord } from '@/lib/api'
import { MessageBubble } from './MessageBubble'
import { VoiceButton } from './VoiceButton'
import { ImageAttach } from './ImageAttach'
import { QuoteSummary } from './QuoteSummary'

interface StreamingMessage {
  text: string
  toolCalls: ToolCallRecord[]
}

const AGENT_NAMES: Record<string, string> = { assistant: 'Assistant', tom: 'Tom' }
const AGENT_HEADER_COLORS: Record<string, string> = { assistant: 'bg-indigo-600', tom: 'bg-emerald-700' }

// Capability cards shown in the empty state for the assistant
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
  onNewMessage: (text: string) => void
}

export function ChatPanel({ agentId, onNewMessage }: Props) {
  const router = useRouter()
  const qc = useQueryClient()
  const bottomRef = useRef<HTMLDivElement>(null)
  const [input, setInput] = useState('')
  const [pendingImageUrl, setPendingImageUrl] = useState<string | undefined>()
  const [streaming, setStreaming] = useState<StreamingMessage | null>(null)
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState('')
  const [optimisticUserMsg, setOptimisticUserMsg] = useState<string | null>(null)

  // Track quote_id from tool results (assistant can now create quotes)
  const [quoteId, setQuoteId] = useState<string | null>(null)

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

  // Restore quoteId from history so the sidebar persists across reloads
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

  async function handleSend(overrideText?: string) {
    const text = (overrideText ?? input).trim()
    if (!text || sending) return
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
        } else if (event.type === 'done') {
          onNewMessage(accumulated.slice(0, 60))
        } else if (event.type === 'error') {
          const errMsg = (event as { type: 'error'; message?: string }).message ?? 'Something went wrong. Please try again.'
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

  const headerColor = AGENT_HEADER_COLORS[agentId] ?? 'bg-indigo-600'
  const isEmpty = history.length === 0 && !streaming && !optimisticUserMsg

  return (
    <div className="flex h-full">
      <div className="flex flex-col flex-1 min-w-0 bg-gray-950">
        {/* Header */}
        <div className="border-b border-gray-800 px-5 py-3 flex items-center gap-3">
          <div className={`w-7 h-7 rounded-full ${headerColor} flex items-center justify-center text-white text-xs font-semibold`}>
            {AGENT_NAMES[agentId]?.[0] ?? '?'}
          </div>
          <span className="font-medium text-white text-sm">{AGENT_NAMES[agentId] ?? agentId}</span>
        </div>

        {/* Messages / Empty state */}
        <div className="flex-1 overflow-y-auto px-5 py-5">
          {isEmpty && agentId === 'assistant' ? (
            <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
              <p className="text-gray-500 text-sm">What would you like to do?</p>
              <div className="grid grid-cols-2 gap-3 w-full max-w-sm">
                {ASSISTANT_CAPABILITIES.map(cap => (
                  <button
                    key={cap.title}
                    onClick={() => handleSend(cap.prompt)}
                    className="flex flex-col items-start gap-1.5 p-4 rounded-xl bg-gray-900 border border-gray-800 hover:border-indigo-500 hover:bg-gray-800 transition-colors text-left"
                  >
                    <span className="text-xl">{cap.icon}</span>
                    <span className="text-sm font-medium text-white">{cap.title}</span>
                    <span className="text-xs text-gray-400 leading-relaxed">{cap.description}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {history.map(msg => (
                <MessageBubble
                  key={msg.id}
                  role={msg.role}
                  content={msg.content}
                  toolCalls={msg.tool_calls}
                />
              ))}
              {optimisticUserMsg && (
                <MessageBubble
                  role="user"
                  content={[{ type: 'text', text: optimisticUserMsg }]}
                  toolCalls={null}
                />
              )}
              {streaming !== null && (
                <MessageBubble
                  role="assistant"
                  content={[{ type: 'text', text: streaming.text }]}
                  toolCalls={streaming.toolCalls.length > 0 ? streaming.toolCalls : null}
                  streaming
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
            <span className="text-xs text-indigo-400">📎 Photo attached</span>
            <button onClick={() => setPendingImageUrl(undefined)} className="text-xs text-gray-500 hover:text-red-400">✕</button>
          </div>
        )}

        {/* Input bar */}
        <div className="border-t border-gray-800 px-4 py-3 flex items-end gap-2">
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
            placeholder={`Message ${AGENT_NAMES[agentId] ?? agentId}…`}
            rows={1}
            className="flex-1 bg-gray-800 text-gray-100 placeholder-gray-500 rounded-xl px-4 py-2.5 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-indigo-500"
            style={{ maxHeight: '120px' }}
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || sending}
            className="p-2.5 rounded-full bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40 transition-colors flex-shrink-0"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Quote sidebar — shown for assistant when a quote has been started */}
      {agentId === 'assistant' && <QuoteSummary quoteId={quoteId} />}
    </div>
  )
}
