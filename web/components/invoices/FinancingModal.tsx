'use client'
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import type { Invoice } from '@/lib/types'
import { sendFinancingLink } from '@/lib/api'

interface Props {
  invoice: Invoice
  onClose: () => void
}

const PROVIDERS = [
  { id: 'synchrony', name: 'Synchrony Car Care', desc: 'Major provider, up to 60 months' },
  { id: 'wisetack', name: 'Wisetack', desc: 'Buy-now-pay-later, instant approval' },
]

export default function FinancingModal({ invoice, onClose }: Props) {
  const [selected, setSelected] = useState('')
  const [sent, setSent] = useState(false)

  const send = useMutation({
    mutationFn: () => sendFinancingLink(invoice.id, selected),
    onSuccess: () => setSent(true),
  })

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
      <div style={{ background: '#1a1a1a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: 24, width: 380 }}>
        {sent ? (
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>✓</div>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 6 }}>Financing link sent</div>
            <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.5)', marginBottom: 20 }}>Application link sent to customer via SMS.</div>
            <button onClick={onClose} style={{ height: 36, padding: '0 20px', borderRadius: 8, border: 'none', background: '#d97706', color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>Done</button>
          </div>
        ) : (
          <>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>Offer Financing</div>
            <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.5)', marginBottom: 16 }}>
              Balance: <strong style={{ color: '#f87171' }}>${Number(invoice.balance).toFixed(2)}</strong>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
              {PROVIDERS.map(p => (
                <div
                  key={p.id}
                  onClick={() => setSelected(p.id)}
                  style={{
                    padding: '12px 14px', borderRadius: 9, cursor: 'pointer',
                    border: `1px solid ${selected === p.id ? '#d97706' : 'rgba(255,255,255,0.1)'}`,
                    background: selected === p.id ? 'rgba(217,119,6,0.08)' : 'rgba(255,255,255,0.02)',
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 2 }}>{p.name}</div>
                  <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)' }}>{p.desc}</div>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={onClose} style={{ flex: 1, height: 36, borderRadius: 8, border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.6)', fontSize: 13, cursor: 'pointer' }}>Cancel</button>
              <button
                onClick={() => send.mutate()}
                disabled={!selected || send.isPending}
                style={{ flex: 1, height: 36, borderRadius: 8, border: 'none', background: selected ? '#d97706' : 'rgba(255,255,255,0.1)', color: '#fff', fontSize: 13, fontWeight: 600, cursor: selected ? 'pointer' : 'default' }}
              >
                {send.isPending ? 'Sending…' : 'Send Link'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
