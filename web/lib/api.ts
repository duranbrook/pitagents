import axios from 'axios'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function getToken(): string {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('token') || ''
  }
  return ''
}

export const api = axios.create({
  baseURL: BASE_URL,
})

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const getReports = () => api.get('/reports').then(r => r.data)
export const getReport = (id: string) => api.get(`/reports/${id}`).then(r => r.data)
export const sendReport = (id: string, payload: { phone?: string; email?: string }) =>
  api.post(`/reports/${id}/send`, payload).then(r => r.data)
