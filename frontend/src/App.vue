<script setup>
import { onMounted, ref } from 'vue'
import { getHealth } from './api.js'

const status = ref('loading')
const message = ref('')
const error = ref('')

onMounted(async () => {
  try {
    const data = await getHealth()
    status.value = data.status || 'ok'
    message.value = data.message || ''
  } catch (err) {
    error.value = err.message
    status.value = 'error'
  }
})
</script>

<template>
  <main class="page">
    <section class="card">
      <h1>Frontend ↔ Backend</h1>
      <p class="label">Flask API status</p>
      <p class="status" :data-status="status">{{ status }}</p>
      <p v-if="message" class="message">{{ message }}</p>
      <p v-if="error" class="error">{{ error }}</p>
    </section>
  </main>
</template>
