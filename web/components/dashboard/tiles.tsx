import type { ComponentType } from 'react'

export type TileStatus = 'live' | 'soon'

export interface TileConfig {
  id: string
  label: string
  icon: ComponentType
  status: TileStatus
  route?: string
}

export interface GroupConfig {
  id: string
  label: string
  accent: string
  tiles: TileConfig[]
}

// ── Icon components ──────────────────────────────────────────────────────────

function IconCustomers() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="6" r="3" stroke="currentColor" strokeWidth="1.5"/><path d="M2 13c0-3 2.5-5 6-5s6 2 6 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}
function IconVehicle() {
  return <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M4 14l2-6h12l2 6v4H4v-4z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/><circle cx="8" cy="18" r="1.5" stroke="currentColor" strokeWidth="1.5"/><circle cx="16" cy="18" r="1.5" stroke="currentColor" strokeWidth="1.5"/></svg>
}
function IconCalendar() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><rect x="2" y="3" width="12" height="11" rx="2" stroke="currentColor" strokeWidth="1.5"/><line x1="5" y1="1" x2="5" y2="5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><line x1="11" y1="1" x2="11" y2="5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><line x1="2" y1="7" x2="14" y2="7" stroke="currentColor" strokeWidth="1.5"/></svg>
}
function IconBell() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><path d="M8 2a4 4 0 0 1 4 4v3l1 2H3l1-2V6a4 4 0 0 1 4-4z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/><path d="M6.5 13a1.5 1.5 0 0 0 3 0" stroke="currentColor" strokeWidth="1.5"/></svg>
}
function IconInspect() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="5" stroke="currentColor" strokeWidth="1.5"/><circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.5"/></svg>
}
function IconReport() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" strokeWidth="1.5"/><line x1="5" y1="6" x2="11" y2="6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><line x1="5" y1="9" x2="9" y2="9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}
function IconClipboard() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><rect x="3" y="2" width="10" height="12" rx="1.5" stroke="currentColor" strokeWidth="1.5"/><line x1="5" y1="6" x2="11" y2="6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><line x1="5" y1="9" x2="9" y2="9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><rect x="5" y="1" width="6" height="3" rx="1" stroke="currentColor" strokeWidth="1.3"/></svg>
}
function IconClock() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5"/><path d="M8 5v3l2 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}
function IconDollar() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5"/><path d="M8 4v8M6 6.5a2 2 0 0 1 4 0c0 1.5-4 1.5-4 3a2 2 0 0 0 4 0" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>
}
function IconReceipt() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><path d="M3 2h10v12l-2-1.5L9 14l-2-1.5L5 14l-2-1.5V2z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/><line x1="5" y1="6" x2="11" y2="6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/><line x1="5" y1="9" x2="9" y2="9" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>
}
function IconCard() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><rect x="1" y="4" width="14" height="9" rx="2" stroke="currentColor" strokeWidth="1.5"/><line x1="1" y1="7" x2="15" y2="7" stroke="currentColor" strokeWidth="1.5"/><rect x="3" y="9.5" width="4" height="1.5" rx="0.5" fill="currentColor"/></svg>
}
function IconChart() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><path d="M2 12l3-4 3 2 3-5 3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/><line x1="2" y1="14" x2="14" y2="14" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>
}
function IconChat() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><path d="M2 3h12v8H2z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/><path d="M5 14h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}
function IconPlug() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><path d="M8 10v3M5 2v4M11 2v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><rect x="3" y="6" width="10" height="4" rx="1.5" stroke="currentColor" strokeWidth="1.5"/></svg>
}
function IconStethoscope() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><path d="M4 2v5a3 3 0 0 0 6 0V2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><path d="M7 9a4 4 0 1 0 4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><circle cx="11" cy="13" r="1" fill="currentColor"/></svg>
}
function IconBook() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><path d="M3 2h7l3 2v10H6L3 12V2z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/><line x1="3" y1="12" x2="6" y2="14" stroke="currentColor" strokeWidth="1.3"/><line x1="6" y1="6" x2="11" y2="6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/><line x1="6" y1="9" x2="9" y2="9" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>
}
function IconMegaphone() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><path d="M3 6h2l6-3v10L5 10H3a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/><path d="M5 10v3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}
function IconStar() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><path d="M8 2l1.8 3.6L14 6.4l-3 2.9.7 4.1L8 11.5l-3.7 1.9.7-4.1-3-2.9 4.2-.8L8 2z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/></svg>
}
function IconTarget() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5"/><circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.5"/><circle cx="8" cy="8" r="1" fill="currentColor"/></svg>
}
function IconMoney() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><rect x="1" y="5" width="14" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.5"/><circle cx="8" cy="9" r="2" stroke="currentColor" strokeWidth="1.3"/><line x1="4" y1="3" x2="12" y2="3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>
}
function IconWrench() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><path d="M10.5 2a3.5 3.5 0 0 0-3.4 4.3L2 11.5 3.5 13l4.7-5.1A3.5 3.5 0 0 0 10.5 9a3.5 3.5 0 1 0 0-7z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/></svg>
}
function IconBox() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><path d="M2 5l6-3 6 3v7l-6 3-6-3V5z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/><line x1="8" y1="2" x2="8" y2="14" stroke="currentColor" strokeWidth="1.3"/><line x1="2" y1="5" x2="14" y2="5" stroke="currentColor" strokeWidth="1.3"/></svg>
}
function IconBuilding() {
  return <svg width="20" height="20" viewBox="0 0 16 16" fill="none"><rect x="2" y="4" width="12" height="10" rx="1" stroke="currentColor" strokeWidth="1.5"/><path d="M5 14V9h6v5" stroke="currentColor" strokeWidth="1.3"/><rect x="6" y="6" width="2" height="2" rx="0.3" stroke="currentColor" strokeWidth="1.2"/><rect x="10" y="6" width="2" height="2" rx="0.3" stroke="currentColor" strokeWidth="1.2"/><line x1="8" y1="2" x2="8" y2="4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}

// ── Group + tile definitions ─────────────────────────────────────────────────

export const GROUPS: GroupConfig[] = [
  {
    id: 'customers',
    label: 'Customers & Vehicles',
    accent: '#d97706',
    tiles: [
      { id: 'customers', label: 'Customers',        icon: IconCustomers, status: 'live', route: '/customers' },
      { id: 'vehicles',  label: 'Vehicles',         icon: IconVehicle,   status: 'live', route: '/customers' },
      { id: 'appointments',      label: 'Appointments',      icon: IconCalendar, status: 'live', route: '/appointments' },
      { id: 'service-reminders', label: 'Service Reminders', icon: IconBell,     status: 'live', route: '/reminders' },
    ],
  },
  {
    id: 'shop-work',
    label: 'Shop Work',
    accent: '#3b82f6',
    tiles: [
      { id: 'inspect',       label: 'Inspect',       icon: IconInspect,   status: 'live', route: '/inspect' },
      { id: 'reports',       label: 'Reports',       icon: IconReport,    status: 'live', route: '/reports' },
      { id: 'job-cards',     label: 'Job Cards',     icon: IconClipboard, status: 'live', route: '/job-cards' },
      { id: 'time-tracking', label: 'Time Tracking', icon: IconClock,     status: 'live', route: '/time-tracking' },
    ],
  },
  {
    id: 'financials',
    label: 'Financials',
    accent: '#22c55e',
    tiles: [
      { id: 'quotes',     label: 'Quotes & Estimates', icon: IconDollar,  status: 'live', route: '/reports' },
      { id: 'invoices',   label: 'Invoices',           icon: IconReceipt, status: 'live', route: '/invoices' },
      { id: 'payments',   label: 'Payments',           icon: IconCard,    status: 'live', route: '/payments' },
      { id: 'accounting', label: 'Accounting',         icon: IconChart,   status: 'live', route: '/accounting' },
    ],
  },
  {
    id: 'ai-tools',
    label: 'AI Tools',
    accent: '#a855f7',
    tiles: [
      { id: 'chat',         label: 'AI Chat',      icon: IconChat,        status: 'live', route: '/chat' },
      { id: 'obd',          label: 'OBD Scanner',  icon: IconPlug,        status: 'soon' },
      { id: 'ai-diagnose',  label: 'AI Diagnose',  icon: IconStethoscope, status: 'live', route: '/diagnose' },
      { id: 'labor-guides', label: 'Labor Guides', icon: IconBook,        status: 'soon' },
    ],
  },
  {
    id: 'growth',
    label: 'Growth & Marketing',
    accent: '#ef4444',
    tiles: [
      { id: 'marketing', label: 'Marketing', icon: IconMegaphone, status: 'live', route: '/marketing' },
      { id: 'reviews',   label: 'Reviews',   icon: IconStar,      status: 'soon' },
      { id: 'leads',     label: 'Leads',     icon: IconTarget,    status: 'soon' },
      { id: 'financing', label: 'Financing', icon: IconMoney,     status: 'soon' },
    ],
  },
  {
    id: 'inventory',
    label: 'Inventory & Parts',
    accent: '#06b6d4',
    tiles: [
      { id: 'parts',     label: 'Parts Lookup', icon: IconWrench,   status: 'live', route: '/chat' },
      { id: 'inventory', label: 'Inventory',    icon: IconBox,      status: 'live', route: '/inventory' },
      { id: 'vendors',   label: 'Vendors',      icon: IconBuilding, status: 'live', route: '/vendors' },
    ],
  },
]
