import { STOCKS } from '@/lib/constants'
import StockCard from '@/components/price/StockCard'

export default function PricePage({ params }: { params: { ticker: string } }) {
  const stock = STOCKS.find(s => s.ticker === params.ticker)

  return (
    <div className="space-y-6">

      {/* 상단: 가격 + ETF/지수 (50/50) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

        {/* Card 1: 가격 */}
        <section className="card p-8">
          <StockCard ticker={params.ticker} name={stock?.name ?? params.ticker} />
        </section>

        {/* Card 2: 관련 ETF/지수 */}
        <section className="card p-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold" style={{ color: 'var(--text-1)' }}>관련 ETF / 지수</h2>
            <span
              className="text-xs px-2 py-0.5 rounded-full"
              style={{ backgroundColor: 'var(--bg-muted)', color: 'var(--text-2)' }}
            >
              {params.ticker === '005930' ? 'KOSPI · KODEX' : 'SOX · SOXX'}
            </span>
          </div>
          <div
            className="rounded-xl flex flex-col items-center justify-center gap-3"
            style={{ backgroundColor: 'var(--bg-muted)', minHeight: '200px' }}
          >
            {[1, 2, 3].map(i => (
              <div
                key={i}
                className="w-full max-w-xs h-8 rounded-lg"
                style={{ backgroundColor: 'var(--border)' }}
              />
            ))}
          </div>
        </section>

      </div>

      {/* 하단: 예측 (전체 너비) */}
      <section className="card p-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold" style={{ color: 'var(--text-1)' }}>예측</h2>
          <span
            className="text-xs px-2 py-0.5 rounded-full"
            style={{ backgroundColor: 'var(--bg-muted)', color: 'var(--text-2)' }}
          >
            Prophet · LSTM
          </span>
        </div>
        <div
          className="rounded-xl flex flex-col items-center justify-center gap-4"
          style={{ backgroundColor: 'var(--bg-muted)', minHeight: '240px' }}
        >
          <div className="w-full px-6">
            <div className="w-full h-32 rounded-lg" style={{ backgroundColor: 'var(--border)' }} />
          </div>
          <div className="flex gap-3">
            {['상승여력', 'MAPE', '예측일', '갱신일'].map(label => (
              <div
                key={label}
                className="h-8 w-20 rounded"
                style={{ backgroundColor: 'var(--border)' }}
              />
            ))}
          </div>
        </div>
      </section>

    </div>
  )
}
