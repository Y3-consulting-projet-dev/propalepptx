export const API_BASE = '/api'

export const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token')
  return token ? { 'Authorization': `Bearer ${token}` } : {}
}
