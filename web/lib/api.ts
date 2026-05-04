import type { Customer, Vehicle, ReportSummary, ReportDetail, Quote, QuoteLineItem, FinalizeQuoteResponse, JobCardColumn, JobCard, JobCardCreate, Invoice, ShopSettings, ShopSettingsUpdate, ShopProfile, UserProfile, Appointment, ServiceReminderConfig, InventoryItem, Vendor, PurchaseOrder, TimeEntry, Expense, PLSummary, PaymentsSummary, PaymentEvent, DiagnoseAnalyzeResult, DiagnosisItem, RepairPlanItem, TsbItem, RecallItem, MaintenanceItem, AudienceSegment, Campaign, CampaignTemplate, ShopAgent, ToolInfo, AgentCreate, AgentUpdate, BookingConfig, BookingConfigUpdate } from './types'
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
    const b64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(b64))
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

export const getAllReports = (vehicleId?: string | null): Promise<ReportSummary[]> =>
  api.get('/reports', vehicleId ? { params: { vehicle_id: vehicleId } } : {}).then(r => r.data)

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

// ── Auth / User ───────────────────────────────────────────────────────────
export const getMe = (): Promise<UserProfile> =>
  api.get('/auth/me').then(r => r.data)

export const updateProfile = (name: string): Promise<UserProfile> =>
  api.patch('/auth/profile', { name }).then(r => r.data)

export const updatePassword = (currentPassword: string, newPassword: string): Promise<{ ok: boolean }> =>
  api.patch('/auth/password', { current_password: currentPassword, new_password: newPassword }).then(r => r.data)

// ── Shop Profile ──────────────────────────────────────────────────────────
export const getShopProfile = (): Promise<ShopProfile> =>
  api.get('/settings/profile').then(r => r.data)

export const updateShopProfile = (data: Omit<Partial<ShopProfile>, 'id'>): Promise<ShopProfile> =>
  api.patch('/settings/profile', data).then(r => r.data)

// ── Booking Config ────────────────────────────────────────────────────────
export const getMyBookingConfig = (): Promise<BookingConfig> =>
  api.get('/appointments/my-config').then(r => r.data)

export const updateMyBookingConfig = (data: BookingConfigUpdate): Promise<BookingConfig> =>
  api.patch('/appointments/my-config', data).then(r => r.data)

// ── Shop Settings ──────────────────────────────────────────────────────────
export const getShopSettings = (): Promise<ShopSettings> =>
  api.get('/settings/shop').then(r => r.data)

export const updateShopSettings = (data: ShopSettingsUpdate): Promise<ShopSettings> =>
  api.patch('/settings/shop', data).then(r => r.data)

// ── Job Card Columns ───────────────────────────────────────────────────────
export const getJobCardColumns = (): Promise<JobCardColumn[]> =>
  api.get('/job-cards/columns').then(r => r.data)

export const createJobCardColumn = (data: { name: string; position: number }): Promise<JobCardColumn> =>
  api.post('/job-cards/columns', data).then(r => r.data)

export const updateJobCardColumn = (id: string, data: { name?: string; position?: number }): Promise<JobCardColumn> =>
  api.patch(`/job-cards/columns/${id}`, data).then(r => r.data)

export const deleteJobCardColumn = (id: string): Promise<void> =>
  api.delete(`/job-cards/columns/${id}`).then(() => undefined)

// ── Job Cards ──────────────────────────────────────────────────────────────
export const getJobCards = (params?: { column_id?: string; card_status?: string }): Promise<JobCard[]> =>
  api.get('/job-cards', { params }).then(r => r.data)

export const getJobCard = (id: string): Promise<JobCard> =>
  api.get(`/job-cards/${id}`).then(r => r.data)

export const createJobCard = (data: JobCardCreate): Promise<JobCard> =>
  api.post('/job-cards', data).then(r => r.data)

export const updateJobCard = (id: string, data: Partial<JobCard>): Promise<JobCard> =>
  api.patch(`/job-cards/${id}`, data).then(r => r.data)

export const deleteJobCard = (id: string): Promise<void> =>
  api.delete(`/job-cards/${id}`).then(() => undefined)

export const lookupLaborTime = (data: {
  year: number; make: string; model: string; engine?: string; service: string
}): Promise<{ hours: number | null; source: string }> =>
  api.post('/labor-lookup', data).then(r => r.data)

// ── Invoices ───────────────────────────────────────────────────────────────
export const getInvoices = (params?: { status?: string }): Promise<Invoice[]> =>
  api.get('/invoices', { params }).then(r => r.data)

export const getInvoice = (id: string): Promise<Invoice> =>
  api.get(`/invoices/${id}`).then(r => r.data)

export const createInvoice = (data: Partial<Invoice>): Promise<Invoice> =>
  api.post('/invoices', data).then(r => r.data)

export const createInvoiceFromJobCard = (job_card_id: string): Promise<Invoice> =>
  api.post('/invoices/from-job-card', { job_card_id }).then(r => r.data)

export const updateInvoice = (id: string, data: Partial<Invoice>): Promise<Invoice> =>
  api.patch(`/invoices/${id}`, data).then(r => r.data)

