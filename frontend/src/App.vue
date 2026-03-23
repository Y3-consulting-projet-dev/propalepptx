
<script setup>
import { ref, onMounted } from 'vue'
import Login from './components/Login.vue'
import Dashboard from './components/Dashboard.vue'
import { isLoggedIn } from './api.js'

const isAuthenticated = ref(false)

const checkAuth = () => {
  isAuthenticated.value = isLoggedIn()
}

onMounted(() => {
  checkAuth()
  // Listen for storage changes (logout from other tabs)
  window.addEventListener('storage', (e) => {
    if (e.key === 'access_token') {
      checkAuth()
    }
  })
})
</script>

<template>
  <Login v-if="!isAuthenticated" @login="checkAuth" />
  <Dashboard v-else @logout="checkAuth" />
</template>
