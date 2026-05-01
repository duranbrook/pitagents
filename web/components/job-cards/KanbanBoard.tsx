'use client'
import type { JobCardColumn, JobCard } from '@/lib/types'
import KanbanColumn from './KanbanColumn'

interface Props {
  columns: JobCardColumn[]
  cards: JobCard[]
  onCardClick: (card: JobCard) => void
  onAddCard: (columnId: string) => void
}

export default function KanbanBoard({ columns, cards, onCardClick, onAddCard }: Props) {
  const sortedColumns = [...columns].sort((a, b) => a.position - b.position)
  return (
    <div style={{ display: 'flex', gap: 12, flex: 1, overflow: 'hidden', padding: '14px 24px 20px' }}>
      {sortedColumns.map(col => (
        <KanbanColumn
          key={col.id}
          column={col}
          cards={cards.filter(c => c.column_id === col.id)}
          onCardClick={onCardClick}
          onAddCard={() => onAddCard(col.id)}
        />
      ))}
    </div>
  )
}
