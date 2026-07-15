<script setup>
import { ref, onMounted } from 'vue'
import { fourd } from '../../api/fourd'
import FourDigits from '../../components/FourDigits.vue'

const rows = ref([])
const total = ref(0)
const limit = 30
const offset = ref(0)
const loading = ref(true)

async function load() {
  loading.value = true
  const res = await fourd.draws(limit, offset.value)
  rows.value = res.items
  total.value = res.total
  loading.value = false
}
function next() { if (offset.value + limit < total.value) { offset.value += limit; load() } }
function prev() { if (offset.value > 0) { offset.value -= limit; load() } }
onMounted(load)
</script>

<template>
  <div class="container">
    <h1 class="page-title">Draw History — 4D</h1>
    <p class="page-sub">{{ total }} draws (official Singapore Pools results), newest first.</p>

    <div class="controls">
      <span class="hint">Showing draws {{ offset + 1 }}–{{ Math.min(offset + limit, total) }}</span>
      <button class="btn ghost" @click="prev" :disabled="offset === 0">← Newer</button>
      <button class="btn ghost" @click="next" :disabled="offset + limit >= total">Older →</button>
    </div>

    <div v-if="loading" class="loading">Loading…</div>

    <div v-else class="card">
      <table class="data">
        <thead>
          <tr><th>Draw</th><th>Date</th><th>1st</th><th>2nd</th><th>3rd</th><th>Starter / Consolation</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.draw_no">
            <td>{{ r.draw_no }}</td>
            <td>{{ r.draw_date }}</td>
            <td><FourDigits :number="r.first" prize size="sm" /></td>
            <td><FourDigits :number="r.second" size="sm" /></td>
            <td><FourDigits :number="r.third" size="sm" /></td>
            <td class="hint">{{ r.starters.length }} starter · {{ r.consolations.length }} consolation</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
