'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppBackground } from '@/components/AppBackground'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('owner@shop.com')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    let navigated = false
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/auth/login`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        },
      )
      if (!res.ok) { setError('Invalid email or password'); return }
      const data = await res.json()
      localStorage.setItem('token', data.access_token)
      navigated = true
      router.push('/chat')
    } catch {
      setError('Could not connect to server')
    } finally {
      if (!navigated) setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <AppBackground />

      <div
        className="w-full max-w-sm glass-panel"
        style={{ padding: '32px 28px', position: 'relative', zIndex: 1 }}
      >
        {/* Logo */}
        <div className="flex items-center gap-2.5 mb-8">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center"
            style={{ background: 'var(--accent)' }}
          >
            <span className="text-white font-bold text-lg">A</span>
          </div>
          <span className="text-white text-xl font-bold tracking-tight">AutoShop</span>
        </div>

        <h1 className="text-white text-2xl font-bold mb-1.5 tracking-tight">Sign in</h1>
        <p className="text-sm mb-8" style={{ color: 'rgba(255,255,255,0.44)' }}>
          Access your shop&apos;s AI team
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm mb-1.5" style={{ color: 'rgba(255,255,255,0.65)' }} htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoComplete="email"
              className="w-full rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none"
              style={{
                background: 'rgba(255,255,255,0.07)',
                border: '1px solid rgba(255,255,255,0.12)',
              }}
              onFocus={e => (e.target.style.borderColor = 'var(--accent)')}
              onBlur={e => (e.target.style.borderColor = 'rgba(255,255,255,0.12)')}
            />
          </div>

          <div>
            <label className="block text-sm mb-1.5" style={{ color: 'rgba(255,255,255,0.65)' }} htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              className="w-full rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none"
              style={{
                background: 'rgba(255,255,255,0.07)',
                border: '1px solid rgba(255,255,255,0.12)',
              }}
              onFocus={e => (e.target.style.borderColor = 'var(--accent)')}
              onBlur={e => (e.target.style.borderColor = 'rgba(255,255,255,0.12)')}
            />
          </div>

          {error && <p className="text-sm" style={{ color: '#f87171' }}>{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg py-2.5 text-sm font-semibold text-white disabled:opacity-50 transition-opacity"
            style={{
              background: 'var(--accent)',
              boxShadow: '0 2px 14px var(--accent-glow)',
            }}
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="text-xs mt-6 text-center" style={{ color: 'rgba(255,255,255,0.28)' }}>
          Use <span className="font-mono">owner@shop.com</span> / <span className="font-mono">testpass</span>
        </p>
      </div>
    </div>
  )
}
