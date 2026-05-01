'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { Vendor } from '@/lib/types'
import { getVendorOrders, receivePurchaseOrder } from '@/lib/api'

interface Props { vendor: Vendor }

const PO_STATUS_COLORS: Record<string, string> = {
  pending: '#fbbf24', ordered: '#60a5fa', received: '#4ade80',
}

export default function VendorDetail({ vendor }: Props) {
  const qc = useQueryClient()
  const { data: orders = [] } = useQuery({
    queryKey: ['vendor-orders', vendor.id],
    queryFn: () => getVendorOrders(vendor.id),
  })

  const receive = useMutation({
    mutationFn: (poId: string) => receivePurchaseOrder(vendor.id, poId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['vendor-orders', vendor.id] }),
  })

  const contactFields = [
    { label: 'Phone', value: vendor.phone },
    { label: 'Email', value: vendor.email },
    { label: 'Website', value: vendor.website, isLink: true },
    { label: 'Address', value: vendor.address },
    { label: 'Rep / Contact', value: vendor.rep_name ? `${vendor.rep_name}${vendor.rep_phone ? ` · ${vendor.rep_phone}` : ''}` : null },
    { label: 'Account #', value: vendor.account_number },
  ]

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>{vendor.name}</div>
        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>{vendor.category} vendor</div>
      </div>

      <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 10, padding: 16, marginBottom: 20 }}>
        <div style={{ fontSize: 10, fontWeight: 800, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>Contact</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px 20px' }}>
          {contactFields.map(({ label, value, isLink }) => (
            <div key={label}>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', marginBottom: 2 }}>{label}</div>
              {value ? (
                isLink ? (
                  <a href={value} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, color: '#60a5fa', textDecoration: 'none' }}>{value}</a>
                ) : (
                  <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.75)' }}>{value}</div>
                )
              ) : (
                <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.2)' }}>—</div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        {[
          { label: 'YTD Spend', value: `$${Number(vendor.ytd_spend).toFixed(0)}` },
          { label: 'Orders', value: String(vendor.order_count) },
          { label: 'Last Order', value: vendor.last_order_at ? new Date(vendor.last_order_at).toLocaleDateString() : '—' },
        ].map(({ label, value }) => (
          <div key={label} style={{ flex: 1, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 9, padding: '10px 14px' }}>
            <div style={{ fontSize: 16, fontWeight: 700 }}>{value}</div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>{label}</div>
          </div>
        ))}
      </div>

      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
          <div style={{ fontSize: 10, fontWeight: 800, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Purchase Orders</div>
          <button style={{ height: 26, padding: '0 10px', borderRadius: 6, border: 'none', background: '#d97706', color: '#fff', fontSize: 10, fontWeight: 600, cursor: 'pointer' }}>
            + New Order
          </button>
        </div>
        {orders.length === 0 ? (
          <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.2)', padding: '12px 0' }}>No orders yet</div>
        ) : orders.map(po => (
          <div key={po.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600 }}>{po.po_number}</div>
              <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{po.items.length} items · ${Number(po.total).toFixed(2)}</div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 5, background: `${PO_STATUS_COLORS[po.status] ?? '#94a3b8'}22`, color: PO_STATUS_COLORS[po.status] ?? '#94a3b8' }}>
                {po.status}
              </span>
              {po.status !== 'received' && (
                <button
                  onClick={() => receive.mutate(po.id)}
                  disabled={receive.isPending}
                  style={{ height: 24, padding: '0 8px', borderRadius: 5, border: '1px solid rgba(74,222,128,0.3)', background: 'rgba(74,222,128,0.06)', color: '#4ade80', fontSize: 10, fontWeight: 600, cursor: 'pointer' }}
                >
                  Mark received
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
