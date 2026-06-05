'use client'

import { useEffect, useState } from 'react'
import {
  ResponsiveContainer, ComposedChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip,
} from 'recharts'
import type { Prediction } from '@/types'
import { formatPrice } from '@/lib/format'

const UP_COLOR   = '#E74C3C'
const DOWN_COLOR = '#3498DB'
const NEUTRAL    = '#888780'

interface HistoryPoint { date: string; close: number }
interface ChartPoint {
  date: string
  close?: number
  pred?: number
  isPrediction?: boolean
}

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (diff < 1)  return '방금 갱신'
  if (diff < 60) return `${diff}분 전 갱신`
  const h = Math.floor(diff / 60)
  if (h < 24)   return `${h}시간 전 갱신`
  return `${Math.floor(h / 24)}일 전 갱신`
}

function nextTradingDay(dateStr: string): string {
  const d = new Date(dateStr)
  d.setDate(d.getDate() + 1)
  while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1)
  return d.toISOString().slice(5, 10)
}

export default function PredictionCard({
  ticker,
  initialHistory = [],
}: {
  ticker: string
  initialHistory?: HistoryPoint[]
}) {
  const [pred,    setPred]    = useState<Prediction | null>(null)
  const [history, setHistory] = useState<HistoryPoint[]>(initialHistory)
  const [status,  setStatus]  = useState<'loading' | 'ok' | 'error'>('loading')

  // initialHistory가 없을 때만 클라이언트 패치
  useEffect(() => {
    if (initialHistory.length > 0) return
    fetch(`/api/history/${ticker}`)
      .then(r => r.json())
      .then(d => { if (Array.isArray(d?.history)) setHistory(d.history) })
      .catch(() => {})
  }, [ticker])

  useEffect(() => {
    let cancelled = false
    const load = () =>
      fetch(`/api/predict/${ticker}`)
        .then(r => r.json())
        .then(d => {
          if (cancelled) return
          if (d?.direction) { setPred(d as Prediction); setStatus('ok') }
          else setStatus('loading')
        })
        .catch(() => { if (!cancelled) setStatus('error') })
    load()
    const id = setInterval(load, 60_000)
    return () => { cancelled = true; clearInterval(id) }
  }, [ticker])

  const isUp      = pred?.direction === 'up'
  const predColor = pred ? (isUp ? UP_COLOR : DOWN_COLOR) : NEUTRAL
  const probPct   = pred ? Math.round(pred.probability * 100) : null

  // 차트 데이터 조립
  const chartData: ChartPoint[] = history.length > 0 ? (() => {
    const lastClose = history[history.length - 1].close
    const nextDate  = nextTradingDay(history[history.length - 1].date)
    const pts: ChartPoint[] = history.map(h => ({ date: h.date.slice(5), close: h.close }))
    // 마지막 히스토리 점에 pred 연결
    pts[pts.length - 1] = { ...pts[pts.length - 1], pred: lastClose }
    // 예측 포인트 추가
    pts.push({ date: nextDate, pred: lastClose, isPrediction: true })
    return pts
  })() : []

  const minClose = history.length > 0 ? Math.min(...history.map(h => h.close)) : 0
  const yMin     = Math.floor(minClose * 0.97)

  // 예측 마커: 방향(▲▼) + 확신도 % 표시
  const PredMarker = (props: any) => {
    const { cx, cy, payload } = props
    if (!payload?.isPrediction || cx == null || cy == null) {
      return <circle cx={cx} cy={cy} r={0} />
    }
    const arrow = isUp ? '▲' : '▼'
    return (
      <g>
        <circle cx={cx} cy={cy} r={14} fill={predColor} fillOpacity={0.12} />
        <circle cx={cx} cy={cy} r={5}  fill={predColor} />
        <text
          x={cx} y={cy - 20}
          textAnchor="middle"
          fill={predColor}
          fontSize={12}
          fontWeight="bold"
        >
          {arrow} {probPct}%
        </text>
      </g>
    )
  }

  return (
    <div className="flex flex-col gap-4">

      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium" style={{ color: 'var(--text-1)' }}>
          과거 90일 + 예측 방향
        </span>
        {pred ? (
          <span
            className="text-xs font-bold px-2.5 py-1 rounded-full tabular-nums"
            style={{ color: predColor, backgroundColor: `${predColor}1a` }}
          >
            {isUp ? '▲ 상승' : '▼ 하락'}&nbsp;&nbsp;확신도 {probPct}%
          </span>
        ) : (
          <span className="text-xs" style={{ color: NEUTRAL }}>
            {status === 'error' ? '연결 오류' : '연산 중…'}
          </span>
        )}
      </div>

      {/* 차트 */}
      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={320}>
          <ComposedChart data={chartData} margin={{ top: 48, right: 30, bottom: 5, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: 'var(--text-2)' }}
              tickLine={false}
              axisLine={false}
              interval={14}
            />
            <YAxis
              tickFormatter={(v: number) => `₩${formatPrice(v)}`}
              tick={{ fontSize: 10, fill: 'var(--text-2)' }}
              width={90}
              tickLine={false}
              axisLine={false}
              domain={[yMin, (dataMax: number) => Math.ceil(dataMax * 1.03)]}
            />
            <Tooltip
              formatter={(v: number, name: string) => [
                `₩${formatPrice(v)}`,
                name === 'close' ? '실제 종가' : '기준가',
              ]}
              contentStyle={{
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border)',
                borderRadius: 8,
                fontSize: 13,
              }}
            />
            {/* 실제 종가 solid */}
            <Line
              type="monotone"
              dataKey="close"
              stroke="var(--text-1)"
              strokeWidth={1.5}
              dot={false}
              name="close"
            />
            {/* 예측 방향 dashed + 컬러 마커 */}
            <Line
              type="monotone"
              dataKey="pred"
              stroke={predColor}
              strokeWidth={2}
              strokeDasharray="6 3"
              dot={(props: any) => <PredMarker {...props} />}
              activeDot={false}
              legendType="none"
            />
          </ComposedChart>
        </ResponsiveContainer>
      ) : (
        <div
          className="flex items-center justify-center text-sm"
          style={{ height: 320, color: NEUTRAL }}
        >
          히스토리 로딩 중…
        </div>
      )}

      {/* 모델 정보 */}
      <div
        className="grid grid-cols-2 gap-4 text-sm pt-4"
        style={{ borderTop: '1px solid var(--border)' }}
      >
        <div className="flex flex-col gap-1">
          <span style={{ color: 'var(--text-2)' }}>선택 모델</span>
          <span className="font-medium" style={{ color: 'var(--text-1)' }}>
            {pred?.bestModel ?? '—'}
          </span>
        </div>
        <div className="flex flex-col gap-1">
          <span style={{ color: 'var(--text-2)' }}>Walk-Forward 정확도</span>
          <span className="font-medium tabular-nums" style={{ color: 'var(--text-1)' }}>
            {pred ? `${(pred.modelAccuracy * 100).toFixed(1)}%` : '—'}
          </span>
        </div>
      </div>

      <div className="text-xs text-right" style={{ color: 'var(--text-2)' }}>
        {pred ? timeAgo(pred.predictedAt) : '—'}
      </div>

    </div>
  )
}
