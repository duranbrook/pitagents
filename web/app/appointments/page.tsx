'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppShell } from '@/components/AppShell'
import CalendarGrid from '@/components/appointments/CalendarGrid'
import NewAppointmentModal from '@/components/appointments/NewAppointmentModal'
import type { Appointment } from '@/lib/types'
import { getAppointments, updateAppointment, convertAppointmentToJobCard } from '@/lib/api'

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

export default function AppointmentsPage() {
  return (
    <AppShell>
      <AppointmentsContent />
    </AppShell>
  )
}

function AppointmentsContent() {
  const qc = useQueryClient()
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [showNewModal, setShowNewModal] = useState(false)
  const [selectedDate, setSelectedDate] = useState(now)
  const [selectedAppt, setSelectedAppt] = useState<Appointment | null>(null)

  const { data: appointments = [] } = useQuery({
    queryKey: ['appointments', year, month],
    queryFn: () => getAppointments({ year, month }),
  })

  const convertToJC = useMutation({
    mutationFn: (id: string) => convertAppointmentToJobCard(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['appointments'] }); setSelectedAppt(null) },
  })

  const updateAppt = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Appointment> }) => updateAppointment(id, data),
    onSuccess: (updated) => { setSelectedAppt(updated); qc.invalidateQueries({ queryKey: ['appointments'] }) },
  })

  const prevMonth = () => { if (month === 1) { setMonth(12); setYear(y => y - 1) } else setMonth(m => m - 1) }
  const nextMonth = () => { if (month === 12) { setMonth(1); setYear(y => y + 1) } else setMonth(m => m + 1) }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px 0', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>Appointments</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button onClick={prevMonth} style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, width: 28, height: 28, color: '#fff', cursor: 'pointer', fontSize: 14 }}>‹</button>
            <span style={{ fontSize: 14, fontWeight: 600, minWidth: 120, textAlign: 'center' }}>{MONTHS[month - 1]} {year}</span>
            <button onClick={nextMonth} style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, width: 28, height: 28, color: '#fff', cursor: 'pointer', fontSize: 14 }}>›</button>
          </div>
        </div>
        <button
          onClick={() => { setSelectedDate(new Date()); setShowNewModal(true) }}
          style={{ height: 32, padding: '0 14px', borderRadius: 7, border: 'none', background: '#d97706', color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
        >
          + New Appointment
        </button>
      </div>

      <CalendarGrid
        year={year}
        month={month}
        appointments={appointments}
        onDayClick={date => { setSelectedDate(date); setShowNewModal(true) }}
        onAppointmentClick={setSelectedAppt}
      />

      {showNewModal && <NewAppointmentModal defaultDate={selectedDate} onClose={() => setShowNewModal(false)} />}

      {selectedAppt && (
        <div key={selectedAppt.id} style={{ position: 'fixed', right: 0, top: 0, bottom: 0, width: 360, background: '#141414', borderLeft: '1px solid rgba(255,255,255,0.08)', display: 'flex', flexDirection: 'column', zIndex: 50 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '18px 20px', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
            <div style={{ fontSize: 16, fontWeight: 700 }}>Appointment</div>
            <button onClick={() => setSelectedAppt(null)} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)', fontSize: 20, cursor: 'pointer' }}>×</button>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
            {([
              { label: 'Customer', value: selectedAppt.customer_name ?? '—' },
              { label: 'Service', value: selectedAppt.service_requested ?? '—' },
              { label: 'Time', value: `${new Date(selectedAppt.starts_at).toLocaleString()} – ${new Date(selectedAppt.ends_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` },
              { label: 'Phone', value: selectedAppt.customer_phone ?? '—' },
              { label: 'Notes', value: selectedAppt.notes ?? '—' },
            ] as const).map(({ label, value }) => (
              <div key={label} style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>{label}</div>
                <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.8)' }}>{value}</div>
              </div>
            ))}
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>Status</div>
              <div style={{ display: 'flex', gap: 6 }}>
                {(['pending', 'confirmed', 'cancelled'] as const).map(s => (
                  <button key={s} onClick={() => updateAppt.mutate({ id: selectedAppt.id, data: { status: s } })} style={{
                    padding: '4px 10px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.1)',
                    background: selectedAppt.status === s ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.03)',
                    color: selectedAppt.status === s ? '#fff' : 'rgba(255,255,255,0.45)',
                    fontSize: 11, fontWeight: 600, cursor: 'pointer', textTransform: 'capitalize',
                  }}>{s}</button>
                ))}
              </div>
            </div>
          </div>
          <div style={{ padding: '14px 20px', borderTop: '1px solid rgba(255,255,255,0.07)' }}>
            {!selectedAppt.job_card_id ? (
              <button onClick={() => convertToJC.mutate(selectedAppt.id)} disabled={convertToJC.isPending} style={{ width: '100%', height: 36, borderRadius: 8, border: 'none', background: '#d97706', color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                {convertToJC.isPending ? 'Creating…' : '→ Convert to Job Card'}
              </button>
            ) : (
              <div style={{ fontSize: 12, color: '#4ade80', textAlign: 'center' }}>✓ Job Card created</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
