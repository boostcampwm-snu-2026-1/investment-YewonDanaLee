export const STOCKS = [
  { name: '삼성전자', ticker: '005930', nameEn: 'Samsung Electronics' },
  { name: 'SK하이닉스', ticker: '000660', nameEn: 'SK Hynix' },
] as const

export type Ticker = '005930' | '000660'
