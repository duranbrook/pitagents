'use client'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AppShell } from '@/components/AppShell'
import FilterBar from '@/components/inventory/FilterBar'
import ReorderQueue from '@/components/inventory/ReorderQueue'
import type { InventoryItem } from '@/lib/types'
import { getInventory } from '@/lib/api'

const STOCK_COLORS: Record<InventoryItem['stock_status'], string> = { ok: '#4ade80', low: '#fbbf24', out: '#f87171' }

export default function InventoryPage() {
  return (
    <AppShell>
      <InventoryContent />
    </AppShell>
  )
}

function InventoryContent() {
  const [filters, setFilters] = useState({ search: '', categories: [] as string[], stockStatuses: [] as string[] })

  const { data: allItems = [], isLoading } = useQuery({
    queryKey: ['inventory', filters.search, filters.categories, filters.stockStatuses],
    queryFn: () => getInventory({
      search: filters.search || undefined,
      category: filters.categories.length === 1 ? filters.categories[0] : undefined,
      stock_status: filters.stockStatuses.length === 1 ? filters.stockStatuses[0] : undefined,
    }),
  })

  const items = allItems.filter(item =>
    (filters.categories.length === 0 || filters.categories.includes(item.category)) &&
    (filters.stockStatuses.length === 0 || filters.stockStatuses.includes(item.stock_status))
  )

  const activePills = [
    ...filters.categories.map(c => ({ type: 'category', value: c })),
    ...filters.stockStatuses.map(s => ({ type: 'stock', value: s })),
  ]

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '20px 24px 14px', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>Inventory</div>
          <button style={{ height: 32, padding: '0 14px', borderRadius: 7, border: 'none', background: '#d97706', color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
            + Add Part
          </button>
        </div>
        <FilterBar filters={filters} onChange={setFilters} />
        {activePills.length > 0 && (
          <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
            {activePills.map(p => (
              <span
                key={`${p.type}-${p.value}`}
                onClick={() => {
                  if (p.type === 'category') setFilters(f => ({ ...f, categories: f.categories.filter(c => c !== p.value) }))
                  else setFilters(f => ({ ...f, stockStatuses: f.stockStatuses.filter(s => s !== p.value) }))
                }}
                style={{ display: 'inline-flex', alignItems: 'center', gap: 4, height: 22, padding: '0 8px', borderRadius: 11, fontSize: 11, fontWeight: 600, background: 'rgba(217,119,6,0.1)', border: '1px solid rgba(217,119,6,0.2)', color: '#fbbf24', cursor: 'pointer' }}
              >
                {p.value} ×
              </span>
            ))}
          </div>
        )}
      </div>

      <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 24px 20px' }}>
          {isLoading ? (
            <div style={{ color: 'rgba(255,255,255,0.3)' }}>Loading…</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ color: 'rgba(255,255,255,0.3)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  {['Part', 'SKU', 'Category', 'Stock', 'Reorder At', 'Cost', 'Sell', 'Margin'].map(h => (
                    <th key={h} style={{ textAlign: 'left', padding: '0 0 10px', fontWeight: 700 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map(item => (
                  <tr key={item.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <td style={{ padding: '11px 0', fontWeight: 600, color: 'rgba(255,255,255,0.88)' }}>{item.name}</td>
                    <td style={{ padding: '11px 0', color: 'rgba(255,255,255,0.4)', fontSize: 11 }}>{item.sku ?? '—'}</td>
                    <td style={{ padding: '11px 0', color: 'rgba(255,255,255,0.55)' }}>{item.category}</td>
                    <td style={{ padding: '11px 0' }}>
                      <span style={{ color: STOCK_COLORS[item.stock_status], fontWeight: 700 }}>{item.quantity}</span>
                    </td>
                    <td style={{ padding: '11px 0', color: 'rgba(255,255,255,0.4)' }}>{item.reorder_at}</td>
                    <td style={{ padding: '11px 0', color: 'rgba(255,255,255,0.6)' }}>${Number(item.cost_price).toFixed(2)}</td>
                    <td style={{ padding: '11px 0', color: 'rgba(255,255,255,0.8)' }}>${Number(item.sell_price).toFixed(2)}</td>
                    <td style={{ padding: '11px 0', color: item.margin_pct >= 30 ? '#4ade80' : item.margin_pct >= 15 ? '#fbbf24' : '#f87171' }}>
                      {Number(item.margin_pct).toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <ReorderQueue items={allItems} />
      </div>
    </div>
  )
}
