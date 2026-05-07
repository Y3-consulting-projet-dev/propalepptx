const API_BASE = '/api'
export const APP_NAVIGATION_STORAGE_KEY = 'app_navigation_state'

// Helper function to get auth headers
export const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token')
  return token ? { 'Authorization': `Bearer ${token}` } : {}
}

export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`)
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`)
  }
  return res.json()
}

export async function getTemplates({ scan = false } = {}) {
  const url = scan ? '/api/templates?scan=1' : '/api/templates'
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`)
  }
  return res.json()
}

export function getTemplatePdfUrl(filename) {
  return `/api/templates/${encodeURIComponent(filename)}/pdf`
}
  
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

export async function getProposals() {
  const res = await fetch(`${API_BASE}/proposals`, {
    headers: getAuthHeaders()
  })

  if (!res.ok) {
    if (res.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('access_token')
      localStorage.removeItem('session_started_at')
      throw new Error('Session expired. Please login again.')
    }
    throw new Error(`API error: ${res.status}`)
  }

  return res.json()
}

export async function generateProposal(title, content) {
  const res = await fetch(`${API_BASE}/generate_proposal`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders()
    },
    body: JSON.stringify({ title, content })
  })

  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('session_started_at')
      throw new Error('Session expired. Please login again.')
    }
    const error = await res.json()
    throw new Error(error.error || 'Generation failed')
  }

  return res.json()
}

export async function createElement(name, value = null, metadata = {}) {
  const res = await fetch(`${API_BASE}/elements`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders()
    },
    body: JSON.stringify({ name, value, metadata })
  })

  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('session_started_at')
      throw new Error('Session expired. Please login again.')
    }
    const error = await res.json()
    throw new Error(error.error || 'Element creation failed')
  }

  return res.json()
}

export async function getElements() {
  const res = await fetch(`${API_BASE}/elements`, {
    headers: getAuthHeaders()
  })

  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('session_started_at')
      throw new Error('Session expired. Please login again.')
    }
    throw new Error(`API error: ${res.status}`)
  }

  return res.json()
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

export async function getNotifications() {
  const res = await fetch(`${API_BASE}/notifications`, {
    headers: getAuthHeaders(),
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({}))
    throw new Error(error.error || 'Notifications load failed')
  }

  return res.json()
}

export async function markNotificationsRead(presentationId = null) {
  const res = await fetch(`${API_BASE}/notifications/read`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(presentationId ? { presentation_id: presentationId } : {}),
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({}))
    throw new Error(error.error || 'Notification update failed')
  }

  return res.json()
}

export async function sendSessionHeartbeat() {
  const res = await fetch(`${API_BASE}/session/heartbeat`, {
    method: 'POST',
    headers: getAuthHeaders(),
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({}))
    throw new Error(error.error || 'Heartbeat failed')
  }

  return res.json()
}

export async function getDashboardSummary(query = '') {
  const params = new URLSearchParams()
  if (query) params.set('q', query)

  const res = await fetch(`${API_BASE}/dashboard/summary${params.toString() ? `?${params.toString()}` : ''}`, {
    headers: getAuthHeaders(),
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({}))
    throw new Error(error.error || 'Dashboard summary failed')
  }

  return res.json()
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

export async function getUsageStats({ range = '30d', compare = false, scope = 'me' } = {}) {
  const params = new URLSearchParams()
  if (range) params.set('range', range)
  if (compare) params.set('compare', '1')
  if (scope) params.set('scope', scope)

  const res = await fetch(`${API_BASE}/stats/usage?${params.toString()}`, {
    headers: getAuthHeaders(),
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

    // Keep message from backend when possible (ex: 403 Forbidden)
    throw new Error(message || `API error: ${res.status}`)
  }

  return res.json()
}
