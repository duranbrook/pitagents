import type { Customer, Vehicle, ReportSummary, ReportDetail, Quote, QuoteLineItem, FinalizeQuoteResponse } from './types'
import axios from 'axios'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function getToken(): string {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('token') || ''
  }
  return ''
}

function getTokenPayload(): Record<string, string> {
  const token = getToken()
  if (!token) return {}
  try {
    return JSON.parse(atob(token.split('.')[1]))
  } catch {
    return {}
  }
}

export function getShopId(): string {
  if (typeof window === 'undefined') return ''
  return getTokenPayload().shop_id ?? ''
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

export const getReport = (id: string) => api.get(`/reports/${id}`).then(r => r.data)
export const sendReport = (id: string, payload: { phone?: string; email?: string }) =>
  api.post(`/reports/${id}/send`, payload).then(r => r.data)
export interface EstimateItemPatch {
  part: string
  labor_hours: number
  labor_rate: number
  parts_cost: number
}

export const patchReportEstimate = (
  reportId: string,
  items: EstimateItemPatch[],
): Promise<ReportDetail> =>
  api.patch(`/reports/${reportId}/estimate`, { items }).then(r => r.data)

export const getConsumerReport = (token: string) =>
  api.get(`/r/${token}`).then(r => r.data)

// ── Chat ──────────────────────────────────────────────────────────────────

export type ChatRole = 'user' | 'assistant'

export interface ContentBlock {
  type: 'text' | 'image' | 'tool_use' | 'tool_result'
  text?: string
  source?: { type: string; url: string }
}

export interface ToolCallRecord {
  name: string
  input: Record<string, unknown>
  output: Record<string, unknown>
}

export interface ChatHistoryItem {
  id: string
  role: ChatRole
  content: ContentBlock[]
  tool_calls: ToolCallRecord[] | null
  created_at: string
  rating?: number | null  // +1, -1, or null
}

export type SSEEvent =
  | { type: 'token'; content: string }
  | { type: 'tool_start'; tool: string; input: Record<string, unknown> }
  | { type: 'tool_end'; tool: string; input: Record<string, unknown>; output: Record<string, unknown> }
  | { type: 'done' }
  | { type: string }

export const getChatHistory = (agentId: string): Promise<ChatHistoryItem[]> =>
  api.get(`/chat/${agentId}/history`).then(r => r.data)

export async function* streamChatMessage(
  agentId: string,
  message: string,
  imageUrl?: string,
): AsyncGenerator<SSEEvent> {
  const token = getToken()
  const res = await fetch(
    `${BASE_URL}/chat/${agentId}/message`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message, image_url: imageUrl }),
    },
  )
  if (!res.ok) throw new Error(`Chat request failed: ${res.status}`)
  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        yield JSON.parse(line.slice(6)) as SSEEvent
      }
    }
  }
}

export async function transcribeAudio(audioBlob: Blob): Promise<string> {
  const res = await fetch(`${BASE_URL}/transcribe`, {
    method: 'POST',
    headers: {
      'Content-Type': audioBlob.type || 'audio/webm',
      Authorization: `Bearer ${getToken()}`,
    },
    body: audioBlob,
  })
  if (!res.ok) throw new Error('Transcription failed')
  const data = await res.json()
  return data.transcript as string
}

export async function uploadImage(file: File): Promise<string> {
  const form = new FormData()
  form.append('file', file)
  const res = await api.post('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data.image_url as string
}

export async function rateFeedback(
  agentId: string,
  messageId: string,
  rating: 1 | -1,
): Promise<void> {
  await api.post(`/chat/${agentId}/feedback`, { message_id: messageId, rating })
}

// ── Customers ─────────────────────────────────────────────────────────────

export const getCustomers = (): Promise<Customer[]> =>
  api.get('/customers').then(r => r.data)

export const createCustomer = (data: {
  name: string
  email?: string
  phone?: string
}): Promise<Customer> =>
  api.post('/customers', data).then(r => r.data)

// ── Vehicles ──────────────────────────────────────────────────────────────

export const getVehicles = (customerId: string): Promise<Vehicle[]> =>
  api.get(`/customers/${customerId}/vehicles`).then(r => r.data)

export const createVehicle = (
  customerId: string,
  data: {
    year: number
    make: string
    model: string
    trim?: string
    vin?: string
    color?: string
  },
): Promise<Vehicle> =>
  api.post(`/customers/${customerId}/vehicles`, data).then(r => r.data)

// ── Reports ───────────────────────────────────────────────────────────────

export const getAllReports = (): Promise<ReportSummary[]> =>
  api.get('/reports').then(r => r.data)

// ── Sessions ──────────────────────────────────────────────────────────────

export const createSession = (vehicleId: string): Promise<{ session_id: string }> =>
  api.post('/sessions', {
    shop_id: getShopId(),
    vehicle_id: vehicleId,
    labor_rate: 120.0,
    pricing_flag: 'shop',
  }).then(r => r.data)

export async function uploadSessionMedia(
  sessionId: string,
  file: File,
  mediaType: 'audio' | 'video' | 'photo',
  tag: 'vin' | 'odometer' | 'tire' | 'damage' | 'general' = 'general',
): Promise<{ media_id: string; s3_url: string }> {
  const form = new FormData()
  form.append('file', file)
  form.append('media_type', mediaType)
  form.append('tag', tag)
  const res = await api.post(`/sessions/${sessionId}/media`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export const generateReport = (
  sessionId: string,
): Promise<{ report_id: string; share_token: string; report_url: string }> =>
  api.post(`/sessions/${sessionId}/generate-report`).then(r => r.data)

// ── Quotes ────────────────────────────────────────────────────────────────

export const createQuote = (
  sessionId: string,
  transcript: string,
): Promise<Quote> =>
  api.post('/quotes', { session_id: sessionId, transcript }).then(r => r.data)

export const getQuote = (quoteId: string): Promise<Quote> =>
  api.get(`/quotes/${quoteId}`).then(r => r.data)

export const updateQuoteLineItems = (
  quoteId: string,
  lineItems: QuoteLineItem[],
): Promise<Quote> =>
  api.patch(`/quotes/${quoteId}/line-items`, { line_items: lineItems }).then(r => r.data)

export const finalizeQuote = (quoteId: string): Promise<FinalizeQuoteResponse> =>
  api.put(`/quotes/${quoteId}/finalize`, {}).then(r => r.data)
