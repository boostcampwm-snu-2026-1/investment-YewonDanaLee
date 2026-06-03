'use client'
import { useStockPolling } from '@/hooks/useStockPolling'
import { formatPrice, formatRate, formatDiff, timeAgo } from '@/lib/format'
import type { ExchangeQuote } from '@/lib/naver'

const UP = '#E74C3C'
const DOWN = '#3498DB'
const NEUTRAL = '#888780'

function diffColor(amount: number) {
  if (amount > 0) return UP
  if (amount < 0) return DOWN
  return NEUTRAL
}

function ExchangeBlock({
  label,
  quote,
}: {
  label: string
  quote: ExchangeQuote | null
}) {
  return (
    <div className="flex-1 min-w-0">
      {/* 거래소 레이블 */}
      <div className="mb-3">
        <span
          className="text-xs font-semibold px-2 py-0.5 rounded"
          style={{ backgroundColor: 'var(--bg-muted)', color: 'var(--text-2)' }}
        >
          {label}
        </span>
      </div>

      {quote ? (
        <>
          {/* 현재가 */}
          <div
            className="text-3xl font-bold tabular-nums mb-1"
            style={{ color: 'var(--text-1)' }}
          >
            ₩{formatPrice(quote.price)}
          </div>

          {/* 등락폭 + 등락률 */}
          <div
            className="text-sm tabular-nums font-medium"
            style={{ color: diffColor(quote.diffAmount) }}
          >
            {formatDiff(quote.diffAmount)}&nbsp;
            <span className="text-xs">({formatRate(quote.diffRate)})</span>
          </div>

          {/* 전일 종가 */}
          <div className="mt-3 text-xs tabular-nums" style={{ color: 'var(--text-2)' }}>
            전일 종가&nbsp;₩{formatPrice(quote.prevClosePrice)}
          </div>
        </>
      ) : (
        <div className="text-sm" style={{ color: 'var(--text-2)' }}>
          데이터 없음
        </div>
      )}
    </div>
  )
}

export default function StockCard({ ticker, name }: { ticker: string; name: string }) {
  const { data, loading, error } = useStockPolling(ticker)

  return (
    <div className="h-full flex flex-col">
      {/* 카드 헤더 */}
      <div className="flex items-baseline gap-2 mb-6">
        <h2 className="text-lg font-semibold" style={{ color: 'var(--text-1)' }}>
          {name}
        </h2>
        <span className="text-sm tabular-nums" style={{ color: 'var(--text-2)' }}>
          {ticker}
        </span>
        {data && (
          <span className="ml-auto text-xs tabular-nums" style={{ color: 'var(--text-2)' }}>
            {timeAgo(data.updatedAt)}
          </span>
        )}
      </div>

      {loading && (
        <div className="flex-1 flex items-center justify-center" style={{ color: 'var(--text-2)' }}>
          <span className="text-sm">불러오는 중…</span>
        </div>
      )}

      {error && !loading && (
        <div className="flex-1 flex items-center justify-center" style={{ color: NEUTRAL }}>
          <span className="text-sm">데이터를 불러올 수 없습니다</span>
        </div>
      )}

      {data && !loading && (
        <>
          {/* KRX / NXT 나란히 */}
          <div className="flex gap-6">
            <ExchangeBlock label="KRX" quote={data.krx} />

            {/* 구분선 */}
            <div className="w-px self-stretch" style={{ backgroundColor: 'var(--border)' }} />

            <ExchangeBlock label="NXT" quote={data.nxt} />
          </div>

          {/* KRX-NXT 스프레드 */}
          {data.krx && data.nxt && (
            <div
              className="mt-5 pt-4 text-xs tabular-nums"
              style={{ borderTop: '1px solid var(--border)', color: 'var(--text-2)' }}
            >
              KRX–NXT 스프레드&ensp;
              <span
                className="font-medium"
                style={{ color: diffColor(data.krx.price - data.nxt.price) }}
              >
                {formatDiff(data.krx.price - data.nxt.price)}원
              </span>
            </div>
          )}
        </>
      )}
    </div>
  )
}
