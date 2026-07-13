// Reusable ECharts option builders. Each takes the API payload + design tokens
// and returns a complete option. Views wrap these in a computed that depends on
// `themeVersion` so charts recolor on light/dark switch.
import { baseOption } from './charts'

const catAxis = (t, data, extra = {}) => ({
  type: 'category', data,
  axisLine: { lineStyle: { color: t.baseline } },
  axisTick: { show: false },
  axisLabel: { color: t.muted, fontSize: 10 },
  ...extra,
})
const valAxis = (t, extra = {}) => ({
  type: 'value',
  splitLine: { lineStyle: { color: t.grid } },
  axisLabel: { color: t.muted, fontSize: 11 },
  ...extra,
})

export function frequencyBar(freq, t) {
  const nums = freq.numbers
  return {
    ...baseOption(t),
    grid: { left: 30, right: 14, top: 20, bottom: 26, containLabel: true },
    tooltip: { ...baseOption(t).tooltip, trigger: 'axis',
      formatter: (p) => `Number ${p[0].name}<br/>Drawn ${p[0].value} times` },
    xAxis: catAxis(t, nums.map((n) => n.number), { axisLabel: { color: t.muted, fontSize: 10, interval: 4 } }),
    yAxis: valAxis(t),
    series: [{
      type: 'bar', data: nums.map((n) => n.count),
      itemStyle: { color: t.series[0], borderRadius: [3, 3, 0, 0] },
      markLine: { silent: true, symbol: 'none', data: [{ yAxis: nums[0].expected }],
        lineStyle: { color: t.series[2], type: 'dashed' },
        label: { formatter: 'fair avg', color: t.muted, fontSize: 10 } },
    }],
  }
}

export function pairHeatmap(pairs, t) {
  const data = pairs.pairs
  const nums = [...new Set(data.flatMap((d) => d.pair))].sort((a, b) => a - b)
  const idx = Object.fromEntries(nums.map((n, i) => [n, i]))
  const cells = []
  for (const d of data) {
    cells.push([idx[d.pair[0]], idx[d.pair[1]], d.count])
    cells.push([idx[d.pair[1]], idx[d.pair[0]], d.count])
  }
  const max = Math.max(...data.map((d) => d.count))
  return {
    ...baseOption(t),
    grid: { left: 40, right: 20, top: 16, bottom: 46, containLabel: true },
    tooltip: { ...baseOption(t).tooltip,
      formatter: (p) => `${nums[p.value[0]]} + ${nums[p.value[1]]}<br/>${p.value[2]} draws together` },
    xAxis: catAxis(t, nums, { splitArea: { show: false } }),
    yAxis: catAxis(t, nums),
    visualMap: { min: 0, max, calculable: true, orient: 'horizontal', left: 'center', bottom: 4,
      inRange: { color: ['#cde2fb', '#3987e5', '#0d366b'] },
      textStyle: { color: t.muted, fontSize: 10 } },
    series: [{ type: 'heatmap', data: cells, itemStyle: { borderColor: t.surface, borderWidth: 2 } }],
  }
}

export function distributionBar(items, labelKey, valueKey, t, color, opts = {}) {
  return {
    ...baseOption(t),
    tooltip: { ...baseOption(t).tooltip, trigger: 'axis',
      formatter: (p) => `${p[0].name}<br/>${p[0].value}${opts.pct ? '%' : ''}` },
    xAxis: catAxis(t, items.map((x) => x[labelKey]), opts.rotate ? { axisLabel: { color: t.muted, fontSize: 10, rotate: opts.rotate } } : {}),
    yAxis: valAxis(t, opts.pct ? { axisLabel: { color: t.muted, fontSize: 11, formatter: '{value}%' } } : {}),
    series: [{
      type: 'bar', data: items.map((x) => x[valueKey]),
      itemStyle: { color, borderRadius: [3, 3, 0, 0] },
      ...(opts.markLine != null ? {
        markLine: { silent: true, symbol: 'none', data: [{ xAxis: opts.markLine }],
          lineStyle: { color: t.critical, type: 'dashed' } },
      } : {}),
    }],
  }
}

export function rollingLine(rolling, expectedRate, t) {
  return {
    ...baseOption(t),
    grid: { left: 44, right: 16, top: 20, bottom: 30, containLabel: true },
    tooltip: { ...baseOption(t).tooltip, trigger: 'axis',
      formatter: (p) => `${p[0].name}<br/>rate ${(p[0].value * 100).toFixed(1)}%` },
    xAxis: catAxis(t, rolling.map((r) => r.draw_date), {
      axisLabel: { color: t.muted, fontSize: 9, interval: Math.floor(rolling.length / 6) || 1 } }),
    yAxis: valAxis(t, { axisLabel: { color: t.muted, fontSize: 11, formatter: (v) => `${(v * 100).toFixed(0)}%` } }),
    series: [{
      type: 'line', data: rolling.map((r) => r.rate), smooth: true, symbol: 'none',
      lineStyle: { color: t.series[0], width: 2 }, areaStyle: { color: t.series[0], opacity: 0.08 },
      markLine: { silent: true, symbol: 'none', data: [{ yAxis: expectedRate }],
        lineStyle: { color: t.series[2], type: 'dashed' },
        label: { formatter: 'expected', color: t.muted, fontSize: 10 } },
    }],
  }
}
