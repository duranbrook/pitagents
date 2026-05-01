'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { AppBackground } from './AppBackground'
import { SettingsDropdown } from './SettingsDropdown'
import { VoiceControlWidget } from './VoiceControlWidget'
import { pravatarUrl } from '@/lib/avatar'

const NAV_ITEMS = [
  { href: '/',           label: 'Home',      icon: <HomeIcon />,      exact: true },
  { href: '/customers',  label: 'Customers', icon: <CustomersIcon />, exact: false },
  { href: '/reports',    label: 'Reports',   icon: <ReportsIcon />,   exact: false },
  { href: '/job-cards',  label: 'Job Cards', icon: <JobCardsIcon />,  exact: false },
  { href: '/invoices',   label: 'Invoices',  icon: <InvoicesIcon />,  exact: false },
  { href: '/inspect',    label: 'Inspect',   icon: <InspectIcon />,   exact: false },
  { href: '/chat',       label: 'Chat',      icon: <ChatIcon />,      exact: false },
]

function getEmail(): string {
  if (typeof window === 'undefined') return ''
  const token = localStorage.getItem('token')
  if (!token) return ''
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return (payload.email as string) ?? ''
  } catch {
    return ''
  }
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [email, setEmail] = useState('')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const settingsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!localStorage.getItem('token')) {
      router.replace('/login')
    } else {
      setEmail(getEmail())
    }
  }, [router])

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) {
        setSettingsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  function handleLogout() {
    localStorage.removeItem('token')
    router.replace('/login')
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <AppBackground />

      <nav
        className="flex-shrink-0 h-12 flex items-center px-6 gap-1"
        style={{
          position: 'relative',
          zIndex: 10,
          background: 'rgba(0,0,0,0.35)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          borderBottom: '1px solid rgba(255,255,255,0.09)',
        }}
      >
        {/* Brand */}
        <div className="flex items-center gap-2 mr-7 flex-shrink-0">
          <div
            className="w-[26px] h-[26px] rounded-md flex items-center justify-center"
            style={{ background: 'var(--accent)' }}
          >
            <span className="text-white text-xs font-bold">A</span>
          </div>
          <span className="text-white text-sm font-bold tracking-tight">AutoShop</span>
        </div>

        {/* Nav items */}
        {NAV_ITEMS.map(item => {
          const active = item.exact ? pathname === item.href : pathname.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-1.5 px-3.5 h-12 text-[13px] font-medium border-b-2 transition-colors whitespace-nowrap"
              style={
                active
                  ? { color: '#fff', borderBottomColor: 'var(--accent)' }
                  : { color: 'rgba(255,255,255,0.48)', borderBottomColor: 'transparent' }
              }
            >
              {item.icon}
              {item.label}
            </Link>
          )
        })}

        {/* Right side */}
        <div className="ml-auto flex items-center gap-3">
          <VoiceControlWidget />
          {/* Avatar + settings dropdown */}
          <div ref={settingsRef} style={{ position: 'relative' }}>
            <button
              onClick={() => setSettingsOpen(v => !v)}
              style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', display: 'block' }}
            >
              <img
                src={pravatarUrl(email || 'default', 40)}
                alt="Settings"
                style={{
                  width: 32, height: 32, borderRadius: '50%', objectFit: 'cover',
                  border: '2px solid rgba(217,119,6,0.5)',
                  display: 'block',
                }}
              />
            </button>
            {settingsOpen && (
              <div style={{ position: 'absolute', top: 'calc(100% + 10px)', right: 0, zIndex: 100 }}>
                <SettingsDropdown email={email} onLogout={handleLogout} />
              </div>
            )}
          </div>
        </div>
      </nav>

      <main className="flex-1 min-h-0 overflow-hidden" style={{ position: 'relative', zIndex: 1 }}>
        {children}
      </main>
    </div>
  )
}

function HomeIcon() {
  return <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}><path d="M2 7l6-5 6 5v7H2V7z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/><rect x="6" y="10" width="4" height="4" rx="0.5" stroke="currentColor" strokeWidth="1.3"/></svg>
}
function CustomersIcon() {
  return <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}><circle cx="8" cy="6" r="3" stroke="currentColor" strokeWidth="1.5"/><path d="M2 13c0-3 2.5-5 6-5s6 2 6 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}
function ReportsIcon() {
  return <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}><rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" strokeWidth="1.5"/><line x1="5" y1="6" x2="11" y2="6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><line x1="5" y1="9" x2="9" y2="9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}
function InspectIcon() {
  return <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}><circle cx="8" cy="8" r="5" stroke="currentColor" strokeWidth="1.5"/><circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.5"/></svg>
}
function ChatIcon() {
  return <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}><path d="M2 3h12v8H2z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/><path d="M5 14h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}
function JobCardsIcon() {
  return <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}><rect x="1" y="3" width="4" height="10" rx="1" stroke="currentColor" strokeWidth="1.4"/><rect x="6" y="3" width="4" height="10" rx="1" stroke="currentColor" strokeWidth="1.4"/><rect x="11" y="3" width="4" height="10" rx="1" stroke="currentColor" strokeWidth="1.4"/></svg>
}
function InvoicesIcon() {
  return <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}><path d="M3 2h10v12l-2-1.5L9 14l-2-1.5L5 14l-2-1.5V2z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/><line x1="5" y1="6" x2="11" y2="6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/><line x1="5" y1="9" x2="9" y2="9" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>
}
