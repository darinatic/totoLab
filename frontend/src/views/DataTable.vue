<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api/client'
import BallSet from '../components/BallSet.vue'

const rows = ref([])
const total = ref(0)
const limit = 50
const offset = ref(0)
const filterNum = ref('')
const loading = ref(true)

async function load() {
  loading.value = true
  const res = await api.draws(limit, offset.value)
  rows.value = res.items
  total.value = res.total
  loading.value = false
}

const shown = computed(() => {
  const f = parseInt(filterNum.value)
  if (!f) return rows.value
  return rows.value.filter((r) => r.numbers.includes(f) || r.additional === f)
})

function next() { if (offset.value + limit < total.value) { offset.value += limit; load() } }
function prev() { if (offset.value > 0) { offset.value -= limit; load() } }

onMounted(load)
</script>

<template>
  <div class="container">
    <h1 class="page-title">Draw History</h1>
    <p class="page-sub">{{ total }} draws in the current 6/49 era, newest first.</p>

    <div class="controls">
      <input class="number-input" type="number" min="1" max="49"
        v-model="filterNum" placeholder="filter #" style="width: 110px" />
      <span class="hint">Showing draws {{ offset + 1 }}–{{ Math.min(offset + limit, total) }}</span>
      <button class="btn ghost" @click="prev" :disabled="offset === 0">← Newer</button>
      <button class="btn ghost" @click="next" :disabled="offset + limit >= total">Older →</button>
    </div>

    <div v-if="loading" class="loading">Loading…</div>

    <div v-else class="card">
      <table class="data">
        <thead>
          <tr><th>Draw</th><th>Date</th><th>Winning numbers</th><th>Sum</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in shown" :key="r.draw_no">
            <td>{{ r.draw_no }}</td>
            <td>{{ r.draw_date }}</td>
            <td><BallSet :numbers="r.numbers" :additional="r.additional" size="sm" /></td>
            <td>{{ r.sum }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="shown.length === 0" class="hint" style="margin-top: 12px">
        No draws on this page contain {{ filterNum }}. Try another page.
      </p>
    </div>
  </div>
</template>
