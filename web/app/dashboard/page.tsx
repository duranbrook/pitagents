'use client'

import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { getReports } from '@/lib/api'

interface Report {
  id: string
  vehicle: {
    year: number
    make: string
    model: string
  }
  summary: string
  total: number
  created_at: string
}

export default function DashboardPage() {
  const { data: reports, isLoading, isError } = useQuery<Report[]>({
    queryKey: ['reports'],
    queryFn: getReports,
  })

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-semibold text-gray-900">Inspection Reports</h1>
      </header>

      <main className="px-6 py-8 max-w-6xl mx-auto">
        {isLoading && (
          <p className="text-gray-500 text-sm">Loading reports...</p>
        )}

        {isError && (
          <p className="text-red-600 text-sm">Failed to load reports. Please try again.</p>
        )}

        {!isLoading && !isError && reports && reports.length === 0 && (
          <div className="text-center py-16">
            <p className="text-gray-500 text-lg">No reports yet</p>
          </div>
        )}

        {!isLoading && !isError && reports && reports.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Vehicle
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Summary
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {reports.map((report) => (
                  <tr key={report.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                      {report.vehicle
                        ? `${report.vehicle.year} ${report.vehicle.make} ${report.vehicle.model}`
                        : '—'}
                    </td>
                    <td className="px-6 py-4 text-gray-600 max-w-xs truncate">
                      {report.summary || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-900">
                      {report.total != null
                        ? `$${Number(report.total).toFixed(2)}`
                        : '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                      {report.created_at
                        ? new Date(report.created_at).toLocaleDateString()
                        : '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link
                        href={`/dashboard/reports/${report.id}`}
                        className="inline-flex items-center px-3 py-1.5 rounded-md bg-blue-600 text-white text-xs font-medium hover:bg-blue-700 transition-colors"
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}
