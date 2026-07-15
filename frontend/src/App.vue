<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUiStore, WINDOWS } from './stores/ui'

const route = useRoute()
const ui = useUiStore()
const { window: dataWindow } = storeToRefs(ui)

// Current game + section derived from the path (/toto/explore, /4d/predict, ...).
const game = computed(() => (route.path.startsWith('/4d') ? '4d' : 'toto'))
const section = computed(() => route.path.split('/')[2] || 'explore')

const tabs = [
  { key: 'explore', label: 'Explore' },
  { key: 'predict', label: 'Predictions' },
  { key: 'reality-check', label: 'Reality Check' },
  { key: 'data', label: 'Data' },
]

const oddsLine = computed(() =>
  game.value === '4d'
    ? 'Singapore 4D draws are independent random events — matching the First prize is 1 in 10,000.'
    : 'Toto draws are independent random events — no method can predict them better than chance.')
</script>

<template>
  <div class="app-shell">
    <nav class="nav">
      <span class="brand">SG&nbsp;Lottery<span class="dot">.</span>Lab</span>

      <div class="game-switch">
        <RouterLink :to="`/toto/${section}`" class="game-btn" :class="{ active: game === 'toto' }">Toto</RouterLink>
        <RouterLink :to="`/4d/${section}`" class="game-btn" :class="{ active: game === '4d' }">4D</RouterLink>
      </div>

      <div class="tabs">
        <RouterLink v-for="t in tabs" :key="t.key" :to="`/${game}/${t.key}`"
          class="tab" :class="{ active: section === t.key }">{{ t.label }}</RouterLink>
      </div>

      <label class="window-select" title="Restrict analysis and predictions to recent draws">
        <span>Window</span>
        <select class="btn ghost" v-model="dataWindow">
          <option v-for="w in WINDOWS" :key="w.key" :value="w.key">{{ w.label }}</option>
        </select>
      </label>
    </nav>

    <RouterView v-slot="{ Component }">
      <KeepAlive>
        <component :is="Component" />
      </KeepAlive>
    </RouterView>

    <footer class="disclaimer-bar">
      <p class="disclaimer-main">
        <strong>For entertainment only.</strong> {{ oddsLine }}
        The expected value of a ticket is negative.
      </p>
      <p class="helpline">
        Gambling problem? Call the National Problem Gambling Helpline
        <a href="tel:1800-6-668-668">1800-6-668-668</a> (24 hrs) or webchat at
        <a href="https://www.ncpg.org.sg" target="_blank" rel="noopener">ncpg.org.sg</a>.
      </p>
    </footer>
  </div>
</template>

<style scoped>
.game-switch { display: flex; gap: 4px; margin-right: 18px; background: var(--surface-2); padding: 3px; border-radius: 9px; }
.game-btn { padding: 6px 14px; border-radius: 7px; font-size: 13px; font-weight: 650; color: var(--text-secondary); }
.game-btn.active { background: var(--series-1); color: #fff; }
.tabs { display: flex; gap: 4px; overflow-x: auto; }
.tab { padding: 8px 14px; border-radius: 8px; color: var(--text-secondary); font-size: 14px; font-weight: 500; white-space: nowrap; }
.tab:hover { background: var(--surface-2); color: var(--text-primary); }
.tab.active { background: var(--series-1); color: #fff; }
.window-select { margin-left: auto; display: flex; align-items: center; gap: 6px; white-space: nowrap; }
.window-select span { color: var(--muted); font-size: 12px; font-weight: 600; }
.window-select select { padding: 6px 8px; font-size: 13px; }
</style>
