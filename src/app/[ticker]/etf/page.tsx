export default function EtfPage({ params }: { params: { ticker: string } }) {
  return (
    <div className="card p-8 text-center" style={{ color: 'var(--text-2)' }}>
      관련 ETF/지수 섹션 — {params.ticker}
    </div>
  )
}
