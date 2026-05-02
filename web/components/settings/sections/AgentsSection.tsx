'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchAgents, fetchToolRegistry, createAgent, updateAgent, deleteAgent } from '@/lib/api'
import type { ShopAgent, ToolInfo, AgentCreate } from '@/lib/types'

export function AgentsSection() {
  const qc = useQueryClient()
  const { data: agents = [] } = useQuery({ queryKey: ['agents'], queryFn: fetchAgents })
  const { data: tools = [] } = useQuery({ queryKey: ['tool-registry'], queryFn: fetchToolRegistry })
  const [editing, setEditing] = useState<ShopAgent | null>(null)
  const [creating, setCreating] = useState(false)

  const del = useMutation({
    mutationFn: deleteAgent,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agents'] }),
  })

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#f9fafb' }}>Agents</span>
        <button
          type="button"
          onClick={() => { setCreating(true); setEditing(null) }}
          style={{
            background: 'var(--accent)', color: '#000', border: 'none', borderRadius: 6,
            padding: '6px 12px', cursor: 'pointer', fontSize: 12, fontWeight: 600,
          }}
        >
          + New Agent
        </button>
      </div>

      {agents.map(agent => (
        <div key={agent.id} style={{
          background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
          borderLeft: `3px solid ${agent.accent_color}`,
          borderRadius: 8, padding: '10px 14px', marginBottom: 8,
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div>
            <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: 13 }}>{agent.name}</div>
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 11, marginTop: 2 }}>{agent.role_tagline}</div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              type="button"
              onClick={() => { setEditing(agent); setCreating(false) }}
              style={{
                background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)',
                color: 'rgba(255,255,255,0.75)', borderRadius: 5, padding: '5px 10px',
                cursor: 'pointer', fontSize: 11,
              }}
            >
              Edit
            </button>
            <button
              type="button"
              onClick={() => del.mutate(agent.id)}
              style={{
                background: 'none', border: '1px solid rgba(255,255,255,0.08)',
                color: 'rgba(255,255,255,0.4)', borderRadius: 5, padding: '5px 10px',
                cursor: 'pointer', fontSize: 11,
              }}
            >
              Delete
            </button>
          </div>
        </div>
      ))}

      {(creating || editing) && (
        <AgentForm
          agent={editing}
          tools={tools}
          onClose={() => { setCreating(false); setEditing(null) }}
          onSaved={() => { qc.invalidateQueries({ queryKey: ['agents'] }); setCreating(false); setEditing(null) }}
        />
      )}
    </div>
  )
}

function AgentForm({
  agent, tools, onClose, onSaved,
}: {
  agent: ShopAgent | null
  tools: ToolInfo[]
  onClose: () => void
  onSaved: () => void
}) {
  const isNew = !agent
  const [name, setName] = useState(agent?.name ?? '')
  const [tagline, setTagline] = useState(agent?.role_tagline ?? '')
  const [color, setColor] = useState(agent?.accent_color ?? '#d97706')
  const [initials, setInitials] = useState(agent?.initials ?? '')
  const [prompt, setPrompt] = useState(agent?.system_prompt ?? '')
  const [selectedTools, setSelectedTools] = useState<string[]>(agent?.tools ?? [])
  const [showPrompt, setShowPrompt] = useState(false)

  const save = useMutation({
    mutationFn: () => {
      const payload: AgentCreate = { name, role_tagline: tagline, accent_color: color, initials, system_prompt: prompt, tools: selectedTools }
      return isNew ? createAgent(payload) : updateAgent(agent!.id, payload)
    },
    onSuccess: onSaved,
  })

  const inputStyle: React.CSSProperties = {
    background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.09)',
    color: '#fff', borderRadius: 6, padding: '7px 10px', fontSize: 12,
    width: '100%', outline: 'none', boxSizing: 'border-box',
  }
  const labelStyle: React.CSSProperties = {
    color: 'rgba(255,255,255,0.3)', fontSize: 10, fontWeight: 600,
    textTransform: 'uppercase', letterSpacing: '.05em', display: 'block', marginBottom: 4,
  }
  const toggleTool = (id: string) =>
    setSelectedTools(prev => prev.includes(id) ? prev.filter(t => t !== id) : [...prev, id])

  return (
    <div style={{
      background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: 10, padding: 16, marginTop: 12,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 14 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#f9fafb' }}>
          {isNew ? 'New Agent' : `Edit: ${agent!.name}`}
        </span>
        <button type="button" onClick={onClose} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)', cursor: 'pointer', fontSize: 18 }}>×</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
        <div>
          <label htmlFor="agent-name" style={labelStyle}>Name</label>
          <input id="agent-name" value={name} onChange={e => setName(e.target.value)} style={inputStyle} placeholder="Service Advisor" />
        </div>
        <div>
          <label htmlFor="agent-initials" style={labelStyle}>Initials</label>
          <input id="agent-initials" value={initials} onChange={e => setInitials(e.target.value.toUpperCase().slice(0, 3))} style={inputStyle} placeholder="SA" maxLength={3} />
        </div>
      </div>

      <div style={{ marginBottom: 10 }}>
        <label htmlFor="agent-tagline" style={labelStyle}>Role Tagline</label>
        <input id="agent-tagline" value={tagline} onChange={e => setTagline(e.target.value)} style={inputStyle} placeholder="Front desk · Customer intake" />
      </div>

      <div style={{ marginBottom: 14 }}>
        <div style={labelStyle}>Accent Color</div>
        <div style={{ display: 'flex', gap: 6 }}>
          {['#d97706', '#3b82f6', '#06b6d4', '#22c55e', '#a855f7', '#ef4444'].map(c => (
            <button type="button" key={c} onClick={() => setColor(c)} style={{ width: 22, height: 22, borderRadius: '50%', background: c, border: 'none', cursor: 'pointer', outline: color === c ? `2px solid ${c}` : 'none', outlineOffset: 2 }} />
          ))}
        </div>
      </div>

      <div style={{ marginBottom: 14 }}>
        <div style={labelStyle}>Tools</div>
        {tools.map(t => (
          <label key={t.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, cursor: 'pointer', marginBottom: 6 }}>
            <input type="checkbox" checked={selectedTools.includes(t.id)} onChange={() => toggleTool(t.id)} style={{ marginTop: 2 }} />
            <div>
              <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.8)', fontWeight: 500 }}>{t.label}</div>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>{t.description}</div>
            </div>
          </label>
        ))}
      </div>

      <div style={{ marginBottom: 14 }}>
        <button type="button" onClick={() => setShowPrompt(v => !v)} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', fontSize: 11, padding: 0, textDecoration: 'underline' }}>
          {showPrompt ? 'Hide' : 'Edit'} system prompt
        </button>
        {showPrompt && (
          <textarea value={prompt} onChange={e => setPrompt(e.target.value)} rows={5}
            style={{ ...inputStyle, marginTop: 6, resize: 'vertical', fontFamily: 'monospace', fontSize: 11 }} />
        )}
      </div>

      <button
        type="button"
        onClick={() => save.mutate()}
        disabled={save.isPending || !name || !initials}
        style={{
          background: 'var(--accent)', color: '#000', border: 'none', borderRadius: 6,
          padding: '8px 18px', cursor: 'pointer', fontWeight: 700, fontSize: 12,
          opacity: (save.isPending || !name || !initials) ? 0.5 : 1,
        }}
      >
        {save.isPending ? 'Saving…' : isNew ? 'Create Agent' : 'Save Changes'}
      </button>
    </div>
  )
}
