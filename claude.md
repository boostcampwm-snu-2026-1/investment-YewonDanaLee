# YENLAB — claude.md

## 1. 서비스 개요

- 삼성전자·SK하이닉스 반도체 2종목 전문 투자 분석 플랫폼
- 기술 스택: Next.js 14 (App Router) / TypeScript / Tailwind CSS
- 대상 유저: 반도체 섹터 집중 투자 개인 투자자 (한국어 UI 전체)
- 배포: Vercel

---

## 2. 종목 고정값

> 전체 화면에서 공통으로 사용하는 종목 목록. 임의로 추가·변경하지 않는다.

```ts
// constants/stocks.ts
export const STOCKS = [
  { name: '삼성전자', ticker: '005930', nameEn: 'Samsung Electronics' },
  { name: 'SK하이닉스', ticker: '000660', nameEn: 'SK Hynix' },
] as const

export type Ticker = '005930' | '000660'
```

---

## 3. 데이터 소스

| 데이터 | 소스 | 방식 |
|--------|------|------|
| 해외 실시간 추정가·애프터마켓가 | 네이버 금융 내부 API | HTTP GET (비공식) |
| 한국 종가·거래량·거래대금·시총 | pykrx → 백엔드 캐싱 | Python 스케줄러 |
| KOSPI 지수·등락률 | pykrx → 백엔드 캐싱 | Python 스케줄러 |
| SOX 지수·등락률 | 네이버 금융 내부 API → 백엔드 캐싱 | Python 스케줄러 |
| USD/KRW 환율 | FinanceDataReader → 백엔드 캐싱 | Python 스케줄러 |
| 증권사 리포트·목표가 | 네이버 증권 리서치 크롤링 | Python 스케줄러 |
| 예측 모델 결과 | 백엔드 Prophet / LSTM API | REST API |

### 네이버 금융 내부 API 엔드포인트

```
GET https://api.stock.naver.com/stock/{ticker}/basic
GET https://api.stock.naver.com/stock/{ticker}/price
```

- 비공식 API이므로 응답 필드명이 바뀔 수 있다.
- 필드 파싱은 반드시 `lib/naver.ts` 한 곳에서만 처리한다.
- 프론트에서 직접 호출 금지. 반드시 백엔드 `/api/stock/:ticker` 프록시 경유.

### pykrx 주요 함수

```python
from pykrx import stock

stock.get_market_ohlcv('YYYYMMDD', ticker='005930')          # 종목 OHLCV
stock.get_market_cap('YYYYMMDD', '005930')                   # 시가총액
stock.get_index_ohlcv('YYYYMMDD', 'YYYYMMDD', '1001')        # KOSPI 지수
stock.get_market_trading_volume_by_investor('YYYYMMDD', 'YYYYMMDD', '005930')  # 수급
```

---

## 4. 백엔드 API 엔드포인트 스펙

> 프론트엔드는 아래 엔드포인트만 호출한다. 외부 소스 직접 호출 금지.

### 4-1. 종목 실시간 시세

```
GET /api/stock/:ticker

Response:
{
  ticker: string
  name: string

  // 해외 실시간 추정가 모드
  overseasPrice: number          // 해외 실시간 추정가 (원)
  overseasPriceUsd: number       // USD 환산
  overseasDiffAmount: number     // 전일 종가 대비 등락폭 (원)
  overseasDiffRate: number       // 전일 종가 대비 등락률 (%)

  // 한국 시장 마감 모드
  koreaClosePrice: number        // 한국 종가 (원)
  koreaClosePriceUsd: number     // USD 환산
  koreaDiffAmount: number        // 전일 종가 대비 등락폭 (원)
  koreaDiffRate: number          // 전일 종가 대비 등락률 (%)

  // 공통
  volume: number                 // 거래량 KRX+NXT (주)
  tradingValue: number           // 거래대금 (원)
  marketCap: number              // 시가총액 (원)
  aftermarketPrice: number | null      // 애프터마켓 마감가, 없으면 null
  aftermarketDiffAmount: number | null
  aftermarketDiffRate: number | null
  prevClosePrice: number         // 전일 종가 (원)
  updatedAt: string              // ISO 8601
}
```

### 4-2. KOSPI 지수

```
GET /api/kospi

Response:
{
  index: number,            // 지수값
  diffAmount: number,
  diffRate: number,
  direction: 'up' | 'down' | 'neutral',
  status: 'OPEN' | 'CLOSE',
  tradedAt: string          // ISO 8601
}
```

### 4-3. SOX 지수

```
GET /api/sox

Response:
{
  index: number,
  diffAmount: number,
  diffRate: number,
  direction: 'up' | 'down' | 'neutral',
  updatedAt: string
}
```

### 4-4. 환율

```
GET /api/exchange-rate

Response:
{
  usdKrw: number     // USD/KRW
  updatedAt: string
}
```

### 4-5. 예측 결과

