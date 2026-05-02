'use client'

import { useState } from 'react'
import Link from 'next/link'

export default function DemoPage() {
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '',
    shop_name: '', locations: '', message: '',
  })
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  function set(field: string, value: string) {
    setForm(f => ({ ...f, [field]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${API}/demo/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!res.ok) { setError('Something went wrong. Please try again.'); return }
      setSubmitted(true)
    } catch {
      setError('Could not connect to server')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '10px 14px',
    background: '#f8fafc', border: '1.5px solid #e2e8f0',
    borderRadius: 9, fontSize: 14, color: '#0f172a',
    outline: 'none', boxSizing: 'border-box', fontFamily: 'inherit',
  }
  const labelStyle: React.CSSProperties = {
    display: 'block', fontSize: 12.5, fontWeight: 600, color: '#374151', marginBottom: 6,
  }

  return (
    <div style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif", minHeight: '100vh', background: '#f8fafc' }}>

      {/* NAV */}
      <nav style={{ background: 'rgba(255,255,255,0.92)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)', borderBottom: '1px solid #f1f5f9', padding: '0 64px', height: 62, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9, fontWeight: 800, fontSize: 15, color: '#0f172a' }}>
          <div style={{ width: 30, height: 30, background: 'linear-gradient(135deg, #2563eb, #1d4ed8)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: 14 }}>A</div>
          AutoShop
        </div>
        <Link href="/" style={{ fontSize: 13, color: '#64748b', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}>← Back to home</Link>
      </nav>

      {/* MAIN */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', minHeight: 'calc(100vh - 62px)' }}>

        {/* LEFT */}
        <div style={{ background: 'linear-gradient(160deg, #0f172a 0%, #1e3a5f 100%)', padding: '72px 64px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', bottom: -80, right: -80, width: 360, height: 360, background: 'radial-gradient(circle, rgba(37,99,235,0.2) 0%, transparent 70%)', pointerEvents: 'none' }} />
          <div style={{ position: 'relative', zIndex: 1 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#60a5fa', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 20 }}>Request a Demo</div>
            <h1 style={{ fontSize: 38, fontWeight: 900, color: '#fff', lineHeight: 1.12, letterSpacing: -1, marginBottom: 18 }}>
              See AutoShop{' '}
              <em style={{ fontStyle: 'normal', color: '#60a5fa' }}>in action</em>
            </h1>
            <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.45)', lineHeight: 1.7, maxWidth: 360, marginBottom: 48 }}>
              We&apos;ll walk you through the full platform — owner dashboard, AI technician assistant, and consumer vehicle history. 30 minutes, no pressure.
            </p>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,0.3)', letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 16 }}>What to expect</div>
            {[
              { title: 'Live walkthrough', desc: "of the owner dashboard and AI agents — using your shop's real workflow" },
              { title: 'AI Technician demo', desc: 'see how inspection reports are generated in seconds' },
              { title: 'Pricing & onboarding', desc: "we'll find the right plan and get you set up fast" },
              { title: 'Q&A', desc: 'ask anything, no sales script' },
            ].map(item => (
              <div key={item.title} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 16 }}>
                <div style={{ width: 20, height: 20, borderRadius: '50%', background: 'rgba(37,99,235,0.3)', border: '1px solid rgba(37,99,235,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 1 }}>
                  <div style={{ width: 6, height: 6, background: '#60a5fa', borderRadius: '50%' }} />
                </div>
                <div style={{ fontSize: 13.5, color: 'rgba(255,255,255,0.6)', lineHeight: 1.5 }}>
                  <strong style={{ color: 'rgba(255,255,255,0.85)', fontWeight: 600 }}>{item.title}</strong> — {item.desc}
                </div>
              </div>
            ))}
          </div>
          <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.2)', position: 'relative', zIndex: 1 }}>Usually responds within 1 business day.</div>
        </div>

        {/* RIGHT */}
        <div style={{ background: '#fff', padding: '72px 64px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          {submitted ? (
            <div style={{ maxWidth: 400, textAlign: 'center' }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>🎉</div>
              <h2 style={{ fontSize: 24, fontWeight: 900, color: '#0f172a', marginBottom: 8 }}>We&apos;ll be in touch!</h2>
              <p style={{ fontSize: 15, color: '#64748b', lineHeight: 1.65 }}>Thanks for your interest. We&apos;ll reach out within 1 business day to schedule your demo.</p>
              <Link href="/" style={{ display: 'inline-block', marginTop: 24, fontSize: 14, color: '#2563eb', textDecoration: 'none', fontWeight: 600 }}>← Back to home</Link>
            </div>
          ) : (
            <div style={{ maxWidth: 400, width: '100%', margin: '0 auto' }}>
              <h2 style={{ fontSize: 26, fontWeight: 900, color: '#0f172a', letterSpacing: -0.5, marginBottom: 6 }}>Book your demo</h2>
              <p style={{ fontSize: 14, color: '#64748b', marginBottom: 32, lineHeight: 1.5 }}>Tell us a little about your shop and we&apos;ll be in touch shortly.</p>

              <form onSubmit={handleSubmit}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 18 }}>
                  <div>
                    <label style={labelStyle}>First name</label>
                    <input style={inputStyle} type="text" placeholder="Marcus" value={form.first_name} onChange={e => set('first_name', e.target.value)} required
                      onFocus={e => (e.target.style.borderColor = '#2563eb')} onBlur={e => (e.target.style.borderColor = '#e2e8f0')} />
                  </div>
                  <div>
                    <label style={labelStyle}>Last name</label>
                    <input style={inputStyle} type="text" placeholder="Thompson" value={form.last_name} onChange={e => set('last_name', e.target.value)} required
                      onFocus={e => (e.target.style.borderColor = '#2563eb')} onBlur={e => (e.target.style.borderColor = '#e2e8f0')} />
                  </div>
                </div>
                <div style={{ marginBottom: 18 }}>
                  <label style={labelStyle}>Work email</label>
                  <input style={inputStyle} type="email" placeholder="marcus@cityauto.com" value={form.email} onChange={e => set('email', e.target.value)} required
                    onFocus={e => (e.target.style.borderColor = '#2563eb')} onBlur={e => (e.target.style.borderColor = '#e2e8f0')} />
                </div>
                <div style={{ marginBottom: 18 }}>
                  <label style={labelStyle}>Shop name</label>
                  <input style={inputStyle} type="text" placeholder="City Auto Center" value={form.shop_name} onChange={e => set('shop_name', e.target.value)} required
                    onFocus={e => (e.target.style.borderColor = '#2563eb')} onBlur={e => (e.target.style.borderColor = '#e2e8f0')} />
                </div>
                <div style={{ marginBottom: 18 }}>
                  <label style={labelStyle}>Number of locations</label>
                  <select style={{ ...inputStyle, cursor: 'pointer' }} value={form.locations} onChange={e => set('locations', e.target.value)} required>
                    <option value="">Select...</option>
                    <option>1 location</option>
                    <option>2–5 locations</option>
                    <option>6–20 locations</option>
                    <option>20+ locations</option>
                  </select>
                </div>
                <div style={{ marginBottom: 18 }}>
                  <label style={labelStyle}>Anything you&apos;d like us to know? <span style={{ color: '#94a3b8', fontWeight: 400 }}>(optional)</span></label>
                  <textarea style={{ ...inputStyle, resize: 'vertical', minHeight: 90 }}
                    placeholder="e.g. We run 3 bays and want to speed up inspection write-ups..."
                    value={form.message} onChange={e => set('message', e.target.value)}
                    onFocus={e => (e.target.style.borderColor = '#2563eb')} onBlur={e => (e.target.style.borderColor = '#e2e8f0')}
                  />
                </div>

                {error && <p style={{ fontSize: 13, color: '#ef4444', marginBottom: 12 }}>{error}</p>}

                <button type="submit" disabled={loading} style={{
                  width: '100%', padding: 13, background: loading ? '#93c5fd' : '#2563eb',
                  color: '#fff', border: 'none', borderRadius: 10,
                  fontSize: 15, fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer',
                  boxShadow: '0 2px 10px rgba(37,99,235,0.3)',
                }}>
                  {loading ? 'Sending…' : 'Request Demo →'}
                </button>
                <p style={{ fontSize: 11.5, color: '#94a3b8', marginTop: 12, textAlign: 'center', lineHeight: 1.5 }}>No spam. We&apos;ll only reach out about your demo request.</p>
              </form>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
