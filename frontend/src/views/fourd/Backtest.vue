<script setup>
import { ref, computed } from 'vue'
import { fourd } from '../../api/fourd'
import { useFourdStore } from '../../stores/fourd'
import { tokens, baseOption, themeVersion } from '../../charts'
import EChart from '../../components/EChart.vue'

const store = useFourdStore()
const bt = ref(null)
const fairness = ref(null)
const testSize = ref(150)
const includeMl = ref(true)
const loading = ref(true)
const running = ref(false)
const isPrecomputed = ref(false)

async function run() {
  running.value = true
  isPrecomputed.value = false
  const [b, f] = await Promise.all([fourd.backtest(testSize.value, includeMl.value, 0), store.fairness()])
  bt.value = b; fairness.value = f; running.value = false; loading.value = false
}

async function loadInitial() {
  const [pre, f] = await Promise.all([fourd.precomputedBacktest(), store.fairness()])
  fairness.value = f
  if (pre) { bt.value = pre; isPrecomputed.value = true; loading.value = false }
  else await run()
}
loadInitial()

const option = computed(() => {
  themeVersion.value
  if (!bt.value) return {}
  const t = tokens()
  const rows = [...bt.value.results].reverse()
  return {
    ...baseOption(t),
    grid: { left: 150, right: 30, top: 20, bottom: 40, containLabel: true },
    tooltip: {
      ...baseOption(t).tooltip, trigger: 'item',
      formatter: (p) => {
        const r = rows[p.dataIndex]
        return `${r.label}<br/>mean matched digits: <b>${r.mean_matches}</b>` +
          `<br/>95% CI: ${r.ci_low}–${r.ci_high}` +
          (r.p_vs_random != null ? `<br/>p vs random: ${r.p_vs_random}` : '')
      },
    },
    xAxis: { type: 'value', name: 'avg. matched digits (of 4)', nameLocation: 'middle', nameGap: 26,
      nameTextStyle: { color: t.muted, fontSize: 11 }, splitLine: { lineStyle: { color: t.grid } },
      axisLabel: { color: t.muted, fontSize: 11 } },
    yAxis: { type: 'category', data: rows.map((r) => r.label), axisLabel: { color: t.secondary, fontSize: 12 },
      axisLine: { lineStyle: { color: t.baseline } }, axisTick: { show: false } },
    series: [
      {
        type: 'bar', barWidth: 16,
        data: rows.map((r) => ({ value: r.mean_matches,
          itemStyle: { color: r.strategy === 'random' ? t.series[2] : t.series[0], borderRadius: [0, 3, 3, 0] } })),
        markLine: { silent: true, symbol: 'none', data: [{ xAxis: bt.value.theoretical_random }],
          lineStyle: { color: t.critical, type: 'dashed', width: 2 },
          label: { formatter: 'random 0.4', color: t.critical, fontSize: 10, position: 'insideEndTop' } },
      },
      {
        type: 'custom', encode: { x: [0, 1], y: 2 },
        renderItem: (params, api) => {
          const lo = api.coord([api.value(0), api.value(2)])
          const hi = api.coord([api.value(1), api.value(2)])
          const y = lo[1], cap = 5, style = { stroke: t.text, lineWidth: 1.5 }
          const line = (x1, y1, x2, y2) => ({ type: 'line', shape: { x1, y1, x2, y2 }, style })
          return { type: 'group', children: [
            line(lo[0], y, hi[0], y), line(lo[0], y - cap, lo[0], y + cap), line(hi[0], y - cap, hi[0], y + cap),
          ] }
        },
        data: rows.map((r, i) => [r.ci_low, r.ci_high, i]), z: 10,
      },
    ],
  }
})
</script>

<template>
  <div class="container">
    <h1 class="page-title">Reality Check — 4D</h1>
    <p class="page-sub">
      We walk forward through history: at each past draw we predict using <em>only</em> the draws
      before it, then score matched digit-positions against the First prize. A random guess scores
      0.4. If any strategy had skill, its bar would sit clearly right of the red line.
    </p>

    <div class="controls">
      <label class="hint">Test window
        <input class="number-input" type="number" v-model.number="testSize" min="20" max="400" step="10" />
      </label>
      <label class="hint"><input type="checkbox" v-model="includeMl" /> include ML</label>
      <button class="btn" :disabled="running" @click="run">{{ running ? 'Running…' : 'Run backtest' }}</button>
    </div>

    <div v-if="loading" class="loading">Running walk-forward backtest…</div>

    <template v-else>
      <div class="card" style="margin-bottom: 16px">
        <span class="badge" :class="bt.any_beats_random ? 'bad' : 'good'">
          {{ bt.any_beats_random ? '⚠ A strategy edged ahead (noise)' : '✓ Nothing beats random' }}
        </span>
        <p class="hint" style="margin-top: 12px">{{ bt.verdict }}</p>
        <p v-if="isPrecomputed" class="hint" style="margin-top: 8px">
          Showing the latest precomputed run (through draw {{ bt.generated_from_draw }}).
          Adjust the settings above and press <strong>Run backtest</strong> to recompute live.
        </p>
      </div>

      <div class="card">
        <h3>Average matched digits per strategy</h3>
        <p class="card-sub">
          Bars show the mean over {{ bt.test_size }} test draws; whiskers are the 95% bootstrap CI.
          Random-baseline theory: {{ bt.theoretical_random }}. Exact-hit-any-prize (random): {{ bt.exact_hit_random }}.
        </p>
        <EChart :option="option" tall />
      </div>

      <div class="card" style="margin-top: 16px">
        <h3>Results table</h3>
        <table class="data">
          <thead>
            <tr><th>Strategy</th><th>Mean digits</th><th>95% CI</th><th>Exact-hit rate</th><th>p vs random</th><th>Verdict</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in bt.results" :key="r.strategy">
              <td>{{ r.label }}</td>
              <td>{{ r.mean_matches }}</td>
              <td>{{ r.ci_low }}–{{ r.ci_high }}</td>
              <td>{{ (r.hit_any_rate * 100).toFixed(2) }}%</td>
              <td>{{ r.p_vs_random ?? '—' }}</td>
              <td><span class="badge" :class="r.beats_random ? 'bad' : 'good'">
                {{ r.beats_random ? 'above (noise)' : 'no edge' }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="fairness" class="card" style="margin-top: 16px">
        <h3>Fairness tests</h3>
        <p class="card-sub">Independent statistical checks that the draw is truly random.</p>
        <table class="data">
          <thead><tr><th>Test</th><th>p-value</th><th>Result</th><th>Interpretation</th></tr></thead>
          <tbody>
            <tr v-for="test in fairness.tests" :key="test.test">
              <td>{{ test.test }}</td>
              <td>{{ test.p_value ?? '—' }}</td>
              <td><span class="badge" :class="test.passes ? 'good' : 'bad'">{{ test.passes ? 'pass' : 'flag' }}</span></td>
              <td class="hint">{{ test.verdict }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="fairness.significance_note" class="hint" style="margin-top: 10px">
          {{ fairness.significance_note }}
        </p>
      </div>
    </template>
  </div>
</template>