```
GET /api/forecast/:ticker
Query: model = 'prophet' | 'lstm'  (default: 'prophet')

Response:
{
  ticker: string
  model: 'prophet' | 'lstm'
  history: [
    { date: string, close: number }   // 과거 90일
  ]
  prediction: {
    date: string           // 예측 날짜 (다음 거래일)
    price: number          // 예측 종가 (원)
    upperBound: number     // 95% 신뢰구간 상단
    lowerBound: number     // 95% 신뢰구간 하단
    upside: number         // 현재가 대비 상승여력 (%)
  }
  metrics: {
    mape: number           // 모델 MAPE (%)
    lastTrainedAt: string  // 마지막 학습 시각
  }
}
```

---

## 5. 디렉토리 구조

```
src/
├── app/
│   ├── layout.tsx                # 공통 레이아웃 (Header 포함)
│   └── [ticker]/                 # 동적 라우트: '005930' | '000660'
│       ├── page.tsx              # 탭 루트 → 가격 섹션 기본 표시
│       ├── report/
│       │   └── page.tsx          # 리포트 섹션
│       └── forecast/
│           └── page.tsx          # 예측 섹션
├── components/
│   ├── layout/
│   │   ├── Header.tsx            # 로고 + KOSPI·SOX 지수 + 환율 + 시각 + 테마 토글
│   │   ├── StockTab.tsx          # 삼성전자 | SK하이닉스 상단 탭
│   │   └── SectionNav.tsx        # 가격 | 관련 ETF/지수 | 예측 섹션 네비
│   ├── price/
│   │   ├── StockCard.tsx         # 종목 카드 (해외/한국 토글 포함)
│   │   ├── PriceDisplay.tsx      # 가격 + 등락 표시
│   │   └── StockMeta.tsx         # 거래량·거래대금·시총
│   ├── etf/
│   │   └── EtfIndexPanel.tsx     # 관련 ETF/지수 카드 목록
목표가 bar
│   │   ├── EarningsTable.tsx     # 연도별 실적 테이블
│   │   ├── ReportTable.tsx       # 증권사별 전망 테이블
│   │   └── SortButton.tsx        # 정렬 버튼 (최신순·영업이익·목표가)
│   └── forecast/
│       ├── ForecastChart.tsx     # 과거 90일 + 예측 1일 차트
│       ├── ModelTab.tsx          # Prophet | LSTM 모델 전환 탭
│       └── MetricsPanel.tsx      # 예측 상승여력·MAPE·예측날짜·갱신일 카드
├── lib/
│   ├── api.ts                    # 백엔드 fetch 함수 모음 (유일한 호출 지점)
│   ├── naver.ts                  # 네이버 금융 API 파싱 전담
│   ├── format.ts                 # formatPrice, formatRate, formatDiff, formatTrillion
│   └── constants.ts              # STOCKS, TICKERS
├── hooks/
│   ├── useStockPolling.ts        # 10초 폴링 (가격 섹션)
│   └── useForecast.ts            # 예측 데이터 fetch + 모델 전환
└── types/
    └── index.ts                  # Stock, Report, Forecast 타입 정의
```

---

## 6. 화면별 스펙

### 공통 레이아웃

모든 페이지 상단에 Header가 고정된다.

| 위치 | 내용 |
|------|------|
| 좌 | 서비스 로고 (YENLAB) |
| 중 | KOSPI 지수·등락률 / SOX 지수·등락률 / USD/KRW 환율 |
| 우 | 현재 시각 + 다크 모드 토글 |

Header 아래에는 **종목 탭(StockTab)**이 위치한다.

```
[ 삼성전자 ] [ SK하이닉스 ]
```

탭 전환 시 URL이 `/005930` ↔ `/000660` 으로 변경되며, 하위 섹션 데이터 전체가 해당 종목 기준으로 교체된다.

종목 탭 아래에는 **섹션 네비(SectionNav)**가 위치한다.

```
[ 가격 ] [ 관련 ETF/지수 ] [ 예측 ]
```

---

### 탭 1 — 삼성전자 (`/005930`) / 탭 2 — SK하이닉스 (`/000660`)

두 탭은 동일한 레이아웃을 공유하며, URL 파라미터(ticker)로 데이터를 분기한다.

#### 섹션 A — 가격 (`/[ticker]`)

- `StockCard` 1개를 중앙에 크게 표시
- 카드 내 토글: **해외 실시간 추정가** ↔ **한국 시장 마감** (카드별 독립)
- 10초마다 `useStockPolling`으로 자동 갱신

**표시 항목 (해외 모드 기준)**

```
● 해외 실시간 추정가
₩{overseasPrice} 원
≈ ${overseasPriceUsd} USD
{날짜} 종가 대비 ▲{overseasDiffAmount}원 | +{overseasDiffRate}%

거래량 (KRX+NXT)    {volume}주
거래대금 (KRX+NXT)  {tradingValue}억 원
시가총액             {marketCap}조 원

한국 종가            ₩{koreaClosePrice}
애프터마켓 마감가    ₩{aftermarketPrice} | "변동없음"
애프터마켓 대비      +{aftermarketDiffRate}% · +₩{aftermarketDiffAmount}
```

