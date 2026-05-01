'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppShell } from '@/components/AppShell'
import { getTimeEntries, getActiveTimeEntries, clockIn, clockOut } from '@/lib/api'
import type { TimeEntry } from '@/lib/types'

const TASK_COLORS: Record<string, string> = { Repair: '#4ade80', Diagnosis: '#60a5fa', Admin: '#fbbf24' }

function formatDuration(minutes: number | null): string {
  if (minutes === null) return '—'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

function groupByDay(entries: TimeEntry[]): Record<string, TimeEntry[]> {
  const groups: Record<string, TimeEntry[]> = {}
  for (const e of entries) {
    const day = new Date(e.started_at).toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })
    if (!groups[day]) groups[day] = []
    groups[day].push(e)
  }
  return groups
}

export default function TimeTrackingPage() {
  return (
    <AppShell>
      <TimeTrackingContent />
    </AppShell>
  )
}

function TimeTrackingContent() {
  const qc = useQueryClient()
  const [taskType, setTaskType] = useState<'Repair' | 'Diagnosis' | 'Admin'>('Repair')

  const { data: active = [] } = useQuery({ queryKey: ['active-entries'], queryFn: getActiveTimeEntries, refetchInterval: 30000 })
  const { data: entries = [], isLoading } = useQuery({ queryKey: ['time-entries'], queryFn: () => getTimeEntries() })

  const clock = useMutation({
    mutationFn: () => clockIn({ task_type: taskType }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['active-entries'] }); qc.invalidateQueries({ queryKey: ['time-entries'] }) },
  })

  const stop = useMutation({
    mutationFn: (id: string) => clockOut(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['active-entries'] }); qc.invalidateQueries({ queryKey: ['time-entries'] }) },
  })

  const grouped = groupByDay(entries)
  const days = Object.keys(grouped)

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '20px 24px 0', flexShrink: 0 }}>
        <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em', marginBottom: 14 }}>Time Tracking</div>

        {active.length > 0 && (
          <div style={{ background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)', borderRadius: 10, padding: '12px 16px', marginBottom: 14 }}>
            <div style={{ fontSize: 10, fontWeight: 800, color: '#4ade80', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
              Currently Clocked In ({active.length})
            </div>
            {active.map(e => (
              <div key={e.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                <div style={{ fontSize: 13 }}>
                  <span style={{ color: TASK_COLORS[e.task_type] ?? '#4ade80', fontWeight: 700 }}>{e.task_type}</span>
                  <span style={{ color: 'rgba(255,255,255,0.5)', marginLeft: 8, fontSize: 11 }}>
                    since {new Date(e.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <button
                  onClick={() => stop.mutate(e.id)}
                  style={{ height: 26, padding: '0 10px', borderRadius: 6, border: '1px solid rgba(239,68,68,0.3)', background: 'rgba(239,68,68,0.08)', color: '#f87171', fontSize: 10, fontWeight: 600, cursor: 'pointer' }}
                >
                  Stop
                </button>
              </div>
            ))}
          </div>
        )}

        {active.length === 0 && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 14 }}>
            <div style={{ display: 'flex', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 7, overflow: 'hidden' }}>
              {(['Repair', 'Diagnosis', 'Admin'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setTaskType(t)}
                  style={{
                    height: 32, padding: '0 14px', border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 600,
                    background: taskType === t ? `${TASK_COLORS[t]}22` : 'transparent',
                    color: taskType === t ? TASK_COLORS[t] : 'rgba(255,255,255,0.45)',
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
            <button
              onClick={() => clock.mutate()}
              disabled={clock.isPending}
              style={{ height: 32, padding: '0 16px', borderRadius: 7, border: 'none', background: '#4ade80', color: '#000', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}
            >
              Clock In
            </button>
          </div>
        )}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '0 24px 20px' }}>
        {isLoading ? (
          <div style={{ color: 'rgba(255,255,255,0.3)' }}>Loading…</div>
        ) : entries.length === 0 ? (
          <div style={{ color: 'rgba(255,255,255,0.25)', textAlign: 'center', padding: '40px 0', fontSize: 13 }}>No time entries yet</div>
        ) : days.map(day => (
          <div key={day} style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 10, fontWeight: 800, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8, paddingBottom: 6, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
              {day}
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ color: 'rgba(255,255,255,0.25)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  {['Task', 'Job Card', 'Start', 'End', 'Duration', 'QB'].map(h => (
                    <th key={h} style={{ textAlign: 'left', padding: '4px 0 6px', fontWeight: 700 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {grouped[day].map(e => (
                  <tr key={e.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '9px 0' }}>
                      <span style={{ color: TASK_COLORS[e.task_type] ?? '#fff', fontWeight: 700, fontSize: 11, padding: '2px 6px', borderRadius: 4, background: `${TASK_COLORS[e.task_type] ?? '#fff'}15` }}>
                        {e.task_type}
                      </span>
                    </td>
                    <td style={{ padding: '9px 0', color: 'rgba(255,255,255,0.4)', fontSize: 11 }}>{e.job_card_id ? e.job_card_id.slice(0, 8) + '…' : '—'}</td>
                    <td style={{ padding: '9px 0', color: 'rgba(255,255,255,0.6)' }}>{new Date(e.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                    <td style={{ padding: '9px 0', color: 'rgba(255,255,255,0.6)' }}>{e.ended_at ? new Date(e.ended_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : <span style={{ color: '#4ade80', fontWeight: 600 }}>Active</span>}</td>
                    <td style={{ padding: '9px 0', color: 'rgba(255,255,255,0.75)', fontWeight: 600 }}>{formatDuration(e.duration_minutes)}</td>
                    <td style={{ padding: '9px 0' }}>
                      <span style={{ fontSize: 10, color: e.qb_synced ? '#4ade80' : 'rgba(255,255,255,0.2)' }}>
                        {e.qb_synced ? '✓' : '—'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  )
}
