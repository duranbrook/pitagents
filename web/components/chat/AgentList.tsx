'use client'

interface Agent {
  id: string
  name: string
  role: string
  initials: string
}

const AGENTS: Agent[] = [
  { id: 'assistant', name: 'Assistant', role: 'VIN lookup · Repair quotes', initials: 'A' },
  { id: 'tom', name: 'Tom', role: 'Technician AI', initials: 'T' },
]

interface Props {
  selectedId: string
  onSelect: (id: string) => void
  lastMessages: Record<string, string>
}

export function AgentList({ selectedId, onSelect, lastMessages }: Props) {
  return (
    <div
      className="flex flex-col h-full flex-shrink-0 glass-panel"
      style={{ width: 208, borderRadius: 0, borderTop: 'none', borderBottom: 'none', borderLeft: 'none' }}
    >
      <div className="px-4 pt-5 pb-3">
        <p className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: 'rgba(255,255,255,0.3)' }}>
          Agents
        </p>
      </div>
      <div className="flex-1 overflow-y-auto px-2 space-y-0.5">
        {AGENTS.map(agent => {
          const active = selectedId === agent.id
          return (
            <button
              key={agent.id}
              onClick={() => onSelect(agent.id)}
              className="w-full flex items-center gap-2.5 py-2 rounded-lg text-left transition-all"
              style={active ? {
                background: 'color-mix(in srgb, var(--accent) 12%, transparent)',
                borderLeft: '2px solid var(--accent)',
                paddingLeft: '8px',
                paddingRight: '10px',
              } : {
                borderLeft: '2px solid transparent',
                paddingLeft: '8px',
                paddingRight: '10px',
              }}
              onMouseEnter={e => {
                if (!active) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)'
              }}
              onMouseLeave={e => {
                if (!active) (e.currentTarget as HTMLElement).style.background = 'transparent'
              }}
            >
              <div
                className="w-7 h-7 rounded-lg flex items-center justify-center text-[11px] font-bold flex-shrink-0"
                style={{
                  background: active ? 'var(--accent)' : 'rgba(255,255,255,0.08)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: active ? '#fff' : 'rgba(255,255,255,0.6)',
                }}
              >
                {agent.initials}
              </div>
              <div className="min-w-0">
                <p className="text-[12px] font-medium text-white truncate">{agent.name}</p>
                <p className="text-[10px] truncate" style={{ color: 'rgba(255,255,255,0.35)' }}>
                  {lastMessages[agent.id] ?? agent.role}
                </p>
              </div>
            </button>
          )
        })}
      </div>
      <div className="p-3" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <a
          href="/settings"
          className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[11px] transition-colors"
          style={{ color: 'rgba(255,255,255,0.35)' }}
          onMouseEnter={e => (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.7)'}
          onMouseLeave={e => (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.35)'}
        >
          ⚙ Settings
        </a>
      </div>
    </div>
  )
}
