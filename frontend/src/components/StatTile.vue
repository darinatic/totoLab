<script setup>
defineProps({
  value: { type: [String, Number], required: true },
  label: { type: String, required: true },
})
</script>

<template>
  <div class="card stat-tile">
    <div class="value">{{ value }}</div>
    <div class="label">{{ label }}</div>
  </div>
</template>
