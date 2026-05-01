'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppShell } from '@/components/AppShell'
import { getInvoices, getPaymentsSummary, chasePayment, recordPayment } from '@/lib/api'
import type { Invoice } from '@/lib/types'

const STATUS_COLORS: Record<string, string> = {
  pending: '#fbbf24', partial: '#60a5fa', paid: '#4ade80', overdue: '#f87171',
}

export default function PaymentsPage() {
  return (
    <AppShell>
      <PaymentsContent />
    </AppShell>
  )
}

function PaymentsContent() {
  const qc = useQueryClient()
  const [filter, setFilter] = useState<string>('unpaid')
  const [selected, setSelected] = useState<Invoice | null>(null)
  const [payAmount, setPayAmount] = useState('')
  const [payMethod, setPayMethod] = useState('cash')

  const { data: summary } = useQuery({ queryKey: ['payments-summary'], queryFn: getPaymentsSummary })
  const { data: invoices = [], isLoading } = useQuery({
    queryKey: ['invoices-payments', filter],
    queryFn: () => getInvoices(filter !== 'unpaid' ? { status: filter } : undefined),
    select: (data: Invoice[]) => filter === 'unpaid' ? data.filter(i => i.status !== 'paid') : data,
  })

  const chase = useMutation({
    mutationFn: (id: string) => chasePayment(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices-payments'] }),
  })

  const addPayment = useMutation({
    mutationFn: () => recordPayment(selected!.id, { amount: parseFloat(payAmount), method: payMethod }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invoices-payments'] })
      qc.invalidateQueries({ queryKey: ['payments-summary'] })
      setPayAmount('')
      setSelected(null)
    },
  })

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '20px 24px 0', flexShrink: 0 }}>
        <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em', marginBottom: 14 }}>Payments</div>

        <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
          {[
            { label: 'Outstanding', value: `$${(summary?.outstanding ?? 0).toFixed(0)}`, color: '#f87171' },
            { label: 'Overdue', value: `$${(summary?.overdue ?? 0).toFixed(0)}`, color: '#f87171' },
            { label: 'Collected this month', value: `$${(summary?.collected_this_month ?? 0).toFixed(0)}`, color: '#4ade80' },
            { label: 'Total invoices', value: String(summary?.total_invoices ?? 0), color: '#fff' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ flex: 1, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 9, padding: '11px 14px' }}>
              <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.03em', color }}>{value}</div>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>{label}</div>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 4 }}>
          {['unpaid', 'pending', 'partial', 'overdue', 'paid'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                height: 28, padding: '0 12px', borderRadius: 6, border: 'none', cursor: 'pointer',
                fontSize: 11, fontWeight: 600, textTransform: 'capitalize',
                background: filter === f ? 'rgba(255,255,255,0.1)' : 'transparent',
                color: filter === f ? '#fff' : 'rgba(255,255,255,0.4)',
              }}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', padding: '12px 24px 20px', gap: 16 }}>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {isLoading ? (
            <div style={{ color: 'rgba(255,255,255,0.3)' }}>Loading…</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ color: 'rgba(255,255,255,0.3)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  {['Invoice', 'Amount', 'Balance', 'Due', 'Status', ''].map(h => (
                    <th key={h || 'action'} style={{ textAlign: 'left', padding: '0 0 10px', fontWeight: 700 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {invoices.map(inv => {
                  const balance = inv.balance ?? (Number(inv.total) - Number(inv.amount_paid))
                  return (
                    <tr
                      key={inv.id}
                      style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', cursor: 'pointer' }}
                      onClick={() => setSelected(inv)}
                    >
                      <td style={{ padding: '11px 0', fontWeight: 600, color: 'rgba(255,255,255,0.85)' }}>{inv.number}</td>
                      <td style={{ padding: '11px 0' }}>${Number(inv.total).toFixed(2)}</td>
                      <td style={{ padding: '11px 0', color: balance > 0 ? '#f87171' : '#4ade80', fontWeight: 600 }}>${balance.toFixed(2)}</td>
                      <td style={{ padding: '11px 0', color: 'rgba(255,255,255,0.4)' }}>{inv.due_date ?? '—'}</td>
                      <td style={{ padding: '11px 0' }}>
                        <span style={{ padding: '2px 8px', borderRadius: 5, fontSize: 10, fontWeight: 700, background: `${STATUS_COLORS[inv.status] ?? '#94a3b8'}22`, color: STATUS_COLORS[inv.status] ?? '#94a3b8' }}>
                          {inv.status}
                        </span>
                      </td>
                      <td style={{ padding: '11px 0' }}>
                        {inv.status !== 'paid' && (
                          <button
                            onClick={e => { e.stopPropagation(); chase.mutate(inv.id) }}
                            style={{ height: 24, padding: '0 8px', borderRadius: 5, border: '1px solid rgba(217,119,6,0.3)', background: 'rgba(217,119,6,0.08)', color: '#fbbf24', fontSize: 10, fontWeight: 600, cursor: 'pointer' }}
                          >
                            Chase
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>

        {selected && (
          <div style={{ width: 260, flexShrink: 0, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 10, padding: 16 }}>
            <div style={{ fontSize: 11, fontWeight: 800, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>Record Payment</div>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{selected.number}</div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 14 }}>
              Balance: <strong style={{ color: '#f87171' }}>${(selected.balance ?? (Number(selected.total) - Number(selected.amount_paid))).toFixed(2)}</strong>
            </div>
            <input
              type="number"
              placeholder="Amount"
              value={payAmount}
              onChange={e => setPayAmount(e.target.value)}
              style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 7, padding: '8px 10px', color: '#fff', fontSize: 13, marginBottom: 8, boxSizing: 'border-box' }}
            />
            <select
              value={payMethod}
              onChange={e => setPayMethod(e.target.value)}
              style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 7, padding: '8px 10px', color: '#fff', fontSize: 13, marginBottom: 12, boxSizing: 'border-box' }}
            >
              {['cash', 'card', 'check', 'stripe'].map(m => <option key={m} value={m}>{m}</option>)}
            </select>
            <button
              onClick={() => addPayment.mutate()}
              disabled={!payAmount || addPayment.isPending}
              style={{ width: '100%', height: 34, borderRadius: 8, border: 'none', background: payAmount ? '#d97706' : 'rgba(255,255,255,0.1)', color: '#fff', fontSize: 12, fontWeight: 700, cursor: payAmount ? 'pointer' : 'default' }}
            >
              {addPayment.isPending ? 'Recording…' : 'Record'}
            </button>
            <button
              onClick={() => setSelected(null)}
              style={{ width: '100%', height: 28, borderRadius: 7, border: '1px solid rgba(255,255,255,0.08)', background: 'transparent', color: 'rgba(255,255,255,0.35)', fontSize: 11, cursor: 'pointer', marginTop: 6 }}
            >
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
