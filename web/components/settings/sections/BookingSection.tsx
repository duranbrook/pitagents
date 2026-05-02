'use client'
import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getMyBookingConfig, updateMyBookingConfig } from '@/lib/api'

const fieldStyle: React.CSSProperties = {
  width: '100%', background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.09)', borderRadius: 6,
  padding: '8px 10px', fontSize: 12, color: 'rgba(255,255,255,0.85)',
  outline: 'none', boxSizing: 'border-box',
}

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 10, fontWeight: 600,
  textTransform: 'uppercase', letterSpacing: '.06em',
  color: 'rgba(255,255,255,0.3)', marginBottom: 5,
}

export function BookingSection() {
  const qc = useQueryClient()
  const { data: cfg, isError } = useQuery({
    queryKey: ['my-booking-config'],
    queryFn: getMyBookingConfig,
    retry: false,
  })

  const [form, setForm] = useState({
    working_hours_start: '08:00',
    working_hours_end: '17:00',
    slot_duration_minutes: '60',
  })
  const [msg, setMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  useEffect(() => {
    if (cfg) {
      setForm({
        working_hours_start: cfg.working_hours_start,
        working_hours_end: cfg.working_hours_end,
        slot_duration_minutes: cfg.slot_duration_minutes,
      })
    }
  }, [cfg])

  const clearTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => () => { if (clearTimer.current) clearTimeout(clearTimer.current) }, [])

  const save = useMutation({
    mutationFn: () => updateMyBookingConfig(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['my-booking-config'] })
      setMsg({ type: 'ok', text: 'Saved' })
      if (clearTimer.current) clearTimeout(clearTimer.current)
      clearTimer.current = setTimeout(() => setMsg(null), 2500)
    },
    onError: (e: Error) => setMsg({ type: 'err', text: e.message }),
  })

  if (isError) {
    return (
      <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 12 }}>
        No booking config found. Run the demo seed or contact support.
      </div>
    )
  }

  return (
    <div>
      {cfg?.slug && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ ...labelStyle }}>Booking link</div>
          <div style={{
            background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
            borderRadius: 6, padding: '8px 10px', fontSize: 11,
            color: 'rgba(255,255,255,0.45)', fontFamily: 'monospace',
          }}>
            /book/{cfg.slug}
          </div>
        </div>
      )}

      <form onSubmit={e => { e.preventDefault(); save.mutate() }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
          <div>
            <label htmlFor="booking-start" style={labelStyle}>Open time</label>
            <input
              id="booking-start"
              type="time"
              value={form.working_hours_start}
              onChange={e => setForm(f => ({ ...f, working_hours_start: e.target.value }))}
              style={fieldStyle}
            />
          </div>
          <div>
            <label htmlFor="booking-end" style={labelStyle}>Close time</label>
            <input
              id="booking-end"
              type="time"
              value={form.working_hours_end}
              onChange={e => setForm(f => ({ ...f, working_hours_end: e.target.value }))}
              style={fieldStyle}
            />
          </div>
        </div>
        <div style={{ marginBottom: 16 }}>
          <label htmlFor="booking-slot" style={labelStyle}>Slot duration (minutes)</label>
          <select
            id="booking-slot"
            value={form.slot_duration_minutes}
            onChange={e => setForm(f => ({ ...f, slot_duration_minutes: e.target.value }))}
            style={{ ...fieldStyle, cursor: 'pointer' }}
          >
            {['15', '30', '45', '60', '90', '120'].map(v => (
              <option key={v} value={v}>{v} min</option>
            ))}
          </select>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            type="submit"
            disabled={save.isPending}
            style={{
              background: 'var(--accent)', color: '#000', border: 'none',
              borderRadius: 6, padding: '7px 16px', fontSize: 12, fontWeight: 700,
              cursor: save.isPending ? 'not-allowed' : 'pointer', opacity: save.isPending ? 0.6 : 1,
            }}
          >
            {save.isPending ? 'Saving…' : 'Save'}
          </button>
        </div>
        {msg && (
          <div style={{ fontSize: 11, marginTop: 8, color: msg.type === 'ok' ? 'rgba(74,222,128,0.9)' : 'rgba(239,68,68,0.9)' }}>
            {msg.text}
          </div>
        )}
      </form>
    </div>
  )
}
