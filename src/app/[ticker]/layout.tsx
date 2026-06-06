import { notFound } from 'next/navigation'
import { STOCKS } from '@/lib/constants'
import StockTab from '@/components/layout/StockTab'

export default function TickerLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: { ticker: string }
}) {
  const valid = STOCKS.some(s => s.ticker === params.ticker)
  if (!valid) notFound()

  return (
    <>
      <StockTab activeTicker={params.ticker} />
      <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
    </>
  )
}
