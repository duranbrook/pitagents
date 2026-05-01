'use client'
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createAppointment } from '@/lib/api'

interface Props {
  defaultDate: Date
  onClose: () => void
}

function toDatetimeLocal(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export default function NewAppointmentModal({ defaultDate, onClose }: Props) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    customer_name: '',
    service_requested: '',
    starts_at: toDatetimeLocal(defaultDate),
    ends_at: toDatetimeLocal(new Date(defaultDate.getTime() + 3600000)),
    status: 'confirmed' as const,
    notes: '',
  })

  const create = useMutation({
    mutationFn: () => createAppointment({
      ...form,
      starts_at: new Date(form.starts_at).toISOString(),
      ends_at: new Date(form.ends_at).toISOString(),
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['appointments'] }); onClose() },
  })

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
      <div style={{ background: '#1a1a1a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: 24, width: 380 }}>
        <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 18 }}>New Appointment</div>
        {([
          { key: 'customer_name', label: 'Customer name', type: 'text' },
          { key: 'service_requested', label: 'Service', type: 'text' },
          { key: 'starts_at', label: 'Start', type: 'datetime-local' },
          { key: 'ends_at', label: 'End', type: 'datetime-local' },
        ] as const).map(({ key, label, type }) => (
          <div key={key} style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</div>
            <input
              type={type}
              value={form[key]}
              onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
              style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 7, padding: '8px 10px', color: '#fff', fontSize: 13 }}
            />
          </div>
        ))}
        <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
          <button onClick={onClose} style={{ flex: 1, height: 36, borderRadius: 8, border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.6)', cursor: 'pointer' }}>Cancel</button>
          <button onClick={() => create.mutate()} disabled={create.isPending} style={{ flex: 1, height: 36, borderRadius: 8, border: 'none', background: '#d97706', color: '#fff', fontWeight: 600, cursor: 'pointer' }}>
            {create.isPending ? 'Saving…' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  )
}
