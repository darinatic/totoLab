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

    <!-- KeepAlive preserves each page's state (incl. the slow backtest and
         prediction results + rendered charts) so switching tabs is instant and
         the expensive work runs only once per session. -->
    <RouterView v-slot="{ Component }">
      <KeepAlive>
        <component :is="Component" />
      </KeepAlive>
    </RouterView>

    <footer class="disclaimer-bar">
      <p class="disclaimer-main">
        <strong>For entertainment only.</strong>
        {{ store.disclaimer || 'Toto draws are independent random events — no method can predict them better than chance.' }}
      </p>
      <p class="helpline">
        Gambling problem? Call the National Problem Gambling Helpline
        <a href="tel:1800-6-668-668">1800-6-668-668</a> (24 hrs) or webchat at
        <a href="https://www.ncpg.org.sg" target="_blank" rel="noopener">ncpg.org.sg</a>.
      </p>
    </footer>
  </div>
</template>