export const sendPaymentLink = (id: string): Promise<{ payment_link: string }> =>
  api.post(`/invoices/${id}/payment-link`).then(r => r.data)

export const sendFinancingLink = (id: string, provider: string): Promise<{ application_link: string; provider: string }> =>
  api.post(`/invoices/${id}/financing-link`, { provider }).then(r => r.data)

export const recordPayment = (id: string, data: { amount: number; method: string; notes?: string }): Promise<Invoice> =>
  api.post(`/invoices/${id}/record-payment`, data).then(r => r.data)

// ── Appointments ──────────────────────────────────────────────────────────
export const getAppointments = (params?: { year?: number; month?: number }): Promise<Appointment[]> =>
  api.get('/appointments', { params }).then(r => r.data)

export const createAppointment = (data: Partial<Appointment>): Promise<Appointment> =>
  api.post('/appointments', data).then(r => r.data)

export const updateAppointment = (id: string, data: Partial<Appointment>): Promise<Appointment> =>
  api.patch(`/appointments/${id}`, data).then(r => r.data)

export const convertAppointmentToJobCard = (id: string): Promise<{ job_card_id: string; number: string }> =>
  api.post(`/appointments/${id}/convert-to-job-card`).then(r => r.data)

// ── Service Reminders ─────────────────────────────────────────────────────
export const getReminderConfigs = (): Promise<ServiceReminderConfig[]> =>
  api.get('/reminders/config').then(r => r.data)

export const createReminderConfig = (data: Partial<ServiceReminderConfig>): Promise<ServiceReminderConfig> =>
  api.post('/reminders/config', data).then(r => r.data)

export const updateReminderConfig = (id: string, data: Partial<ServiceReminderConfig>): Promise<ServiceReminderConfig> =>
  api.patch(`/reminders/config/${id}`, data).then(r => r.data)

export const runReminderJob = (): Promise<{ reminders_sent: number }> =>
  api.post('/reminders/run').then(r => r.data)

// ── Inventory ─────────────────────────────────────────────────────────────

export const getInventory = (params?: {
  search?: string; category?: string; stock_status?: string; vendor_id?: string
}): Promise<InventoryItem[]> =>
  api.get('/inventory', { params }).then(r => r.data)

export const createInventoryItem = (data: Partial<InventoryItem>): Promise<InventoryItem> =>
  api.post('/inventory', data).then(r => r.data)

export const updateInventoryItem = (id: string, data: Partial<InventoryItem>): Promise<InventoryItem> =>
  api.patch(`/inventory/${id}`, data).then(r => r.data)

export const adjustInventoryStock = (id: string, delta: number, reason?: string): Promise<InventoryItem> =>
  api.post(`/inventory/${id}/adjust`, { delta, reason }).then(r => r.data)

export const deleteInventoryItem = (id: string): Promise<void> =>
  api.delete(`/inventory/${id}`).then(() => undefined)

// ── Vendors ───────────────────────────────────────────────────────────────

export const getVendors = (params?: { category?: string }): Promise<Vendor[]> =>
  api.get('/vendors', { params }).then(r => r.data)

export const createVendor = (data: Partial<Vendor>): Promise<Vendor> =>
  api.post('/vendors', data).then(r => r.data)

export const updateVendor = (id: string, data: Partial<Vendor>): Promise<Vendor> =>
  api.patch(`/vendors/${id}`, data).then(r => r.data)

export const deleteVendor = (id: string): Promise<void> =>
  api.delete(`/vendors/${id}`).then(() => undefined)

export const getVendorOrders = (vendorId: string): Promise<PurchaseOrder[]> =>
  api.get(`/vendors/${vendorId}/orders`).then(r => r.data)

export const createPurchaseOrder = (vendorId: string, data: { items: PurchaseOrder['items']; notes?: string }): Promise<PurchaseOrder> =>
  api.post(`/vendors/${vendorId}/orders`, data).then(r => r.data)

export const receivePurchaseOrder = (vendorId: string, poId: string): Promise<PurchaseOrder> =>
  api.post(`/vendors/${vendorId}/orders/${poId}/receive`).then(r => r.data)

// ── Time Tracking ─────────────────────────────────────────────────────────

export const getTimeEntries = (params?: { user_id?: string; job_card_id?: string }): Promise<TimeEntry[]> =>
  api.get('/time-entries', { params }).then(r => r.data)

export const getActiveTimeEntries = (): Promise<TimeEntry[]> =>
  api.get('/time-entries/active').then(r => r.data)

export const clockIn = (data: { task_type: string; job_card_id?: string; notes?: string }): Promise<TimeEntry> =>
  api.post('/time-entries/clock-in', data).then(r => r.data)

export const clockOut = (entryId: string): Promise<TimeEntry> =>
  api.post(`/time-entries/${entryId}/clock-out`).then(r => r.data)

// ── Payments ──────────────────────────────────────────────────────────────

export const getPaymentsSummary = (): Promise<PaymentsSummary> =>
  api.get('/payments/summary').then(r => r.data)

