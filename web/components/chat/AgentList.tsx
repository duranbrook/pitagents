'use client'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchAgents } from '@/lib/api'
import type { ShopAgent } from '@/lib/types'

interface Props {
  selectedId: string
  onSelect: (id: string) => void
  lastMessages: Record<string, string>
}

export function AgentList({ selectedId, onSelect, lastMessages }: Props) {
  const { data: agents = [], isLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: fetchAgents,
  })

  return (
    <div
      className="flex flex-col h-full flex-shrink-0 glass-panel"
      style={{ width: 208, borderRadius: 0, borderTop: 'none', borderBottom: 'none', borderLeft: 'none' }}
    >
      <div className="px-4 pt-5 pb-3">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-400">
          Agents
        </p>
      </div>
      <div className="flex-1 overflow-y-auto px-2 space-y-0.5">
        {isLoading && (
          <p className="text-[11px] px-2 py-3 text-gray-400">Loading…</p>
        )}
        {agents.map(agent => (
          <AgentRow
            key={agent.id}
            agent={agent}
            active={selectedId === agent.id}
            lastMessage={lastMessages[agent.id]}
            onSelect={() => onSelect(agent.id)}
          />
        ))}
      </div>
      <div className="p-3 border-t border-gray-100">
        <a
          href="/settings"
          className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[11px] transition-colors text-gray-400 hover:text-gray-600"
        >
          ⚙ Settings
        </a>
      </div>
    </div>
  )
}

const TOOL_LABELS: Record<string, string> = {
  vin_lookup: 'VIN Lookup',
  quote_builder: 'Quotes & Estimates',
  parts_search: 'Parts Search',
  shop_data: 'Customer & Vehicle Records',
}

function AgentRow({
  agent, active, lastMessage, onSelect,
}: {
  agent: ShopAgent
  active: boolean
  lastMessage?: string
  onSelect: () => void
}) {
  const [hovered, setHovered] = useState(false)
  const [tooltipTimer, setTooltipTimer] = useState<ReturnType<typeof setTimeout> | null>(null)
  const [showTooltip, setShowTooltip] = useState(false)

  const handleMouseEnter = () => {
    setHovered(true)
    const t = setTimeout(() => setShowTooltip(true), 400)
    setTooltipTimer(t)
  }

  const handleMouseLeave = () => {
    setHovered(false)
    setShowTooltip(false)
    if (tooltipTimer) clearTimeout(tooltipTimer)
  }

  const capabilities = agent.tools.map(t => TOOL_LABELS[t] ?? t)

  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={onSelect}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        className="w-full flex items-center gap-2.5 py-2 rounded-lg text-left transition-all"
        style={active ? {
          background: `color-mix(in srgb, ${agent.accent_color} 10%, #fff)`,
          borderLeft: `2px solid ${agent.accent_color}`,
          paddingLeft: '8px',
          paddingRight: '10px',
        } : {
          borderLeft: '2px solid transparent',
          paddingLeft: '8px',
          paddingRight: '10px',
          background: hovered ? '#f9fafb' : 'transparent',
        }}
      >
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center text-[11px] font-bold flex-shrink-0"
          style={{
            background: active ? agent.accent_color : '#f3f4f6',
            border: '1px solid #e5e7eb',
            color: active ? '#fff' : '#6b7280',
          }}
        >
          {agent.initials}
        </div>
        <div className="min-w-0">
          <p className="text-[12px] font-medium text-gray-900 truncate">{agent.name}</p>
          <p className="text-[10px] truncate text-gray-400">
            {lastMessage ?? agent.role_tagline}
          </p>
        </div>
      </button>

      {showTooltip && (
        <div
          style={{
            position: 'absolute',
            left: '100%',
            top: 0,
            marginLeft: '8px',
            zIndex: 50,
            background: '#ffffff',
            border: `1px solid ${agent.accent_color}44`,
            borderRadius: '8px',
            padding: '10px 12px',
            width: '180px',
            boxShadow: '0 4px 16px rgba(0,0,0,0.1)',
            pointerEvents: 'none',
          }}
        >
          <p className="text-[10px] font-semibold uppercase tracking-widest"
            style={{ color: agent.accent_color, marginBottom: '6px' }}>
            Can help with
          </p>
          {capabilities.length > 0
            ? capabilities.map(cap => (
                <p key={cap} className="text-[11px] text-gray-700 mb-1">· {cap}</p>
              ))
            : <p className="text-[11px] text-gray-400">General assistance</p>
          }
        </div>
      )}
    </div>
  )
}
