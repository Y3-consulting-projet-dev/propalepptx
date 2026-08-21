<script setup>
import { ref } from 'vue'
import { loginUser } from '../services'

const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const showPassword = ref(false)

const emit = defineEmits(['login'])

const handleSubmit = async () => {
  if (!email.value || !password.value) {
    error.value = 'Veuillez remplir tous les champs'
    return
  }

  try {
    loading.value = true
    error.value = ''
    await loginUser(email.value, password.value)
    emit('login')
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const togglePasswordVisibility = () => {
  showPassword.value = !showPassword.value
}
</script>

<template>
  <div class="login-container">
    <!-- Left Side -->
    <div class="login-left">
      <div class="left-content">
        <h1>BIENVENUE SUR L'OUTIL GENERATEUR DE PRESENTATIONS</h1>
        <div class="illustration">
          <img
            src="https://i.pinimg.com/736x/18/58/dd/1858dd74ca0f0210decf784547217053.jpg"
            alt="Presentation tool illustration"
          >
        </div>
        <p class="tagline">Simplifier vos présentations, boostez votre productivité avec l'IA</p>
      </div>
    </div>

    <!-- Right Side -->
    <div class="login-right">
      <div class="login-form">
        <h2 class="title">CONNEXION</h2>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <form @submit.prevent="handleSubmit">
          <div class="form-group">
            <label for="email">EMAIL</label>
            <input
              id="email"
              v-model="email"
              placeholder="EMAIL"
              required
            >
          </div>

          <div class="form-group">
            <label for="password">MOT DE PASSE</label>
            <div class="password-wrapper">
              <input
                id="password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                placeholder="MOT DE PASSE"
                required
              >
              <button
                type="button"
                class="toggle-password-btn"
                @click="togglePasswordVisibility"
                :aria-label="showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'"
              >
                <svg v-if="!showPassword" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M3 3l18 18" />
                  <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8" />
                  <path d="M9.9 5.2A11.4 11.4 0 0 1 12 5c6.5 0 10 7 10 7a18.7 18.7 0 0 1-4.3 5" />
                  <path d="M6.2 6.2A18.8 18.8 0 0 0 2 12s3.5 7 10 7a11.3 11.3 0 0 0 5-1.1" />
                </svg>
              </button>
            </div>
          </div>

          <button class="login-btn" @click="handleSubmit" :disabled="loading">
            {{ loading ? 'Chargement...' : 'Se Connecter' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  min-height: 100vh;
  background: #f5f5f5;
}

.login-left {
  flex: 1;
  background: linear-gradient(135deg, #003d5c 0%, #00527a 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: white;
}

.left-content {
  text-align: center;
  max-width: 400px;
}

.left-content h1 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 40px;
  line-height: 1.4;
  letter-spacing: 0.5px;
}

.illustration {
  width: 250px;
  height: 250px;
  margin: 0 auto 40px;
  opacity: 0.9;
}

.illustration img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 12px;
}

.tagline {
  font-size: 16px;
  line-height: 1.6;
  opacity: 0.95;
  margin: 0;
}

.login-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: #f5f5f5;
}

.login-form {
  width: 100%;
  max-width: 380px;
}

.title {
  font-size: 32px;
  font-weight: 700;
  color: #7ec33b;
  margin: 0 0 40px 0;
  letter-spacing: 1px;
  text-align: center;
}

.error-message {
  background: #fee;
  color: #c33;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 24px;
  font-size: 14px;
  text-align: center;
  border: 1px solid #fcc;
}

.form-group {
  margin-bottom: 24px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
  letter-spacing: 0.5px;
}

.form-group input {
  width: 100%;
  padding: 14px 16px;
  border: 2px solid #7ec33b;
  border-radius: 12px;
  font-size: 14px;
  background: white;
  color: #333;
  transition: all 0.3s ease;
}

.form-group input::placeholder {
  color: #999;
}

.form-group input:focus {
  outline: none;
  border-color: #6ab32f;
  background: #fafafa;
}

.password-wrapper {
  position: relative;
}

.password-wrapper input {
  padding-right: 48px;
}

.toggle-password-btn {
  position: absolute;
  top: 50%;
  right: 12px;
  transform: translateY(-50%);
  border: none;
  background: transparent;
  cursor: pointer;
  color: #7ec33b;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2px;
}

.toggle-password-btn:hover {
  color: #6ab32f;
}

.toggle-password-btn svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.login-btn {
  width: 100%;
  padding: 14px;
  background: #7ec33b;
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-bottom: 24px;
}

.login-btn:hover:not(:disabled) {
  background: #6ab32f;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(122, 195, 59, 0.3);
}

.login-btn:disabled {
  background: #999;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .login-container {
    flex-direction: column;
  }

  .login-left {
    padding: 30px 20px;
    min-height: 40vh;
  }

  .left-content h1 {
    font-size: 20px;
    margin-bottom: 30px;
  }

  .illustration {
    width: 180px;
    height: 180px;
    margin-bottom: 30px;
  }

  .tagline {
    font-size: 14px;
  }

  .login-right {
    padding: 30px 20px;
    min-height: 60vh;
  }

  .login-form {
    max-width: 100%;
  }

  .title {
    font-size: 28px;
    margin-bottom: 30px;
  }
}
</style>
