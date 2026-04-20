'use client'

import { useQuery, useMutation } from '@tanstack/react-query'
import Link from 'next/link'
import { use, useState } from 'react'
import { getReport, sendReport } from '@/lib/api'

interface Vehicle {
  year: number
  make: string
  model: string
  vin: string
  mileage: number
  tire_size: string
}

interface Finding {
  part: string
  severity: string
  notes: string
}

interface EstimateItem {
  part: string
  labor_hours: number
  labor_cost: number
  parts_cost: number
  total: number
}

interface Report {
  id: string
  vehicle: Vehicle
  summary: string
  findings: Finding[]
  estimate: EstimateItem[]
  total: number
  created_at: string
}

export default function ReportDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = use(params)

  const { data: report, isLoading, isError } = useQuery<Report>({
    queryKey: ['report', id],
    queryFn: () => getReport(id),
    enabled: !!id,
  })

  const [showSendForm, setShowSendForm] = useState(false)
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [sendSuccess, setSendSuccess] = useState(false)

  const { mutate: send, isPending: isSending, isError: isSendError } = useMutation({
    mutationFn: () => sendReport(id, { phone: phone || undefined, email: email || undefined }),
    onSuccess: () => {
      setSendSuccess(true)
      setShowSendForm(false)
      setPhone('')
      setEmail('')
    },
  })

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500 text-sm">Loading report...</p>
      </div>
    )
  }

  if (isError || !report) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 text-sm mb-4">Failed to load report.</p>
          <Link href="/dashboard" className="text-blue-600 hover:underline text-sm">
            Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  const { vehicle, summary, findings = [], estimate = [], total } = report

  return (
    <div className="min-h-screen bg-gray-50 print:bg-white">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 print:hidden">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            <span aria-hidden="true">←</span>
            Back to Dashboard
          </Link>
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                setShowSendForm((prev) => !prev)
                setSendSuccess(false)
              }}
              className="px-4 py-2 rounded-md bg-green-600 text-white text-sm font-medium hover:bg-green-700 transition-colors"
            >
              Send to Customer
            </button>
            <button
              onClick={() => window.print()}
              className="px-4 py-2 rounded-md bg-gray-800 text-white text-sm font-medium hover:bg-gray-900 transition-colors"
            >
              Print PDF
            </button>
          </div>
        </div>
      </header>

      <main className="px-6 py-8 max-w-4xl mx-auto space-y-8">
        {/* Send to Customer form */}
        {showSendForm && (
          <div className="rounded-lg border border-green-200 bg-green-50 p-5 print:hidden">
            <h2 className="text-base font-semibold text-green-800 mb-4">Send Report to Customer</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              <div>
                <label htmlFor="send-phone" className="block text-sm font-medium text-gray-700 mb-1">
                  Phone Number
                </label>
                <input
                  id="send-phone"
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+1 555 000 0000"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                />
              </div>
              <div>
                <label htmlFor="send-email" className="block text-sm font-medium text-gray-700 mb-1">
                  Email Address
                </label>
                <input
                  id="send-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="customer@example.com"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                />
              </div>
            </div>
            {isSendError && (
              <p className="text-red-600 text-xs mb-3">Failed to send. Please try again.</p>
            )}
            <div className="flex items-center gap-3">
              <button
                onClick={() => send()}
                disabled={isSending || (!phone && !email)}
                className="px-4 py-2 rounded-md bg-green-600 text-white text-sm font-medium hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSending ? 'Sending...' : 'Send'}
              </button>
              <button
                onClick={() => setShowSendForm(false)}
                className="px-4 py-2 rounded-md border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {sendSuccess && (
          <div className="rounded-lg border border-green-200 bg-green-50 px-5 py-3 text-green-800 text-sm print:hidden">
            Report sent successfully.
          </div>
        )}

        {/* Vehicle Info */}
        <section className="rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
            <h2 className="text-base font-semibold text-gray-900">Vehicle Information</h2>
          </div>
          <div className="px-6 py-4 grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-0.5">Year / Make / Model</p>
              <p className="text-sm font-medium text-gray-900">
                {vehicle
                  ? `${vehicle.year} ${vehicle.make} ${vehicle.model}`
                  : '—'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-0.5">VIN</p>
              <p className="text-sm font-mono text-gray-900">{vehicle?.vin || '—'}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-0.5">Mileage</p>
              <p className="text-sm text-gray-900">
                {vehicle?.mileage != null
                  ? vehicle.mileage.toLocaleString() + ' mi'
                  : '—'}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-0.5">Tire Size</p>
              <p className="text-sm text-gray-900">{vehicle?.tire_size || '—'}</p>
            </div>
          </div>
        </section>

        {/* Summary */}
        <section className="rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
            <h2 className="text-base font-semibold text-gray-900">Summary</h2>
          </div>
          <div className="px-6 py-4">
            <p className="text-sm text-gray-700 leading-relaxed">{summary || 'No summary available.'}</p>
          </div>
        </section>

        {/* Findings */}
        <section className="rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
            <h2 className="text-base font-semibold text-gray-900">Findings</h2>
          </div>
          {findings.length === 0 ? (
            <p className="px-6 py-4 text-sm text-gray-500">No findings recorded.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Part</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Severity</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {findings.map((f, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-6 py-3 font-medium text-gray-900">{f.part || '—'}</td>
                      <td className="px-6 py-3">
                        <SeverityBadge severity={f.severity} />
                      </td>
                      <td className="px-6 py-3 text-gray-600">{f.notes || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Estimate */}
        <section className="rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
            <h2 className="text-base font-semibold text-gray-900">Estimate</h2>
          </div>
          {estimate.length === 0 ? (
            <p className="px-6 py-4 text-sm text-gray-500">No estimate items.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Part</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Labor Hrs</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Labor Cost</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Parts Cost</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {estimate.map((item, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-6 py-3 font-medium text-gray-900">{item.part || '—'}</td>
                      <td className="px-6 py-3 text-right text-gray-700">
                        {item.labor_hours != null ? item.labor_hours.toFixed(1) : '—'}
                      </td>
                      <td className="px-6 py-3 text-right text-gray-700">
                        {item.labor_cost != null ? `$${Number(item.labor_cost).toFixed(2)}` : '—'}
                      </td>
                      <td className="px-6 py-3 text-right text-gray-700">
                        {item.parts_cost != null ? `$${Number(item.parts_cost).toFixed(2)}` : '—'}
                      </td>
                      <td className="px-6 py-3 text-right font-medium text-gray-900">
                        {item.total != null ? `$${Number(item.total).toFixed(2)}` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-gray-50">
                  <tr>
                    <td colSpan={4} className="px-6 py-3 text-right text-sm font-semibold text-gray-900">
                      Grand Total
                    </td>
                    <td className="px-6 py-3 text-right text-sm font-bold text-gray-900">
                      {total != null ? `$${Number(total).toFixed(2)}` : '—'}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  const lower = (severity || '').toLowerCase()
  let classes = 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium '
  if (lower === 'critical' || lower === 'high') {
    classes += 'bg-red-100 text-red-800'
  } else if (lower === 'medium' || lower === 'moderate') {
    classes += 'bg-yellow-100 text-yellow-800'
  } else if (lower === 'low') {
    classes += 'bg-green-100 text-green-800'
  } else {
    classes += 'bg-gray-100 text-gray-700'
  }
  return <span className={classes}>{severity || '—'}</span>
}
