<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTotoStore } from '../stores/toto'
import { api } from '../api/client'
import { tokens, themeVersion } from '../charts'
import * as B from '../chartBuilders'
import BallSet from '../components/BallSet.vue'
import StatTile from '../components/StatTile.vue'
import EChart from '../components/EChart.vue'

const store = useTotoStore()
const d = ref({}) // all datasets keyed by name
const loading = ref(true)

// Number Explorer state
const pool = Array.from({ length: 49 }, (_, i) => i + 1)
const selected = ref(23)
const numberDetail = ref(null)

async function pickNumber(n) {
  selected.value = n
  numberDetail.value = await api.numberDetail(n)
}

onMounted(async () => {
  const [latest, freq, fairness, pairs, sums, oddeven, repeats, consecutive, waittime] =
    await Promise.all([
      store.latest(), store.frequency(), store.fairness(), store.pairs(),
      store.sums(), store.oddeven(), store.repeats(), store.consecutive(), store.waittime(),
    ])
  d.value = { latest, freq, fairness, pairs, sums, oddeven, repeats, consecutive, waittime }
  await pickNumber(selected.value)
  loading.value = false
})

const hottest = computed(() =>
  d.value.freq ? [...d.value.freq.numbers].sort((a, b) => b.count - a.count)[0] : null)

// --- chart options (depend on themeVersion so they recolor on theme flip) ---
const freqOpt = computed(() => (themeVersion.value, d.value.freq ? B.frequencyBar(d.value.freq, tokens()) : {}))
const heatOpt = computed(() => (themeVersion.value, d.value.pairs ? B.pairHeatmap(d.value.pairs, tokens()) : {}))
const sumOpt = computed(() => (themeVersion.value, d.value.sums
  ? B.distributionBar(d.value.sums.histogram, 'bucket', 'count', tokens(), tokens().series[1], { rotate: 40 }) : {}))
const oddEvenOpt = computed(() => {
  themeVersion.value
  if (!d.value.oddeven) return {}
  const items = d.value.oddeven.odd_even.map((x) => ({ label: `${x.odd}/${x.even}`, pct: x.pct }))
  return B.distributionBar(items, 'label', 'pct', tokens(), tokens().series[4], { pct: true })
})
const repeatsOpt = computed(() => {
  themeVersion.value
  if (!d.value.repeats) return {}
  return B.distributionBar(d.value.repeats.distribution, 'repeats', 'pct', tokens(), tokens().series[2], { pct: true })
})
const consecutiveOpt = computed(() => {
  themeVersion.value
  if (!d.value.consecutive) return {}
  return B.distributionBar(d.value.consecutive.distribution, 'pairs', 'pct', tokens(), tokens().series[3], { pct: true })
})
const waitOpt = computed(() => {
  themeVersion.value
  if (!d.value.waittime) return {}
  return B.distributionBar(d.value.waittime.histogram, 'gap', 'count', tokens(), tokens().series[0])
})
const rollingOpt = computed(() => (themeVersion.value, numberDetail.value && numberDetail.value.rolling.length
  ? B.rollingLine(numberDetail.value.rolling, numberDetail.value.expected_rate, tokens()) : {}))

