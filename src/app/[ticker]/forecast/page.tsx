import PredictionCard from '@/components/forecast/PredictionCard'

export default function ForecastPage({ params }: { params: { ticker: string } }) {
  return (
    <div className="max-w-lg mx-auto py-6 px-4">
      <PredictionCard ticker={params.ticker} />
    </div>
  )
}
