'use client'

import { useState } from 'react'
import { AppShell } from '@/components/AppShell'
import { useAccent } from '@/components/ThemeProvider'

const PRESETS = [
  { label: 'Amber', value: '#d97706' },
  { label: 'Indigo', value: '#4f46e5' },
  { label: 'Emerald', value: '#059669' },
  { label: 'Sky', value: '#0284c7' },
  { label: 'Rose', value: '#e11d48' },
  { label: 'Violet', value: '#7c3aed' },
]

export default function SettingsPage() {
  const { accent, setAccent } = useAccent()
  const [custom, setCustom] = useState(accent)

  function applyCustom() {
    if (/^#[0-9a-fA-F]{6}$/.test(custom)) setAccent(custom)
  }

  return (
    <AppShell>
      <div className="max-w-lg mx-auto px-6 py-10">
        <h1 className="text-white text-xl font-semibold mb-1">Settings</h1>
        <p className="text-sm mb-8" style={{ color: 'rgba(255,255,255,0.4)' }}>
          Personalize your AutoShop experience.
        </p>

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
      </div>
    </AppShell>
  )
}
