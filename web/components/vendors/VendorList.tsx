'use client'
import type { Vendor } from '@/lib/types'

const CATEGORY_COLORS: Record<string, string> = {
  Parts: '#60a5fa', Equipment: '#c084fc', Utilities: '#4ade80', Services: '#fbbf24',
}

interface Props {
  vendors: Vendor[]
  selectedId: string | null
  onSelect: (v: Vendor) => void
}

export default function VendorList({ vendors, selectedId, onSelect }: Props) {
  return (
    <div style={{ width: 280, flexShrink: 0, borderRight: '1px solid rgba(255,255,255,0.07)', overflowY: 'auto', padding: '14px 0' }}>
      {vendors.map(v => (
        <div
          key={v.id}
          onClick={() => onSelect(v)}
          style={{
            padding: '12px 20px', cursor: 'pointer',
            background: v.id === selectedId ? 'rgba(255,255,255,0.06)' : 'transparent',
            borderRight: v.id === selectedId ? '2px solid #d97706' : '2px solid transparent',
          }}
          onMouseEnter={e => { if (v.id !== selectedId) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)' }}
          onMouseLeave={e => { if (v.id !== selectedId) (e.currentTarget as HTMLElement).style.background = 'transparent' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 3 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.88)' }}>{v.name}</div>
            <span style={{
              fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4,
              background: `${CATEGORY_COLORS[v.category] ?? '#94a3b8'}22`,
              color: CATEGORY_COLORS[v.category] ?? '#94a3b8',
            }}>
              {v.category}
            </span>
          </div>
          {v.phone && <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginBottom: 4 }}>{v.phone}</div>}
          <div style={{ display: 'flex', gap: 12, fontSize: 11, color: 'rgba(255,255,255,0.35)' }}>
            <span>YTD ${Number(v.ytd_spend).toFixed(0)}</span>
            <span>{v.order_count} orders</span>
          </div>
        </div>
      ))}
    </div>
  )
}
