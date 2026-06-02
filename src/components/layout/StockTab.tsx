import Link from 'next/link'
import { STOCKS } from '@/lib/constants'

export default function StockTab({ activeTicker }: { activeTicker: string }) {
  return (
    <nav
      className="border-b"
      style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border)' }}
    >
      <div className="max-w-7xl mx-auto px-6 flex justify-center">
        {STOCKS.map(s => {
          const active = activeTicker === s.ticker
          return (
            <Link
              key={s.ticker}
              href={`/${s.ticker}`}
              className="px-8 py-3 text-sm font-medium border-b-2 transition-colors"
              style={{
                borderColor: active ? 'var(--text-1)' : 'transparent',
                color:       active ? 'var(--text-1)' : 'var(--text-2)',
              }}
            >
              {s.name}
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
