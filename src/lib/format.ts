export function formatPrice(price: number): string {
  return price.toLocaleString('ko-KR')
}

export function formatTrillion(price: number): string {
  const jo = Math.floor(price / 1_000_000_000_000)
  const eok = Math.floor((price % 1_000_000_000_000) / 100_000_000)
  if (jo === 0) return `${eok.toLocaleString('ko-KR')}억`
  if (eok === 0) return `${jo.toLocaleString('ko-KR')}조`
  return `${jo.toLocaleString('ko-KR')}조 ${eok.toLocaleString('ko-KR')}억`
}

export function formatRate(rate: number): string {
  const sign = rate >= 0 ? '+' : ''
  return `${sign}${rate.toFixed(2)}%`
}

export function formatDiff(amount: number): string {
  if (amount > 0) return `▲${amount.toLocaleString('ko-KR')}`
  if (amount < 0) return `▼${Math.abs(amount).toLocaleString('ko-KR')}`
  return `―${Math.abs(amount).toLocaleString('ko-KR')}`
}

export function timeAgo(isoString: string): string {
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000)
  if (diff < 60) return `${diff}초 전 갱신`
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전 갱신`
  return `${Math.floor(diff / 3600)}시간 전 갱신`
}
