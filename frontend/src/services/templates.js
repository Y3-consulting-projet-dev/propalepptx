import { API_BASE } from './http.js'

export async function getTemplates({ scan = false } = {}) {
  const url = scan ? '/api/templates?scan=1' : '/api/templates'
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`)
  }
  return res.json()
}

export function getTemplatePdfUrl(filename) {
  return `${API_BASE}/templates/${encodeURIComponent(filename)}/pdf`
}
