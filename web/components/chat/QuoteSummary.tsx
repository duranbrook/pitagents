'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { api } from '@/lib/api'

interface LineItem {
  description: string
  quantity: number | string
  unit_price: number
  total: number
}

interface Quote {
  id: string
  status: 'draft' | 'final'
  line_items: LineItem[]
  total: number
}

interface Props {
  quoteId: string | null
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

export function QuoteSummary({ quoteId }: Props) {
  const [quote, setQuote] = useState<Quote | null>(null)
  const [loading, setLoading] = useState(false)
  const [finalizing, setFinalizing] = useState(false)
  const [error, setError] = useState('')
  // Ref to allow the interval to see the latest quote status without stale closure
  const quoteStatusRef = useRef<string | undefined>(undefined)

  const fetchQuote = useCallback(async () => {
    if (!quoteId) return
    try {
      const res = await api.get<Quote>(`/quotes/${quoteId}`)
      quoteStatusRef.current = res.data.status
      setQuote(res.data)
    } catch {
      // silently ignore fetch errors during polling
    }
  }, [quoteId])

  useEffect(() => {
    if (!quoteId) {
      setQuote(null)
      quoteStatusRef.current = undefined
      return
    }
    setLoading(true)
    fetchQuote().finally(() => setLoading(false))

    const interval = setInterval(async () => {
      // Stop polling once the quote is finalized
      if (quoteStatusRef.current === 'final') {
        clearInterval(interval)
        return
      }
      await fetchQuote()
    }, 3000)

    return () => clearInterval(interval)
  }, [quoteId, fetchQuote])

  async function handleFinalize() {
    if (!quoteId) return
    setFinalizing(true)
    setError('')
    try {
      const res = await api.put<Quote>(`/quotes/${quoteId}/finalize`)
      setQuote(res.data)
    } catch {
      setError('Failed to finalize quote. Please try again.')
    } finally {
      setFinalizing(false)
    }
  }

  return (
    <div className="w-72 flex-shrink-0 border-l border-gray-800 bg-gray-900 flex flex-col">
      {/* Header */}
      <div className="px-4 pt-4 pb-3 border-b border-gray-800">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Quote Summary</h2>
          {quote?.status === 'final' && (
            <span className="text-xs text-emerald-400 font-medium">Finalized</span>
          )}
          {quote?.status === 'draft' && (
            <span className="text-xs text-amber-400 font-medium">Draft</span>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {!quoteId && (
          <p className="text-xs text-gray-500 mt-4 text-center">No quote yet</p>
        )}

        {quoteId && loading && !quote && (
          <p className="text-xs text-gray-500 mt-4 text-center">Loading…</p>
        )}

        {quote && (
          <>
            {quote.line_items.length === 0 ? (
              <p className="text-xs text-gray-500 mt-2 text-center">No line items yet</p>
            ) : (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-800">
                    <th className="text-left pb-2 font-medium">Description</th>
                    <th className="text-right pb-2 font-medium">Qty</th>
                    <th className="text-right pb-2 font-medium">Price</th>
                    <th className="text-right pb-2 font-medium">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {quote.line_items.map((item, i) => (
                    <tr key={i} className="border-b border-gray-800/60">
                      <td className="py-2 text-gray-200 pr-2">{item.description}</td>
                      <td className="py-2 text-gray-400 text-right">{item.quantity}</td>
                      <td className="py-2 text-gray-400 text-right">{formatCurrency(item.unit_price)}</td>
                      <td className="py-2 text-gray-200 text-right">{formatCurrency(item.total)}</td>
                    </tr>
                  ))}
                  {/* Total row */}
                  <tr>
                    <td colSpan={3} className="pt-3 text-right font-semibold text-white pr-2">TOTAL</td>
                    <td className="pt-3 text-right font-semibold text-white">{formatCurrency(quote.total)}</td>
                  </tr>
                </tbody>
              </table>
            )}
          </>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 pb-4 pt-2 border-t border-gray-800">
        {error && <p className="text-xs text-red-400 mb-2">{error}</p>}
        {quote?.status === 'draft' && quote.line_items.length > 0 && (
          <button
            onClick={handleFinalize}
            disabled={finalizing}
            className="w-full py-2 rounded-lg bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white text-sm font-medium transition-colors"
          >
            {finalizing ? 'Finalizing…' : 'Finalize Quote'}
          </button>
        )}
        {quote?.status === 'final' && (
          <p className="text-xs text-emerald-400 text-center">Quote finalized</p>
        )}
        {!quoteId && (
          <p className="text-xs text-gray-600 text-center">Start chatting to build a quote</p>
        )}
      </div>
    </div>
  )
}
