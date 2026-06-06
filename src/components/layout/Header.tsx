'use client'
import { useEffect, useState } from 'react'
import { useTheme } from 'next-themes'

const UP = '#E74C3C'
const DOWN = '#3498DB'
const NEUTRAL = '#888780'

interface FxData {
  usdKrw: number
  diffAmount: number
  diffRate: number
  direction: 'up' | 'down' | 'neutral'
}

export default function Header() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const [time, setTime] = useState('')
  const [fx, setFx] = useState<FxData | null>(null)

  useEffect(() => {
    setMounted(true)

    const tick = () =>
      setTime(new Date().toLocaleTimeString('ko-KR', {
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
      }))
    tick()
    const tickId = setInterval(tick, 1000)

    const loadFx = () =>
      fetch('/api/usdkrw', { cache: 'no-store' })
        .then(r => r.ok ? r.json() : null)
        .then(d => { if (d?.usdKrw != null) setFx(d) })
        .catch(() => {})
    loadFx()
    const fxId = setInterval(loadFx, 10_000)

    return () => { clearInterval(tickId); clearInterval(fxId) }
  }, [])

  const diffColor = fx
    ? fx.direction === 'up' ? UP : fx.direction === 'down' ? DOWN : NEUTRAL
    : NEUTRAL

  return (
    <header
      className="sticky top-0 z-50 border-b"
      style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border)' }}
    >
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">

        {/* 좌: 로고 */}
        <span className="font-bold text-xl tracking-tight" style={{ color: 'var(--text-1)' }}>
          YENLAB
        </span>

        {/* 중: USD/KRW */}
        <div className="flex items-baseline gap-2 tabular-nums">
          <span className="text-xs font-medium" style={{ color: 'var(--text-2)' }}>
            USD/KRW
          </span>
          <span className="text-sm font-semibold" style={{ color: 'var(--text-1)' }}>
            {fx
              ? fx.usdKrw.toLocaleString('ko-KR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
              : '—'}
          </span>
          {fx && (
            <span className="text-xs font-medium" style={{ color: diffColor }}>
              {fx.diffAmount > 0 ? '▲' : fx.diffAmount < 0 ? '▼' : ''}{Math.abs(fx.diffAmount).toFixed(2)}
              &ensp;({fx.diffRate > 0 ? '+' : ''}{fx.diffRate.toFixed(2)}%)
            </span>
          )}
        </div>

        {/* 우: 시각 + 테마 토글 */}
        <div className="flex items-center gap-4">
          {mounted && (
            <span className="text-xs tabular-nums" style={{ color: 'var(--text-2)' }}>
              {time}
            </span>
          )}
          {mounted && (
            <button
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="w-16 h-8 rounded-full flex items-center px-1 transition-colors"
              style={{ backgroundColor: 'var(--bg-muted)', border: '1px solid var(--border)' }}
              aria-label="테마 전환"
            >
              <span
                className="w-6 h-6 rounded-full flex items-center justify-center text-xs transition-transform"
                style={{
                  backgroundColor: 'var(--bg-card)',
                  transform: theme === 'dark' ? 'translateX(32px)' : 'translateX(0)',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
                }}
              >
                {theme === 'dark' ? '🌙' : '☀️'}
              </span>
            </button>
          )}
        </div>

      </div>
    </header>
  )
}