function scrollTo(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
</script>

<template>
  <div class="container">
    <h1 class="page-title">Explore</h1>
    <p class="page-sub">Overview, patterns, and per-number history — all the honest analysis in one place.</p>

    <div v-if="loading" class="loading">Loading analysis…</div>

    <template v-else>
      <div class="subnav">
        <button class="btn ghost" @click="scrollTo('overview')">Overview</button>
        <button class="btn ghost" @click="scrollTo('patterns')">Patterns</button>
        <button class="btn ghost" @click="scrollTo('numbers')">Number explorer</button>
      </div>

      <!-- ================= OVERVIEW ================= -->
      <h2 id="overview" class="section-title">Overview</h2>
      <div class="grid cols-3" style="margin-bottom: 16px">
        <StatTile :value="d.freq.n_draws" label="Draws analysed (6/49 era)" />
        <StatTile value="1 in 13.98M" label="Jackpot odds (fixed, unbeatable)" />
        <StatTile :value="`#${hottest.number}`" :label="`Most drawn (${hottest.count} times)`" />
      </div>
      <div class="grid cols-2">
        <div class="card">
          <h3>Latest draw</h3>
          <p class="card-sub">Draw {{ d.latest.draw_no }} · {{ d.latest.draw_date }}</p>
          <BallSet :numbers="d.latest.numbers" :additional="d.latest.additional" />
        </div>
        <div class="card">
          <h3>Fairness check</h3>
          <p class="card-sub">Is the draw statistically fair?</p>
          <span class="badge" :class="d.fairness.overall_passes ? 'good' : 'bad'">
            {{ d.fairness.overall_passes ? '✓ Consistent with a fair draw' : '⚠ Anomaly detected' }}
          </span>
          <p class="hint" style="margin-top: 12px">{{ d.fairness.tests[0].verdict }}</p>
        </div>
      </div>
      <div class="card" style="margin-top: 16px">
        <h3>Appearance frequency — all 49 numbers</h3>
        <p class="card-sub">How often each number has been drawn vs the fair average. Spread is normal random variation.</p>
        <EChart :option="freqOpt" />
      </div>

      <!-- ================= PATTERNS ================= -->
      <h2 id="patterns" class="section-title">Patterns</h2>
      <p class="hint" style="margin-top: -8px; margin-bottom: 14px">
        Interesting structure — but each of these is exactly what randomness produces, and none predicts the next draw.
      </p>
      <div class="card">
        <h3>Number pair co-occurrence</h3>
        <p class="card-sub">How often the most common number pairs have been drawn together (darker = more often).</p>
        <EChart :option="heatOpt" tall />
      </div>
      <div class="grid cols-2" style="margin-top: 16px">
        <div class="card">
          <h3>Sum of the 6 numbers</h3>
          <p class="card-sub">Distribution of draw totals — bell-shaped, as expected.</p>
          <EChart :option="sumOpt" />
        </div>
        <div class="card">
          <h3>Odd / even split</h3>
          <p class="card-sub">How the six numbers divide between odd and even.</p>
          <EChart :option="oddEvenOpt" />
        </div>
        <div class="card">
          <h3>Repeats from the previous draw</h3>
          <p class="card-sub">
            Numbers shared with the draw before. Averages {{ d.repeats.expected_mean }} —
            exactly the independence prediction.
          </p>
          <EChart :option="repeatsOpt" />
        </div>
        <div class="card">
          <h3>Consecutive numbers</h3>
          <p class="card-sub">
            Adjacent pairs like 23–24 per draw. {{ d.consecutive.pct_with_consecutive }}% of draws contain at least one.
          </p>
          <EChart :option="consecutiveOpt" />
        </div>
      </div>
      <div class="card" style="margin-top: 16px">
        <h3>Wait time between appearances</h3>
        <p class="card-sub">
          Draws a number waits between hits. Roughly geometric with mean
          {{ d.waittime.observed_mean }} (expected {{ d.waittime.expected_mean }}) — the hallmark of a memoryless process.
        </p>
        <EChart :option="waitOpt" />
      </div>

      <!-- ================= NUMBER EXPLORER ================= -->
      <h2 id="numbers" class="section-title">Number explorer</h2>
      <div class="card" style="margin-bottom: 16px">
        <div class="balls">
          <button v-for="n in pool" :key="n" class="ball sm" :class="{ main: n === selected }"
            style="cursor: pointer; border: none" @click="pickNumber(n)">{{ n }}</button>
        </div>
      </div>
      <template v-if="numberDetail">
        <div class="grid cols-4" style="margin-bottom: 16px">
          <StatTile :value="numberDetail.frequency.count" label="times drawn" />
          <StatTile :value="numberDetail.gaps.current_gap" label="draws since last seen" />
          <StatTile :value="numberDetail.gaps.avg_gap ?? '—'" label="average gap" />
          <StatTile :value="`${numberDetail.frequency.deviation > 0 ? '+' : ''}${numberDetail.frequency.deviation}`" label="vs. fair average" />
        </div>
        <div class="card" style="margin-bottom: 16px">
          <h3>Rolling appearance rate — #{{ numberDetail.number }}</h3>
          <p class="card-sub">
            Share of the last 50 draws containing this number. It hovers around the expected
            {{ (numberDetail.expected_rate * 100).toFixed(1) }}% with no trend — no number gets "hot" or "cold".
          </p>
          <EChart :option="rollingOpt" />
        </div>
        <div class="grid cols-2">
          <div class="card">
            <h3>Most frequent partners</h3>
            <p class="card-sub">Numbers most often drawn alongside {{ numberDetail.number }}.</p>
            <table class="data">
              <thead><tr><th>Number</th><th>Times together</th></tr></thead>
              <tbody>
                <tr v-for="p in numberDetail.top_partners" :key="p.number">
                  <td><span class="ball sm main" style="vertical-align: middle">{{ p.number }}</span></td>
                  <td>{{ p.count }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="card">
            <h3>Summary</h3>
            <p class="card-sub">At a glance.</p>
            <table class="data">
              <tbody>
                <tr><td>Last seen</td><td>{{ numberDetail.last_seen ?? 'never' }}</td></tr>
                <tr><td>Longest dry spell</td><td>{{ numberDetail.gaps.max_gap ?? '—' }} draws</td></tr>
                <tr><td>Frequency rank</td><td>#{{ numberDetail.frequency.rank }} of 49</td></tr>
              </tbody>
            </table>
            <p class="hint" style="margin-top: 12px">
              A long "draws since last seen" does <strong>not</strong> make this number due — each draw is independent.
            </p>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.subnav {
  position: sticky; top: 60px; z-index: 5;
  display: flex; gap: 8px; padding: 10px 0; margin-bottom: 8px;
  background: var(--page);
}
.section-title {
  font-size: 20px; font-weight: 700; letter-spacing: -0.01em;
  margin: 34px 0 14px; padding-bottom: 8px; border-bottom: 1px solid var(--border);
}
</style>
