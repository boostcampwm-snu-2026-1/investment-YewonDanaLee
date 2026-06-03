'use client'
import { useEffect, useState } from 'react'
import type { DualQuote } from '@/lib/naver'

export function useStockPolling(ticker: string, intervalMs = 10_000) {
  const [data, setData] = useState<DualQuote | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      try {
        const res = await fetch(`/api/stock/${ticker}`, { cache: 'no-store' })
        if (!res.ok) throw new Error(String(res.status))
        const json: DualQuote = await res.json()
        if (!cancelled) { setData(json); setLoading(false); setError(false) }
      } catch {
        if (!cancelled) { setLoading(false); setError(true) }
      }
    }

    load()
    const id = setInterval(load, intervalMs)
    return () => { cancelled = true; clearInterval(id) }
  }, [ticker, intervalMs])

  return { data, loading, error }
}
