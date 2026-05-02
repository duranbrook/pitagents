'use client'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getReminderConfigs, updateReminderConfig } from '@/lib/api'
import type { ServiceReminderConfig } from '@/lib/types'
import { useState } from 'react'

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 10, fontWeight: 600,
  textTransform: 'uppercase', letterSpacing: '.06em',
  color: 'rgba(255,255,255,0.3)', marginBottom: 5,
}

const sectionHeadingStyle: React.CSSProperties = {
  fontSize: 10, fontWeight: 600, textTransform: 'uppercase',
  letterSpacing: '.07em', color: 'rgba(255,255,255,0.3)', marginBottom: 10,
}

function ReminderRow({ cfg }: { cfg: ServiceReminderConfig }) {
  const qc = useQueryClient()
  const [windowStart, setWindowStart] = useState(String(cfg.window_start_months))
  const [windowEnd, setWindowEnd] = useState(String(cfg.window_end_months))
  const [smsEnabled, setSmsEnabled] = useState(cfg.sms_enabled)
  const [emailEnabled, setEmailEnabled] = useState(cfg.email_enabled)
  const [msg, setMsg] = useState<string | null>(null)

  const save = useMutation({
    mutationFn: () => updateReminderConfig(cfg.id, {
      window_start_months: Number(windowStart),
      window_end_months: Number(windowEnd),
      sms_enabled: smsEnabled,
      email_enabled: emailEnabled,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reminder-configs'] })
      setMsg('Saved')
      setTimeout(() => setMsg(null), 2000)
    },
  })

  const inputStyle: React.CSSProperties = {
    background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.09)',
    borderRadius: 5, padding: '5px 8px', fontSize: 11, color: 'rgba(255,255,255,0.8)',
    outline: 'none', width: 48,
  }

  return (
    <div style={{
      background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)',
      borderRadius: 8, padding: '12px 14px', marginBottom: 8,
    }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: '#fff', marginBottom: 8, textTransform: 'capitalize' }}>
        {cfg.service_type.replace(/_/g, ' ')}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>Remind</span>
        <input value={windowStart} onChange={e => setWindowStart(e.target.value)} style={inputStyle} type="number" min="1" />
        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>–</span>
        <input value={windowEnd} onChange={e => setWindowEnd(e.target.value)} style={inputStyle} type="number" min="1" />
        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>months out</span>
        <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'rgba(255,255,255,0.5)', cursor: 'pointer', marginLeft: 4 }}>
          <input type="checkbox" checked={smsEnabled} onChange={e => setSmsEnabled(e.target.checked)} />
          SMS
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'rgba(255,255,255,0.5)', cursor: 'pointer' }}>
          <input type="checkbox" checked={emailEnabled} onChange={e => setEmailEnabled(e.target.checked)} />
          Email
        </label>
        <button
          type="button"
          onClick={() => save.mutate()}
          disabled={save.isPending}
          style={{
            marginLeft: 'auto', background: 'var(--accent)', color: '#000', border: 'none',
            borderRadius: 5, padding: '4px 10px', fontSize: 11, fontWeight: 700, cursor: 'pointer',
            opacity: save.isPending ? 0.6 : 1,
          }}
        >
          {save.isPending ? '…' : msg ?? 'Save'}
        </button>
      </div>
    </div>
  )
}

export function NotificationsSection() {
  const { data: configs = [], isLoading } = useQuery({
    queryKey: ['reminder-configs'],
    queryFn: getReminderConfigs,
  })

  if (isLoading) {
    return <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>Loading…</div>
  }

  return (
    <div>
      <div style={sectionHeadingStyle}>Service Reminder Windows</div>
      <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', marginBottom: 14 }}>
        Configure when automatic reminders are sent to customers before their next service is due.
      </div>
      {configs.length === 0 && (
        <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>
          No reminder configs found. Add them from the Reminders page.
        </div>
      )}
      {configs.map(cfg => <ReminderRow key={cfg.id} cfg={cfg} />)}
    </div>
  )
}
