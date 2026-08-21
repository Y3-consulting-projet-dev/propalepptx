import { API_BASE, getAuthHeaders } from './http.js'

export const APP_NAVIGATION_STORAGE_KEY = 'app_navigation_state'

export async function registerUser(email, password, name = null) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ email, password, name })
  })

  if (!res.ok) {
    const error = await res.json()
    throw new Error(error.error || 'Registration failed')
  }

  return res.json()
}

export async function loginUser(email, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ email, password })
  })

  if (!res.ok) {
    const error = await res.json()
    throw new Error(error.error || 'Login failed')
  }

  const data = await res.json()
  // Store token in localStorage
  localStorage.setItem('access_token', data.access_token)
  localStorage.setItem('session_started_at', new Date().toISOString())
  if (data.user) {
    localStorage.setItem('user', JSON.stringify(data.user))
  }
  return data
}

export function logout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
  localStorage.removeItem('session_started_at')
  localStorage.removeItem(APP_NAVIGATION_STORAGE_KEY)
}

export function isLoggedIn() {
  return !!localStorage.getItem('access_token')
}

export function getCurrentUser() {
  const raw = localStorage.getItem('user')
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export async function changePassword(old_password, new_password) {
  const res = await fetch(`${API_BASE}/auth/change_password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ old_password, new_password }),
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({}))
    const message = error.error || error.msg || error.message

    if (res.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      localStorage.removeItem('session_started_at')
      throw new Error(message || 'Session expired. Please login again.')
    }

    throw new Error(message || 'Password change failed')
  }

  return res.json()
}
