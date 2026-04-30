'use client'

import { useState, useEffect, Suspense } from 'react'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'next/navigation'
import { AppShell } from '@/components/AppShell'
import { getAllReports, getReport } from '@/lib/api'
import type { ReportSummary, ReportDetail, Finding } from '@/lib/types'

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

function formatCurrency(n: number): string {
  return n === 0 ? '—' : `$${n.toFixed(2)}`
}

function ReportsPageInner() {
  const searchParams = useSearchParams()
  const vehicleFilter = searchParams.get('vehicle')
  const preselectedId = searchParams.get('id')
  const voiceSelect = searchParams.get('voice_select')
  const [selectedId, setSelectedId] = useState<string | null>(preselectedId)

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
              {detail.estimate.length > 0 && (
                <SectionCard title="Estimate">
                  <div>
                    <div className="grid grid-cols-[1fr_60px_60px_72px] gap-2 pb-2 mb-2" style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                      {['Service', 'Labor', 'Parts', 'Total'].map(h => (
                        <p key={h} className={`text-[10px] font-medium ${h !== 'Service' ? 'text-right' : ''}`} style={{ color: 'rgba(255,255,255,0.3)' }}>{h}</p>
                      ))}
                    </div>
                    {detail.estimate.map((item, i) => {
                      const hourlyRate = item.labor_hours > 0 ? item.labor_cost / item.labor_hours : 0
                      return (
                        <div
                          key={i}
                          className="grid grid-cols-[1fr_60px_60px_72px] gap-2 py-2.5"
                          style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}
                        >
                          <div>
                            <p className="text-sm font-medium text-white">{item.part}</p>
                            {item.labor_hours > 0 && (
                              <p className="text-[10px] mt-0.5" style={{ color: 'rgba(255,255,255,0.3)' }}>
                                {item.labor_hours.toFixed(1)} hrs @ {formatCurrency(hourlyRate)}/hr
                              </p>
                            )}
                          </div>
                          <p className="text-xs text-right self-center" style={{ color: 'rgba(255,255,255,0.5)' }}>{formatCurrency(item.labor_cost)}</p>
                          <p className="text-xs text-right self-center" style={{ color: 'rgba(255,255,255,0.5)' }}>{formatCurrency(item.parts_cost)}</p>
                          <p className="text-sm font-semibold text-right self-center text-white">{formatCurrency(item.total)}</p>
                        </div>
                      )
                    })}
                    <div className="flex items-center justify-between pt-3">
                      <p className="text-sm font-semibold text-white">Grand Total</p>
                      <p className="text-lg font-bold" style={{ color: 'var(--accent)' }}>
                        ${detail.total.toFixed(2)}
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
                <a
                  href={`${API_URL}/reports/${detail.id}/pdf`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm px-4 py-2 rounded-lg transition-opacity text-white"
                  style={{ background: 'var(--accent)' }}
                >
                  🖨 Open Report PDF
                </a>
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
