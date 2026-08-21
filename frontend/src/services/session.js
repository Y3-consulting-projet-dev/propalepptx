import { API_BASE, getAuthHeaders } from './http.js'

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
