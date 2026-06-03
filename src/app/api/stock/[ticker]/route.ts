import { NextResponse } from 'next/server'
import { fetchDualQuote } from '@/lib/naver'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export async function GET(_req: Request, { params }: { params: { ticker: string } }) {
  try {
    const data = await fetchDualQuote(params.ticker)
    if (!data) return NextResponse.json({ error: 'Parse failed' }, { status: 502 })
    return NextResponse.json(data)
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 502 })
  }
}
