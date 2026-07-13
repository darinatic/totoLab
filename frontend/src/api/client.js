// Thin fetch wrapper. In dev, calls go to /api/* which Vite proxies to the
// backend; in production set VITE_API_BASE to the deployed API origin.
const BASE = import.meta.env.VITE_API_BASE || '/api'

async function get(path) {
  // API data must never be served from the browser's HTTP cache.
  const res = await fetch(`${BASE}${path}`, { cache: 'no-store' })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`API ${res.status}: ${body || res.statusText}`)
  }
  return res.json()
}

export const api = {
  health: () => get('/health'),
  latest: () => get('/draws/latest'),
  draws: (limit = 50, offset = 0) => get(`/draws?limit=${limit}&offset=${offset}`),
  frequency: () => get('/stats/frequency'),
  gaps: () => get('/stats/gaps'),
  pairs: (top = 30) => get(`/stats/pairs?top=${top}`),
  sums: () => get('/stats/sums'),
  oddeven: () => get('/stats/oddeven'),
  decades: () => get('/stats/decades'),
  repeats: () => get('/stats/repeats'),
  consecutive: () => get('/stats/consecutive'),
  waittime: () => get('/stats/waittime'),
  numberDetail: (n) => get(`/stats/number/${n}`),
  fairness: () => get('/fairness'),
  strategies: () => get('/strategies'),
  predict: (strategy = 'all', seed, count = 6, sets = 1) => {
    const s = seed != null ? `&seed=${seed}` : ''
    return get(`/predict?strategy=${strategy}&count=${count}&sets=${sets}${s}`)
  },
  backtest: (testSize = 150, includeMl = true, seed = 0) =>
    get(`/backtest?test_size=${testSize}&include_ml=${includeMl}&seed=${seed}`),

  // Static precomputed default backtest (fast first load). Served from the SPA's
  // public/ dir at the site root, so it bypasses the /api base. Returns null if
  // absent, so callers can fall back to the live endpoint.
  precomputedBacktest: async () => {
    try {
      const res = await fetch('/precomputed/backtest.json', { cache: 'no-store' })
      return res.ok ? res.json() : null
    } catch {
      return null
    }
  },
}
