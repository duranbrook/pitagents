export interface Customer {
  customer_id: string
  shop_id: string
  name: string
  email: string | null
  phone: string | null
  created_at: string
}

export interface Vehicle {
  vehicle_id: string
  customer_id: string
  year: number
  make: string
  model: string
  trim: string | null
  vin: string | null
  color: string | null
  created_at: string
}

// Shape returned by GET /reports (list endpoint)
export interface ReportSummary {
  id: string
  vehicle: {
    vehicle_id?: string
    year?: number
    make?: string
    model?: string
  }
  summary: string
  total: number
  share_token: string
  created_at: string | null
}

export interface Finding {
  part: string
  severity: string
  notes: string
  photo_url?: string | null
}

export interface EstimateItem {
  part: string
  labor_hours: number
  labor_rate: number
  labor_cost: number
  parts_cost: number
  total: number
}

// Shape returned by GET /reports/{id} (detail endpoint)
export interface ReportDetail {
  id: string
  vehicle: {
    vehicle_id?: string
    year?: number
    make?: string
    model?: string
    trim?: string | null
    vin?: string | null
  } | null
  summary: string
  findings: Finding[]
  estimate: EstimateItem[]
  total: number
  share_token: string
  created_at: string | null
}

export interface QuoteLineItem {
  type: 'labor' | 'part'
  description: string
  qty: number
  unit_price: number
  total: number
}

export interface Quote {
  quote_id: string
  status: 'draft' | 'final'
  total: number
  line_items: QuoteLineItem[]
  session_id: string | null
  created_at: string | null
}

export interface FinalizeQuoteResponse {
  quote_id: string
  status: 'draft' | 'final'
  total: number
  pdf_url: string | null
  report_id: string | null
  report_pdf_url: string | null
  share_token: string | null
}

// ── Job Cards ─────────────────────────────────────────────────────────────

export interface JobCardColumn {
  id: string
  shop_id: string
  name: string
  position: number
  created_at: string
}

export interface ServiceLine {
  description: string
  labor_hours: number
  labor_rate: number
  labor_cost: number
}

export interface PartLine {
  name: string
  sku: string | null
  qty: number
  unit_cost: number
  sell_price: number
  inventory_item_id: string | null
}

export interface JobCard {
  id: string
  shop_id: string
  number: string
  customer_id: string | null
  vehicle_id: string | null
  column_id: string | null
  technician_ids: string[]
  services: ServiceLine[]
  parts: PartLine[]
  notes: string | null
  status: 'active' | 'closed' | 'void'
  created_at: string
  updated_at: string
}

export interface JobCardCreate {
  customer_id?: string
  vehicle_id?: string
  column_id?: string
  technician_ids?: string[]
  services?: ServiceLine[]
  parts?: PartLine[]
  notes?: string
}

// ── Invoices ──────────────────────────────────────────────────────────────

export interface InvoiceLineItem {
  type: 'labor' | 'part'
  description: string
  qty: number
  unit_price: number
  total: number
}

export interface Invoice {
  id: string
  shop_id: string
  job_card_id: string | null
  number: string
  customer_id: string | null
  vehicle_id: string | null
  status: 'pending' | 'partial' | 'paid' | 'void' | 'overdue'
  line_items: InvoiceLineItem[]
  subtotal: number
  tax_rate: number
  total: number
  amount_paid: number
  balance: number
  due_date: string | null
  stripe_payment_link: string | null
  pdf_url: string | null
  created_at: string
  updated_at: string
}

// ── Auth / User ───────────────────────────────────────────────────────────

export interface UserProfile {
  id: string
  email: string
  name: string | null
  role: string
  shop_id: string
}

export interface ShopProfile {
  id: string
  name: string
  address: string | null
  labor_rate: string
}

export interface ShopSettings {
  id: string
  shop_id: string
  nav_pins: string[]
  stripe_publishable_key: string | null
  has_stripe_secret: boolean
  mitchell1_enabled: boolean
  has_mitchell1_key: boolean
  synchrony_enabled: boolean
  synchrony_dealer_id: string | null
  wisetack_enabled: boolean
  wisetack_merchant_id: string | null
  quickbooks_enabled: boolean
  has_quickbooks_token: boolean
  carmd_api_key: string | null
  financing_threshold: string
}

// ── Appointments ──────────────────────────────────────────────────────────

export interface Appointment {
  id: string
  shop_id: string
  customer_id: string | null
  vehicle_id: string | null
  starts_at: string
  ends_at: string
  service_requested: string | null
  status: 'pending' | 'confirmed' | 'cancelled'
  notes: string | null
  source: 'manual' | 'booking_link'
  job_card_id: string | null
  customer_name: string | null
  customer_phone: string | null
  customer_email: string | null
  created_at: string
}

export interface BookingConfig {
  id: string
  shop_id: string
  slug: string
  available_services: string  // JSON-serialised array from backend, e.g. "[]"
  working_hours_start: string
  working_hours_end: string
  slot_duration_minutes: string
  working_days: string        // JSON-serialised array from backend, e.g. "[1,2,3,4,5]"
  created_at: string | null
}

