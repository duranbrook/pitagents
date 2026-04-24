'use client'

import { useState } from 'react'
import type { ContentBlock, ToolCallRecord } from '@/lib/api'

interface Props {
  role: 'user' | 'assistant'
  content: ContentBlock[]
  toolCalls?: ToolCallRecord[] | null
  streaming?: boolean
}

function extractText(content: ContentBlock[]): string {
  return content
    .filter(b => b.type === 'text')
    .map(b => b.text ?? '')
    .join('')
}

function ToolCallsCollapse({ toolCalls }: { toolCalls: ToolCallRecord[] }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mt-1.5">
      <button
        onClick={() => setOpen(o => !o)}
        className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
      >
        <span>{open ? '▼' : '▶'}</span>
        {toolCalls.length} tool call{toolCalls.length !== 1 ? 's' : ''}
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {toolCalls.map((tc, i) => (
            <div key={i} className="bg-gray-900 rounded-md p-2 text-xs font-mono">
              <p className="text-yellow-400 mb-1">{tc.name}</p>
              <p className="text-gray-400">in: {JSON.stringify(tc.input)}</p>
              <p className="text-green-400">out: {JSON.stringify(tc.output)}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function MessageBubble({ role, content, toolCalls, streaming }: Props) {
  const text = extractText(content)
  const hasImage = content.some(b => b.type === 'image')
  const isUser = role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-semibold mr-2 flex-shrink-0 mt-0.5">
          A
        </div>
      )}
      <div className={`max-w-[75%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        {hasImage && (
          <div className="mb-1 text-xs text-gray-400 italic">📎 photo attached</div>
        )}
        <div
          className={`px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap break-words ${
            isUser
              ? 'bg-indigo-600 text-white rounded-br-sm'
              : 'bg-gray-800 text-gray-100 rounded-bl-sm'
          }`}
        >
          {text}
          {streaming && <span className="inline-block w-1.5 h-4 bg-current ml-0.5 animate-pulse align-middle" />}
        </div>
        {!isUser && toolCalls && toolCalls.length > 0 && (
          <ToolCallsCollapse toolCalls={toolCalls} />
        )}
      </div>
    </div>
  )
}
