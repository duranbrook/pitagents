'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppShell } from '@/components/AppShell'
import { getPLSummary, getExpenses, createExpense, deleteExpense, syncToQuickBooks } from '@/lib/api'
import type { Expense } from '@/lib/types'

const PERIODS = [
  { value: 'mtd', label: 'MTD' },
  { value: 'qtd', label: 'QTD' },
  { value: 'ytd', label: 'YTD' },
  { value: '1m', label: '30 days' },
]

const EXPENSE_CATEGORIES = ['Parts', 'Labor', 'Utilities', 'Equipment', 'Misc']

export default function AccountingPage() {
  return (
    <AppShell>
      <AccountingContent />
    </AppShell>
  )
}

function AccountingContent() {
  const qc = useQueryClient()
  const [period, setPeriod] = useState('mtd')
  const [tab, setTab] = useState('Expenses')
  const [showAddExpense, setShowAddExpense] = useState(false)
  const [newExpense, setNewExpense] = useState({ description: '', amount: '', category: 'Misc', vendor: '', expense_date: new Date().toISOString().slice(0, 10) })

  const { data: pl } = useQuery({ queryKey: ['pl', period], queryFn: () => getPLSummary(period) })
  const { data: expenses = [], isLoading: expLoading } = useQuery<Expense[]>({ queryKey: ['expenses'], queryFn: () => getExpenses() })

  const addExpense = useMutation({
    mutationFn: () => createExpense({ ...newExpense, amount: parseFloat(newExpense.amount) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['expenses'] })
      qc.invalidateQueries({ queryKey: ['pl'] })
      setShowAddExpense(false)
      setNewExpense({ description: '', amount: '', category: 'Misc', vendor: '', expense_date: new Date().toISOString().slice(0, 10) })
    },
  })

  const removeExpense = useMutation({
    mutationFn: (id: string) => deleteExpense(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['expenses'] }); qc.invalidateQueries({ queryKey: ['pl'] }) },
  })

  const syncQB = useMutation({
    mutationFn: syncToQuickBooks,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['expenses'] }),
  })

  const categoryTotals = EXPENSE_CATEGORIES.map(cat => ({
    cat,
    total: expenses.filter((e: Expense) => e.category === cat).reduce((s: number, e: Expense) => s + e.amount, 0),
  })).filter(({ total }) => total > 0)

  const maxCatTotal = Math.max(...categoryTotals.map(c => c.total), 1)

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '20px 24px 0', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>Accounting</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ display: 'flex', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 7, overflow: 'hidden' }}>
              {PERIODS.map(p => (
                <button key={p.value} onClick={() => setPeriod(p.value)} style={{ height: 30, padding: '0 12px', border: 'none', cursor: 'pointer', fontSize: 11, fontWeight: 600, background: period === p.value ? 'rgba(255,255,255,0.12)' : 'transparent', color: period === p.value ? '#fff' : 'rgba(255,255,255,0.45)' }}>
                  {p.label}
                </button>
              ))}
            </div>
            <button
              onClick={() => syncQB.mutate()}
              disabled={syncQB.isPending}
              style={{ height: 30, padding: '0 12px', borderRadius: 7, border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.6)', fontSize: 11, fontWeight: 600, cursor: 'pointer' }}
            >
              {syncQB.isPending ? 'Syncing…' : 'Sync to QuickBooks'}
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
          {[
            { label: 'Revenue', value: `$${(pl?.revenue ?? 0).toFixed(0)}`, color: '#4ade80' },
            { label: 'Expenses', value: `$${(pl?.expenses ?? 0).toFixed(0)}`, color: '#f87171' },
            { label: 'Net Profit', value: `$${(pl?.net_profit ?? 0).toFixed(0)}`, color: (pl?.net_profit ?? 0) >= 0 ? '#4ade80' : '#f87171' },
            { label: 'Outstanding A/R', value: `$${(pl?.outstanding_ar ?? 0).toFixed(0)}`, color: '#fbbf24' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ flex: 1, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 9, padding: '11px 14px' }}>
              <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.03em', color }}>{value}</div>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>{label}</div>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 4 }}>
          {['Expenses', 'P&L Report'].map(t => (
            <button key={t} onClick={() => setTab(t)} style={{ height: 28, padding: '0 12px', borderRadius: 6, border: 'none', cursor: 'pointer', fontSize: 11, fontWeight: 600, background: tab === t ? 'rgba(255,255,255,0.1)' : 'transparent', color: tab === t ? '#fff' : 'rgba(255,255,255,0.4)' }}>
              {t}
            </button>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', padding: '12px 24px 20px', gap: 16 }}>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {tab === 'Expenses' && (
            <>
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 10 }}>
                <button onClick={() => setShowAddExpense(s => !s)} style={{ height: 30, padding: '0 12px', borderRadius: 7, border: 'none', background: '#d97706', color: '#fff', fontSize: 11, fontWeight: 600, cursor: 'pointer' }}>
                  + Add Expense
                </button>
              </div>

              {showAddExpense && (
                <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 10, padding: 14, marginBottom: 14 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
                    {[
                      { key: 'description', label: 'Description', type: 'text' },
                      { key: 'amount', label: 'Amount ($)', type: 'number' },
                      { key: 'vendor', label: 'Vendor', type: 'text' },
                      { key: 'expense_date', label: 'Date', type: 'date' },
                    ].map(({ key, label, type }) => (
                      <div key={key}>
                        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginBottom: 4 }}>{label}</div>
                        <input
                          type={type}
                          value={(newExpense as Record<string, string>)[key]}
                          onChange={e => setNewExpense(f => ({ ...f, [key]: e.target.value }))}
                          style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, padding: '7px 10px', color: '#fff', fontSize: 12, boxSizing: 'border-box' }}
                        />
                      </div>
                    ))}
                  </div>
                  <div style={{ marginBottom: 10 }}>
                    <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginBottom: 4 }}>Category</div>
                    <select value={newExpense.category} onChange={e => setNewExpense(f => ({ ...f, category: e.target.value }))} style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, padding: '7px 10px', color: '#fff', fontSize: 12 }}>
                      {EXPENSE_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <button onClick={() => addExpense.mutate()} disabled={!newExpense.description || !newExpense.amount || addExpense.isPending} style={{ height: 30, padding: '0 14px', borderRadius: 7, border: 'none', background: '#d97706', color: '#fff', fontSize: 11, fontWeight: 600, cursor: 'pointer' }}>
                    Save
                  </button>
                </div>
              )}

              {expLoading ? (
                <div style={{ color: 'rgba(255,255,255,0.3)' }}>Loading…</div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ color: 'rgba(255,255,255,0.3)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                      {['Date', 'Description', 'Category', 'Vendor', 'Amount', 'QB', ''].map(h => (
                        <th key={h || 'del'} style={{ textAlign: 'left', padding: '0 0 10px', fontWeight: 700 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {expenses.map((exp: Expense) => (
                      <tr key={exp.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '10px 0', color: 'rgba(255,255,255,0.45)', fontSize: 11 }}>{exp.expense_date}</td>
                        <td style={{ padding: '10px 0', color: 'rgba(255,255,255,0.85)', fontWeight: 600 }}>{exp.description}</td>
                        <td style={{ padding: '10px 0', color: 'rgba(255,255,255,0.5)' }}>{exp.category}</td>
                        <td style={{ padding: '10px 0', color: 'rgba(255,255,255,0.4)', fontSize: 11 }}>{exp.vendor ?? '—'}</td>
                        <td style={{ padding: '10px 0', fontWeight: 600 }}>${exp.amount.toFixed(2)}</td>
                        <td style={{ padding: '10px 0', fontSize: 11, color: exp.qb_synced ? '#4ade80' : 'rgba(255,255,255,0.2)' }}>{exp.qb_synced ? '✓ Synced' : '—'}</td>
                        <td style={{ padding: '10px 0' }}>
                          <button onClick={() => removeExpense.mutate(exp.id)} style={{ fontSize: 11, color: 'rgba(255,255,255,0.25)', background: 'none', border: 'none', cursor: 'pointer' }}>×</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </>
          )}

          {tab === 'P&L Report' && pl && (
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 10, padding: 16 }}>
              <div style={{ fontSize: 11, fontWeight: 800, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 14 }}>Income vs Expenses</div>
              {[
                { label: 'Revenue', value: pl.revenue, color: '#4ade80' },
                { label: 'Total Expenses', value: pl.expenses, color: '#f87171' },
                { label: 'Net Profit', value: pl.net_profit, color: pl.net_profit >= 0 ? '#4ade80' : '#f87171' },
                { label: 'Outstanding A/R', value: pl.outstanding_ar, color: '#fbbf24' },
              ].map(({ label, value, color }) => (
                <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: 14 }}>
                  <span style={{ color: 'rgba(255,255,255,0.65)' }}>{label}</span>
                  <span style={{ fontWeight: 700, color }}>${value.toFixed(2)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ width: 220, flexShrink: 0 }}>
          <div style={{ fontSize: 10, fontWeight: 800, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>Expense Breakdown</div>
          {categoryTotals.length === 0 ? (
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.2)' }}>No expenses yet</div>
          ) : categoryTotals.map(({ cat, total }) => (
            <div key={cat} style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                <span style={{ color: 'rgba(255,255,255,0.6)' }}>{cat}</span>
                <span style={{ fontWeight: 600, color: '#f87171' }}>${total.toFixed(0)}</span>
              </div>
              <div style={{ height: 6, background: 'rgba(255,255,255,0.06)', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${(total / maxCatTotal) * 100}%`, background: '#d97706', borderRadius: 3 }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
