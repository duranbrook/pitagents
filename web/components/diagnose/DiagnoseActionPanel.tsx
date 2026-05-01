'use client'
import { useState } from 'react'
import type { DiagnosisItem, RepairPlanItem } from '@/lib/types'
import { diagnoseAddToJobCard, diagnoseSendSummary } from '@/lib/api'

interface Props {
  diagnosis: DiagnosisItem[]
  repairPlan: RepairPlanItem[]
  jobCardId: string | null
  customerId: string | null
}

export function DiagnoseActionPanel({ diagnosis, repairPlan, jobCardId, customerId }: Props) {
  const [addedToCard, setAddedToCard] = useState(false)
  const [smsSent, setSmsSent] = useState(false)
  const [smsPreview, setSmsPreview] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)

  const partsNeeded = diagnosis
    .filter(d => d.part)
    .slice(0, 5)
    .map(d => d.part as string)

  const totalLaborHrs = repairPlan.reduce((sum, r) => sum + (r.labor_hrs || 0), 0)

  const handleAddToJobCard = async () => {
    if (!jobCardId) return
    setAdding(true)
    await diagnoseAddToJobCard(jobCardId, diagnosis, repairPlan)
    setAddedToCard(true)
    setAdding(false)
  }

  const handleSendSummary = async () => {
    if (!customerId) return
    const result = await diagnoseSendSummary(customerId, diagnosis)
    setSmsPreview(result.sms_text)
    setSmsSent(true)
  }

  const sectionStyle = { marginBottom: '20px' }
  const labelStyle = { color: '#9ca3af', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase' as const, letterSpacing: '0.05em', marginBottom: '8px' }
  const cardStyle = { background: '#1a1a1a', border: '1px solid #2a2a2a', borderRadius: '6px', padding: '10px 12px', marginBottom: '6px', fontSize: '13px', color: '#e5e7eb' }

  return (
    <div style={{ width: '280px', flexShrink: 0, borderLeft: '1px solid #222', paddingLeft: '24px' }}>
      <div style={sectionStyle}>
        <div style={labelStyle}>Parts Needed</div>
        {partsNeeded.length === 0 ? (
          <div style={{ color: '#4b5563', fontSize: '13px' }}>No parts identified yet</div>
        ) : (
          partsNeeded.map((part, i) => (
            <div key={i} style={cardStyle}>{part}</div>
          ))
        )}
      </div>

      <div style={sectionStyle}>
        <div style={labelStyle}>Labor Estimate</div>
        <div style={{ ...cardStyle, color: '#d97706', fontWeight: 600 }}>
          {totalLaborHrs > 0 ? `${totalLaborHrs.toFixed(1)} hrs` : '—'}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column' as const, gap: '10px' }}>
        <button
          onClick={handleAddToJobCard}
          disabled={!jobCardId || addedToCard || adding}
          style={{
            background: addedToCard ? '#14532d' : '#d97706',
            color: addedToCard ? '#86efac' : '#000',
            border: 'none',
            borderRadius: '6px',
            padding: '10px 14px',
            cursor: !jobCardId || addedToCard ? 'not-allowed' : 'pointer',
            fontWeight: 600,
            fontSize: '13px',
            opacity: !jobCardId ? 0.4 : 1,
          }}
        >
          {addedToCard ? '✓ Added to Job Card' : adding ? 'Adding…' : '+ Add to Job Card'}
        </button>

        <button
          onClick={handleSendSummary}
          disabled={!customerId || smsSent}
          style={{
            background: smsSent ? '#1e3a5f' : '#1a1a1a',
            color: smsSent ? '#93c5fd' : '#e5e7eb',
            border: '1px solid #333',
            borderRadius: '6px',
            padding: '10px 14px',
            cursor: !customerId || smsSent ? 'not-allowed' : 'pointer',
            fontSize: '13px',
            opacity: !customerId ? 0.4 : 1,
          }}
        >
          {smsSent ? '✓ Summary Sent' : 'Send Summary to Customer'}
        </button>

        {smsPreview && (
          <div style={{ background: '#111', border: '1px solid #1d4ed8', borderRadius: '6px', padding: '10px', fontSize: '12px', color: '#93c5fd', lineHeight: 1.5 }}>
            <div style={{ color: '#6b7280', fontSize: '10px', marginBottom: '4px' }}>PREVIEW</div>
            {smsPreview}
          </div>
        )}
      </div>
    </div>
  )
}
