'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppShell } from '@/components/AppShell'
import { useAccent } from '@/components/ThemeProvider'
import { fetchAgents, fetchToolRegistry, createAgent, updateAgent, deleteAgent } from '@/lib/api'
import type { ShopAgent, ToolInfo, AgentCreate } from '@/lib/types'

const PRESETS = [
  { label: 'Amber', value: '#d97706' },
  { label: 'Indigo', value: '#4f46e5' },
  { label: 'Emerald', value: '#059669' },
  { label: 'Sky', value: '#0284c7' },
  { label: 'Rose', value: '#e11d48' },
  { label: 'Violet', value: '#7c3aed' },
]

const TABS = ['Appearance', 'Agents']

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('Appearance')

  return (
    <AppShell>
      <div className="max-w-2xl mx-auto px-6 py-10">
        <h1 className="text-white text-xl font-semibold mb-1">Settings</h1>
        <p className="text-sm mb-6" style={{ color: 'rgba(255,255,255,0.4)' }}>
          Personalize your AutoShop experience.
        </p>

        <div className="flex gap-1 mb-8" style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '0' }}>
          {TABS.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className="px-4 py-2 text-sm font-medium transition-colors"
              style={{
                color: activeTab === tab ? '#fff' : 'rgba(255,255,255,0.4)',
                background: 'none',
                border: 'none',
                borderBottom: activeTab === tab ? '2px solid var(--accent)' : '2px solid transparent',
                cursor: 'pointer',
                marginBottom: '-1px',
                padding: '8px 16px',
              }}
            >
              {tab}
            </button>
          ))}
        </div>

        {activeTab === 'Appearance' && <AppearanceTab />}
        {activeTab === 'Agents' && <AgentsTab />}
      </div>
    </AppShell>
  )
}

function AppearanceTab() {
  const { accent, setAccent } = useAccent()
  const [custom, setCustom] = useState(accent)

  function applyCustom() {
    if (/^#[0-9a-fA-F]{6}$/.test(custom)) setAccent(custom)
  }

  return (
    <section className="mb-8">
      <h2 className="text-[11px] font-semibold uppercase tracking-widest mb-4" style={{ color: 'rgba(255,255,255,0.3)' }}>
        Accent Color
      </h2>
      <div className="flex flex-wrap gap-3 mb-4">
        {PRESETS.map(p => (
          <button
            key={p.value}
            onClick={() => { setAccent(p.value); setCustom(p.value) }}
            title={p.label}
            className="w-9 h-9 rounded-lg transition-all"
            style={{
              background: p.value,
              outline: accent === p.value ? `2px solid ${p.value}` : '2px solid transparent',
              outlineOffset: '2px',
              boxShadow: accent === p.value ? '0 0 0 1px rgba(255,255,255,0.2)' : 'none',
            }}
          />
        ))}
      </div>
      <div className="flex items-center gap-3">
        <input
          type="color"
          value={custom}
          onChange={e => { setCustom(e.target.value); setAccent(e.target.value) }}
          className="w-9 h-9 rounded-lg border-0 cursor-pointer"
          style={{ background: 'transparent', padding: 0 }}
        />
        <input
          type="text"
          value={custom}
          onChange={e => setCustom(e.target.value)}
          onBlur={applyCustom}
          onKeyDown={e => e.key === 'Enter' && applyCustom()}
          placeholder="#d97706"
          className="flex-1 rounded-lg px-3 py-2 text-sm focus:outline-none"
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.1)',
            color: 'rgba(255,255,255,0.8)',
          }}
        />
        <button
          onClick={applyCustom}
          className="px-3 py-2 rounded-lg text-sm font-medium text-white transition-opacity"
          style={{ background: 'var(--accent)' }}
        >
          Apply
        </button>
      </div>
    </section>
  )
}