export const getPaymentHistory = (): Promise<PaymentEvent[]> =>
  api.get('/payments/history').then(r => r.data)

export const chasePayment = (invoiceId: string): Promise<{ status: string; payment_link: string }> =>
  api.post(`/payments/chase/${invoiceId}`).then(r => r.data)

// ── Accounting ────────────────────────────────────────────────────────────

export const getExpenses = (params?: { category?: string }): Promise<Expense[]> =>
  api.get('/accounting/expenses', { params }).then(r => r.data)

export const createExpense = (data: Partial<Expense>): Promise<Expense> =>
  api.post('/accounting/expenses', data).then(r => r.data)

export const deleteExpense = (id: string): Promise<void> =>
  api.delete(`/accounting/expenses/${id}`).then(() => undefined)

export const getPLSummary = (period?: string): Promise<PLSummary> =>
  api.get('/accounting/pl', { params: { period: period ?? 'mtd' } }).then(r => r.data)

export const syncToQuickBooks = (): Promise<{ invoices_synced: number; expenses_synced: number }> =>
  api.post('/accounting/sync-to-qb').then(r => r.data)

// ── Diagnose ──────────────────────────────────────────────────────────────────

export interface AnalyzeRequest {
  year: number
  make: string
  model: string
  engine?: string
  mileage?: number
  dtcs: string[]
}

export const diagnoseAnalyze = async (req: AnalyzeRequest): Promise<DiagnoseAnalyzeResult> => {
  const { data } = await api.post('/diagnose/analyze', req)
  return data
}

export const diagnoseTsb = async (year: number, make: string, model: string, engine?: string): Promise<{ tsbs: TsbItem[] }> => {
  const { data } = await api.get('/diagnose/tsb', { params: { year, make, model, engine } })
  return data
}

export const diagnoseRecalls = async (year: number, make: string, model: string): Promise<{ recalls: RecallItem[] }> => {
  const { data } = await api.get('/diagnose/recalls', { params: { year, make, model } })
  return data
}

export const diagnoseMaintenance = async (year: number, make: string, model: string, mileage = 0): Promise<{ maintenance: MaintenanceItem[] }> => {
  const { data } = await api.get('/diagnose/maintenance', { params: { year, make, model, mileage } })
  return data
}

export const diagnoseAddToJobCard = async (jobCardId: string, diagnosis: DiagnosisItem[], repairPlan: RepairPlanItem[]): Promise<{ ok: boolean }> => {
  const { data } = await api.post('/diagnose/add-to-job-card', { job_card_id: jobCardId, diagnosis, repair_plan: repairPlan })
  return data
}

export const diagnoseSendSummary = async (customerId: string, diagnosis: DiagnosisItem[]): Promise<{ sms_text: string; sent: boolean }> => {
  const { data } = await api.post('/diagnose/send-summary', { customer_id: customerId, diagnosis })
  return data
}

// ── Marketing ─────────────────────────────────────────────────────────────────

export const fetchCampaignTemplates = async (): Promise<CampaignTemplate[]> => {
  const { data } = await api.get('/marketing/templates')
  return data
}

export const fetchCampaigns = async (status?: string): Promise<Campaign[]> => {
  const { data } = await api.get('/marketing/campaigns', { params: status ? { status } : undefined })
  return data
}

export const createCampaign = async (payload: Partial<Campaign>): Promise<Campaign> => {
  const { data } = await api.post('/marketing/campaigns', payload)
  return data
}

export const updateCampaign = async (id: string, payload: Partial<Campaign>): Promise<Campaign> => {
  const { data } = await api.put(`/marketing/campaigns/${id}`, payload)
  return data
}

export const deleteCampaign = async (id: string): Promise<void> => {
  await api.delete(`/marketing/campaigns/${id}`)
}

export const fetchAudienceCount = async (segment: AudienceSegment): Promise<number> => {
  const { data } = await api.get('/marketing/audience/count', {
    params: {
      segment_type: segment.type,
      service_type: segment.service_type,
      last_visit_months_start: segment.last_visit_months_start,
      last_visit_months_end: segment.last_visit_months_end,
      vehicle_type: segment.vehicle_type,
    },
  })
  return data.count
}

export const sendCampaign = async (id: string): Promise<Campaign> => {
  const { data } = await api.post(`/marketing/campaigns/${id}/send`)
  return data
}

// ── Agents ────────────────────────────────────────────────────────────────────

export const fetchAgents = (): Promise<ShopAgent[]> =>
  api.get('/agents').then(r => r.data)

export const fetchToolRegistry = (): Promise<ToolInfo[]> =>
  api.get('/agents/tools').then(r => r.data)

export const createAgent = (payload: AgentCreate): Promise<ShopAgent> =>
  api.post('/agents', payload).then(r => r.data)

export const updateAgent = (id: string, payload: AgentUpdate): Promise<ShopAgent> =>
  api.put(`/agents/${id}`, payload).then(r => r.data)

export const deleteAgent = (id: string): Promise<void> =>
  api.delete(`/agents/${id}`).then(() => undefined)
