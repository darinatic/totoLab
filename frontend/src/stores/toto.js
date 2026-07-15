import { defineStore } from 'pinia'
import { api } from '../api/client'
import { useUiStore } from './ui'

// Simple caching store: each dataset is fetched once and reused across views.
export const useTotoStore = defineStore('toto', {
  state: () => ({
    cache: {},
    disclaimer: '',
  }),
  actions: {
    // Fetch-and-cache helper keyed by an arbitrary string.
    async load(key, fetcher) {
      // Namespace by the current window so switching windows fetches fresh.
      const fullKey = `${useUiStore().window}:${key}`
      if (this.cache[fullKey]) return this.cache[fullKey]
      const data = await fetcher()
      if (data && data.disclaimer) this.disclaimer = data.disclaimer
      this.cache[fullKey] = data
      return data
    },
    latest() { return this.load('latest', api.latest) },
    frequency() { return this.load('frequency', api.frequency) },
    gaps() { return this.load('gaps', api.gaps) },
    pairs() { return this.load('pairs', () => api.pairs(40)) },
    sums() { return this.load('sums', api.sums) },
    oddeven() { return this.load('oddeven', api.oddeven) },
    decades() { return this.load('decades', api.decades) },
    repeats() { return this.load('repeats', api.repeats) },
    consecutive() { return this.load('consecutive', api.consecutive) },
    waittime() { return this.load('waittime', api.waittime) },
    fairness() { return this.load('fairness', api.fairness) },
    numberDetail(n) { return this.load(`num-${n}`, () => api.numberDetail(n)) },
    backtest(size, ml, seed) {
      return this.load(`bt-${size}-${ml}-${seed}`, () => api.backtest(size, ml, seed))
    },
  },
})
