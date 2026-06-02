'use client'
import { useEffect, useState } from 'react'
import { useTheme } from 'next-themes'
import { formatRate } from '@/lib/format'
import type { Kospi, Sox, ExchangeRate } from '@/types'

const UP = '#E74C3C'
const DOWN = '#3498DB'
const NEUTRAL = '#888780'

function dirColor(dir?: 'up' | 'down' | 'neutral') {
  if (dir === 'up') return UP
  if (dir === 'down') return DOWN
  return NEUTRAL
}

export default function Header() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const [time, setTime] = useState('')
  const [kospi, setKospi] = useState<Kospi | null>(null)
  const [sox, setSox] = useState<Sox | null>(null)
  const [fx, setFx] = useState<ExchangeRate | null>(null)

  useEffect(() => {
    setMounted(true)

    const tick = () =>
      setTime(new Date().toLocaleTimeString('ko-KR', {
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
      }))
    tick()
    const tickId = setInterval(tick, 1000)

    const loadKospi = () =>
      fetch('/api/kospi').then(r => r.ok ? r.json() : null).then(d => d && setKospi(d)).catch(() => {})
    const loadSox = () =>
      fetch('/api/sox').then(r => r.ok ? r.json() : null).then(d => d && setSox(d)).catch(() => {})
    const loadFx = () =>
      fetch('/api/exchange-rate').then(r => r.ok ? r.json() : null).then(d => d && setFx(d)).catch(() => {})

    loadKospi(); loadSox(); loadFx()
    const dataId = setInterval(() => { loadKospi(); loadSox(); loadFx() }, 30_000)

    return () => { clearInterval(tickId); clearInterval(dataId) }
  }, [])

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

        {/* 중: KOSPI · SOX · USD/KRW */}
        <div className="flex items-center gap-6 tabular-nums">
          {/* KOSPI */}
          <div className="flex items-baseline gap-1.5">
            <span className="text-xs font-medium" style={{ color: 'var(--text-2)' }}>KOSPI</span>
            <span className="text-sm font-semibold" style={{ color: 'var(--text-1)' }}>
              {kospi ? kospi.index.toLocaleString('ko-KR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}
            </span>
            {kospi && (
              <span className="text-xs" style={{ color: dirColor(kospi.direction) }}>
                {formatRate(kospi.diffRate)}
              </span>
            )}
          </div>

          <span style={{ color: 'var(--border)' }}>|</span>

          {/* SOX */}
          <div className="flex items-baseline gap-1.5">
            <span className="text-xs font-medium" style={{ color: 'var(--text-2)' }}>SOX</span>
            <span className="text-sm font-semibold" style={{ color: 'var(--text-1)' }}>
              {sox ? sox.index.toLocaleString('ko-KR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}
            </span>
            {sox && (
              <span className="text-xs" style={{ color: dirColor(sox.direction) }}>
                {formatRate(sox.diffRate)}
              </span>
            )}
          </div>

          <span style={{ color: 'var(--border)' }}>|</span>

          {/* USD/KRW */}
          <div className="flex items-baseline gap-1.5">
            <span className="text-xs font-medium" style={{ color: 'var(--text-2)' }}>USD/KRW</span>
            <span className="text-sm font-semibold" style={{ color: 'var(--text-1)' }}>
              {fx ? fx.usdKrw.toLocaleString('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : '—'}
            </span>
          </div>
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
