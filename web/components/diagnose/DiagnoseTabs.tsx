'use client'
import type { DiagnosisItem, RepairPlanItem, TsbItem, RecallItem, MaintenanceItem } from '@/lib/types'

type Tab = 'diagnosis' | 'repair' | 'tsb' | 'recalls' | 'maintenance'

interface Props {
  activeTab: Tab
  onTabChange: (tab: Tab) => void
  diagnosis: DiagnosisItem[]
  repairPlan: RepairPlanItem[]
  tsbs: TsbItem[]
  recalls: RecallItem[]
  maintenance: MaintenanceItem[]
  loading: boolean
}

const TABS: { key: Tab; label: string }[] = [
  { key: 'diagnosis', label: 'Diagnosis' },
  { key: 'repair', label: 'Repair Plan' },
  { key: 'tsb', label: 'TSB' },
  { key: 'recalls', label: 'Recalls' },
  { key: 'maintenance', label: 'Maintenance' },
]

export function DiagnoseTabs({ activeTab, onTabChange, diagnosis, repairPlan, tsbs, recalls, maintenance, loading }: Props) {
  const tabBar = (
    <div style={{ display: 'flex', borderBottom: '1px solid #222', marginBottom: '20px' }}>
      {TABS.map(tab => (
        <button
          key={tab.key}
          onClick={() => onTabChange(tab.key)}
          style={{
            background: 'none',
            border: 'none',
            color: activeTab === tab.key ? '#d97706' : '#6b7280',
            borderBottom: activeTab === tab.key ? '2px solid #d97706' : '2px solid transparent',
            padding: '10px 16px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: activeTab === tab.key ? 600 : 400,
            marginBottom: '-1px',
          }}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )

  const itemCard = (children: React.ReactNode, key: string | number) => (
    <div key={key} style={{ background: '#141414', border: '1px solid #222', borderRadius: '8px', padding: '14px 16px', marginBottom: '10px' }}>
      {children}
    </div>
  )

  const pill = (text: string, color = '#374151') => (
    <span style={{ background: color, color: '#e5e7eb', borderRadius: '12px', padding: '2px 10px', fontSize: '11px', fontWeight: 600 }}>{text}</span>
  )

  if (loading) {
    return (
      <div style={{ flex: 1 }}>
        {tabBar}
        <div style={{ color: '#6b7280', fontSize: '14px', paddingTop: '20px' }}>Analyzing…</div>
      </div>
    )
  }

  return (
    <div style={{ flex: 1 }}>
      {tabBar}

      {activeTab === 'diagnosis' && (
        diagnosis.length === 0
          ? <div style={{ color: '#4b5563', fontSize: '14px' }}>Run an analysis to see diagnostic results.</div>
          : diagnosis.map((d, i) => itemCard(
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: '14px' }}>{d.layman_desc || d.desc}</div>
                {d.urgency_desc && pill(d.urgency_desc, d.urgency === 1 ? '#7f1d1d' : d.urgency === 2 ? '#78350f' : '#1e3a5f')}
              </div>
              {d.layman_desc && d.desc !== d.layman_desc && (
                <div style={{ color: '#6b7280', fontSize: '12px', marginBottom: '4px' }}>{d.desc}</div>
              )}
              {d.part && <div style={{ color: '#d97706', fontSize: '12px' }}>Part: {d.part}</div>}
            </>,
            i
          ))
      )}

      {activeTab === 'repair' && (
        repairPlan.length === 0
          ? <div style={{ color: '#4b5563', fontSize: '14px' }}>No repair plan data yet.</div>
          : repairPlan.map((r, i) => itemCard(
            <>
              <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>{r.repair_desc || r.desc}</div>
              <div style={{ display: 'flex', gap: '12px', fontSize: '12px', color: '#9ca3af' }}>
                {r.labor_hrs != null && <span>Labor: {r.labor_hrs}h</span>}
                {r.confidence && <span>Confidence: {r.confidence}</span>}
              </div>
            </>,
            i
          ))
      )}

      {activeTab === 'tsb' && (
        tsbs.length === 0
          ? <div style={{ color: '#4b5563', fontSize: '14px' }}>No TSBs found for this vehicle.</div>
          : tsbs.map((t, i) => itemCard(
            <>
              <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>{t.title || 'TSB'}</div>
              {t.component && <div style={{ color: '#9ca3af', fontSize: '12px', marginBottom: '4px' }}>Component: {t.component}</div>}
              {t.desc && <div style={{ color: '#6b7280', fontSize: '12px' }}>{t.desc}</div>}
            </>,
            i
          ))
      )}

      {activeTab === 'recalls' && (
        recalls.length === 0
          ? <div style={{ color: '#4b5563', fontSize: '14px' }}>No open recalls found.</div>
          : recalls.map((r, i) => itemCard(
            <>
              <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>{r.component || 'Recall'}</div>
              {r.consequence && <div style={{ color: '#fca5a5', fontSize: '12px', marginBottom: '4px' }}>Risk: {r.consequence}</div>}
              {r.remedy && <div style={{ color: '#9ca3af', fontSize: '12px', marginBottom: '4px' }}>Remedy: {r.remedy}</div>}
              {r.nhtsa_id && <div style={{ color: '#6b7280', fontSize: '11px' }}>NHTSA: {r.nhtsa_id}</div>}
            </>,
            i
          ))
      )}

      {activeTab === 'maintenance' && (
        maintenance.length === 0
          ? <div style={{ color: '#4b5563', fontSize: '14px' }}>No maintenance data available.</div>
          : maintenance.map((m, i) => itemCard(
            <>
              <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>{m.desc || 'Maintenance'}</div>
              {m.mileage != null && <div style={{ color: '#d97706', fontSize: '12px' }}>Due at: {m.mileage.toLocaleString()} mi</div>}
            </>,
            i
          ))
      )}
    </div>
  )
}