function AgentsTab() {
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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h2 style={{ fontSize: '15px', fontWeight: 700, color: '#f9fafb', margin: 0 }}>Agents</h2>
        <button
          onClick={() => { setCreating(true); setEditing(null) }}
          style={{ background: 'var(--accent)', color: '#000', border: 'none', borderRadius: '6px',
                   padding: '7px 14px', cursor: 'pointer', fontSize: '13px', fontWeight: 600 }}
        >
          + New Agent
        </button>
      </div>

      {agents.map(agent => (
        <div key={agent.id} style={{
          background: '#111', border: '1px solid #222', borderLeft: `3px solid ${agent.accent_color}`,
          borderRadius: '8px', padding: '12px 16px', marginBottom: '8px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div>
            <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: '14px' }}>{agent.name}</div>
            <div style={{ color: '#6b7280', fontSize: '12px', marginTop: '2px' }}>{agent.role_tagline}</div>
            <div style={{ color: '#4b5563', fontSize: '11px', marginTop: '4px' }}>
              Tools: {agent.tools.length > 0 ? agent.tools.join(', ') : 'none'}
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => { setEditing(agent); setCreating(false) }}
              style={{ background: '#1a1a1a', border: '1px solid #333', color: '#e5e7eb',
                       borderRadius: '6px', padding: '6px 12px', cursor: 'pointer', fontSize: '12px' }}
            >
              Edit
            </button>
            <button
              onClick={() => del.mutate(agent.id)}
              style={{ background: 'none', border: '1px solid #333', color: '#6b7280',
                       borderRadius: '6px', padding: '6px 12px', cursor: 'pointer', fontSize: '12px' }}
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
      const payload: AgentCreate = {
        name, role_tagline: tagline, accent_color: color,
        initials, system_prompt: prompt, tools: selectedTools,
      }
      return isNew ? createAgent(payload) : updateAgent(agent!.id, payload)
    },
    onSuccess: onSaved,
  })

  const inputStyle: React.CSSProperties = {
    background: '#1a1a1a', border: '1px solid #333', color: '#fff',
    borderRadius: '6px', padding: '8px 10px', fontSize: '13px',
    width: '100%', outline: 'none', boxSizing: 'border-box',
  }
  const labelStyle: React.CSSProperties = {
    color: '#9ca3af', fontSize: '11px', fontWeight: 600,
    textTransform: 'uppercase', letterSpacing: '0.05em',
    display: 'block', marginBottom: '5px',
  }

  const toggleTool = (id: string) =>
    setSelectedTools(prev => prev.includes(id) ? prev.filter(t => t !== id) : [...prev, id])

  return (
    <div style={{ background: '#0d0d0d', border: '1px solid #333', borderRadius: '10px',
                  padding: '20px', marginTop: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
        <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 700, color: '#f9fafb' }}>
          {isNew ? 'New Agent' : `Edit: ${agent!.name}`}
        </h3>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer', fontSize: '18px' }}>×</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
        <div>
          <label style={labelStyle}>Name</label>
          <input value={name} onChange={e => setName(e.target.value)} style={inputStyle} placeholder="e.g. Service Advisor" />
        </div>
        <div>
          <label style={labelStyle}>Initials (2-3 chars)</label>
          <input
            value={initials}
            onChange={e => setInitials(e.target.value.toUpperCase().slice(0, 3))}
            style={inputStyle}
            placeholder="SA"
            maxLength={3}
          />
        </div>
      </div>

      <div style={{ marginBottom: '12px' }}>
        <label style={labelStyle}>Role Tagline</label>
        <input value={tagline} onChange={e => setTagline(e.target.value)} style={inputStyle} placeholder="Front desk · Customer intake" />
      </div>

      <div style={{ marginBottom: '16px' }}>
        <label style={labelStyle}>Accent Color</label>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {['#d97706', '#3b82f6', '#06b6d4', '#22c55e', '#a855f7', '#ef4444', '#f59e0b'].map(c => (
            <button key={c} onClick={() => setColor(c)} style={{
              width: '24px', height: '24px', borderRadius: '50%', background: c, border: 'none',
              cursor: 'pointer', outline: color === c ? `2px solid ${c}` : 'none', outlineOffset: '2px',
            }} />
          ))}
        </div>
      </div>

      <div style={{ marginBottom: '16px' }}>
        <label style={labelStyle}>Tools</label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {tools.map(t => (
            <label key={t.id} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={selectedTools.includes(t.id)}
                onChange={() => toggleTool(t.id)}
                style={{ marginTop: '2px', flexShrink: 0 }}
              />
              <div>
                <div style={{ fontSize: '13px', color: '#e5e7eb', fontWeight: 500 }}>{t.label}</div>
                <div style={{ fontSize: '11px', color: '#6b7280' }}>{t.description}</div>
              </div>
            </label>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: '16px' }}>
        <button onClick={() => setShowPrompt(v => !v)}
          style={{ background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer',
                   fontSize: '12px', padding: 0, textDecoration: 'underline' }}>
          {showPrompt ? 'Hide' : 'Edit'} system prompt ▾
        </button>
        {showPrompt && (
          <textarea
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            rows={6}
            style={{ ...inputStyle, marginTop: '8px', resize: 'vertical', fontFamily: 'monospace', fontSize: '12px' }}
          />
        )}
      </div>

      <button
        onClick={() => save.mutate()}
        disabled={save.isPending || !name || !initials}
        style={{ background: 'var(--accent)', color: '#000', border: 'none', borderRadius: '6px',
                 padding: '9px 20px', cursor: 'pointer', fontWeight: 700, fontSize: '13px',
                 opacity: (save.isPending || !name || !initials) ? 0.5 : 1 }}
      >
        {save.isPending ? 'Saving…' : isNew ? 'Create Agent' : 'Save Changes'}
      </button>
    </div>
  )
}
