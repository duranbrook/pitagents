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
