export async function getHealth() {
  const res = await fetch('/api/health')
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
