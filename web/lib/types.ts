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
