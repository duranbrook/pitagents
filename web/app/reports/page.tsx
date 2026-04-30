'use client'

import { useState, useEffect, useCallback, useRef, Suspense } from 'react'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'next/navigation'
import { AppShell } from '@/components/AppShell'
import { getAllReports, getReport, patchReportEstimate } from '@/lib/api'
import { useVoiceContext } from '@/contexts/VoiceContext'
import type { ReportSummary, ReportDetail, Finding, EstimateItem } from '@/lib/types'
import type { EditField } from '@/contexts/VoiceContext'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function severityIcon(s: string) {
  switch ((s ?? '').toLowerCase()) {
    case 'high':
    case 'urgent':
      return { icon: '✕', color: '#f87171' }
    case 'medium':
    case 'moderate':
      return { icon: '⚠', color: '#fb923c' }
    default:
      return { icon: '✓', color: '#4ade80' }
  }
}

function FindingCard({ f }: { f: Finding }) {
  const { icon, color } = severityIcon(f.severity)
  return (
    <div
      className="rounded-xl p-4"
      style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}
    >
      <div className="flex items-start gap-3 mb-2">
        <span className="text-base leading-none mt-0.5 flex-shrink-0" style={{ color }}>{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-semibold text-white">{f.part}</p>
            <span
              className="text-[10px] font-semibold px-2 py-0.5 rounded-full flex-shrink-0"
              style={{ background: `${color}18`, color }}
            >
              {f.severity}
            </span>
          </div>
          <p className="text-sm mt-1 leading-relaxed" style={{ color: 'rgba(255,255,255,0.5)' }}>{f.notes}</p>
        </div>
      </div>
      {f.photo_url && (
        <img
          src={f.photo_url}
          alt={f.part}
          className="mt-2 w-full max-h-52 object-cover rounded-lg"
          style={{ border: '1px solid rgba(255,255,255,0.07)' }}
        />
      )}
    </div>
  )
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-widest mb-2 px-0.5" style={{ color: 'rgba(255,255,255,0.3)' }}>
        {title}
      </p>
      <div
        className="rounded-xl p-4"
        style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)' }}
      >
        {children}
      </div>
    </div>
  )
}

function vehicleLabel(r: ReportSummary): string {
  const v = r.vehicle
  if (!v || (!v.year && !v.make)) return 'Unknown Vehicle'
  return [v.year, v.make, v.model].filter(Boolean).join(' ')
}