#### 섹션 B — 관련 ETF/지수 (`/[ticker]/etf`)

- 종목별 연관 지수·ETF를 카드 형태로 나열
- 각 카드: 지수명 / 현재값 / 전일 대비 등락률

| 탭 | 우선 표시 항목 |
|----|--------------|
| 삼성전자 | KOSPI, KOSPI 200, KODEX 삼성그룹 등 삼성전자 비중 높은 국내 ETF |
| SK하이닉스 | SOX (필라델피아 반도체), SOXX, 글로벌 반도체 ETF |

#### 섹션 C — 예측 (`/[ticker]/forecast`)

- 상단: `ModelTab` — `Prophet` | `LSTM` 전환 (기본: Prophet)
- 중앙: `ForecastChart` (크게)
  - 과거 90일: **실선** (실제 종가)
  - 예측 1일: **점선** + 95% 신뢰구간 반투명 영역
  - x축: 날짜, y축: 주가(원)
- 하단: `MetricsPanel` — 4개 카드
  - 예측 상승여력 (%)
  - 모델 정확도 MAPE (%)
  - 예측 날짜
  - 마지막 업데이트

---

## 7. 디자인 시스템

### 색상 토큰

```ts
// 한국 주식 시장 관행 — 절대 반전 금지
const PRICE_COLORS = {
  up:      '#E74C3C',   // 상승 빨강
  down:    '#3498DB',   // 하락 파랑
  neutral: '#888780',   // 보합
}
```

### 수치 폰트

- 가격·퍼센트·지수: `font-variant-numeric: tabular-nums` 필수
- 대형 가격 (`₩300,711`): `text-4xl font-bold tabular-nums`

### 테마

- 라이트/다크 토글: Header 우상단
- `next-themes` + Tailwind `class` 전략
- 다크 모드에서도 상승=빨강, 하락=파랑 유지

### 반응형 grid (가격 섹션)

| 뷰포트 | StockCard 열 수 |
|--------|----------------|
| < 640px | 1열 |
| ≥ 640px | 1열 (카드 1개이므로 중앙 정렬) |

---

## 8. 유틸 함수 규칙 (`lib/format.ts`)

```ts
formatPrice(price: number): string
// 300711 → "300,711"  (단위 "원"은 컴포넌트에서 별도로 붙임)

formatTrillion(price: number): string
// 1710365_0000_0000 → "1710조 365억"

formatRate(rate: number): string
// 2.81 → "+2.81%"  /  -1.2 → "-1.20%"

formatDiff(amount: number): string
// 8211 → "▲8,211"  /  -500 → "▼500"
```

---

## 9. 금지 사항

```
❌ 상승=파랑, 하락=빨강 (한국 관행 반전 절대 금지)
❌ 가격 comma 생략 — 300711원 (x) → 300,711원 (o)
❌ formatPrice / formatRate / formatDiff 우회하여 직접 문자열 생성
❌ 프론트에서 네이버 금융 API 직접 호출 (/api/* 프록시 필수)
❌ 네이버 금융 파싱 코드를 lib/naver.ts 외부에 작성
❌ STOCKS 상수 외 종목 임의 추가 (현대차 등 3종목째 추가 금지)
❌ 컴포넌트 이름을 디렉토리 구조와 다르게 생성
❌ aftermarketPrice === null 일 때 "₩0" 또는 빈칸 — "변동없음" 텍스트 표시
❌ USD 환산 시 환율 하드코딩 — 반드시 /api/exchange-rate 응답값 사용
❌ 조 단위 생략하여 숫자만 표기 — 반드시 formatTrillion() 사용
❌ Hyperliquid API 사용 — YENLAB은 코인 파생 지표를 사용하지 않음
```

## 10. 강제 사항

```
✅ 모든 가격 표시는 formatPrice() 통과
✅ 모든 등락률은 formatRate() 통과
✅ 모든 등락폭은 formatDiff() 통과
✅ 상승 시 #E74C3C, 하락 시 #3498DB 적용
✅ 가격 섹션 StockCard는 10초마다 useStockPolling으로 자동 갱신
✅ ForecastChart 과거선=solid, 예측선=dashed 시각 구분
✅ 모든 API 응답 updatedAt → 화면에 "N분 전 갱신" 형태로 표시
✅ 리포트 정렬 상태는 URL query(?sort=)로 관리
✅ 다크 모드 전환 시 상승/하락 색상 유지
✅ 신규 컴포넌트는 반드시 해당 기능 폴더 하위에 생성
✅ 종목 탭 전환은 URL 파라미터([ticker])로 관리
✅ SOX 지수는 Header 중앙 패널에 KOSPI·환율과 함께 상시 표시
```