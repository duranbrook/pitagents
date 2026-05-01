'use client'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AppShell } from '@/components/AppShell'
import VendorList from '@/components/vendors/VendorList'
import VendorDetail from '@/components/vendors/VendorDetail'
import type { Vendor } from '@/lib/types'
import { getVendors } from '@/lib/api'

export default function VendorsPage() {
  return (
    <AppShell>
      <VendorsContent />
    </AppShell>
  )
}

function VendorsContent() {
  const [selectedVendor, setSelectedVendor] = useState<Vendor | null>(null)
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null)

  const { data: vendors = [], isLoading } = useQuery({
    queryKey: ['vendors', categoryFilter],
    queryFn: () => getVendors(categoryFilter ? { category: categoryFilter } : undefined),
  })

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px 14px', flexShrink: 0 }}>
        <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>Vendors</div>
        <div style={{ display: 'flex', gap: 8 }}>
          {([null, 'Parts', 'Equipment', 'Utilities', 'Services'] as const).map(cat => (
            <button
              key={cat ?? 'all'}
              onClick={() => setCategoryFilter(cat)}
              style={{
                height: 28, padding: '0 10px', borderRadius: 6, border: 'none', cursor: 'pointer', fontSize: 11, fontWeight: 600,
                background: categoryFilter === cat ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.04)',
                color: categoryFilter === cat ? '#fff' : 'rgba(255,255,255,0.45)',
              }}
            >
              {cat ?? 'All'}
            </button>
          ))}
          <button style={{ height: 28, padding: '0 12px', borderRadius: 6, border: 'none', background: '#d97706', color: '#fff', fontSize: 11, fontWeight: 600, cursor: 'pointer' }}>
            + Add Vendor
          </button>
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {isLoading ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)' }}>Loading…</div>
        ) : vendors.length === 0 ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.25)', fontSize: 13 }}>No vendors yet</div>
        ) : (
          <>
            <VendorList vendors={vendors} selectedId={selectedVendor?.id ?? null} onSelect={setSelectedVendor} />
            {selectedVendor ? (
              <VendorDetail key={selectedVendor.id} vendor={selectedVendor} />
            ) : (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.2)', fontSize: 13 }}>
                Select a vendor
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
