export interface Stock {
  ticker: string
  name: string
  overseasPrice: number
  overseasPriceUsd: number
  overseasDiffAmount: number
  overseasDiffRate: number
  koreaClosePrice: number
  koreaClosePriceUsd: number
  koreaDiffAmount: number
  koreaDiffRate: number
  volume: number
  tradingValue: number
  marketCap: number
  aftermarketPrice: number | null
  aftermarketDiffAmount: number | null
  aftermarketDiffRate: number | null
  prevClosePrice: number
  updatedAt: string
}

export interface Kospi {
  index: number
  diffAmount: number
  diffRate: number
  direction: 'up' | 'down' | 'neutral'
  status: 'OPEN' | 'CLOSE'
  tradedAt: string
}

export interface Sox {
  index: number
  diffAmount: number
  diffRate: number
  direction: 'up' | 'down' | 'neutral'
  updatedAt: string
}

export interface ExchangeRate {
  usdKrw: number
  updatedAt: string
}

export interface Forecast {
  ticker: string
  model: 'prophet' | 'lstm'
  history: { date: string; close: number }[]
  prediction: {
    date: string
    price: number
    upperBound: number
    lowerBound: number
    upside: number
  }
  metrics: {
    mape: number
    lastTrainedAt: string
  }
}
