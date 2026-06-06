'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const SECTIONS = [
  { label: '가격',         suffix: '' },
  { label: '관련 ETF/지수', suffix: '/etf' },
  { label: '예측',         suffix: '/forecast' },
]

export default function SectionNav({ ticker }: { ticker: string }) {
  const pathname = usePathname()

  return (
    <nav
      className="border-b"
      style={{ backgroundColor: 'var(--bg-page)', borderColor: 'var(--border)' }}
    >
      <div className="max-w-7xl mx-auto px-6 flex gap-1">
        {SECTIONS.map(s => {
          const href = `/${ticker}${s.suffix}`
          const active = pathname === href
          return (
            <Link
              key={s.suffix}
              href={href}
              className="px-5 py-2.5 text-sm font-medium border-b-2 transition-colors"
              style={{
                borderColor: active ? 'var(--accent)' : 'transparent',
                color:       active ? 'var(--accent)' : 'var(--text-2)',
              }}
            >
              {s.label}
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
