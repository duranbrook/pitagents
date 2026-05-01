'use client'
import type { JobCardColumn, JobCard } from '@/lib/types'
import JobCardCard from './JobCardCard'

const COLUMN_COLORS: Record<number, string> = {
  0: '#60a5fa', 1: '#fbbf24', 2: '#c084fc', 3: '#4ade80',
}

interface Props {
  column: JobCardColumn
  cards: JobCard[]
  onCardClick: (card: JobCard) => void
  onAddCard: () => void
}

export default function KanbanColumn({ column, cards, onCardClick, onAddCard }: Props) {
  const color = COLUMN_COLORS[column.position] ?? '#94a3b8'
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: 10 }}>
        <span style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.05em', textTransform: 'uppercase', color }}>
          {column.name}
        </span>
        <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 9, background: `${color}22`, color }}>
          {cards.length}
        </span>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 7 }}>
        {cards.map(card => (
          <JobCardCard key={card.id} card={card} accentColor={color} onClick={() => onCardClick(card)} />
        ))}
        <button
          onClick={onAddCard}
          style={{
            border: '1px dashed rgba(255,255,255,0.12)', borderRadius: 9, padding: '11px 12px',
            textAlign: 'center', fontSize: 11, color: 'rgba(255,255,255,0.25)',
            cursor: 'pointer', background: 'transparent', marginTop: 2,
          }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.25)' }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.12)' }}
        >
          + Add card
        </button>
      </div>
    </div>
  )
}
