'use client'
import { useEffect, useState } from 'react'
import type { DualQuote } from '@/lib/naver'

// 모듈 레벨 캐시 — 탭 전환 시 즉시 이전 데이터 표시
const _cache = new Map<string, DualQuote>()

export function useStockPolling(ticker: string, intervalMs = 10_000) {
  const [data, setData] = useState<DualQuote | null>(() => _cache.get(ticker) ?? null)
  const [loading, setLoading] = useState(!_cache.has(ticker))
  const [error, setError] = useState(false)

  useEffect(() => {
    // 캐시에 데이터가 있으면 즉시 표시 (로딩 없음)
    const cached = _cache.get(ticker)
    if (cached) {
      setData(cached)
      setLoading(false)
      setError(false)
    } else {
      setData(null)
      setLoading(true)
      setError(false)
    }

    let cancelled = false

    const load = async () => {
      try {
        const res = await fetch(`/api/stock/${ticker}`, { cache: 'no-store' })
        if (!res.ok) throw new Error(String(res.status))
        const json: DualQuote = await res.json()
        _cache.set(ticker, json)
        if (!cancelled) {
          setData(json)
          setLoading(false)
          setError(false)
        }
      } catch {
        if (!cancelled) {
          setLoading(false)
          setError(!_cache.has(ticker))
        }
      }
    }

    load()
    const id = setInterval(load, intervalMs)
    return () => { cancelled = true; clearInterval(id) }
  }, [ticker, intervalMs])

  return { data, loading, error }
}
