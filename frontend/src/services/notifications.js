import { API_BASE, getAuthHeaders } from './http.js'

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
