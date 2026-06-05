'use client'
import Image from 'next/image'
import { useStockPolling } from '@/hooks/useStockPolling'
import { formatPrice, formatRate, formatDiff, formatTrillion } from '@/lib/format'
import type { ExchangeQuote } from '@/lib/naver'

const UP = '#E74C3C'
const DOWN = '#3498DB'
const NEUTRAL = '#888780'

function diffColor(amount: number) {
  if (amount > 0) return UP
  if (amount < 0) return DOWN
  return NEUTRAL
}

function ExchangeBlock({ label, quote }: { label: string; quote: ExchangeQuote | null }) {
  return (
    <div className="flex-1 min-w-0">
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
          <div className="text-xl sm:text-2xl md:text-3xl font-bold tabular-nums mb-1" style={{ color: 'var(--text-1)' }}>
            ₩{formatPrice(quote.price)}
          </div>
          <div className="text-xs sm:text-sm tabular-nums font-medium" style={{ color: diffColor(quote.diffAmount) }}>
            {formatDiff(quote.diffAmount)}&nbsp;
            <span className="text-xs">({formatRate(quote.diffRate)})</span>
          </div>
          <div className="mt-3 text-xs tabular-nums" style={{ color: 'var(--text-2)' }}>
            전일 종가&nbsp;₩{formatPrice(quote.prevClosePrice)}
          </div>
        </>
      ) : (
        <div className="text-sm" style={{ color: 'var(--text-2)' }}>데이터 없음</div>
      )}
    </div>
  )
}

export default function StockCard({ ticker, name }: { ticker: string; name: string }) {
  const { data, loading, error } = useStockPolling(ticker)

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-3 mb-6">
        <Image
          src={`/${ticker}.${ticker === '005930' ? 'jpg' : 'png'}`}
          alt={name}
          width={36}
          height={36}
          className="rounded-full object-cover shrink-0"
          style={{ border: '1px solid var(--border)' }}
          priority
        />
        <div className="flex items-baseline gap-2">
          <h2 className="text-lg font-semibold" style={{ color: 'var(--text-1)' }}>{name}</h2>
          <span className="text-sm tabular-nums" style={{ color: 'var(--text-2)' }}>{ticker}</span>
        </div>
      </div>

      {!data && loading && (
        <div className="flex-1 flex items-center justify-center" style={{ color: 'var(--text-2)' }}>
          <span className="text-sm">불러오는 중…</span>
        </div>
      )}

      {!data && error && (
        <div className="flex-1 flex items-center justify-center" style={{ color: NEUTRAL }}>
          <span className="text-sm">데이터를 불러올 수 없습니다</span>
        </div>
      )}

      {data && (
        <>
          {/* KRX / NXT 나란히 */}
          <div className="flex gap-6">
            <ExchangeBlock label="KRX" quote={data.krx} />

            {/* 구분선 */}
            <div className="w-px self-stretch" style={{ backgroundColor: 'var(--border)' }} />

            <ExchangeBlock label="NXT" quote={data.nxt} />
          </div>

          {/* KRX-NXT 스프레드 + 거래량·거래대금 */}
          <div
            className="mt-5 pt-4 space-y-3"
            style={{ borderTop: '1px solid var(--border)' }}
          >
            {data.krx && data.nxt && (
              <div className="text-xs tabular-nums" style={{ color: 'var(--text-2)' }}>
                KRX–NXT 스프레드&ensp;
                <span
                  className="font-medium"
                  style={{ color: diffColor(data.krx.price - data.nxt.price) }}
                >
                  {formatDiff(data.krx.price - data.nxt.price)}원
                </span>
              </div>
            )}

            {(() => {
              const krxVol = data.krx?.volume ?? 0
              const nxtVol = data.nxt?.volume ?? 0
              const totalVolume = krxVol + nxtVol

              const krxAmt = data.krx?.tradingValue ?? 0
              const nxtAmt = data.nxt?.tradingValue ?? 0
              const totalAmount = krxAmt + nxtAmt

              return (
                <div className="grid grid-cols-2 gap-x-6 gap-y-1">
                  <div className="text-xs" style={{ color: 'var(--text-2)' }}>
                    거래량 (KRX+NXT)
                  </div>
                  <div className="text-xs" style={{ color: 'var(--text-2)' }}>
                    거래대금 (KRX+NXT)
                  </div>
                  <div className="text-sm font-semibold tabular-nums" style={{ color: 'var(--text-1)' }}>
                    {totalVolume > 0 ? `${formatPrice(totalVolume)}주` : '—'}
                  </div>
                  <div className="text-sm font-semibold tabular-nums" style={{ color: 'var(--text-1)' }}>
                    {totalAmount > 0
                      ? `${formatTrillion(totalAmount * 1_000_000)}원`
                      : '—'}
                  </div>
                </div>
              )
            })()}
          </div>
        </>
      )}
    </div>
  )
}
