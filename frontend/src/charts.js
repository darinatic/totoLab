// Central ECharts registration (tree-shaken) + theme helpers that read the CSS
// design tokens so charts match light/dark automatically.
import { ref } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, HeatmapChart, ScatterChart, CustomChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  VisualMapComponent,
  MarkLineComponent,
  DataZoomComponent,
} from 'echarts/components'

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  HeatmapChart,
  ScatterChart,
  CustomChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  VisualMapComponent,
  MarkLineComponent,
  DataZoomComponent,
])

// Bumps whenever the OS theme flips; option computeds depend on it so charts
// re-read tokens and recolor without a page reload.
export const themeVersion = ref(0)
if (typeof window !== 'undefined' && window.matchMedia) {
  window
    .matchMedia('(prefers-color-scheme: dark)')
    .addEventListener('change', () => themeVersion.value++)
}

export function tokens() {
  const s = getComputedStyle(document.documentElement)
  const v = (name) => s.getPropertyValue(name).trim()
  return {
    text: v('--text-primary'),
    secondary: v('--text-secondary'),
    muted: v('--muted'),
    grid: v('--grid'),
    baseline: v('--baseline'),
    surface: v('--surface-1'),
    series: [
      v('--series-1'), v('--series-2'), v('--series-3'),
      v('--series-4'), v('--series-5'), v('--series-6'),
    ],
    good: v('--good'),
    warning: v('--warning'),
    critical: v('--critical'),
  }
}

// Shared axis/tooltip styling applied to every chart for consistency.
export function baseOption(t) {
  return {
    textStyle: { fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif' },
    grid: { left: 44, right: 18, top: 24, bottom: 34, containLabel: true },
    tooltip: {
      backgroundColor: t.surface,
      borderColor: t.grid,
      textStyle: { color: t.text, fontSize: 13 },
      confine: true,
    },
  }
}
