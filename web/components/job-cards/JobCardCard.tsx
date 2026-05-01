'use client'
import type { JobCard } from '@/lib/types'

interface Props {
  card: JobCard
  accentColor: string
  onClick: () => void
}

export default function JobCardCard({ card, accentColor, onClick }: Props) {
  const serviceCount = card.services?.length ?? 0
  const partsCount = card.parts?.length ?? 0
  return (
    <div
      onClick={onClick}
      style={{
        background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.09)',
        borderLeft: `3px solid ${accentColor}55`, borderRadius: 9, padding: '11px 12px',
        cursor: 'pointer', transition: 'background 0.12s',
      }}
      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.07)' }}
      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)' }}
    >
      <div style={{ fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,0.4)', marginBottom: 3 }}>{card.number}</div>
      <div style={{ fontSize: 12, fontWeight: 700, color: 'rgba(255,255,255,0.88)', marginBottom: 3 }}>
        {card.vehicle_id ? 'Vehicle attached' : 'No vehicle'}
      </div>
      <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', marginBottom: card.notes ? 7 : 0 }}>
        {serviceCount} service{serviceCount !== 1 ? 's' : ''}{partsCount > 0 ? ` · ${partsCount} part${partsCount !== 1 ? 's' : ''}` : ''}
      </div>
      {card.notes && (
        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {card.notes}
        </div>
      )}
    </div>
  )
}
