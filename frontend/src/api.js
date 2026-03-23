const API_BASE = '/api'

// Helper function to get auth headers
const getAuthHeaders = () => {
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
      throw new Error('Session expired. Please login again.')
    }
    const error = await res.json()
    throw new Error(error.error || 'Generation failed')
  }

  return res.json()
}

export function logout() {
  localStorage.removeItem('access_token')
}

export function isLoggedIn() {
  return !!localStorage.getItem('access_token')
}
