import { API_BASE, getAuthHeaders } from './http.js'

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
