'use client'

import { useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Script from 'next/script'
import Link from 'next/link'

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: object) => void
          renderButton: (element: HTMLElement, config: object) => void
        }
      }
    }
  }
}

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const googleBtnRef = useRef<HTMLDivElement>(null)

  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  function initGoogle() {
    if (!window.google || !googleBtnRef.current) return
    window.google.accounts.id.initialize({
      client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '',
      callback: handleGoogleCredential,
    })
    window.google.accounts.id.renderButton(googleBtnRef.current, {
      theme: 'outline',
      size: 'large',
      width: 380,
      text: 'continue_with',
    })
  }

  async function handleGoogleCredential(response: { credential: string }) {
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${API}/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: response.credential }),
      })
      if (!res.ok) {
        const data = await res.json()
        setError(data.detail || 'Google sign-in failed')
        setLoading(false)
        return
      }
      const data = await res.json()
      localStorage.setItem('token', data.access_token)
      router.push('/chat')
    } catch {
      setError('Could not connect to server')
      setLoading(false)
    }
  }

  async function handleEmailSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    let navigated = false
    try {
      const res = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
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
    <>
      <Script
        src="https://accounts.google.com/gsi/client"
        onLoad={initGoogle}
        strategy="afterInteractive"
      />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', minHeight: '100vh', fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif" }}>

        {/* LEFT */}
        <div style={{
          background: 'linear-gradient(160deg, #0f172a 0%, #1e3a5f 100%)',
          padding: '60px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          position: 'relative',
          overflow: 'hidden',
        }}>
          <div style={{ position: 'absolute', bottom: -100, right: -100, width: 400, height: 400, background: 'radial-gradient(circle, rgba(37,99,235,0.25) 0%, transparent 70%)', pointerEvents: 'none' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 34, height: 34, background: 'linear-gradient(135deg,#2563eb,#1d4ed8)', borderRadius: 9, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 900, fontSize: 16 }}>A</div>
            <span style={{ fontSize: 17, fontWeight: 800, color: '#fff', letterSpacing: -0.3 }}>AutoShop</span>
          </div>

          <div style={{ position: 'relative', zIndex: 1 }}>
            <h1 style={{ fontSize: 36, fontWeight: 900, color: '#fff', lineHeight: 1.15, letterSpacing: -1, marginBottom: 16 }}>
              Your shop&apos;s{' '}
              <em style={{ fontStyle: 'normal', color: '#60a5fa' }}>AI team</em>
              <br />is waiting.
            </h1>
            <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.45)', lineHeight: 1.65, maxWidth: 340 }}>
              Sign in to access your owner dashboard, AI technician assistant, and full shop intelligence — in one place.
            </p>
          </div>

          <div style={{ display: 'flex', gap: 32, position: 'relative', zIndex: 1 }}>
            {[{ val: '2×', label: 'Faster inspections' }, { val: '40%', label: 'Less admin' }, { val: '$0', label: 'For customers' }].map(s => (
              <div key={s.label}>
                <div style={{ fontSize: 22, fontWeight: 900, color: '#fff' }}>{s.val}</div>
                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* RIGHT */}
        <div style={{ background: '#fff', padding: '60px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ maxWidth: 380, width: '100%', margin: '0 auto' }}>
            <h2 style={{ fontSize: 26, fontWeight: 900, color: '#0f172a', letterSpacing: -0.5, marginBottom: 6 }}>Sign in</h2>
            <p style={{ fontSize: 14, color: '#64748b', marginBottom: 32 }}>Welcome back. Sign in to your shop account.</p>

            <div ref={googleBtnRef} style={{ marginBottom: 20 }} />

            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
              <div style={{ flex: 1, borderTop: '1px solid #f1f5f9' }} />
              <span style={{ fontSize: 12, color: '#94a3b8', fontWeight: 500, whiteSpace: 'nowrap' }}>or sign in with email</span>
              <div style={{ flex: 1, borderTop: '1px solid #f1f5f9' }} />
            </div>

            <form onSubmit={handleEmailSubmit}>
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 12.5, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Email</label>
                <input
                  type="email" value={email} onChange={e => setEmail(e.target.value)} required
                  placeholder="you@yourshop.com"
                  style={{ width: '100%', padding: '10px 14px', background: '#f8fafc', border: '1.5px solid #e2e8f0', borderRadius: 9, fontSize: 14, color: '#0f172a', outline: 'none', boxSizing: 'border-box' }}
                  onFocus={e => (e.target.style.borderColor = '#2563eb')}
                  onBlur={e => (e.target.style.borderColor = '#e2e8f0')}
                />
              </div>
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 12.5, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Password</label>
                <input
                  type="password" value={password} onChange={e => setPassword(e.target.value)} required
                  placeholder="••••••••"
                  style={{ width: '100%', padding: '10px 14px', background: '#f8fafc', border: '1.5px solid #e2e8f0', borderRadius: 9, fontSize: 14, color: '#0f172a', outline: 'none', boxSizing: 'border-box' }}
                  onFocus={e => (e.target.style.borderColor = '#2563eb')}
                  onBlur={e => (e.target.style.borderColor = '#e2e8f0')}
                />
              </div>

              {error && <p style={{ fontSize: 13, color: '#ef4444', marginBottom: 12 }}>{error}</p>}

              <button
                type="submit" disabled={loading}
                style={{ width: '100%', padding: 12, background: loading ? '#93c5fd' : '#2563eb', color: '#fff', border: 'none', borderRadius: 10, fontSize: 14, fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer', boxShadow: '0 2px 8px rgba(37,99,235,0.3)' }}
              >
                {loading ? 'Signing in…' : 'Sign in'}
              </button>
            </form>

            <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 20, textAlign: 'center' }}>
              Don&apos;t have an account?{' '}
              <Link href="/demo" style={{ color: '#2563eb', fontWeight: 600, textDecoration: 'none' }}>Request a demo</Link>
            </p>
          </div>
        </div>

      </div>
    </>
  )
}
