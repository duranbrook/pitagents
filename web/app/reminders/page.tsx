'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppShell } from '@/components/AppShell'
import { getReminderConfigs, updateReminderConfig, runReminderJob } from '@/lib/api'
import type { ServiceReminderConfig } from '@/lib/types'

export default function RemindersPage() {
  return (
    <AppShell>
      <RemindersContent />
    </AppShell>
  )
}

function RemindersContent() {
  const qc = useQueryClient()
  const { data: configs = [], isLoading } = useQuery({ queryKey: ['reminder-configs'], queryFn: getReminderConfigs })
  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ServiceReminderConfig> }) => updateReminderConfig(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reminder-configs'] }),
  })
  const runJob = useMutation({ mutationFn: runReminderJob })

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px 14px', flexShrink: 0 }}>
        <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>Service Reminders</div>
        <button onClick={() => runJob.mutate()} disabled={runJob.isPending} style={{ height: 32, padding: '0 14px', borderRadius: 7, border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.65)', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
          {runJob.isPending ? 'Running…' : 'Run job now'}
        </button>
      </div>
      {runJob.isSuccess && (
        <div style={{ margin: '0 24px 12px', padding: '10px 14px', background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)', borderRadius: 8, fontSize: 13, color: '#4ade80' }}>
          ✓ Sent {runJob.data?.reminders_sent ?? 0} reminder{runJob.data?.reminders_sent !== 1 ? 's' : ''}
        </div>
      )}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0 24px 20px' }}>
        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.4)', marginBottom: 16, lineHeight: 1.6 }}>
          Reminders are sent monthly. Customers in the service window receive a message every 30 days until they book. Hard stop at 12 months with no visit.
        </div>
        {isLoading ? <div style={{ color: 'rgba(255,255,255,0.3)' }}>Loading…</div> : configs.map(cfg => (
          <div key={cfg.id} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 10, padding: 16, marginBottom: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <div style={{ fontSize: 14, fontWeight: 700 }}>{cfg.service_type}</div>
              <div style={{ display: 'flex', gap: 6 }}>
                {(['sms_enabled', 'email_enabled'] as const).map(field => (
                  <button key={field} onClick={() => update.mutate({ id: cfg.id, data: { [field]: !cfg[field] } })} style={{
                    padding: '3px 10px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.1)', cursor: 'pointer',
                    background: cfg[field] ? 'rgba(217,119,6,0.15)' : 'rgba(255,255,255,0.04)',
                    color: cfg[field] ? '#fbbf24' : 'rgba(255,255,255,0.35)',
                    fontSize: 10, fontWeight: 700,
                  }}>{field === 'sms_enabled' ? 'SMS' : 'Email'}</button>
                ))}
              </div>
            </div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', marginBottom: 8 }}>
              Window: {cfg.window_start_months}–{cfg.window_end_months} months after last service
            </div>
            {cfg.message_template && (
              <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', fontStyle: 'italic', padding: '8px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: 6 }}>
                &ldquo;{cfg.message_template}&rdquo;
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
