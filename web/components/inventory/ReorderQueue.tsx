'use client'
import type { InventoryItem } from '@/lib/types'

interface Props { items: InventoryItem[] }

export default function ReorderQueue({ items }: Props) {
  const reorderItems = items.filter(i => i.stock_status !== 'ok')
  return (
    <div style={{ width: 240, flexShrink: 0, borderLeft: '1px solid rgba(255,255,255,0.07)', padding: '16px 16px', overflowY: 'auto' }}>
      <div style={{ fontSize: 10, fontWeight: 800, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>
        Reorder Queue ({reorderItems.length})
      </div>
      {reorderItems.length === 0 ? (
        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.2)', textAlign: 'center', padding: '16px 0' }}>All stock OK</div>
      ) : reorderItems.map(item => (
        <div key={item.id} style={{ padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'rgba(255,255,255,0.8)', marginBottom: 2 }}>{item.name}</div>
          <div style={{ fontSize: 10, color: item.stock_status === 'out' ? '#f87171' : '#fbbf24', marginBottom: 6 }}>
            {item.stock_status === 'out' ? 'Out of stock' : `Low: ${item.quantity} left`}
          </div>
          <button
            onClick={() => {
              const sku = item.sku ? `&item=${encodeURIComponent(item.sku)}` : ''
              window.open(`https://shop.partstech.com/search?q=${encodeURIComponent(item.name)}${sku}`, '_blank')
            }}
            style={{
              width: '100%', height: 26, borderRadius: 6, border: '1px solid rgba(255,255,255,0.12)',
              background: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.55)', fontSize: 10,
              fontWeight: 600, cursor: 'pointer',
            }}
          >
            Order via PartsTech
          </button>
        </div>
      ))}
    </div>
  )
}
