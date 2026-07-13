<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api/client'
import BallSet from '../components/BallSet.vue'

const picks = ref([])
const nextAfter = ref('')
const seed = ref(1)
const count = ref(6)   // numbers per set (Toto System 6–12)
const sets = ref(1)    // independent sets per strategy
const loading = ref(true)

async function generate() {
  loading.value = true
  const res = await api.predict('all', seed.value, count.value, sets.value)
  picks.value = res.picks
  nextAfter.value = res.next_draw_after
  loading.value = false
}

function regenerate() {
  seed.value = Math.floor(Math.random() * 100000)
  generate()
}

onMounted(generate)
</script>

<template>
  <div class="container">
    <h1 class="page-title">Predictions</h1>
    <p class="page-sub">
      Seven strategies, for the draw after {{ nextAfter }}. They look different but are
      statistically equivalent to random — that's the whole point.
    </p>

    <div class="controls">
      <label class="hint">Numbers per set
        <select class="btn ghost" v-model.number="count" @change="generate">
          <option v-for="c in [6, 7, 8, 9, 10, 11, 12]" :key="c" :value="c">{{ c }} (System {{ c }})</option>
        </select>
      </label>
      <label class="hint">Sets per strategy
        <select class="btn ghost" v-model.number="sets" @change="generate">
          <option v-for="s in [1, 2, 3, 5]" :key="s" :value="s">{{ s }}</option>
        </select>
      </label>
      <button class="btn" @click="regenerate">↻ Regenerate</button>
      <span class="hint">Every set is equally (un)likely to win.</span>
    </div>

    <div v-if="loading" class="loading">Generating…</div>

    <div v-else class="grid cols-2">
      <div v-for="p in picks" :key="p.strategy" class="card">
        <h3>{{ p.label }}</h3>
        <p class="card-sub">{{ p.blurb }}</p>
        <div v-for="(set, i) in p.sets" :key="i" class="pick-row">
          <span v-if="p.sets.length > 1" class="set-label">{{ i + 1 }}</span>
          <BallSet :numbers="set" :size="count > 8 ? 'sm' : ''" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pick-row { display: flex; align-items: center; gap: 10px; margin-top: 10px; }
.set-label {
  color: var(--muted); font-size: 12px; font-weight: 600; width: 16px;
  font-variant-numeric: tabular-nums;
}
</style>
