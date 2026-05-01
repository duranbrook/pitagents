'use client'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { Invoice } from '@/lib/types'
import { getInvoices, getShopSettings } from '@/lib/api'
import InvoiceDetail from '@/components/invoices/InvoiceDetail'

const STATUS_COLORS: Record<string, string> = {
  pending: '#fbbf24', partial: '#60a5fa', paid: '#4ade80', overdue: '#f87171',
}
const FILTERS = ['all', 'pending', 'partial', 'paid', 'overdue']

export default function InvoicesPage() {
  const [filter, setFilter] = useState('all')
  const [selected, setSelected] = useState<Invoice | null>(null)

  const { data: invoices = [], isLoading } = useQuery({
    queryKey: ['invoices', filter],
    queryFn: () => getInvoices(filter !== 'all' ? { status: filter } : undefined),
  })
  const { data: allInvoices = [] } = useQuery({
    queryKey: ['invoices', 'all'],
    queryFn: () => getInvoices(),
  })
  const { data: settings } = useQuery({ queryKey: ['shop-settings'], queryFn: getShopSettings })
  const financingThreshold = parseFloat(settings?.financing_threshold ?? '500')

  const now = new Date()
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)

  const outstanding = allInvoices
    .filter(i => i.status !== 'paid' && i.status !== 'void')
    .reduce((s, i) => s + Number(i.balance), 0)
  const collected = allInvoices
    .filter(i => i.status === 'paid' && new Date(i.created_at) >= startOfMonth)
    .reduce((s, i) => s + Number(i.amount_paid), 0)

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '20px 24px 0', flexShrink: 0 }}>
        <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em', marginBottom: 14 }}>Invoices</div>

        {/* Stats */}
        <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
          {[
            { label: 'Outstanding', value: `$${outstanding.toFixed(0)}`, color: '#f87171' },
            { label: 'Collected this month', value: `$${collected.toFixed(0)}`, color: '#4ade80' },
            { label: 'Total invoices', value: String(allInvoices.length), color: '#fff' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ flex: 1, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 9, padding: '11px 14px' }}>
              <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.03em', color }}>{value}</div>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>{label}</div>
            </div>
          ))}
        </div>

        {/* Filter tabs */}
        <div style={{ display: 'flex', gap: 4, marginBottom: 0 }}>
          {FILTERS.map(f => (
            <button key={f} onClick={() => setFilter(f)} style={{
              height: 28, padding: '0 12px', borderRadius: 6, border: 'none', cursor: 'pointer',
              fontSize: 11, fontWeight: 600, textTransform: 'capitalize',
              background: filter === f ? 'rgba(255,255,255,0.1)' : 'transparent',
              color: filter === f ? '#fff' : 'rgba(255,255,255,0.4)',
            }}>{f}</button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 24px 20px' }}>
        {isLoading ? (
          <div style={{ color: 'rgba(255,255,255,0.3)', padding: '20px 0' }}>Loading…</div>
        ) : invoices.length === 0 ? (
          <div style={{ color: 'rgba(255,255,255,0.25)', padding: '40px 0', textAlign: 'center', fontSize: 13 }}>No invoices yet</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ color: 'rgba(255,255,255,0.3)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                {['Number', 'Total', 'Balance', 'Status', 'Date'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '0 0 10px', fontWeight: 700 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {invoices.map(inv => (
                <tr key={inv.id} onClick={() => setSelected(inv)} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', cursor: 'pointer' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)' }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent' }}>
                  <td style={{ padding: '12px 0', fontWeight: 600 }}>{inv.number}</td>
                  <td style={{ padding: '12px 0' }}>${Number(inv.total).toFixed(2)}</td>
                  <td style={{ padding: '12px 0', color: inv.balance > 0 ? '#f87171' : '#4ade80' }}>${Number(inv.balance).toFixed(2)}</td>
                  <td style={{ padding: '12px 0' }}>
                    <span style={{ padding: '2px 8px', borderRadius: 5, fontSize: 10, fontWeight: 700, background: `${STATUS_COLORS[inv.status] ?? '#94a3b8'}22`, color: STATUS_COLORS[inv.status] ?? '#94a3b8' }}>
                      {inv.status}
                    </span>
                  </td>
                  <td style={{ padding: '12px 0', color: 'rgba(255,255,255,0.4)' }}>{new Date(inv.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {selected && (
        <InvoiceDetail
          key={selected.id}
          invoice={selected}
          onClose={() => setSelected(null)}
          financingThreshold={financingThreshold}
        />
      )}
    </div>
  )
}
