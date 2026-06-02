export default function ForecastPage({ params }: { params: { ticker: string } }) {
  return (
    <div className="card p-8 text-center" style={{ color: 'var(--text-2)' }}>
      예측 섹션 — {params.ticker}
    </div>
  )
}
