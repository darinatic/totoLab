import { defineStore } from 'pinia'
import { fourd } from '../api/fourd'

// Caching store for 4D datasets (same fetch-once pattern as the Toto store).
export const useFourdStore = defineStore('fourd', {
  state: () => ({ cache: {}, disclaimer: '' }),
  actions: {
    async load(key, fetcher) {
      if (this.cache[key]) return this.cache[key]
      const data = await fetcher()
      if (data && data.disclaimer) this.disclaimer = data.disclaimer
      this.cache[key] = data
      return data
    },
    latest() { return this.load('latest', fourd.latest) },
    digitFrequency(source) { return this.load(`digitfreq-${source}`, () => fourd.digitFrequency(source)) },
    overallDigits() { return this.load('overall', fourd.overallDigits) },
    sums() { return this.load('sums', fourd.sums) },
    repeats() { return this.load('repeats', fourd.repeats) },
    patterns() { return this.load('patterns', fourd.patterns) },
    mostDrawn() { return this.load('mostdrawn', () => fourd.mostDrawn(20)) },
    fairness() { return this.load('fairness', fourd.fairness) },
    numberDetail(n) { return this.load(`num-${n}`, () => fourd.numberDetail(n)) },
  },
})
