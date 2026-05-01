'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchCampaigns, deleteCampaign } from '@/lib/api'
import type { Campaign } from '@/lib/types'

interface Props {
  selectedId: string | null
  onSelect: (c: Campaign) => void
  onNew: () => void
}

const STATUS_COLORS: Record<string, string> = {
  draft: '#374151',
  scheduled: '#1e3a5f',
  active: '#14532d',
  sent: '#1f2937',
}

const STATUS_TEXT: Record<string, string> = {
  draft: '#9ca3af',
  scheduled: '#93c5fd',
  active: '#86efac',
  sent: '#6b7280',
}

export function CampaignList({ selectedId, onSelect, onNew }: Props) {
  const qc = useQueryClient()
  const { data: campaigns = [], isLoading } = useQuery({ queryKey: ['campaigns'], queryFn: () => fetchCampaigns() })

  const del = useMutation({
    mutationFn: deleteCampaign,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaigns'] }),
  })

  return (
    <div style={{ flex: 1 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#f9fafb' }}>Campaigns</h2>
        <button
          onClick={onNew}
          style={{ background: '#d97706', color: '#000', border: 'none', borderRadius: '6px', padding: '7px 16px', cursor: 'pointer', fontWeight: 600, fontSize: '13px' }}
        >
          + New Campaign
        </button>
      </div>

      {isLoading ? (
        <div style={{ color: '#6b7280', fontSize: '14px' }}>Loading…</div>
      ) : campaigns.length === 0 ? (
        <div style={{ background: '#111', border: '1px solid #222', borderRadius: '8px', padding: '40px', textAlign: 'center', color: '#4b5563' }}>
          No campaigns yet. Create your first one.
        </div>
      ) : (
        campaigns.map(c => (
          <div
            key={c.campaign_id}
            onClick={() => onSelect(c)}
            style={{
              background: selectedId === c.campaign_id ? '#1a1a1a' : '#111',
              border: `1px solid ${selectedId === c.campaign_id ? '#d97706' : '#222'}`,
              borderRadius: '8px',
              padding: '14px 16px',
              marginBottom: '8px',
              cursor: 'pointer',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>{c.name}</div>
                <div style={{ color: '#6b7280', fontSize: '12px', marginBottom: '6px' }}>
                  {c.channel.toUpperCase()} · {new Date(c.created_at).toLocaleDateString()}
                </div>
                {c.stats.sent_count != null && (
                  <div style={{ color: '#6b7280', fontSize: '12px' }}>
                    Sent: {c.stats.sent_count} · Opened: {c.stats.opened_count || 0} · Booked: {c.stats.booked_count || 0}
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
                <span style={{ background: STATUS_COLORS[c.status] || '#1f2937', color: STATUS_TEXT[c.status] || '#9ca3af', borderRadius: '12px', padding: '2px 10px', fontSize: '11px', fontWeight: 600 }}>
                  {c.status}
                </span>
                {c.status === 'draft' && (
                  <button
                    onClick={e => { e.stopPropagation(); del.mutate(c.campaign_id) }}
                    style={{ background: 'none', border: 'none', color: '#4b5563', cursor: 'pointer', fontSize: '12px' }}
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  )
}