export interface BookingConfigUpdate {
  working_hours_start?: string
  working_hours_end?: string
  slot_duration_minutes?: string
}

// ── Service Reminders ─────────────────────────────────────────────────────

export interface ServiceReminderConfig {
  id: string
  shop_id: string
  service_type: string
  window_start_months: number
  window_end_months: number
  sms_enabled: boolean
  email_enabled: boolean
  message_template: string | null
  created_at: string
}

// ── Inventory ─────────────────────────────────────────────────────────────

export interface InventoryItem {
  id: string
  shop_id: string
  name: string
  sku: string | null
  category: string
  quantity: number
  reorder_at: number
  cost_price: number
  sell_price: number
  margin_pct: number
  stock_status: 'ok' | 'low' | 'out'
  vendor_id: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

// ── Vendors ───────────────────────────────────────────────────────────────

export interface Vendor {
  id: string
  shop_id: string
  name: string
  category: string
  phone: string | null
  email: string | null
  website: string | null
  address: string | null
  rep_name: string | null
  rep_phone: string | null
  account_number: string | null
  notes: string | null
  source: string
  ytd_spend: number
  order_count: number
  last_order_at: string | null
  created_at: string
}

export interface PurchaseOrder {
  id: string
  vendor_id: string
  po_number: string
  status: 'pending' | 'ordered' | 'received'
  items: Array<{ name: string; sku: string | null; qty: number; unit_cost: number }>
  total: number
  notes: string | null
  ordered_at: string | null
  received_at: string | null
  created_at: string
}

// ── Time Tracking ─────────────────────────────────────────────────────────

export interface TimeEntry {
  id: string
  shop_id: string
  user_id: string
  job_card_id: string | null
  task_type: 'Repair' | 'Diagnosis' | 'Admin'
  started_at: string
  ended_at: string | null
  duration_minutes: number | null
  notes: string | null
  qb_synced: boolean
  created_at: string
}

// ── Accounting ────────────────────────────────────────────────────────────

export interface Expense {
  id: string
  shop_id: string
  description: string
  amount: number
  category: string
  vendor: string | null
  expense_date: string
  qb_synced: boolean
  created_at: string
}

export interface PLSummary {
  period: string
  revenue: number
  expenses: number
  net_profit: number
  outstanding_ar: number
}

// ── Payments ──────────────────────────────────────────────────────────────

export interface PaymentsSummary {
  outstanding: number
  overdue: number
  collected_this_month: number
  total_invoices: number
}

export interface PaymentEvent {
  id: string
  invoice_id: string
  amount: number
  method: string
  recorded_at: string | null
  notes: string | null
}

// ── Diagnose ──────────────────────────────────────────────────────────────────

export interface DiagnosisItem {
  urgency?: number
  urgency_desc?: string
  desc: string
  layman_desc?: string
  part?: string
  repair?: { difficulty?: string }
}

export interface RepairPlanItem {
  repair_desc?: string
  desc?: string
  labor_hrs?: number
  labor_cost?: number
  confidence?: string
}

export interface TsbItem {
  tsb_id?: string
  title?: string
  component?: string
  pub_date?: string
  desc?: string
}

export interface RecallItem {
  recall_date?: string
  component?: string
  consequence?: string
  remedy?: string
  nhtsa_id?: string
}

export interface MaintenanceItem {
  desc?: string
  mileage?: number
  due_date?: string
}

export interface DiagnoseAnalyzeResult {
  diagnosis: DiagnosisItem[]
  repair_plan: RepairPlanItem[]
}

// ── Marketing ─────────────────────────────────────────────────────────────────

export interface Campaign {
  campaign_id: string
  shop_id: string
  name: string
  status: 'draft' | 'scheduled' | 'active' | 'sent'
  message_body: string
  channel: 'sms' | 'email' | 'both'
  audience_segment: AudienceSegment
  send_at: string | null
  sent_at: string | null
  stats: CampaignStats
  created_at: string
}

export interface AudienceSegment {
  type: 'all_customers' | 'by_service' | 'by_last_visit' | 'by_vehicle_type'
  service_type?: string
  last_visit_months_start?: number
  last_visit_months_end?: number
  vehicle_type?: string
}

export interface CampaignStats {
  sent_count?: number
  opened_count?: number
  booked_count?: number
  revenue_attributed?: number
}

export interface CampaignTemplate {
  id: string
  name: string
  message_body: string
}

export interface ShopAgent {
  id: string
  name: string
  role_tagline: string
  accent_color: string
  initials: string
  system_prompt: string
  tools: string[]
  sort_order: number
}

export interface ToolInfo {
  id: string
  label: string
  description: string
}

export interface AgentCreate {
  name: string
  role_tagline: string
  accent_color: string
  initials: string
  system_prompt: string
  tools: string[]
  sort_order?: number
}

export interface AgentUpdate {
  name?: string
  role_tagline?: string
  accent_color?: string
  initials?: string
  system_prompt?: string
  tools?: string[]
  sort_order?: number
}
