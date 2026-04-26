'use client'

import { useState, Suspense } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'next/navigation'
import { AppShell } from '@/components/AppShell'
import { getAllReports, getReport } from '@/lib/api'
import type { ReportSummary, ReportDetail, Finding } from '@/lib/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const SEVERITY_CLASSES: Record<string, string> = {
  high: 'bg-red-900/40 text-red-300 border-red-800',
  urgent: 'bg-red-900/40 text-red-300 border-red-800',
  medium: 'bg-yellow-900/40 text-yellow-300 border-yellow-800',
  moderate: 'bg-yellow-900/40 text-yellow-300 border-yellow-800',
  low: 'bg-green-900/40 text-green-300 border-green-800',
}
function severityClass(s: string) {
  return SEVERITY_CLASSES[(s ?? '').toLowerCase()] ?? 'bg-gray-800 text-gray-400 border-gray-700'
}

function FindingCard({ f }: { f: Finding }) {
  return (
    <div className="border border-gray-700 rounded-xl p-4">
      <div className="flex items-start justify-between gap-3 mb-2">
        <p className="text-sm font-semibold text-white">{f.part}</p>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full border flex-shrink-0 ${severityClass(f.severity)}`}>
          {f.severity}
        </span>
      </div>
      <p className="text-sm text-gray-400 leading-relaxed">{f.notes}</p>
      {f.photo_url && (
        <img
          src={f.photo_url}
          alt={f.part}
          className="mt-3 w-full max-h-52 object-cover rounded-lg border border-gray-700"
        />
      )}
    </div>
  )
}

function vehicleLabel(r: ReportSummary): string {
  const v = r.vehicle
  if (!v || (!v.year && !v.make)) return 'Unknown Vehicle'
  return [v.year, v.make, v.model].filter(Boolean).join(' ')
}

function ReportsPageInner() {
  const searchParams = useSearchParams()
  const vehicleFilter = searchParams.get('vehicle')
  const preselectedId = searchParams.get('id')
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

  const displayed = vehicleFilter
    ? reports.filter(r => r.vehicle?.vehicle_id === vehicleFilter)
    : reports

  return (
    <AppShell>
      <div className="flex h-full overflow-hidden">
        {/* Left panel: report list */}
        <div className="w-64 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
          <div className="p-3 border-b border-gray-800 flex items-center gap-2">
            <span className="text-sm font-semibold text-white flex-1">Reports</span>
            {vehicleFilter && (
              <a href="/reports" className="text-xs text-indigo-400 hover:underline">
                clear filter
              </a>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
            {isLoading && (
              <p className="text-gray-500 text-xs px-2 py-3">Loading…</p>
            )}
            {displayed.map(r => (
              <button
                key={r.id}
                onClick={() => setSelectedId(r.id)}
                className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors ${
                  selectedId === r.id
                    ? 'bg-gray-700 border-l-2 border-indigo-500 pl-2'
                    : 'hover:bg-gray-800'
                }`}
              >
                <p className="text-xs font-semibold text-white truncate">{vehicleLabel(r)}</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {r.created_at ? new Date(r.created_at).toLocaleDateString() : '—'}
                  {r.total ? ` · $${r.total.toFixed(0)}` : ''}
                </p>
              </button>
            ))}
            {!isLoading && displayed.length === 0 && (
              <p className="text-gray-600 text-xs px-2 py-4 text-center">No reports</p>
            )}
          </div>
        </div>

        {/* Right panel: report detail */}
        <div className="flex-1 bg-gray-950 overflow-y-auto">
          {!selectedId ? (
            <div className="flex h-full items-center justify-center text-gray-600 text-sm">
              Select a report
            </div>
          ) : detailLoading ? (
            <div className="flex h-full items-center justify-center text-gray-500 text-sm">
              Loading…
            </div>
          ) : detail ? (
            <div className="p-6 max-w-3xl space-y-8">
              {/* Header */}
              <div>
                <h1 className="text-xl font-semibold text-white">
                  {[detail.vehicle?.year, detail.vehicle?.make, detail.vehicle?.model]
                    .filter(Boolean)
                    .join(' ') || 'Unknown Vehicle'}
                </h1>
                <div className="flex items-center gap-3 mt-1">
                  {detail.vehicle?.vin && (
                    <p className="text-xs text-gray-500 font-mono">VIN: {detail.vehicle.vin}</p>
                  )}
                  {detail.created_at && (
                    <p className="text-xs text-gray-500">
                      {new Date(detail.created_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
              </div>

              {/* Summary */}
              {detail.summary && (
                <section>
                  <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold mb-2">
                    Summary
                  </p>
                  <p className="text-sm text-gray-300 leading-relaxed">{detail.summary}</p>
                </section>
              )}

              {/* Findings */}
              {detail.findings.length > 0 && (
                <section>
                  <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold mb-3">
                    Findings
                  </p>
                  <div className="space-y-3">
                    {detail.findings.map((f, i) => (
                      <FindingCard key={i} f={f} />
                    ))}
                  </div>
                </section>
              )}

              {/* Estimate */}
              {detail.estimate.length > 0 && (
                <section>
                  <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold mb-3">
                    Estimate
                  </p>
                  <div className="border border-gray-700 rounded-xl overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-800">
                        <tr>
                          <th className="text-left text-xs text-gray-400 px-4 py-2.5 font-medium">
                            Service
                          </th>
                          <th className="text-right text-xs text-gray-400 px-4 py-2.5 font-medium">
                            Labor
                          </th>
                          <th className="text-right text-xs text-gray-400 px-4 py-2.5 font-medium">
                            Parts
                          </th>
                          <th className="text-right text-xs text-gray-400 px-4 py-2.5 font-medium">
                            Total
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-800">
                        {detail.estimate.map((item, i) => (
                          <tr key={i}>
                            <td className="px-4 py-2.5 text-white font-medium">{item.part}</td>
                            <td className="px-4 py-2.5 text-right text-gray-400">
                              ${item.labor_cost.toFixed(2)}
                            </td>
                            <td className="px-4 py-2.5 text-right text-gray-400">
                              ${item.parts_cost.toFixed(2)}
                            </td>
                            <td className="px-4 py-2.5 text-right text-white font-semibold">
                              ${item.total.toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot className="bg-gray-800">
                        <tr>
                          <td colSpan={3} className="px-4 py-2.5 text-right text-sm font-semibold text-white">
                            Grand Total
                          </td>
                          <td className="px-4 py-2.5 text-right text-indigo-400 font-bold text-base">
                            ${detail.total.toFixed(2)}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </section>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-1">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(
                      `${window.location.origin}/r/${detail.share_token}`,
                    )
                  }}
                  className="text-sm border border-gray-700 text-gray-300 px-4 py-2 rounded-lg hover:bg-gray-800 transition-colors"
                >
                  📋 Copy Share Link
                </button>
                <a
                  href={`${API_URL}/reports/${detail.id}/pdf`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-500 transition-colors"
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
