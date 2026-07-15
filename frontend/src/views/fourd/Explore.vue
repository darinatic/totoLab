<script setup>
import { ref, computed, onMounted } from 'vue'
import { useFourdStore } from '../../stores/fourd'
import { fourd } from '../../api/fourd'
import { tokens, themeVersion } from '../../charts'
import * as B from '../../chartBuilders'
import FourDigits from '../../components/FourDigits.vue'
import StatTile from '../../components/StatTile.vue'
import EChart from '../../components/EChart.vue'

const store = useFourdStore()
const d = ref({})
const loading = ref(true)

// number explorer
const numInput = ref('1234')
const numberDetail = ref(null)
async function lookup() {
  const n = String(numInput.value).padStart(4, '0').slice(0, 4)
  numberDetail.value = await fourd.numberDetail(n)
}

// rolling digit rate
const rollPos = ref(0)
const rollDigit = ref(8)
const rolling = ref(null)
async function loadRolling() {
  rolling.value = await fourd.rolling(rollPos.value, rollDigit.value)
}

onMounted(async () => {
  const [latest, freq, overall, sums, repeats, patterns, mostDrawn, fairness] =
    await Promise.all([
      store.latest(), store.digitFrequency('first'), store.overallDigits(), store.sums(),
      store.repeats(), store.patterns(), store.mostDrawn(), store.fairness(),
    ])
  d.value = { latest, freq, overall, sums, repeats, patterns, mostDrawn, fairness }
  await Promise.all([lookup(), loadRolling()])
  loading.value = false
})

const heatOpt = computed(() => (themeVersion.value, d.value.freq ? B.digitHeatmap(d.value.freq.positions, tokens()) : {}))
const overallOpt = computed(() => (themeVersion.value, d.value.overall
  ? B.distributionBar(d.value.overall.digits, 'digit', 'count', tokens(), tokens().series[0]) : {}))
const sumOpt = computed(() => (themeVersion.value, d.value.sums
  ? B.distributionBar(d.value.sums.histogram, 'sum', 'count', tokens(), tokens().series[1]) : {}))
const repeatsOpt = computed(() => (themeVersion.value, d.value.repeats
  ? B.distributionBar(d.value.repeats.distribution, 'matches', 'pct', tokens(), tokens().series[2], { pct: true }) : {}))
const rollOpt = computed(() => (themeVersion.value, rolling.value && rolling.value.rolling.length
  ? B.rollingLine(rolling.value.rolling, rolling.value.expected_rate, tokens()) : {}))

function scrollTo(id) { document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }
</script>

