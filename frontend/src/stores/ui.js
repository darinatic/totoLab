import { defineStore } from 'pinia'

// Global lookback window shared across games and views. A window changes which
// numbers the heuristics favour but NOT the odds - the backtest proves it.
export const WINDOWS = [
  { key: 'all', label: 'All time' },
  { key: '1y', label: 'Last year' },
  { key: '6m', label: 'Last 6 months' },
  { key: '3m', label: 'Last 3 months' },
]

export const useUiStore = defineStore('ui', {
  state: () => ({ window: 'all' }),
  getters: {
    windowLabel: (s) => (WINDOWS.find((w) => w.key === s.window)?.label ?? 'All time'),
  },
})
