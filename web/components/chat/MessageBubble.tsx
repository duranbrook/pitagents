'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ContentBlock, ToolCallRecord } from '@/lib/api'

interface Props {
  role: 'user' | 'assistant'
  content: ContentBlock[]
  toolCalls?: ToolCallRecord[] | null
  streaming?: boolean
  showHeader?: boolean
  timestamp?: string
  onReportLink?: (token: string) => void
}

function extractText(content: ContentBlock[]): string {
  return content.filter(b => b.type === 'text').map(b => b.text ?? '').join('')
}

function ToolPill({ toolCalls }: { toolCalls: ToolCallRecord[] }) {
  const [open, setOpen] = useState(false)
  return (
    <span>
      <button
        onClick={() => setOpen(o => !o)}
        className="inline-flex items-center gap-1 ml-2 px-1.5 py-0.5 rounded text-[10px] transition-colors"
        style={{ background: '#f3f4f6', border: '1px solid #e5e7eb', color: '#9ca3af' }}
      >
        · {toolCalls.length} action{toolCalls.length !== 1 ? 's' : ''}
      </button>
      {open && (
        <div className="mt-2 space-y-1.5">
          {toolCalls.map((tc, i) => (
            <div
              key={i}
              className="rounded-md p-2 text-xs font-mono"
              style={{ background: '#f9fafb', border: '1px solid #e5e7eb' }}
            >
              <p className="text-amber-600 mb-1">{tc.name}</p>
              <p className="text-gray-500">in: {JSON.stringify(tc.input)}</p>
              <p className="text-gray-600">out: {JSON.stringify(tc.output)}</p>
            </div>
          ))}
        </div>
      )}
    </span>
  )
}

export function MessageBubble({ role, content, toolCalls, streaming, showHeader = true, timestamp, onReportLink }: Props) {
  const text = extractText(content)
  const hasImage = content.some(b => b.type === 'image')
  const isUser = role === 'user'
  const timeLabel = timestamp
    ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : ''

  if (isUser) {
    return (
      <div className="flex items-start gap-2.5 justify-end py-1">
        <div className="flex flex-col items-end max-w-[72%]">
          {showHeader && (
            <div className="flex items-baseline gap-1.5 mb-1 justify-end">
              {timeLabel && <span className="text-[10px] text-gray-300">{timeLabel}</span>}
              <span className="text-[11px] font-semibold text-gray-400">You</span>
            </div>
          )}
          {hasImage && <div className="mb-1 text-xs italic text-gray-400">📎 photo attached</div>}
          <p className="text-sm leading-relaxed text-right text-gray-700">{text}</p>
        </div>
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5"
          style={{ background: '#f3f4f6', border: '1px solid #e5e7eb', color: '#9ca3af' }}
        >
          P
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-2.5 py-1">
      <div
        className="w-7 h-7 rounded-lg flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5"
        style={{ background: '#fff7ed', border: '1px solid #fed7aa', color: '#d97706' }}
      >
        A
      </div>
      <div className="flex-1 min-w-0">
        {showHeader && (
          <div className="flex items-baseline gap-1.5 mb-1">
            <span className="text-[11px] font-semibold text-gray-700">Assistant</span>
            {timeLabel && <span className="text-[10px] text-gray-300">{timeLabel}</span>}
            {toolCalls && toolCalls.length > 0 && <ToolPill toolCalls={toolCalls} />}
          </div>
        )}
        {!showHeader && toolCalls && toolCalls.length > 0 && (
          <div className="mb-1"><ToolPill toolCalls={toolCalls} /></div>
        )}
        <div className="prose prose-sm max-w-none text-sm text-gray-800">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ href, children }) => {
                if (href && onReportLink) {
                  const m = href.match(/\/r\/([0-9a-f-]{36})/i)
                  if (m) {
                    return (
                      <button
                        onClick={() => onReportLink(m[1])}
                        className="underline cursor-pointer"
                        style={{ color: 'var(--accent)' }}
                      >
                        {children}
                      </button>
                    )
                  }
                }
                return <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>
              },
            }}
          >
            {text}
          </ReactMarkdown>
          {streaming && <span className="inline-block w-1.5 h-3.5 bg-current ml-0.5 animate-pulse align-middle opacity-70" />}
        </div>
      </div>
    </div>
  )
}