<template>
  <div class="container">
    <h1 class="page-title">Explore — 4D</h1>
    <p class="page-sub">Digit patterns across all 23 winning numbers, focused on the First prize.</p>

    <div v-if="loading" class="loading">Loading analysis…</div>

    <template v-else>
      <div class="subnav">
        <button class="btn ghost" @click="scrollTo('overview')">Overview</button>
        <button class="btn ghost" @click="scrollTo('patterns')">Patterns</button>
        <button class="btn ghost" @click="scrollTo('numbers')">Number explorer</button>
      </div>

      <h2 id="overview" class="section-title">Overview</h2>
      <div class="grid cols-3" style="margin-bottom: 16px">
        <StatTile :value="d.freq.n_draws" label="Draws analysed (official results)" />
        <StatTile value="1 in 10,000" label="First prize odds (fixed, unbeatable)" />
        <StatTile :value="d.patterns.patterns[0].pct + '%'" label="First prize all-different" />
      </div>
      <div class="grid cols-2">
        <div class="card">
          <h3>Latest draw</h3>
          <p class="card-sub">Draw {{ d.latest.draw_no }} · {{ d.latest.draw_date }}</p>
          <div class="prize-row"><span class="plabel">1st</span><FourDigits :number="d.latest.first" prize /></div>
          <div class="prize-row"><span class="plabel">2nd</span><FourDigits :number="d.latest.second" /></div>
          <div class="prize-row"><span class="plabel">3rd</span><FourDigits :number="d.latest.third" /></div>
        </div>
        <div class="card">
          <h3>Fairness check</h3>
          <p class="card-sub">Are the digits statistically fair?</p>
          <span class="badge" :class="d.fairness.overall_passes ? 'good' : 'bad'">
            {{ d.fairness.overall_passes ? '✓ Consistent with a fair draw' : '⚠ Anomaly detected' }}
          </span>
          <p class="hint" style="margin-top: 12px">{{ d.fairness.tests[0].verdict }}</p>
        </div>
      </div>

      <h2 id="patterns" class="section-title">Patterns</h2>
      <p class="hint" style="margin-top: -8px; margin-bottom: 14px">
        Structure in the digits — all of it exactly what randomness produces.
      </p>
      <div class="card">
        <h3>First-prize digit frequency by position</h3>
        <p class="card-sub">How often each digit 0–9 lands in each position (darker = more often).</p>
        <EChart :option="heatOpt" />
      </div>
      <div class="grid cols-2" style="margin-top: 16px">
        <div class="card">
          <h3>Overall digit frequency</h3>
          <p class="card-sub">Every digit across all 23 winning numbers — flat, as expected.</p>
          <EChart :option="overallOpt" />
        </div>
        <div class="card">
          <h3>First-prize digit sum</h3>
          <p class="card-sub">Sum of the 4 digits — bell-shaped around {{ d.sums.mean }}.</p>
          <EChart :option="sumOpt" />
        </div>
        <div class="card">
          <h3>Repeats from previous draw</h3>
          <p class="card-sub">
            Digit-positions shared with the previous First prize. Averages
            {{ d.repeats.expected_mean }} — the independence prediction.
          </p>
          <EChart :option="repeatsOpt" />
        </div>
        <div class="card">
          <h3>Most-drawn numbers</h3>
          <p class="card-sub">Across all 23 winning numbers, all history.</p>
          <table class="data">
            <thead><tr><th>Number</th><th>Times</th></tr></thead>
            <tbody>
              <tr v-for="n in d.mostDrawn.numbers.slice(0, 8)" :key="n.number">
                <td><FourDigits :number="n.number" size="sm" /></td>
                <td>{{ n.count }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <h2 id="numbers" class="section-title">Number explorer</h2>
      <div class="grid cols-2">
        <div class="card">
          <h3>Look up a number</h3>
          <div class="controls">
            <input class="number-input" v-model="numInput" maxlength="4" @keyup.enter="lookup" />
            <button class="btn" @click="lookup">Look up</button>
          </div>
          <template v-if="numberDetail">
            <FourDigits :number="numberDetail.number" prize />
            <table class="data" style="margin-top: 14px">
              <tbody>
                <tr><td>Times drawn (any prize)</td><td>{{ numberDetail.appearances }}</td></tr>
                <tr><td>Last seen</td><td>{{ numberDetail.last_seen ?? 'never' }}</td></tr>
                <tr><td>Digit sum</td><td>{{ numberDetail.digit_sum }}</td></tr>
              </tbody>
            </table>
            <p class="hint" style="margin-top: 10px">
              Past appearances do <strong>not</strong> change its 1-in-10,000 chance next draw.
            </p>
          </template>
        </div>
        <div class="card">
          <h3>Rolling digit rate</h3>
          <div class="controls">
            <label class="hint">Position
              <select class="btn ghost" v-model.number="rollPos" @change="loadRolling">
                <option v-for="p in [0,1,2,3]" :key="p" :value="p">{{ p + 1 }}</option>
              </select>
            </label>
            <label class="hint">Digit
              <select class="btn ghost" v-model.number="rollDigit" @change="loadRolling">
                <option v-for="dg in [0,1,2,3,4,5,6,7,8,9]" :key="dg" :value="dg">{{ dg }}</option>
              </select>
            </label>
          </div>
          <p class="card-sub">Share of recent draws with this digit in this position — hovers around 10%.</p>
          <EChart :option="rollOpt" />
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.subnav { position: sticky; top: 60px; z-index: 5; display: flex; gap: 8px; padding: 10px 0; margin-bottom: 8px; background: var(--page); }
.section-title { font-size: 20px; font-weight: 700; letter-spacing: -0.01em; margin: 34px 0 14px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
.prize-row { display: flex; align-items: center; gap: 12px; margin-top: 10px; }
.plabel { color: var(--muted); font-size: 12px; font-weight: 700; width: 26px; }
</style>
