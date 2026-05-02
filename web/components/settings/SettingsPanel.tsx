'use client'
import { useState, useEffect } from 'react'
import { AccountSection } from './sections/AccountSection'
import { ShopProfileSection } from './sections/ShopProfileSection'
import { AppearanceSection } from './sections/AppearanceSection'
import { BookingSection } from './sections/BookingSection'
import { NotificationsSection } from './sections/NotificationsSection'
import { IntegrationsSection } from './sections/IntegrationsSection'
import { AgentsSection } from './sections/AgentsSection'

const SECTIONS = [
  { id: 'account',       label: 'Account',       emoji: '👤' },
  { id: 'shop',          label: 'Shop Profile',   emoji: '🏪' },
  { id: 'appearance',    label: 'Appearance',     emoji: '🎨' },
  { id: 'booking',       label: 'Booking',        emoji: '📅' },
  { id: 'notifications', label: 'Notifications',  emoji: '🔔' },
  { id: 'integrations',  label: 'Integrations',   emoji: '🔌' },
  { id: 'agents',        label: 'Agents & AI',    emoji: '🤖' },
] as const

type SectionId = typeof SECTIONS[number]['id']

interface Props {
  onClose: () => void
  onLogout: () => void
}

export function SettingsPanel({ onClose, onLogout }: Props) {
  const [active, setActive] = useState<SectionId>('account')

  useEffect(() => {
    function onKey(e: KeyboardEvent) { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,0,0,0.45)',
          zIndex: 49,
        }}
      />

      {/* Panel */}
      <div
        style={{
          position: 'fixed', top: 0, right: 0, bottom: 0,
          width: 420, display: 'flex',
          background: 'rgba(10,10,14,0.98)',
          borderLeft: '1px solid rgba(255,255,255,0.1)',
          boxShadow: '-20px 0 60px rgba(0,0,0,0.6)',
          zIndex: 50,
        }}
      >
        {/* Sidebar */}
        <div
          style={{
            width: 140, flexShrink: 0,
            borderRight: '1px solid rgba(255,255,255,0.07)',
            padding: '12px 8px',
            display: 'flex', flexDirection: 'column',
          }}
        >
          <div
            style={{
              fontSize: 9, textTransform: 'uppercase', letterSpacing: '.08em',
              color: 'rgba(255,255,255,0.25)', padding: '0 6px', marginBottom: 8,
            }}
          >
            Settings
          </div>

          {SECTIONS.map(s => (
            <button
              key={s.id}
              type="button"
              onClick={() => setActive(s.id)}
              style={{
                display: 'block', width: '100%', textAlign: 'left',
                padding: '6px 8px', borderRadius: 6, border: 'none', cursor: 'pointer',
                marginBottom: 2,
                background: active === s.id ? 'rgba(255,255,255,0.08)' : 'transparent',
                color: active === s.id ? 'var(--accent)' : 'rgba(255,255,255,0.45)',
                fontSize: 11, fontWeight: active === s.id ? 600 : 400,
              }}
            >
              {s.emoji} {s.label}
            </button>
          ))}

          <div style={{ marginTop: 'auto', borderTop: '1px solid rgba(255,255,255,0.07)', paddingTop: 8 }}>
            <button
              type="button"
              onClick={onLogout}
              style={{
                display: 'block', width: '100%', textAlign: 'left',
                padding: '6px 8px', borderRadius: 6, border: 'none', cursor: 'pointer',
                background: 'transparent',
                color: 'rgba(255,80,80,0.65)', fontSize: 11,
              }}
            >
              ↪ Sign out
            </button>
          </div>
        </div>

        {/* Content pane */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <div style={{ color: '#fff', fontSize: 14, fontWeight: 700 }}>
              {SECTIONS.find(s => s.id === active)?.label}
            </div>
            <button
              type="button"
              onClick={onClose}
              style={{
                background: 'none', border: 'none',
                color: 'rgba(255,255,255,0.3)', fontSize: 20,
                cursor: 'pointer', lineHeight: 1, padding: 0,
              }}
            >
              ×
            </button>
          </div>

          {active === 'account' && <AccountSection />}
          {active === 'shop' && <ShopProfileSection />}
          {active === 'appearance' && <AppearanceSection />}
          {active === 'booking' && <BookingSection />}
          {active === 'notifications' && <NotificationsSection />}
          {active === 'integrations' && <IntegrationsSection />}
          {active === 'agents' && <AgentsSection />}
        </div>
      </div>
    </>
  )
}
