'use client'
import { useEffect, useState } from 'react'
import { formatRate, formatDiff } from '@/lib/format'


const UP = '#E74C3C'
const DOWN = '#3498DB'
const NEUTRAL = '#888780'

function dirColor(dir?: 'up' | 'down' | 'neutral') {
  if (dir === 'up') return UP
  if (dir === 'down') return DOWN
  return NEUTRAL
}

// /sox, /drametf, /ewy, /koru 가 공유하는 응답 형태
interface IndexData {
  index: number
  diffAmount: number
  diffRate: number
  direction: 'up' | 'down' | 'neutral'
  updatedAt: string
}

// 모듈 레벨 캐시 (탭 전환 시 깜빡임 방지)
const _cache: Record<string, IndexData> = {}

function useIndexPolling(path: string) {
  const [data, setData] = useState<IndexData | null>(() => _cache[path] ?? null)
  const [error, setError] = useState(false)

  useEffect(() => {
    const load = () =>
      fetch(path, { cache: 'no-store' })
        .then(r => { if (!r.ok) throw new Error(); return r.json() })
        .then(d => {
          if (d?.index == null) { setError(true); return }
          _cache[path] = d as IndexData
          setData(d as IndexData)
          setError(false)
        })
        .catch(() => setError(true))

    load()
    const id = setInterval(load, 10_000)
    return () => clearInterval(id)
  }, [path])

  return { data, error }
}

const ITEMS: { path: string; label: string; subtitle: string; badge: string }[] = [
  { path: '/api/sox',     label: 'SOX',  subtitle: 'Philadelphia Semiconductor', badge: 'PHLX' },
  { path: '/api/drametf', label: 'DRAM', subtitle: 'VanEck Dynamic Semiconductor', badge: 'ETF' },
  { path: '/api/ewy',     label: 'EWY',  subtitle: 'iShares MSCI South Korea',    badge: 'ETF' },
  { path: '/api/koru',    label: 'KORU', subtitle: 'Direxion Daily S.Korea Bull 3x', badge: 'ETF' },
]

export default function EtfIndexPanel() {
  const sox   = useIndexPolling('/api/sox')
  const dram  = useIndexPolling('/api/drametf')
  const ewy   = useIndexPolling('/api/ewy')
  const koru  = useIndexPolling('/api/koru')

  const polls = [sox, dram, ewy, koru]

  return (
    <div className="h-full flex flex-col">
      <h2 className="text-lg font-semibold mb-5" style={{ color: 'var(--text-1)' }}>
        관련 ETF / 지수
      </h2>

      <div className="flex flex-col gap-2 overflow-y-auto flex-1 pr-1"
        style={{ scrollbarWidth: 'thin', scrollbarColor: 'var(--border) transparent' }}
      >
        {ITEMS.map((item, i) => {
          const { data, error } = polls[i]
          return (
            <IndexCard
              key={item.path}
              label={item.label}
              subtitle={item.subtitle}
              badge={item.badge}
              data={data}
              loading={!data && !error}
              error={error && !data}
            />
          )
        })}
      </div>
    </div>
  )
}

function IndexCard({
  label, subtitle, badge, data, loading, error,
}: {
  label: string; subtitle: string; badge: string
  data: IndexData | null; loading: boolean; error: boolean
}) {
  return (
    <div
      className="rounded-xl px-4 py-3 flex items-center justify-between gap-3"
      style={{ backgroundColor: 'var(--bg-muted)' }}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold" style={{ color: 'var(--text-1)' }}>
            {label}
          </span>
          <span
            className="text-xs px-1.5 rounded"
            style={{ backgroundColor: 'var(--border)', color: 'var(--text-2)' }}
          >
            {badge}
          </span>
        </div>
        <div className="text-xs mt-0.5 truncate" style={{ color: 'var(--text-2)' }}>
          {subtitle}
        </div>
      </div>

      <div className="text-right shrink-0">
        {loading && <span className="text-xs" style={{ color: 'var(--text-2)' }}>—</span>}
        {error   && <span className="text-xs" style={{ color: NEUTRAL }}>백엔드 꺼짐</span>}
        {data && (
          <>
            <div className="text-sm font-bold tabular-nums" style={{ color: 'var(--text-1)' }}>
              {data.index.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <div className="text-xs tabular-nums font-medium" style={{ color: dirColor(data.direction) }}>
              {formatDiff(data.diffAmount)}&thinsp;({formatRate(data.diffRate)})
            </div>
          </>
        )}
      </div>
    </div>
  )
}
