import { STOCKS } from '@/lib/constants'

const NAVER_FINANCE_URL = 'https://finance.naver.com/item/main.naver'

const NAVER_HEADERS = {
  'User-Agent':
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
  Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
  Referer: 'https://finance.naver.com',
}

export interface ExchangeQuote {
  price: number
  diffAmount: number
  diffRate: number
  prevClosePrice: number
}

export interface DualQuote {
  ticker: string
  name: string
  krx: ExchangeQuote | null
  nxt: ExchangeQuote | null
  updatedAt: string
}

function toNumber(text: string | undefined): number {
  const normalized = (text ?? '').replace(/,/g, '').replace(/[^\d.-]/g, '')
  const value = Number(normalized)
  return Number.isFinite(value) ? value : 0
}

// 네이버는 숫자를 CSS 클래스명(no0~no9)으로 인코딩하여 스크래핑을 방해함
function toNaverNumber(markup: string): number {
  let raw = ''
  for (const match of Array.from(markup.matchAll(/<span\s+class="([^"]+)"[^>]*>[\s\S]*?<\/span>/g))) {
    const className = match[1]
    const digit = className.match(/\bno(\d)\b/)
    if (digit) raw += digit[1]
    else if (className.includes('shim')) raw += ','
    else if (className.includes('jum')) raw += '.'
  }
  return raw ? toNumber(raw) : toNumber(markup)
}

function signedValue(value: number, className: string): number {
  if (className.includes('no_down')) return -Math.abs(value)
  if (className.includes('no_up')) return Math.abs(value)
  return 0
}

function stripTags(html: string): string {
  return html.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim()
}

function getStockName(html: string, ticker: string): string {
  const fromWrap = stripTags(html.match(/<div\s+class="wrap_company"[\s\S]*?<h2>[\s\S]*?<a[^>]*>([\s\S]*?)<\/a>/)?.[1] ?? '')
  if (fromWrap) return fromWrap
  const fromTitle = stripTags(html.match(/<title>([\s\S]*?)<\/title>/)?.[1] ?? '').split(':')[0]?.trim()
  if (fromTitle) return fromTitle
  return STOCKS.find(s => s.ticker === ticker)?.name ?? ticker
}

function parseSection(sectionHtml: string): ExchangeQuote | null {
  const priceMarkup = sectionHtml.match(/<p\s+class="no_today">([\s\S]*?)<\/p>/)?.[1] ?? ''
  const price = toNaverNumber(priceMarkup)
  if (price <= 0) return null

  const exdayMarkup = sectionHtml.match(/<p\s+class="no_exday">([\s\S]*?)<\/p>/)?.[1] ?? ''
  const exdayMatches = Array.from(exdayMarkup.matchAll(/<em\s+class="([^"]*)"[^>]*>([\s\S]*?)<\/em>/g))
  const diffClass = exdayMatches[0]?.[1] ?? ''
  const rateClass = exdayMatches[1]?.[1] ?? diffClass
  const diffAmount = signedValue(toNaverNumber(exdayMatches[0]?.[2] ?? ''), diffClass)
  const diffRate = signedValue(toNaverNumber(exdayMatches[1]?.[2] ?? ''), rateClass)

  return { price, diffAmount, diffRate, prevClosePrice: price - diffAmount }
}

export function parseNaverDualQuote(html: string, ticker: string): DualQuote | null {
  // rate_info_krx 섹션: KRX 거래가
  const krxHtml = html.match(
    /<div[^>]+id="rate_info_krx"[\s\S]*?(?=<div[^>]+id="rate_info_nxt"|<script|<\/body>)/
  )?.[0] ?? null

  // rate_info_nxt 섹션: NXT 거래가
  const nxtHtml = html.match(
    /<div[^>]+id="rate_info_nxt"[\s\S]*?(?=<div[^>]+id="|<script|<\/body>)/
  )?.[0] ?? null

  const krx = krxHtml ? parseSection(krxHtml) : null
  const nxt = nxtHtml ? parseSection(nxtHtml) : null

  if (!krx && !nxt) return null

  return {
    ticker,
    name: getStockName(html, ticker),
    krx,
    nxt,
    updatedAt: new Date().toISOString(),
  }
}

export async function fetchDualQuote(ticker: string): Promise<DualQuote | null> {
  if (!/^\d{6}$/.test(ticker)) return null

  const res = await fetch(`${NAVER_FINANCE_URL}?code=${ticker}`, {
    cache: 'no-store',
    headers: NAVER_HEADERS,
  })

  if (!res.ok) throw new Error(`Naver Finance ${res.status} for ${ticker}`)

  const html = await res.text()
  return parseNaverDualQuote(html, ticker)
}
