// 4D API client. Endpoints live under /api/4d; the precomputed backtest is a
// static asset at the site root, mirroring the Toto client.
import { useUiStore } from '../stores/ui'

const BASE = (import.meta.env.VITE_API_BASE || '/api') + '/4d'

async function get(path) {
  const w = useUiStore().window
  if (w && w !== 'all') path += (path.includes('?') ? '&' : '?') + 'window=' + w
  const res = await fetch(`${BASE}${path}`, { cache: 'no-store' })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`API ${res.status}: ${body || res.statusText}`)
  }
  return res.json()
}

export const fourd = {
  latest: () => get('/draws/latest'),
  draws: (limit = 30, offset = 0) => get(`/draws?limit=${limit}&offset=${offset}`),
  digitFrequency: (source = 'all') => get(`/stats/digit-frequency?source=${source}`),
  overallDigits: () => get('/stats/overall-digits'),
  hotcold: () => get('/stats/hotcold'),
  sums: () => get('/stats/sums'),
  repeats: () => get('/stats/repeats'),
  patterns: () => get('/stats/patterns'),
  mostDrawn: (top = 20) => get(`/stats/most-drawn?top=${top}`),
  rolling: (position, digit) => get(`/stats/rolling?position=${position}&digit=${digit}`),
  numberDetail: (n) => get(`/stats/number/${n}`),
  fairness: () => get('/fairness'),
  predict: (strategy = 'all', seed, sets = 1) => {
    const s = seed != null ? `&seed=${seed}` : ''
    return get(`/predict?strategy=${strategy}&sets=${sets}${s}`)
  },
  backtest: (testSize = 150, includeMl = true, seed = 0) =>
    get(`/backtest?test_size=${testSize}&include_ml=${includeMl}&seed=${seed}`),
  precomputedBacktest: async () => {
    try {
      const res = await fetch('/precomputed/4d_backtest.json', { cache: 'no-store' })
      return res.ok ? res.json() : null
    } catch {
      return null
    }
  },
}
