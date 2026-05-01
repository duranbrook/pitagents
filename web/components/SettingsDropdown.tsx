'use client'

import { useTheme, BgTheme } from '@/hooks/useTheme'
import { pravatarUrl } from '@/lib/avatar'

interface Props {
  email: string
  onLogout: () => void
}

const THEMES: { id: BgTheme; label: string; swatch: string }[] = [
  { id: 'dark',    label: 'Dark',    swatch: 'linear-gradient(135deg,#080808,#1c1c1c)' },
  { id: 'moody',   label: 'Moody',   swatch: 'linear-gradient(135deg,rgba(10,8,5,0.9),rgba(30,20,10,0.7))' },
  { id: 'vivid',   label: 'Vivid',   swatch: 'linear-gradient(135deg,rgba(220,210,190,0.6),rgba(180,170,150,0.4))' },
]

export function SettingsDropdown({ email, onLogout }: Props) {
  const { theme, setTheme } = useTheme()

  return (
    <div
      style={{
        width: 255,
        background: 'rgba(12,12,15,0.95)',
        backdropFilter: 'blur(28px)',
        WebkitBackdropFilter: 'blur(28px)',
        border: '1px solid rgba(255,255,255,0.11)',
        borderRadius: 12,
        overflow: 'hidden',
        boxShadow: '0 20px 50px rgba(0,0,0,0.55)',
      }}
    >
      {/* Profile header */}
      <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 10, borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
        <img
          src={pravatarUrl(email, 40)}
          alt=""
          style={{ width: 36, height: 36, borderRadius: '50%', objectFit: 'cover', border: '2px solid rgba(217,119,6,0.4)' }}
        />
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>
            {email.split('@')[0]}
          </div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.38)', marginTop: 1 }}>{email}</div>
        </div>
      </div>

      {/* Background theme */}
      <div style={{ padding: '10px 16px 8px' }}>
        <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.07em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.35)', marginBottom: 8 }}>
          Background Theme
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {THEMES.map(t => (
            <button
              key={t.id}
              onClick={() => setTheme(t.id)}
              style={{
                flex: 1, padding: '7px 4px', borderRadius: 8, cursor: 'pointer',
                textAlign: 'center', fontSize: 11, fontWeight: 500,
                color: theme === t.id ? '#fbbf24' : 'rgba(255,255,255,0.55)',
                border: theme === t.id ? '1px solid #d97706' : '1px solid rgba(255,255,255,0.09)',
                background: theme === t.id ? 'rgba(217,119,6,0.14)' : 'rgba(255,255,255,0.04)',
                transition: 'all 0.15s',
              }}
            >
              <div style={{ width: '100%', height: 22, borderRadius: 4, marginBottom: 4, background: t.swatch }} />
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ height: 1, background: 'rgba(255,255,255,0.07)' }} />

      {/* Nav rows */}
      {[
        { label: 'Profile & Account', icon: <PersonIcon /> },
        { label: 'Shop Settings', icon: <SettingsIcon /> },
      ].map(row => (
        <div
          key={row.label}
          style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 16px', cursor: 'pointer', fontSize: 13, color: 'rgba(255,255,255,0.60)' }}
        >
          {row.icon}
          {row.label}
        </div>
      ))}

      <div style={{ height: 1, background: 'rgba(255,255,255,0.07)' }} />

      {/* Sign out */}
      <div style={{ padding: '4px 0 8px' }}>
        <button
          onClick={onLogout}
          style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 16px', width: '100%', cursor: 'pointer', fontSize: 13, color: 'rgba(255,80,80,0.75)', background: 'none', border: 'none' }}
        >
          <SignOutIcon />
          Sign out
        </button>
      </div>
    </div>
  )
}

function PersonIcon() {
  return <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="6" r="3" stroke="currentColor" strokeWidth="1.5"/><path d="M2 13c0-3 2.5-5 6-5s6 2 6 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}
function SettingsIcon() {
  return <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" strokeWidth="1.5"/><line x1="5" y1="8" x2="11" y2="8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><line x1="8" y1="5" x2="8" y2="11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}
function SignOutIcon() {
  return <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M6 3H3v10h3M11 5l3 3-3 3M14 8H6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
}
