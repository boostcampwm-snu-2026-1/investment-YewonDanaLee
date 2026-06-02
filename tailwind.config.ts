import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        up:      '#E74C3C',
        down:    '#3498DB',
        neutral: '#888780',
        page:    'var(--bg-page)',
        card:    'var(--bg-card)',
        muted:   'var(--bg-muted)',
        border:  'var(--border)',
        ink:     'var(--text-1)',
        dim:     'var(--text-2)',
        accent:  'var(--accent)',
      },
    },
  },
  plugins: [],
}
export default config
