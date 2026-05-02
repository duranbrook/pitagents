'use client'
import { useState } from 'react'
import { useAccent } from '@/components/ThemeProvider'
import { useTheme, BgTheme } from '@/hooks/useTheme'

const ACCENT_PRESETS = [
  { label: 'Amber',   value: '#d97706' },
  { label: 'Indigo',  value: '#4f46e5' },
  { label: 'Emerald', value: '#059669' },
  { label: 'Sky',     value: '#0284c7' },
  { label: 'Rose',    value: '#e11d48' },
  { label: 'Violet',  value: '#7c3aed' },
]

const BG_THEMES: { id: BgTheme; label: string; swatch: string }[] = [
  { id: 'dark',  label: 'Dark',  swatch: 'linear-gradient(135deg,#080808,#1c1c1c)' },
  { id: 'moody', label: 'Moody', swatch: 'linear-gradient(135deg,rgba(10,8,5,0.9),rgba(30,20,10,0.7))' },
  { id: 'vivid', label: 'Vivid', swatch: 'linear-gradient(135deg,rgba(220,210,190,0.6),rgba(180,170,150,0.4))' },
]

const sectionHeadingStyle: React.CSSProperties = {
  fontSize: 10, fontWeight: 600, textTransform: 'uppercase',
  letterSpacing: '.07em', color: 'rgba(255,255,255,0.3)', marginBottom: 10,
}

export function AppearanceSection() {
  const { accent, setAccent } = useAccent()
  const { theme, setTheme } = useTheme()
  const [custom, setCustom] = useState(accent)

  function applyCustom() {
    if (/^#[0-9a-fA-F]{6}$/.test(custom)) setAccent(custom)
  }

  return (
    <div>
      <div style={sectionHeadingStyle}>Accent Color</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
        {ACCENT_PRESETS.map(p => (
          <button
            key={p.value}
            type="button"
            onClick={() => { setAccent(p.value); setCustom(p.value) }}
            title={p.label}
            style={{
              width: 30, height: 30, borderRadius: 8, border: 'none', cursor: 'pointer',
              background: p.value,
              outline: accent === p.value ? `2px solid ${p.value}` : '2px solid transparent',
              outlineOffset: 2,
              boxShadow: accent === p.value ? '0 0 0 1px rgba(255,255,255,0.2)' : 'none',
            }}
          />
        ))}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 24 }}>
        <input
          type="color"
          value={custom}
          onChange={e => { setCustom(e.target.value); setAccent(e.target.value) }}
          style={{ width: 30, height: 30, borderRadius: 6, border: 'none', cursor: 'pointer', padding: 0, background: 'transparent' }}
        />
        <input
          type="text"
          value={custom}
          onChange={e => setCustom(e.target.value)}
          onBlur={applyCustom}
          onKeyDown={e => e.key === 'Enter' && applyCustom()}
          placeholder="#d97706"
          style={{
            flex: 1, background: 'rgba(255,255,255,0.05)',
            border: '1px solid rgba(255,255,255,0.09)', borderRadius: 6,
            padding: '6px 10px', fontSize: 12, color: 'rgba(255,255,255,0.85)', outline: 'none',
          }}
        />
        <button
          type="button"
          onClick={applyCustom}
          style={{
            background: 'var(--accent)', color: '#000', border: 'none',
            borderRadius: 6, padding: '6px 12px', fontSize: 12, fontWeight: 700, cursor: 'pointer',
          }}
        >
          Apply
        </button>
      </div>

      <div style={{ height: 1, background: 'rgba(255,255,255,0.07)', marginBottom: 20 }} />

      <div style={sectionHeadingStyle}>Background Theme</div>
      <div style={{ display: 'flex', gap: 8 }}>
        {BG_THEMES.map(t => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTheme(t.id)}
            style={{
              flex: 1, padding: '8px 4px', borderRadius: 8, cursor: 'pointer',
              textAlign: 'center', fontSize: 11, fontWeight: 500,
              color: theme === t.id ? 'var(--accent)' : 'rgba(255,255,255,0.55)',
              border: theme === t.id ? '1px solid var(--accent)' : '1px solid rgba(255,255,255,0.09)',
              background: theme === t.id ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.03)',
            }}
          >
            <div style={{ width: '100%', height: 22, borderRadius: 4, marginBottom: 4, background: t.swatch }} />
            {t.label}
          </button>
        ))}
      </div>
    </div>
  )
}
