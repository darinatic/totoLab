<script setup>
// Renders a row of Toto number balls. `additional` is optional and rendered
// after a "+" separator, matching how Singapore Pools presents a draw.
defineProps({
  numbers: { type: Array, required: true },
  additional: { type: Number, default: null },
  size: { type: String, default: '' }, // '' | 'sm'
})
</script>

<template>
  <div class="balls">
    <span v-for="n in numbers" :key="n" class="ball main" :class="size">{{ n }}</span>
    <template v-if="additional != null">
      <span class="ball-plus">+</span>
      <span class="ball additional" :class="size">{{ additional }}</span>
    </template>
  </div>
</template>
