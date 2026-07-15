<script setup>
import { ref, onMounted } from 'vue'
import { fourd } from '../../api/fourd'
import FourDigits from '../../components/FourDigits.vue'

const picks = ref([])
const nextAfter = ref('')
const seed = ref(1)
const sets = ref(3)
const loading = ref(true)

async function generate() {
  loading.value = true
  const res = await fourd.predict('all', seed.value, sets.value)
  picks.value = res.picks
  nextAfter.value = res.next_draw_after
  loading.value = false
}
function regenerate() { seed.value = Math.floor(Math.random() * 100000); generate() }
onMounted(generate)
</script>

<template>
  <div class="container">
    <h1 class="page-title">Predictions — 4D</h1>
    <p class="page-sub">
      Seven strategies, each suggesting numbers for the draw after {{ nextAfter }}. They look
      different but are statistically equivalent to random — that's the whole point.
    </p>

    <div class="controls">
      <label class="hint">Numbers per strategy
        <select class="btn ghost" v-model.number="sets" @change="generate">
          <option v-for="s in [1, 3, 5, 10]" :key="s" :value="s">{{ s }}</option>
        </select>
      </label>
      <button class="btn" @click="regenerate">↻ Regenerate</button>
      <span class="hint">Every number has the same 1-in-10,000 chance.</span>
    </div>

    <div v-if="loading" class="loading">Generating…</div>

    <div v-else class="grid cols-2">
      <div v-for="p in picks" :key="p.strategy" class="card">
        <h3>{{ p.label }}</h3>
        <p class="card-sub">{{ p.blurb }}</p>
        <div class="num-grid">
          <FourDigits v-for="(num, i) in p.sets" :key="i" :number="num" size="sm" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.num-grid { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; }
</style>
