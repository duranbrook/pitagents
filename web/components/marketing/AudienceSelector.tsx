'use client'
import { useEffect, useState } from 'react'
import { fetchAudienceCount } from '@/lib/api'
import type { AudienceSegment } from '@/lib/types'

interface Props {
  value: AudienceSegment
  onChange: (seg: AudienceSegment) => void
}

const SEGMENT_OPTIONS: { type: AudienceSegment['type']; label: string }[] = [
  { type: 'all_customers', label: 'All Customers' },
  { type: 'by_service', label: 'By Service History' },
  { type: 'by_last_visit', label: 'By Last Visit Window' },
  { type: 'by_vehicle_type', label: 'By Vehicle Type' },
]

const SERVICE_TYPES = ['Oil Change', 'Tire Rotation', 'AC Check', 'Full Service', 'Brakes', 'Alignment']

export function AudienceSelector({ value, onChange }: Props) {
  const [count, setCount] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchAudienceCount(value)
      .then(c => { if (!cancelled) setCount(c) })
      .catch(() => { if (!cancelled) setCount(null) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [JSON.stringify(value)])

  const inputStyle = {
    background: '#1a1a1a',
    border: '1px solid #333',
    color: '#fff',
    borderRadius: '6px',
    padding: '7px 10px',
    fontSize: '13px',
    width: '100%',
    outline: 'none',
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <div style={{ color: '#9ca3af', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Audience</div>
        <div style={{ color: loading ? '#6b7280' : '#d97706', fontSize: '13px', fontWeight: 600 }}>
          {loading ? '…' : count != null ? `${count} contacts` : '—'}
        </div>
      </div>

      <select
        value={value.type}
        onChange={e => onChange({ type: e.target.value as AudienceSegment['type'] })}
        style={{ ...inputStyle, marginBottom: '10px', cursor: 'pointer' }}
      >
        {SEGMENT_OPTIONS.map(o => (
          <option key={o.type} value={o.type}>{o.label}</option>
        ))}
      </select>

      {value.type === 'by_service' && (
        <select
          value={value.service_type || ''}
          onChange={e => onChange({ ...value, service_type: e.target.value })}
          style={{ ...inputStyle, cursor: 'pointer' }}
        >
          <option value="">Select service type…</option>
          {SERVICE_TYPES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      )}

      {value.type === 'by_last_visit' && (
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <input
            type="number"
            placeholder="From (months)"
            value={value.last_visit_months_start || ''}
            onChange={e => onChange({ ...value, last_visit_months_start: parseInt(e.target.value) || undefined })}
            style={{ ...inputStyle, flex: 1 }}
          />
          <span style={{ color: '#6b7280' }}>–</span>
          <input
            type="number"
            placeholder="To (months)"
            value={value.last_visit_months_end || ''}
            onChange={e => onChange({ ...value, last_visit_months_end: parseInt(e.target.value) || undefined })}
            style={{ ...inputStyle, flex: 1 }}
          />
        </div>
      )}

      {value.type === 'by_vehicle_type' && (
        <input
          placeholder="Vehicle make (e.g. Toyota)"
          value={value.vehicle_type || ''}
          onChange={e => onChange({ ...value, vehicle_type: e.target.value })}
          style={inputStyle}
        />
      )}
    </div>
  )
}
