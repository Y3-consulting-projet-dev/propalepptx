// Endpoints kept for reference but not called anywhere in the current UI.
// getProposals/generateProposal/createElement/getElements/getUsageStats target
// routes that no longer exist on the backend (proposals/elements/stats.usage).
import { API_BASE, getAuthHeaders } from './http.js'

export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`)
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`)
  }
  return res.json()
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
