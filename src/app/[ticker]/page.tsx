import { STOCKS } from '@/lib/constants'
import StockCard from '@/components/price/StockCard'
import EtfIndexPanel from '@/components/etf/EtfIndexPanel'
import PredictionCard from '@/components/forecast/PredictionCard'

const BACKEND = process.env.BACKEND_URL ?? 'http://localhost:8000'

async function fetchHistory(ticker: string) {
  try {
    const res = await fetch(`${BACKEND}/history/${ticker}`, { cache: 'no-store' })
    if (!res.ok) return []
    const data = await res.json()
    return data.history ?? []
  } catch {
    return []
  }
}

export default async function PricePage({ params }: { params: { ticker: string } }) {
  const stock   = STOCKS.find(s => s.ticker === params.ticker)
  const history = await fetchHistory(params.ticker)

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
          <EtfIndexPanel />
        </section>

      </div>

      {/* 하단: 예측 (전체 너비) */}
      <section className="card p-8">
        <h2 className="text-lg font-semibold mb-6" style={{ color: 'var(--text-1)' }}>내일 예측</h2>
        <PredictionCard ticker={params.ticker} initialHistory={history} />
      </section>

    </div>
  )
}
