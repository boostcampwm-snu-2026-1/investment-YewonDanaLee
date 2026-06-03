import { NextResponse } from 'next/server'

const BACKEND = process.env.BACKEND_URL ?? 'http://localhost:8000'
export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const res = await fetch(`${BACKEND}/drametf`, { cache: 'no-store' })
    if (!res.ok) throw new Error()
    return NextResponse.json(await res.json())
  } catch {
    return NextResponse.json({ error: 'unavailable' }, { status: 502 })
  }
}
