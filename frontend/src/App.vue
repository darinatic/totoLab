<script setup>
import { onMounted } from 'vue'
import { useTotoStore } from './stores/toto'

const store = useTotoStore()
// Prime the disclaimer text early so the banner is populated on first paint.
onMounted(() => { store.fairness().catch(() => {}) })
</script>

<template>
  <div class="app-shell">
    <nav class="nav">
      <span class="brand">Toto<span class="dot">.</span>Lab</span>
      <RouterLink to="/">Explore</RouterLink>
      <RouterLink to="/predict">Predictions</RouterLink>
      <RouterLink to="/reality-check">Reality Check</RouterLink>
      <RouterLink to="/data">Data</RouterLink>
    </nav>

    <RouterView />

    <footer class="disclaimer-bar">
      <strong>For entertainment only.</strong>
      {{ store.disclaimer || 'Toto draws are independent random events — no method can predict them better than chance.' }}
    </footer>
  </div>
</template>
