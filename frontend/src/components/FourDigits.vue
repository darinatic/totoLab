<script setup>
// Renders a 4D number as four digit tiles. `prize` styles the First prize.
defineProps({
  number: { type: [String, Number], required: true },
  prize: { type: Boolean, default: false },
  size: { type: String, default: '' }, // '' | 'sm'
})
</script>

<template>
  <span class="digits" :class="[size, { prize }]">
    <span v-for="(d, i) in String(number).padStart(4, '0')" :key="i" class="digit">{{ d }}</span>
  </span>
</template>

<style scoped>
.digits { display: inline-flex; gap: 4px; }
.digit {
  width: 34px; height: 42px; border-radius: 8px;
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 20px; font-variant-numeric: tabular-nums;
  background: var(--surface-2); color: var(--text-primary);
  border: 1px solid var(--border);
}
.digits.prize .digit { background: var(--series-1); color: #fff; border-color: transparent; }
.digits.sm .digit { width: 24px; height: 30px; font-size: 14px; border-radius: 6px; }
</style>
