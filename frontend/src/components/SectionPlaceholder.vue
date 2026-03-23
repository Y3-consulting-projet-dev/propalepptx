<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    default: '',
  },
})
</script>

<template>
  <section class="card px-6 py-6">
    <h2 class="text-xl font-semibold text-slate-900">{{ title }}</h2>
    <p v-if="description" class="mt-2 text-sm text-slate-500">{{ description }}</p>
  </section>
</template>
