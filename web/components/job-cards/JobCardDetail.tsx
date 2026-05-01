'use client'
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { JobCard, JobCardColumn, ServiceLine } from '@/lib/types'
import { updateJobCard, createInvoiceFromJobCard } from '@/lib/api'

interface Props {
  card: JobCard
  columns: JobCardColumn[]
  onClose: () => void
}

export default function JobCardDetail({ card, columns, onClose }: Props) {
  const qc = useQueryClient()
  const [notes, setNotes] = useState(card.notes ?? '')
  const [services, setServices] = useState<ServiceLine[]>(card.services ?? [])
  const [columnId, setColumnId] = useState(card.column_id ?? '')

  const save = useMutation({
    mutationFn: () => updateJobCard(card.id, { notes, services, column_id: columnId } as Partial<JobCard>),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['job-cards'] }),
  })

  const createInvoice = useMutation({
    mutationFn: () => createInvoiceFromJobCard(card.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['invoices'] }); onClose() },
  })

  return (
    <div style={{
      position: 'fixed', right: 0, top: 0, bottom: 0, width: 420,
      background: '#141414', borderLeft: '1px solid rgba(255,255,255,0.08)',
      display: 'flex', flexDirection: 'column', zIndex: 50,
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '18px 20px', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
        <div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginBottom: 2 }}>{card.number}</div>
          <div style={{ fontSize: 16, fontWeight: 700 }}>Job Card</div>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)', fontSize: 20, cursor: 'pointer' }}>×</button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Column selector */}
        <div>
          <div style={{ fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,0.35)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Status</div>
          <select
            value={columnId}
            onChange={e => setColumnId(e.target.value)}
            style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 7, padding: '8px 10px', color: '#fff', fontSize: 13 }}
          >
            <option value="">— No column —</option>
            {[...columns].sort((a, b) => a.position - b.position).map(col => (
              <option key={col.id} value={col.id}>{col.name}</option>
            ))}
          </select>
        </div>

        {/* Services */}
        <div>
          <div style={{ fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,0.35)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Services</div>
          {services.map((svc, i) => (
            <div key={i} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, padding: '10px 12px', marginBottom: 6, fontSize: 12, color: 'rgba(255,255,255,0.7)' }}>
              {svc.description} — {svc.labor_hours}h @ ${svc.labor_rate}/hr
            </div>
          ))}
          <button
            style={{ width: '100%', padding: '8px', borderRadius: 7, border: '1px dashed rgba(255,255,255,0.15)', background: 'transparent', color: 'rgba(255,255,255,0.4)', fontSize: 11, cursor: 'pointer' }}
            onClick={() => setServices([...services, { description: 'New service', labor_hours: 1, labor_rate: 90, labor_cost: 90 }])}
          >
            + Add service
          </button>
        </div>

        {/* Notes */}
        <div>
          <div style={{ fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,0.35)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Notes</div>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            rows={4}
            style={{ width: '100%', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 7, padding: '8px 10px', color: '#fff', fontSize: 13, resize: 'vertical', boxSizing: 'border-box' }}
          />
        </div>
      </div>

      {/* Footer */}
      <div style={{ padding: '14px 20px', borderTop: '1px solid rgba(255,255,255,0.07)', display: 'flex', gap: 8 }}>
        <button
          onClick={() => save.mutate()}
          style={{ flex: 1, height: 36, borderRadius: 8, border: 'none', background: '#d97706', color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
        >
          {save.isPending ? 'Saving…' : 'Save'}
        </button>
        <button
          onClick={() => createInvoice.mutate()}
          style={{ flex: 1, height: 36, borderRadius: 8, border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.7)', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
        >
          {createInvoice.isPending ? 'Creating…' : '→ Invoice'}
        </button>
      </div>
    </div>
  )
}
