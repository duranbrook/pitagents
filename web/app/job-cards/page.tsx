'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppShell } from '@/components/AppShell'
import KanbanBoard from '@/components/job-cards/KanbanBoard'
import JobCardDetail from '@/components/job-cards/JobCardDetail'
import type { JobCard } from '@/lib/types'
import { getJobCardColumns, getJobCards, createJobCard, updateJobCard } from '@/lib/api'

function JobCardsPageInner() {
  const qc = useQueryClient()
  const [view, setView] = useState<'kanban' | 'list'>('kanban')
  const [selectedCard, setSelectedCard] = useState<JobCard | null>(null)

  const { data: columns = [] } = useQuery({ queryKey: ['job-card-columns'], queryFn: getJobCardColumns })
  const { data: cards = [], isLoading } = useQuery({ queryKey: ['job-cards'], queryFn: () => getJobCards() })

  const addCard = useMutation({
    mutationFn: (columnId: string) => createJobCard({ column_id: columnId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['job-cards'] }),
  })

  const moveCard = useMutation({
    mutationFn: ({ id, columnId }: { id: string; columnId: string }) => updateJobCard(id, { column_id: columnId } as Partial<JobCard>),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['job-cards'] }),
  })

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px 0', flexShrink: 0 }}>
        <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>Job Cards</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <div style={{ display: 'flex', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 7, overflow: 'hidden' }}>
            {(['kanban', 'list'] as const).map(v => (
              <button key={v} onClick={() => setView(v)} style={{
                height: 32, padding: '0 14px', border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 600,
                background: view === v ? 'rgba(255,255,255,0.12)' : 'transparent',
                color: view === v ? '#fff' : 'rgba(255,255,255,0.5)', textTransform: 'capitalize',
              }}>
                {v}
              </button>
            ))}
          </div>
          <button
            onClick={() => addCard.mutate(columns[0]?.id ?? '')}
            style={{ height: 32, padding: '0 14px', borderRadius: 7, border: 'none', background: '#d97706', color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
          >
            + New Card
          </button>
        </div>
      </div>

      {isLoading ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)' }}>Loading…</div>
      ) : (
        <KanbanBoard
          columns={columns}
          cards={cards}
          onCardClick={setSelectedCard}
          onAddCard={columnId => addCard.mutate(columnId)}
        />
      )}

      {selectedCard && (
        <JobCardDetail
          key={selectedCard.id}
          card={selectedCard}
          columns={columns}
          onClose={() => setSelectedCard(null)}
        />
      )}
    </div>
  )
}

export default function JobCardsPage() {
  return (
    <AppShell>
      <JobCardsPageInner />
    </AppShell>
  )
}
