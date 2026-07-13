<script setup>
// Thin wrapper around vue-echarts. The parent computes `option` from design
// tokens and includes `themeVersion` in that computed, so a theme flip produces
// a fresh option object and the chart recolors automatically.
import VChart from 'vue-echarts'
import '../charts'

defineProps({
  option: { type: Object, required: true },
  tall: { type: Boolean, default: false },
})
</script>

<template>
  <v-chart class="chart" :class="{ tall }" :option="option" autoresize />
</template>