function EstimateTable({
  items,
  editingCell,
  patchError,
  onCellFocus,
  onCellChange,
  onCellBlur,
  onAddLine,
}: {
  items: EstimateItem[]
  editingCell: { row: number; field: 'hours' | 'rate' | 'parts' } | null
  patchError: string
  onCellFocus: (row: number, field: 'hours' | 'rate' | 'parts') => void
  onCellChange: (row: number, field: 'hours' | 'rate' | 'parts', value: string) => void
  onCellBlur: () => void
  onAddLine: () => void
}) {
  const colStyle = 'text-[10px] font-medium text-right'
  const cellStyle: React.CSSProperties = {
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.15)',
    borderRadius: '4px',
    color: 'white',
    fontSize: '12px',
    textAlign: 'right',
    padding: '2px 4px',
    width: '100%',
    outline: 'none',
  }

  return (
    <div>
      {/* Header */}
      <div
        className="grid gap-2 pb-2 mb-2"
        style={{
          gridTemplateColumns: '1fr 64px 64px 72px 72px',
          borderBottom: '1px solid rgba(255,255,255,0.07)',
        }}
      >
        {['Service', 'Hours', '$/hr', 'Parts', 'Total'].map(h => (
          <p
            key={h}
            className={`text-[10px] font-medium ${h !== 'Service' ? 'text-right' : ''}`}
            style={{ color: 'rgba(255,255,255,0.3)' }}
          >
            {h}
          </p>
        ))}
      </div>

      {/* Rows */}
      {items.map((item, i) => {
        const liveTotal = ((item.labor_hours * item.labor_rate) + item.parts_cost).toFixed(2)
        const isEditing = (field: 'hours' | 'rate' | 'parts') =>
          editingCell?.row === i && editingCell.field === field

        return (
          <div
            key={i}
            className="grid gap-2 py-2.5"
            style={{
              gridTemplateColumns: '1fr 64px 64px 72px 72px',
              borderBottom: '1px solid rgba(255,255,255,0.05)',
            }}
          >
            <div>
              <p className="text-sm font-medium text-white">{item.part}</p>
              <p className="text-[10px] mt-0.5" style={{ color: 'rgba(255,255,255,0.3)' }}>
                {item.labor_hours > 0 ? `${item.labor_hours.toFixed(1)} hrs @ $${item.labor_rate.toFixed(0)}/hr` : ''}
              </p>
            </div>

            <div className="self-center">
              {isEditing('hours') ? (
                <input
                  type="number" min="0" step="0.5"
                  defaultValue={item.labor_hours}
                  style={cellStyle}
                  autoFocus
                  onChange={e => onCellChange(i, 'hours', e.target.value)}
                  onBlur={onCellBlur}
                />
              ) : (
                <p
                  className={`${colStyle} cursor-pointer hover:text-white`}
                  style={{ color: 'rgba(255,255,255,0.5)' }}
                  onClick={() => onCellFocus(i, 'hours')}
                >
                  {item.labor_hours.toFixed(1)}
                </p>
              )}
            </div>

            <div className="self-center">
              {isEditing('rate') ? (
                <input
                  type="number" min="0" step="5"
                  defaultValue={item.labor_rate}
                  style={cellStyle}
                  autoFocus
                  onChange={e => onCellChange(i, 'rate', e.target.value)}
                  onBlur={onCellBlur}
                />
              ) : (
                <p
                  className={`${colStyle} cursor-pointer hover:text-white`}
                  style={{ color: 'rgba(255,255,255,0.5)' }}
                  onClick={() => onCellFocus(i, 'rate')}
                >
                  ${item.labor_rate.toFixed(0)}
                </p>
              )}
            </div>

            <div className="self-center">
              {isEditing('parts') ? (
                <input
                  type="number" min="0" step="1"
                  defaultValue={item.parts_cost}
                  style={cellStyle}
                  autoFocus
                  onChange={e => onCellChange(i, 'parts', e.target.value)}
                  onBlur={onCellBlur}
                />
              ) : (
                <p
                  className={`${colStyle} cursor-pointer hover:text-white`}
                  style={{ color: 'rgba(255,255,255,0.5)' }}
                  onClick={() => onCellFocus(i, 'parts')}
                >
                  {item.parts_cost === 0 ? '—' : `$${item.parts_cost.toFixed(2)}`}
                </p>
              )}
            </div>

            <p className="text-sm font-semibold text-right self-center text-white">
              ${liveTotal}
            </p>
          </div>
        )
      })}

      {patchError && (
        <p className="text-xs mt-2" style={{ color: '#f87171' }}>{patchError}</p>
      )}

      <button
        onClick={onAddLine}
        className="mt-3 text-xs px-3 py-1.5 rounded-lg transition-colors"
        style={{ border: '1px solid rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.5)', background: 'transparent' }}
        onMouseEnter={e => (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.85)'}
        onMouseLeave={e => (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.5)'}
      >
        + Add line
      </button>
    </div>
  )
}

function ReportsPageInner() {
  const searchParams = useSearchParams()
  const vehicleFilter = searchParams.get('vehicle')
  const preselectedId = searchParams.get('id')
  const voiceSelect = searchParams.get('voice_select')
  const [selectedId, setSelectedId] = useState<string | null>(preselectedId)

  const [items, setItems] = useState<EstimateItem[]>([])
  const [editingCell, setEditingCell] = useState<{ row: number; field: 'hours' | 'rate' | 'parts' } | null>(null)
  const [patchError, setPatchError] = useState('')
  const [pdfLoading, setPdfLoading] = useState(false)
  const [pdfError, setPdfError] = useState('')
  const itemsRef = useRef<EstimateItem[]>([])
  const pendingValueRef = useRef<string>('')

  const { data: reports = [], isLoading } = useQuery<ReportSummary[]>({
    queryKey: ['reports'],
    queryFn: getAllReports,
  })

  const { data: detail, isLoading: detailLoading } = useQuery<ReportDetail>({
    queryKey: ['report', selectedId],
    queryFn: () => getReport(selectedId!),
    enabled: !!selectedId,
  })

  useEffect(() => {
    if (!voiceSelect || reports.length === 0) return
    const q = voiceSelect.toLowerCase()
    const match = reports.find(r => vehicleLabel(r).toLowerCase().includes(q))
    if (match) setSelectedId(match.id)
  }, [voiceSelect, reports])

  // Sync local items when report detail loads
  useEffect(() => {
    if (detail) {
      setItems(detail.estimate)
      itemsRef.current = detail.estimate
    }
  }, [detail])

  const patchAndSync = useCallback(async (nextItems: EstimateItem[]) => {
    if (!detail) return
    setPatchError('')
    try {
      const patches = nextItems.map(it => ({
        part: it.part,
        labor_hours: it.labor_hours,
        labor_rate: it.labor_rate,
        parts_cost: it.parts_cost,
      }))
      const updated = await patchReportEstimate(detail.id, patches)
      setItems(updated.estimate)
      itemsRef.current = updated.estimate
    } catch {
      setPatchError('Failed to save estimate. Changes reverted.')
      setItems(itemsRef.current)
    }
  }, [detail])

  const handleCellFocus = useCallback((row: number, field: 'hours' | 'rate' | 'parts') => {
    setEditingCell({ row, field })
  }, [])

  const handleCellChange = useCallback((_row: number, _field: 'hours' | 'rate' | 'parts', value: string) => {
    pendingValueRef.current = value
  }, [])

  const handleCellBlur = useCallback(() => {
    if (!editingCell) return
    const { row, field } = editingCell
    const rawVal = parseFloat(pendingValueRef.current)
    const val = isNaN(rawVal) ? 0 : rawVal
    setEditingCell(null)
    pendingValueRef.current = ''
    setItems(prev => {
      const updated = [...prev]
      const item = { ...updated[row] }
      if (field === 'hours') item.labor_hours = val
      else if (field === 'rate') item.labor_rate = val
      else item.parts_cost = val
      updated[row] = item
      patchAndSync(updated)
      return updated
    })
  }, [editingCell, patchAndSync])

  const handleAddLine = useCallback(() => {
    const newItem: EstimateItem = {
      part: 'New service',
      labor_hours: 1.0,
      labor_rate: 90.0,
      parts_cost: 0,
      labor_cost: 0,
      total: 0,
    }
    setItems(prev => {
      const updated = [...prev, newItem]
      patchAndSync(updated)
      return updated
    })
  }, [patchAndSync])

  const handleOpenPdf = useCallback(async () => {
    if (!detail) return
    setPdfError('')
    setPdfLoading(true)
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') || '' : ''
      const resp = await fetch(`${API_URL}/reports/${detail.id}/pdf`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!resp.ok) throw new Error(`PDF fetch failed: ${resp.status}`)
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
    } catch {
      setPdfError('Could not load PDF. Please try again.')
    } finally {
      setPdfLoading(false)
    }
  }, [detail])

  const voice = useVoiceContext()

  useEffect(() => {
    if (!detail) return

    voice.registerEditLine((service: string, field: EditField, value: number) => {
      setItems(prev => {
        const idx = prev.findIndex(it =>
          it.part.toLowerCase().includes(service.toLowerCase())
        )
        if (idx === -1) return prev
        const updated = [...prev]
        const item = { ...updated[idx] }
        if (field === 'hours') item.labor_hours = value
        else if (field === 'rate') item.labor_rate = value
        else item.parts_cost = value
        updated[idx] = item
        patchAndSync(updated)
        return updated
      })
    })

    voice.registerAddLine((service: string, hours: number, rate: number, parts: number) => {
      setItems(prev => {
        const newItem: EstimateItem = {
          part: service,
          labor_hours: hours,
          labor_rate: rate,
          parts_cost: parts,
          labor_cost: 0,
          total: 0,
        }
        const updated = [...prev, newItem]
        patchAndSync(updated)
        return updated
      })
    })

    return () => {
      voice.registerEditLine(() => {})
      voice.registerAddLine(() => {})
    }
  }, [detail, voice, patchAndSync])

  const displayed = vehicleFilter
    ? reports.filter(r => r.vehicle?.vehicle_id === vehicleFilter)
    : reports

  return (
    <AppShell>
      <div className="flex h-full overflow-hidden">
        {/* Left panel: report list */}
        <div
          className="w-64 flex-shrink-0 flex flex-col"
          style={{ background: 'rgba(255,255,255,0.015)', borderRight: '1px solid rgba(255,255,255,0.07)' }}
        >
          <div
            className="p-3 flex items-center gap-2"
            style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
          >
            <span className="text-sm font-semibold text-white flex-1">Reports</span>
            {vehicleFilter && (
              <Link href="/reports" className="text-xs" style={{ color: 'var(--accent)' }}>
                clear filter
              </Link>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
            {isLoading && (
              <p className="text-xs px-2 py-3" style={{ color: 'rgba(255,255,255,0.3)' }}>Loading…</p>
            )}
            {displayed.map(r => {
              const active = selectedId === r.id
              return (
                <button
                  key={r.id}
                  onClick={() => setSelectedId(r.id)}
                  className="w-full text-left px-3 py-2.5 rounded-lg transition-colors"
                  style={active ? {
                    background: 'rgba(255,255,255,0.06)',
                    borderLeft: '2px solid var(--accent)',
                    paddingLeft: '10px',
                  } : {
                    borderLeft: '2px solid transparent',
                    paddingLeft: '10px',
                  }}
                >
                  <p className="text-xs font-semibold text-white truncate">{vehicleLabel(r)}</p>
                  <p className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.35)' }}>
                    {r.created_at ? new Date(r.created_at).toLocaleDateString() : '—'}
                    {r.total ? ` · $${r.total.toFixed(0)}` : ''}
                  </p>
                </button>
              )
            })}
            {!isLoading && displayed.length === 0 && (
              <p className="text-xs px-2 py-4 text-center" style={{ color: 'rgba(255,255,255,0.25)' }}>No reports</p>
            )}
          </div>
        </div>

        {/* Right panel: report detail */}
        <div className="flex-1 overflow-y-auto" style={{ background: '#030712' }}>
          {!selectedId ? (
            <div className="flex h-full items-center justify-center text-sm" style={{ color: 'rgba(255,255,255,0.2)' }}>
              Select a report
            </div>
          ) : detailLoading ? (
            <div className="flex h-full items-center justify-center text-sm" style={{ color: 'rgba(255,255,255,0.3)' }}>
              Loading…
            </div>
          ) : detail ? (
            <div className="p-6 max-w-3xl space-y-5">
              {/* Vehicle header */}
              <div>
                <h1 className="text-xl font-semibold text-white">
                  {[detail.vehicle?.year, detail.vehicle?.make, detail.vehicle?.model]
                    .filter(Boolean).join(' ') || 'Unknown Vehicle'}
                </h1>
                <div className="flex items-center gap-3 mt-1.5">
                  {detail.vehicle?.vin && (
                    <p className="text-xs font-mono" style={{ color: 'rgba(255,255,255,0.35)' }}>
                      VIN: {detail.vehicle.vin}
                    </p>
                  )}
                  {detail.created_at && (
                    <p className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>
                      {new Date(detail.created_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
              </div>

              {/* Summary */}
              {detail.summary && (
                <SectionCard title="Summary">
                  <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.65)' }}>
                    {detail.summary}
                  </p>
                </SectionCard>
              )}

              {/* Findings */}
              {detail.findings.length > 0 && (
                <SectionCard title="Inspection Findings">
                  <div className="space-y-3">
                    {detail.findings.map((f, i) => (
                      <FindingCard key={i} f={f} />
                    ))}
                  </div>
                </SectionCard>
              )}

              {/* Estimate */}
              {(items.length > 0 || detail.estimate.length > 0) && (
                <SectionCard title="Estimate">
                  <div>
                    <EstimateTable
                      items={items}
                      editingCell={editingCell}
                      patchError={patchError}
                      onCellFocus={handleCellFocus}
                      onCellChange={handleCellChange}
                      onCellBlur={handleCellBlur}
                      onAddLine={handleAddLine}
                    />
                    <div className="flex items-center justify-between pt-3">
                      <p className="text-sm font-semibold text-white">Grand Total</p>
                      <p className="text-lg font-bold" style={{ color: 'var(--accent)' }}>
                        ${items.reduce((sum, it) => sum + (it.labor_hours * it.labor_rate + it.parts_cost), 0).toFixed(2)}
                      </p>
                    </div>
                  </div>
                </SectionCard>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-1 pb-6">
                <button
                  onClick={() => navigator.clipboard.writeText(`${window.location.origin}/r/${detail.share_token}`)}
                  className="text-sm px-4 py-2 rounded-lg transition-colors"
                  style={{ border: '1px solid rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.6)', background: 'transparent' }}
                  onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)'}
                  onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = 'transparent'}
                >
                  📋 Copy Share Link
                </button>
                <button
                  onClick={handleOpenPdf}
                  disabled={pdfLoading}
                  className="text-sm px-4 py-2 rounded-lg transition-opacity text-white"
                  style={{ background: 'var(--accent)', opacity: pdfLoading ? 0.6 : 1 }}
                >
                  {pdfLoading ? 'Loading…' : '🖨 Open Report PDF'}
                </button>
                {pdfError && (
                  <p className="text-xs self-center" style={{ color: '#f87171' }}>{pdfError}</p>
                )}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </AppShell>
  )
}

export default function ReportsPage() {
  return (
    <Suspense>
      <ReportsPageInner />
    </Suspense>
  )
}
