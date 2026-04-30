'use client'

import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'

const NAV_ITEMS = [
  { href: '/customers', label: 'Customers', icon: '👥' },
  { href: '/reports', label: 'Reports', icon: '📋' },
  { href: '/inspect', label: 'Inspect', icon: '🔍' },
  { href: '/chat', label: 'Chat', icon: '💬' },
]

function getInitials(): string {
  if (typeof window === 'undefined') return '?'
  const token = localStorage.getItem('token')
  if (!token) return '?'
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    const email = payload.email as string
    return email ? email[0].toUpperCase() : '?'
  } catch {
    return '?'
  }
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (!localStorage.getItem('token')) {
      router.replace('/login')
    }
  }, [router])

  function handleLogout() {
    localStorage.removeItem('token')
    router.replace('/login')
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden" style={{ background: '#030712' }}>
      <nav
        className="flex-shrink-0 h-11 flex items-center px-4 gap-1"
        style={{ background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid rgba(255,255,255,0.07)' }}
      >
        <div className="flex items-center gap-2 mr-6 flex-shrink-0">
          <div className="w-6 h-6 rounded-md flex items-center justify-center" style={{ background: 'var(--accent)' }}>
            <span className="text-white text-xs font-bold">P</span>
          </div>
          <span className="text-white text-sm font-semibold">AutoShop</span>
        </div>
        {NAV_ITEMS.map(item => {
          const active = pathname.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-1.5 px-3 h-11 text-sm border-b-2 transition-colors whitespace-nowrap"
              style={active ? {
                color: 'var(--accent)',
                borderBottomColor: 'var(--accent)',
              } : {
                color: 'rgba(255,255,255,0.4)',
                borderBottomColor: 'transparent',
              }}
            >
              <span className="text-base leading-none">{item.icon}</span>
              {item.label}
            </Link>
          )
        })}
        <button
          onClick={handleLogout}
          title="Log out"
          className="ml-auto w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-colors"
          style={{ background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.6)' }}
        >
          {getInitials()}
        </button>
      </nav>
      <main className="flex-1 min-h-0 overflow-hidden">
        {children}
      </main>
    </div>
  )
}
