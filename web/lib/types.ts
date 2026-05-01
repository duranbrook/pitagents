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
  status: 'pending' | 'partial' | 'paid' | 'void'
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

export interface ShopSettings {
  id: string
  shop_id: string
  nav_pins: string[]
  stripe_publishable_key: string | null
  mitchell1_enabled: boolean
  synchrony_enabled: boolean
  synchrony_dealer_id: string | null
  wisetack_enabled: boolean
  wisetack_merchant_id: string | null
  quickbooks_enabled: boolean
  financing_threshold: string
}
