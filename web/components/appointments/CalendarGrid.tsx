'use client'
import type { Appointment } from '@/lib/types'

interface Props {
  year: number
  month: number
  appointments: Appointment[]
  onDayClick: (date: Date) => void
  onAppointmentClick: (appt: Appointment) => void
}

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const STATUS_COLORS: Record<string, string> = {
  confirmed: '#4ade80', pending: '#fbbf24', cancelled: 'rgba(255,255,255,0.2)',
}

export default function CalendarGrid({ year, month, appointments, onDayClick, onAppointmentClick }: Props) {
  const firstDay = new Date(year, month - 1, 1).getDay()
  const daysInMonth = new Date(year, month, 0).getDate()
  const cells: (number | null)[] = [
    ...Array(firstDay).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ]
  while (cells.length % 7 !== 0) cells.push(null)

  const apptsByDay: Record<number, Appointment[]> = {}
  for (const a of appointments) {
    const d = new Date(a.starts_at).getDate()
    if (!apptsByDay[d]) apptsByDay[d] = []
    apptsByDay[d].push(a)
  }

  const today = new Date()
  const isToday = (day: number) =>
    today.getFullYear() === year && today.getMonth() + 1 === month && today.getDate() === day

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '14px 24px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4, marginBottom: 4 }}>
        {DAYS.map(d => (
          <div key={d} style={{ fontSize: 10, fontWeight: 700, color: 'rgba(255,255,255,0.3)', textAlign: 'center', padding: '4px 0', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{d}</div>
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4 }}>
        {cells.map((day, i) => (
          <div
            key={i}
            onClick={() => day && onDayClick(new Date(year, month - 1, day))}
            style={{
              minHeight: 80,
              background: day ? 'rgba(255,255,255,0.02)' : 'transparent',
              border: day ? `1px solid ${isToday(day!) ? 'rgba(217,119,6,0.5)' : 'rgba(255,255,255,0.06)'}` : 'none',
              borderRadius: 8, padding: '6px 8px', cursor: day ? 'pointer' : 'default',
            }}
            onMouseEnter={e => { if (day) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)' }}
            onMouseLeave={e => { if (day) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.02)' }}
          >
            {day && (
              <>
                <div style={{ fontSize: 12, fontWeight: isToday(day) ? 700 : 400, color: isToday(day) ? '#d97706' : 'rgba(255,255,255,0.6)', marginBottom: 4 }}>{day}</div>
                {(apptsByDay[day] ?? []).slice(0, 3).map(a => (
                  <div
                    key={a.id}
                    onClick={e => { e.stopPropagation(); onAppointmentClick(a) }}
                    style={{
                      fontSize: 10, fontWeight: 600, padding: '2px 5px', borderRadius: 4, marginBottom: 2,
                      background: `${STATUS_COLORS[a.status] ?? '#94a3b8'}22`,
                      color: STATUS_COLORS[a.status] ?? '#94a3b8',
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                    }}
                  >
                    {new Date(a.starts_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} {a.customer_name ?? a.service_requested ?? 'Appointment'}
                  </div>
                ))}
                {(apptsByDay[day]?.length ?? 0) > 3 && (
                  <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)' }}>+{(apptsByDay[day]?.length ?? 0) - 3} more</div>
                )}
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
