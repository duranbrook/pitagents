'use client'

interface Agent {
  id: string
  name: string
  role: string
  color: string
  initials: string
  lastMessage?: string
}

const AGENTS: Agent[] = [
  { id: 'assistant', name: 'Assistant', role: 'General assistant', color: '#4f46e5', initials: 'A' },
  { id: 'tom', name: 'Tom', role: 'Technician AI', color: '#059669', initials: 'T' },
]

interface Props {
  selectedId: string
  onSelect: (id: string) => void
  lastMessages: Record<string, string>
}

export function AgentList({ selectedId, onSelect, lastMessages }: Props) {
  return (
    <div className="flex flex-col h-full bg-gray-900 w-56 border-r border-gray-800">
      <div className="px-4 pt-5 pb-3">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Team</p>
      </div>
      <div className="flex-1 overflow-y-auto px-2">
        {AGENTS.map(agent => (
          <button
            key={agent.id}
            onClick={() => onSelect(agent.id)}
            aria-current={selectedId === agent.id ? 'true' : undefined}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 text-left transition-colors ${
              selectedId === agent.id ? 'bg-gray-700' : 'hover:bg-gray-800'
            }`}
          >
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-semibold flex-shrink-0"
              style={{ background: agent.color }}
            >
              {agent.initials}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-white truncate">{agent.name}</p>
              <p className="text-xs text-gray-400 truncate">
                {lastMessages[agent.id] ?? agent.role}
              </p>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
