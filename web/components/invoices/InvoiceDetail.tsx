'use client'
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { Invoice } from '@/lib/types'
import { sendPaymentLink, recordPayment } from '@/lib/api'
import FinancingModal from './FinancingModal'

interface Props {
  invoice: Invoice
  onClose: () => void
  financingThreshold: number
}

const STATUS_COLORS: Record<string, string> = {
  pending: '#fbbf24', partial: '#60a5fa', paid: '#4ade80', overdue: '#f87171',
}

export default function InvoiceDetail({ invoice, onClose, financingThreshold }: Props) {
  const qc = useQueryClient()
  const [showPayment, setShowPayment] = useState(false)
  const [showFinancing, setShowFinancing] = useState(false)
  const [payAmount, setPayAmount] = useState('')
  const [payMethod, setPayMethod] = useState('cash')

  const sendLink = useMutation({
    mutationFn: () => sendPaymentLink(invoice.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices'] }),
  })

  const addPayment = useMutation({
    mutationFn: () => recordPayment(invoice.id, { amount: parseFloat(payAmount), method: payMethod }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invoices'] })
      setShowPayment(false)
      setPayAmount('')
    },
  })

  const statusColor = STATUS_COLORS[invoice.status] ?? '#94a3b8'

  return (
    <div style={{ position: 'fixed', right: 0, top: 0, bottom: 0, width: 440, background: '#141414', borderLeft: '1px solid rgba(255,255,255,0.08)', display: 'flex', flexDirection: 'column', zIndex: 50 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '18px 20px', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
        <div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginBottom: 2 }}>{invoice.number}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 16, fontWeight: 700 }}>Invoice</span>
            <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 5, background: `${statusColor}22`, color: statusColor }}>{invoice.status}</span>
          </div>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)', fontSize: 20, cursor: 'pointer' }}>×</button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
        {/* Totals */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 20 }}>
          {[
            { label: 'Total', value: `$${Number(invoice.total).toFixed(2)}` },
            { label: 'Balance', value: `$${Number(invoice.balance).toFixed(2)}`, color: invoice.balance > 0 ? '#f87171' : '#4ade80' },
            { label: 'Paid', value: `$${Number(invoice.amount_paid).toFixed(2)}`, color: '#4ade80' },
            { label: 'Due', value: invoice.due_date ?? '—' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 9, padding: '10px 14px' }}>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>{label}</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: color ?? '#fff', marginTop: 2 }}>{value}</div>
            </div>
          ))}
        </div>

        {/* Line items */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8 }}>Line Items</div>
          {invoice.line_items.map((item, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: 13 }}>
              <span style={{ color: 'rgba(255,255,255,0.7)' }}>{item.description}</span>
              <span style={{ color: 'rgba(255,255,255,0.9)', fontWeight: 600 }}>${Number(item.total).toFixed(2)}</span>
            </div>
          ))}
        </div>

        {/* Record payment form */}
        {showPayment && (
          <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 10, padding: 14, marginBottom: 14 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,0.5)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Record Payment</div>
            <input
              type="number"
              placeholder="Amount"
              value={payAmount}
              onChange={e => setPayAmount(e.target.value)}
              style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, padding: '7px 10px', color: '#fff', fontSize: 13, marginBottom: 8, boxSizing: 'border-box' }}
            />
            <select
              value={payMethod}
              onChange={e => setPayMethod(e.target.value)}
              style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, padding: '7px 10px', color: '#fff', fontSize: 13, marginBottom: 10 }}
            >
              {['cash', 'card', 'check', 'stripe'].map(m => <option key={m} value={m}>{m}</option>)}
            </select>
            <button onClick={() => addPayment.mutate()} disabled={!payAmount || addPayment.isPending} style={{ width: '100%', height: 32, borderRadius: 7, border: 'none', background: '#d97706', color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
              {addPayment.isPending ? 'Recording…' : 'Record'}
            </button>
          </div>
        )}
      </div>

      {/* Footer */}
      {invoice.status !== 'paid' && (
        <div style={{ padding: '14px 20px', borderTop: '1px solid rgba(255,255,255,0.07)', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <button onClick={() => sendLink.mutate()} style={{ height: 36, borderRadius: 8, border: 'none', background: '#d97706', color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
            {sendLink.isPending ? 'Sending…' : 'Send Payment Link'}
          </button>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => setShowPayment(!showPayment)} style={{ flex: 1, height: 32, borderRadius: 7, border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.65)', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
              Record Payment
            </button>
            {Number(invoice.balance) >= financingThreshold && (
              <button onClick={() => setShowFinancing(true)} style={{ flex: 1, height: 32, borderRadius: 7, border: '1px solid rgba(168,85,247,0.3)', background: 'rgba(168,85,247,0.08)', color: '#c084fc', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                Offer Financing
              </button>
            )}
          </div>
        </div>
      )}

      {showFinancing && <FinancingModal invoice={invoice} onClose={() => setShowFinancing(false)} />}
    </div>
  )
}
