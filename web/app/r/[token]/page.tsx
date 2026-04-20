'use client'

import { use } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'next/navigation'
import { getConsumerReport } from '@/lib/api'

interface Finding {
  description: string
  severity: 'urgent' | 'moderate' | 'low'
}

interface EstimateItem {
  label: string
  amount: number
}

interface Vehicle {
  year: number
  make: string
  model: string
  vin?: string
  mileage?: number
  tire_size?: string
}

interface ConsumerReport {
  id: string
  vehicle: Vehicle
  summary?: string
  findings?: Finding[]
  estimate_items?: EstimateItem[]
  total?: number
  media_urls?: string[]
  created_at?: string
}

const severityStyles: Record<string, string> = {
  urgent: 'bg-red-100 text-red-800 border border-red-200',
  moderate: 'bg-yellow-100 text-yellow-800 border border-yellow-200',
  low: 'bg-green-100 text-green-800 border border-green-200',
}

function isVideoUrl(url: string): boolean {
  return /\.(mp4|mov|webm|ogg)(\?|$)/i.test(url)
}

export default function ConsumerReportPage() {
  const params = useParams()
  const token = Array.isArray(params.token) ? params.token[0] : params.token as string

  const { data: report, isLoading, isError } = useQuery<ConsumerReport>({
    queryKey: ['consumer-report', token],
    queryFn: () => getConsumerReport(token),
    enabled: !!token,
  })

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-500 text-sm">Loading report...</p>
        </div>
      </div>
    )
  }

  if (isError || !report) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center max-w-sm">
          <div className="text-5xl mb-4">&#x26A0;&#xFE0F;</div>
          <h1 className="text-xl font-semibold text-gray-900 mb-2">Report Not Found</h1>
          <p className="text-gray-500 text-sm">
            This report link may have expired or is invalid. Please contact your service shop for a new link.
          </p>
        </div>
      </div>
    )
  }

  const { vehicle, summary, findings = [], estimate_items = [], total, media_urls = [], created_at } = report

  const photos = media_urls.filter(url => !isVideoUrl(url))
  const videos = media_urls.filter(url => isVideoUrl(url))

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-blue-700 text-white px-4 py-5 text-center shadow-md">
        <h1 className="text-lg font-bold tracking-wide uppercase">Vehicle Inspection Report</h1>
        {created_at && (
          <p className="text-blue-200 text-xs mt-1">
            {new Date(created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
        )}
      </header>

      <main className="max-w-xl mx-auto px-4 py-6 space-y-6">
        {/* Vehicle Info */}
        <section className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">Vehicle</h2>
          <p className="text-xl font-bold text-gray-900 mb-3">
            {vehicle ? `${vehicle.year} ${vehicle.make} ${vehicle.model}` : '—'}
          </p>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            {vehicle?.vin && (
              <>
                <dt className="text-gray-500">VIN</dt>
                <dd className="text-gray-900 font-mono break-all">{vehicle.vin}</dd>
              </>
            )}
            {vehicle?.mileage != null && (
              <>
                <dt className="text-gray-500">Mileage</dt>
                <dd className="text-gray-900">{vehicle.mileage.toLocaleString()} mi</dd>
              </>
            )}
            {vehicle?.tire_size && (
              <>
                <dt className="text-gray-500">Tire Size</dt>
                <dd className="text-gray-900">{vehicle.tire_size}</dd>
              </>
            )}
          </dl>
        </section>

        {/* Summary */}
        {summary && (
          <section className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">Summary</h2>
            <p className="text-gray-800 text-sm leading-relaxed">{summary}</p>
          </section>
        )}

        {/* Findings */}
        {findings.length > 0 && (
          <section className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">Findings</h2>
            <ul className="space-y-3">
              {findings.map((finding, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <span
                    className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap mt-0.5 ${severityStyles[finding.severity] ?? severityStyles.low}`}
                  >
                    {finding.severity}
                  </span>
                  <span className="text-gray-800 text-sm leading-relaxed">{finding.description}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Estimate */}
        {(estimate_items.length > 0 || total != null) && (
          <section className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">Estimate</h2>
            {estimate_items.length > 0 && (
              <table className="w-full text-sm mb-3">
                <tbody className="divide-y divide-gray-100">
                  {estimate_items.map((item, idx) => (
                    <tr key={idx}>
                      <td className="py-2 text-gray-700">{item.label}</td>
                      <td className="py-2 text-right text-gray-900 font-medium">
                        ${Number(item.amount).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {total != null && (
              <div className="flex justify-between items-center border-t border-gray-200 pt-3">
                <span className="font-semibold text-gray-900">Total</span>
                <span className="font-bold text-blue-700 text-lg">${Number(total).toFixed(2)}</span>
              </div>
            )}
          </section>
        )}

        {/* Media */}
        {(photos.length > 0 || videos.length > 0) && (
          <section className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">Attached Media</h2>

            {photos.length > 0 && (
              <div className="grid grid-cols-2 gap-2 mb-4">
                {photos.map((url, idx) => (
                  <a key={idx} href={url} target="_blank" rel="noopener noreferrer">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={url}
                      alt={`Inspection photo ${idx + 1}`}
                      className="w-full h-36 object-cover rounded-lg border border-gray-200 hover:opacity-90 transition-opacity"
                    />
                  </a>
                ))}
              </div>
            )}

            {videos.length > 0 && (
              <div className="space-y-3">
                {videos.map((url, idx) => (
                  <video
                    key={idx}
                    src={url}
                    controls
                    playsInline
                    className="w-full rounded-lg border border-gray-200"
                    aria-label={`Inspection video ${idx + 1}`}
                  />
                ))}
              </div>
            )}
          </section>
        )}
      </main>

      <footer className="text-center text-xs text-gray-400 py-6 px-4">
        This report was prepared by your service technician. For questions, contact the shop directly.
      </footer>
    </div>
  )
}
