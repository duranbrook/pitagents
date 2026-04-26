# Web Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Next.js web app shell and add full iOS-parity features: customers, vehicles, upload-based inspection, complete report detail with per-finding photos, all inside a new top-nav + split-panel layout.

**Architecture:** Replace the chat-centric `AppShell` with a top-nav shell (`AppShell.tsx`). Each section page owns its own two-panel layout inside the shell. New pages: `/customers`, `/reports`, `/inspect`. Existing chat migrated into the new shell. Old `/dashboard` routes deleted.

**Tech Stack:** Next.js 16 (App Router), React 19, TanStack Query v5, Axios, Tailwind CSS v4. Backend: FastAPI on Railway (`NEXT_PUBLIC_API_URL`).

**Working directory:** `web/` — all paths below are relative to `/Users/joehe/workspace/projects/pitagents/web/`.

**Dev server:** `cd web && npm run dev` → http://localhost:3000. Login with `owner@shop.com` / `testpass`.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `lib/types.ts` | Create | All shared TypeScript types (Customer, Vehicle, ReportSummary, ReportDetail, Finding, EstimateItem) |
| `lib/api.ts` | Modify | Add: getCustomers, createCustomer, getVehicles, createVehicle, getAllReports, createSession, uploadSessionMedia, generateReport, getShopId |
| `components/AppShell.tsx` | Create | Top nav (logo + nav links + user avatar), auth check, children slot |
| `components/chat/AppShell.tsx` | Delete | Replaced by `components/AppShell.tsx` |
| `app/page.tsx` | Modify | Redirect to `/customers` instead of `/chat` |
| `app/chat/page.tsx` | Rewrite | Use new AppShell; AgentList left panel + ChatPanel right panel |
| `app/customers/page.tsx` | Create | Customer list (left) + vehicle cards + modals (right) |
| `app/reports/page.tsx` | Create | Report list (left, filterable by vehicleId) + full report detail with photos (right) |
| `app/inspect/page.tsx` | Create | Vehicle picker (left) + audio/photo upload flow (right) |
| `app/dashboard/page.tsx` | Delete | Replaced by `/reports` |
| `app/dashboard/reports/[id]/page.tsx` | Delete | Replaced by `/reports` |

---

## Task 1: Shared types

**Files:**
- Create: `lib/types.ts`

- [ ] **Step 1: Create `lib/types.ts`**

```typescript
// lib/types.ts

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
```

- [ ] **Step 2: Commit**

```bash
git add lib/types.ts
git commit -m "feat(web): add shared TypeScript types"
```

---

## Task 2: New API functions

**Files:**
- Modify: `lib/api.ts`

The session endpoint requires `shop_id` — decode it from the JWT stored in localStorage (the server put it there at login; we don't need to verify the signature client-side).

- [ ] **Step 1: Add imports and helpers to `lib/api.ts`**

Add the type import at the very top of the file, with the other imports (line 1):

```typescript
import type { Customer, Vehicle, ReportSummary, ReportDetail } from './types'
```

Then add these two functions immediately after the existing `getToken()` function:

```typescript
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
  return getTokenPayload().shop_id ?? ''
}
```

- [ ] **Step 2: Add customer and vehicle functions at the end of `lib/api.ts`**

```typescript
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

// vehicleId filters client-side (backend returns all, we match r.vehicle.vehicle_id)
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
): Promise<{ media_id: string; s3_url: string }> {
  const form = new FormData()
  form.append('file', file)
  form.append('media_type', mediaType)
  const res = await api.post(`/sessions/${sessionId}/media`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export const generateReport = (
  sessionId: string,
): Promise<{ report_id: string; share_token: string; report_url: string }> =>
  api.post(`/sessions/${sessionId}/generate-report`).then(r => r.data)
```

- [ ] **Step 3: Verify build compiles**

```bash
cd /Users/joehe/workspace/projects/pitagents/web
npm run build 2>&1 | tail -20
```

Expected: no TypeScript errors related to the new functions. (Other pre-existing errors are OK if they exist.)

- [ ] **Step 4: Commit**

```bash
git add lib/api.ts
git commit -m "feat(web): add customers, vehicles, sessions API functions"
```

---

## Task 3: New AppShell

**Files:**
- Rewrite: `components/AppShell.tsx`

The new shell is nav-only. It does NOT know about agents or chat — that logic stays in the chat page.

- [ ] **Step 1: Rewrite `components/AppShell.tsx`**

```tsx
'use client'

import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'

const NAV_ITEMS = [
  { href: '/customers', label: 'Customers', icon: '👥' },
  { href: '/reports', label: 'Reports', icon: '📋' },
  { href: '/inspect', label: 'Inspect', icon: '🔍' },
  { href: '/chat', label: 'Chat', icon: '💬' },
]

function getInitials(): string {
  if (typeof window === 'undefined') return '?'
  const token = localStorage.getItem('token')
  if (!token) return '?'
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    const email = payload.email as string
    return email ? email[0].toUpperCase() : '?'
  } catch {
    return '?'
  }
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (!localStorage.getItem('token')) {
      router.replace('/login')
    }
  }, [router])

  function handleLogout() {
    localStorage.removeItem('token')
    router.replace('/login')
  }

  return (
    <div className="flex flex-col h-screen bg-gray-950 overflow-hidden">
      {/* Top nav */}
      <nav className="flex-shrink-0 h-11 bg-gray-900 border-b border-gray-800 flex items-center px-4 gap-1">
        <div className="flex items-center gap-2 mr-6 flex-shrink-0">
          <div className="w-6 h-6 bg-indigo-600 rounded-md flex items-center justify-center">
            <span className="text-white text-xs font-bold">P</span>
          </div>
          <span className="text-white text-sm font-semibold">AutoShop</span>
        </div>
        {NAV_ITEMS.map(item => {
          const active = pathname.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-1.5 px-3 h-11 text-sm border-b-2 transition-colors whitespace-nowrap ${
                active
                  ? 'text-indigo-400 border-indigo-500'
                  : 'text-gray-400 border-transparent hover:text-gray-200 hover:border-gray-600'
              }`}
            >
              <span className="text-base leading-none">{item.icon}</span>
              {item.label}
            </Link>
          )
        })}
        <button
          onClick={handleLogout}
          title="Log out"
          className="ml-auto w-7 h-7 bg-gray-700 hover:bg-gray-600 rounded-full flex items-center justify-center text-gray-300 text-xs font-semibold transition-colors flex-shrink-0"
        >
          {getInitials()}
        </button>
      </nav>
      {/* Content fills remaining height */}
      <main className="flex-1 min-h-0 overflow-hidden">
        {children}
      </main>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add components/AppShell.tsx
git commit -m "feat(web): replace icon-rail shell with top-nav AppShell"
```

---

## Task 4: Update routing — home redirect + chat page

**Files:**
- Modify: `app/page.tsx`
- Rewrite: `app/chat/page.tsx`

- [ ] **Step 1: Update `app/page.tsx` to redirect to `/customers`**

```tsx
import { redirect } from 'next/navigation'

export default function Home() {
  redirect('/customers')
}
```

- [ ] **Step 2: Rewrite `app/chat/page.tsx`**

The chat page now uses the new AppShell and puts AgentList in the left panel slot.

```tsx
'use client'

import { useState } from 'react'
import { AppShell } from '@/components/AppShell'
import { AgentList } from '@/components/chat/AgentList'
import { ChatPanel } from '@/components/chat/ChatPanel'

export default function ChatPage() {
  const [selectedAgent, setSelectedAgent] = useState('assistant')
  const [lastMessages, setLastMessages] = useState<Record<string, string>>({})

  return (
    <AppShell>
      <div className="flex h-full">
        <AgentList
          selectedId={selectedAgent}
          onSelect={setSelectedAgent}
          lastMessages={lastMessages}
        />
        <div className="flex-1 min-w-0">
          <ChatPanel
            key={selectedAgent}
            agentId={selectedAgent}
            onNewMessage={(text) =>
              setLastMessages(prev => ({ ...prev, [selectedAgent]: text }))
            }
          />
        </div>
      </div>
    </AppShell>
  )
}
```

- [ ] **Step 3: Start dev server and verify**

```bash
cd /Users/joehe/workspace/projects/pitagents/web
npm run dev
```

1. Open http://localhost:3000 → should redirect to http://localhost:3000/customers (login page shows)
2. Log in with `owner@shop.com` / `testpass`
3. Check: top nav appears with Customers · Reports · Inspect · Chat links
4. Click Chat tab → chat interface works as before (agent list on left, chat panel on right)
5. Check: user initial avatar in top right

- [ ] **Step 4: Commit**

```bash
git add app/page.tsx app/chat/page.tsx
git commit -m "feat(web): wire new AppShell into chat page, redirect home to /customers"
```

---

## Task 5: Customers page

**Files:**
- Create: `app/customers/page.tsx`

- [ ] **Step 1: Create `app/customers/page.tsx`**

```tsx
'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { AppShell } from '@/components/AppShell'
import { getCustomers, createCustomer, getVehicles, createVehicle } from '@/lib/api'
import type { Customer, Vehicle } from '@/lib/types'

const AVATAR_COLORS = ['#6366f1', '#8b5cf6', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444']
function colorFor(id: string) {
  return AVATAR_COLORS[id.charCodeAt(0) % AVATAR_COLORS.length]
}
function initials(name: string) {
  return name
    .split(' ')
    .map(w => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

export default function CustomersPage() {
  const queryClient = useQueryClient()
  const router = useRouter()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [showAddCustomer, setShowAddCustomer] = useState(false)
  const [showAddVehicle, setShowAddVehicle] = useState(false)
  const [customerForm, setCustomerForm] = useState({ name: '', email: '', phone: '' })
  const [vehicleForm, setVehicleForm] = useState({
    year: '', make: '', model: '', trim: '', vin: '', color: '',
  })

  const { data: customers = [], isLoading } = useQuery<Customer[]>({
    queryKey: ['customers'],
    queryFn: getCustomers,
  })

  const { data: vehicles = [] } = useQuery<Vehicle[]>({
    queryKey: ['vehicles', selectedId],
    queryFn: () => getVehicles(selectedId!),
    enabled: !!selectedId,
  })

  const addCustomer = useMutation({
    mutationFn: () =>
      createCustomer({
        name: customerForm.name,
        email: customerForm.email || undefined,
        phone: customerForm.phone || undefined,
      }),
    onSuccess: (newCustomer) => {
      queryClient.invalidateQueries({ queryKey: ['customers'] })
      setShowAddCustomer(false)
      setCustomerForm({ name: '', email: '', phone: '' })
      setSelectedId(newCustomer.customer_id)
    },
  })

  const addVehicle = useMutation({
    mutationFn: () =>
      createVehicle(selectedId!, {
        year: parseInt(vehicleForm.year),
        make: vehicleForm.make,
        model: vehicleForm.model,
        trim: vehicleForm.trim || undefined,
        vin: vehicleForm.vin || undefined,
        color: vehicleForm.color || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vehicles', selectedId] })
      setShowAddVehicle(false)
      setVehicleForm({ year: '', make: '', model: '', trim: '', vin: '', color: '' })
    },
  })

  const filtered = customers.filter(c =>
    c.name.toLowerCase().includes(search.toLowerCase()),
  )
  const selected = customers.find(c => c.customer_id === selectedId)

  return (
    <AppShell>
      <div className="flex h-full overflow-hidden">
        {/* Left panel: customer list */}
        <div className="w-56 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
          <div className="p-3 border-b border-gray-800 flex items-center justify-between gap-2">
            <span className="text-sm font-semibold text-white">Customers</span>
            <button
              onClick={() => setShowAddCustomer(true)}
              className="text-xs bg-indigo-600 text-white px-2 py-1 rounded hover:bg-indigo-500 transition-colors"
            >
              + Add
            </button>
          </div>
          <div className="p-2 border-b border-gray-800">
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search…"
              className="w-full bg-gray-800 text-gray-200 text-xs px-2 py-1.5 rounded outline-none placeholder-gray-500"
            />
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
            {isLoading && (
              <p className="text-gray-500 text-xs px-2 py-3">Loading…</p>
            )}
            {filtered.map(c => (
              <button
                key={c.customer_id}
                onClick={() => setSelectedId(c.customer_id)}
                className={`w-full flex items-center gap-2 px-2 py-2 rounded-md text-left transition-colors ${
                  selectedId === c.customer_id
                    ? 'bg-gray-700 border-l-2 border-indigo-500 pl-1.5'
                    : 'hover:bg-gray-800'
                }`}
              >
                <div
                  className="w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-white text-xs font-bold"
                  style={{ background: colorFor(c.customer_id) }}
                >
                  {initials(c.name)}
                </div>
                <p className="text-xs font-medium text-white truncate">{c.name}</p>
              </button>
            ))}
            {!isLoading && filtered.length === 0 && (
              <p className="text-gray-600 text-xs px-2 py-4 text-center">
                {search ? 'No matches' : 'No customers yet'}
              </p>
            )}
          </div>
        </div>

        {/* Right panel: customer detail */}
        <div className="flex-1 bg-gray-950 overflow-y-auto">
          {!selected ? (
            <div className="flex h-full items-center justify-center text-gray-600 text-sm">
              Select a customer
            </div>
          ) : (
            <div className="p-6">
              <div className="flex items-center gap-4 mb-8">
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-lg flex-shrink-0"
                  style={{ background: colorFor(selected.customer_id) }}
                >
                  {initials(selected.name)}
                </div>
                <div className="flex-1 min-w-0">
                  <h1 className="text-xl font-semibold text-white truncate">{selected.name}</h1>
                  <p className="text-sm text-gray-400 mt-0.5 truncate">
                    {[selected.email, selected.phone].filter(Boolean).join(' · ') || 'No contact info'}
                  </p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    onClick={() => router.push(`/inspect?customer=${selected.customer_id}`)}
                    className="text-xs border border-gray-700 text-gray-300 px-3 py-1.5 rounded-lg hover:bg-gray-800 transition-colors"
                  >
                    🔍 New Inspection
                  </button>
                  <button
                    onClick={() => setShowAddVehicle(true)}
                    className="text-xs bg-indigo-600 text-white px-3 py-1.5 rounded-lg hover:bg-indigo-500 transition-colors"
                  >
                    + Add Vehicle
                  </button>
                </div>
              </div>

              <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold mb-4">Vehicles</p>
              <div className="flex flex-wrap gap-4">
                {vehicles.map(v => (
                  <button
                    key={v.vehicle_id}
                    onClick={() => router.push(`/reports?vehicle=${v.vehicle_id}`)}
                    className="bg-gray-800 hover:bg-gray-700 border border-gray-700 hover:border-gray-600 rounded-xl p-4 text-left w-52 transition-colors"
                  >
                    <div className="text-2xl mb-2">🚗</div>
                    <p className="text-white text-sm font-semibold leading-snug">
                      {v.year} {v.make} {v.model}
                    </p>
                    {(v.trim || v.color) && (
                      <p className="text-gray-400 text-xs mt-0.5">
                        {[v.trim, v.color].filter(Boolean).join(' · ')}
                      </p>
                    )}
                    {v.vin && (
                      <p className="text-gray-600 text-xs font-mono mt-1 truncate">{v.vin}</p>
                    )}
                    <p className="text-indigo-400 text-xs mt-3">View reports →</p>
                  </button>
                ))}
                <button
                  onClick={() => setShowAddVehicle(true)}
                  className="border-2 border-dashed border-gray-700 rounded-xl p-4 w-52 flex flex-col items-center justify-center gap-2 hover:border-gray-500 text-gray-600 hover:text-gray-400 transition-colors"
                >
                  <span className="text-2xl">+</span>
                  <span className="text-xs">Add vehicle</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Add Customer modal */}
      {showAddCustomer && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-96 shadow-xl">
            <h2 className="text-white font-semibold mb-4">New Customer</h2>
            <div className="space-y-3">
              <input
                autoFocus
                placeholder="Name *"
                value={customerForm.name}
                onChange={e => setCustomerForm(f => ({ ...f, name: e.target.value }))}
                className="w-full bg-gray-800 text-white text-sm px-3 py-2 rounded-lg outline-none placeholder-gray-500 border border-gray-700 focus:border-indigo-500"
              />
              <input
                placeholder="Email"
                type="email"
                value={customerForm.email}
                onChange={e => setCustomerForm(f => ({ ...f, email: e.target.value }))}
                className="w-full bg-gray-800 text-white text-sm px-3 py-2 rounded-lg outline-none placeholder-gray-500 border border-gray-700 focus:border-indigo-500"
              />
              <input
                placeholder="Phone"
                type="tel"
                value={customerForm.phone}
                onChange={e => setCustomerForm(f => ({ ...f, phone: e.target.value }))}
                className="w-full bg-gray-800 text-white text-sm px-3 py-2 rounded-lg outline-none placeholder-gray-500 border border-gray-700 focus:border-indigo-500"
              />
            </div>
            {addCustomer.isError && (
              <p className="text-red-400 text-xs mt-3">Failed to add. Try again.</p>
            )}
            <div className="flex justify-end gap-2 mt-5">
              <button
                onClick={() => setShowAddCustomer(false)}
                className="text-sm text-gray-400 px-3 py-1.5 hover:text-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={() => addCustomer.mutate()}
                disabled={!customerForm.name || addCustomer.isPending}
                className="text-sm bg-indigo-600 text-white px-4 py-1.5 rounded-lg hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {addCustomer.isPending ? 'Adding…' : 'Add Customer'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Vehicle modal */}
      {showAddVehicle && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-96 shadow-xl">
            <h2 className="text-white font-semibold mb-4">New Vehicle</h2>
            <div className="space-y-3">
              {[
                { key: 'year', placeholder: 'Year *', type: 'number' },
                { key: 'make', placeholder: 'Make *', type: 'text' },
                { key: 'model', placeholder: 'Model *', type: 'text' },
                { key: 'trim', placeholder: 'Trim', type: 'text' },
                { key: 'vin', placeholder: 'VIN', type: 'text' },
                { key: 'color', placeholder: 'Color', type: 'text' },
              ].map(({ key, placeholder, type }) => (
                <input
                  key={key}
                  placeholder={placeholder}
                  type={type}
                  value={vehicleForm[key as keyof typeof vehicleForm]}
                  onChange={e => setVehicleForm(f => ({ ...f, [key]: e.target.value }))}
                  className="w-full bg-gray-800 text-white text-sm px-3 py-2 rounded-lg outline-none placeholder-gray-500 border border-gray-700 focus:border-indigo-500"
                />
              ))}
            </div>
            {addVehicle.isError && (
              <p className="text-red-400 text-xs mt-3">Failed to add. Try again.</p>
            )}
            <div className="flex justify-end gap-2 mt-5">
              <button
                onClick={() => setShowAddVehicle(false)}
                className="text-sm text-gray-400 px-3 py-1.5 hover:text-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={() => addVehicle.mutate()}
                disabled={
                  !vehicleForm.year || !vehicleForm.make || !vehicleForm.model || addVehicle.isPending
                }
                className="text-sm bg-indigo-600 text-white px-4 py-1.5 rounded-lg hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {addVehicle.isPending ? 'Adding…' : 'Add Vehicle'}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  )
}
```

- [ ] **Step 2: Verify in browser**

Navigate to http://localhost:3000/customers (dev server must be running).

Check:
1. Customer list shows on left with search bar and "+ Add" button
2. Clicking a customer shows their detail on the right with vehicle cards
3. "+ Add" button opens modal; fill Name + Email → submit → new customer appears in list and is selected
4. "+ Add Vehicle" button opens modal; fill year/make/model → submit → new vehicle card appears
5. Clicking a vehicle card navigates to `/reports?vehicle={vehicleId}`
6. "🔍 New Inspection" button navigates to `/inspect?customer={customerId}`

- [ ] **Step 3: Commit**

```bash
git add app/customers/page.tsx
git commit -m "feat(web): add customers page with vehicle cards and add modals"
```

---

## Task 6: Reports page

**Files:**
- Create: `app/reports/page.tsx`

The right panel shows full report detail including per-finding photos. Vehicle filter (`?vehicle=`) filters client-side. Report pre-selection (`?id=`) auto-selects a report (used when navigating from the inspect page after analysis).

- [ ] **Step 1: Create `app/reports/page.tsx`**

```tsx
'use client'

import { useState, Suspense } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'next/navigation'
import { AppShell } from '@/components/AppShell'
import { getAllReports, getReport } from '@/lib/api'
import type { ReportSummary, ReportDetail, Finding } from '@/lib/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const SEVERITY_CLASSES: Record<string, string> = {
  high: 'bg-red-900/40 text-red-300 border-red-800',
  urgent: 'bg-red-900/40 text-red-300 border-red-800',
  medium: 'bg-yellow-900/40 text-yellow-300 border-yellow-800',
  moderate: 'bg-yellow-900/40 text-yellow-300 border-yellow-800',
  low: 'bg-green-900/40 text-green-300 border-green-800',
}
function severityClass(s: string) {
  return SEVERITY_CLASSES[(s ?? '').toLowerCase()] ?? 'bg-gray-800 text-gray-400 border-gray-700'
}

function FindingCard({ f }: { f: Finding }) {
  return (
    <div className="border border-gray-700 rounded-xl p-4">
      <div className="flex items-start justify-between gap-3 mb-2">
        <p className="text-sm font-semibold text-white">{f.part}</p>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full border flex-shrink-0 ${severityClass(f.severity)}`}>
          {f.severity}
        </span>
      </div>
      <p className="text-sm text-gray-400 leading-relaxed">{f.notes}</p>
      {f.photo_url && (
        <img
          src={f.photo_url}
          alt={f.part}
          className="mt-3 w-full max-h-52 object-cover rounded-lg border border-gray-700"
        />
      )}
    </div>
  )
}

function vehicleLabel(r: ReportSummary): string {
  const v = r.vehicle
  if (!v || (!v.year && !v.make)) return 'Unknown Vehicle'
  return [v.year, v.make, v.model].filter(Boolean).join(' ')
}

function ReportsPageInner() {
  const searchParams = useSearchParams()
  const vehicleFilter = searchParams.get('vehicle')
  const preselectedId = searchParams.get('id')
  const [selectedId, setSelectedId] = useState<string | null>(preselectedId)

  const { data: reports = [], isLoading } = useQuery<ReportSummary[]>({
    queryKey: ['reports'],
    queryFn: getAllReports,
  })

  const { data: detail, isLoading: detailLoading } = useQuery<ReportDetail>({
    queryKey: ['report', selectedId],
    queryFn: () => getReport(selectedId!),
    enabled: !!selectedId,
  })

  const displayed = vehicleFilter
    ? reports.filter(r => r.vehicle?.vehicle_id === vehicleFilter)
    : reports

  return (
    <AppShell>
      <div className="flex h-full overflow-hidden">
        {/* Left panel: report list */}
        <div className="w-64 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
          <div className="p-3 border-b border-gray-800 flex items-center gap-2">
            <span className="text-sm font-semibold text-white flex-1">Reports</span>
            {vehicleFilter && (
              <a href="/reports" className="text-xs text-indigo-400 hover:underline">
                clear filter
              </a>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
            {isLoading && (
              <p className="text-gray-500 text-xs px-2 py-3">Loading…</p>
            )}
            {displayed.map(r => (
              <button
                key={r.id}
                onClick={() => setSelectedId(r.id)}
                className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors ${
                  selectedId === r.id
                    ? 'bg-gray-700 border-l-2 border-indigo-500 pl-2'
                    : 'hover:bg-gray-800'
                }`}
              >
                <p className="text-xs font-semibold text-white truncate">{vehicleLabel(r)}</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {r.created_at ? new Date(r.created_at).toLocaleDateString() : '—'}
                  {r.total ? ` · $${r.total.toFixed(0)}` : ''}
                </p>
              </button>
            ))}
            {!isLoading && displayed.length === 0 && (
              <p className="text-gray-600 text-xs px-2 py-4 text-center">No reports</p>
            )}
          </div>
        </div>

        {/* Right panel: report detail */}
        <div className="flex-1 bg-gray-950 overflow-y-auto">
          {!selectedId ? (
            <div className="flex h-full items-center justify-center text-gray-600 text-sm">
              Select a report
            </div>
          ) : detailLoading ? (
            <div className="flex h-full items-center justify-center text-gray-500 text-sm">
              Loading…
            </div>
          ) : detail ? (
            <div className="p-6 max-w-3xl space-y-8">
              {/* Header */}
              <div>
                <h1 className="text-xl font-semibold text-white">
                  {[detail.vehicle?.year, detail.vehicle?.make, detail.vehicle?.model]
                    .filter(Boolean)
                    .join(' ') || 'Unknown Vehicle'}
                </h1>
                <div className="flex items-center gap-3 mt-1">
                  {detail.vehicle?.vin && (
                    <p className="text-xs text-gray-500 font-mono">VIN: {detail.vehicle.vin}</p>
                  )}
                  {detail.created_at && (
                    <p className="text-xs text-gray-500">
                      {new Date(detail.created_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
              </div>

              {/* Summary */}
              {detail.summary && (
                <section>
                  <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold mb-2">
                    Summary
                  </p>
                  <p className="text-sm text-gray-300 leading-relaxed">{detail.summary}</p>
                </section>
              )}

              {/* Findings */}
              {detail.findings.length > 0 && (
                <section>
                  <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold mb-3">
                    Findings
                  </p>
                  <div className="space-y-3">
                    {detail.findings.map((f, i) => (
                      <FindingCard key={i} f={f} />
                    ))}
                  </div>
                </section>
              )}

              {/* Estimate */}
              {detail.estimate.length > 0 && (
                <section>
                  <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold mb-3">
                    Estimate
                  </p>
                  <div className="border border-gray-700 rounded-xl overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-800">
                        <tr>
                          <th className="text-left text-xs text-gray-400 px-4 py-2.5 font-medium">
                            Service
                          </th>
                          <th className="text-right text-xs text-gray-400 px-4 py-2.5 font-medium">
                            Labor
                          </th>
                          <th className="text-right text-xs text-gray-400 px-4 py-2.5 font-medium">
                            Parts
                          </th>
                          <th className="text-right text-xs text-gray-400 px-4 py-2.5 font-medium">
                            Total
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-800">
                        {detail.estimate.map((item, i) => (
                          <tr key={i}>
                            <td className="px-4 py-2.5 text-white font-medium">{item.part}</td>
                            <td className="px-4 py-2.5 text-right text-gray-400">
                              ${item.labor_cost.toFixed(2)}
                            </td>
                            <td className="px-4 py-2.5 text-right text-gray-400">
                              ${item.parts_cost.toFixed(2)}
                            </td>
                            <td className="px-4 py-2.5 text-right text-white font-semibold">
                              ${item.total.toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot className="bg-gray-800">
                        <tr>
                          <td colSpan={3} className="px-4 py-2.5 text-right text-sm font-semibold text-white">
                            Grand Total
                          </td>
                          <td className="px-4 py-2.5 text-right text-indigo-400 font-bold text-base">
                            ${detail.total.toFixed(2)}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </section>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-1">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(
                      `${window.location.origin}/r/${detail.share_token}`,
                    )
                  }}
                  className="text-sm border border-gray-700 text-gray-300 px-4 py-2 rounded-lg hover:bg-gray-800 transition-colors"
                >
                  📋 Copy Share Link
                </button>
                <a
                  href={`${API_URL}/reports/${detail.id}/pdf`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-500 transition-colors"
                >
                  🖨 Open Report PDF
                </a>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </AppShell>
  )
}

export default function ReportsPage() {
  return (
    <Suspense>
      <ReportsPageInner />
    </Suspense>
  )
}
```

- [ ] **Step 2: Verify in browser**

Navigate to http://localhost:3000/reports.

Check:
1. Report list loads in left panel; clicking a report shows full detail on the right
2. Summary, findings, and estimate table all render correctly
3. If a report has `photo_url` on a finding, the photo appears below the finding text
4. "Copy Share Link" button copies to clipboard (check browser console for errors)
5. "Open Report PDF" link opens the PDF in a new tab
6. Navigate to `/customers`, click a vehicle card → should land on `/reports?vehicle={id}` with the list filtered to that vehicle

- [ ] **Step 3: Commit**

```bash
git add app/reports/page.tsx
git commit -m "feat(web): add reports page with full detail and per-finding photos"
```

---

## Task 7: Inspect page

**Files:**
- Create: `app/inspect/page.tsx`

The flow: pick vehicle from left panel → upload audio file → upload photos → click Analyze → navigate to the new report.

`createSession` needs `shop_id`. This comes from the JWT payload via `getShopId()` added in Task 2.

- [ ] **Step 1: Create `app/inspect/page.tsx`**

```tsx
'use client'

import { useState, useRef, Suspense } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams, useRouter } from 'next/navigation'
import { AppShell } from '@/components/AppShell'
import {
  getCustomers,
  getVehicles,
  createSession,
  uploadSessionMedia,
  generateReport,
  transcribeAudio,
} from '@/lib/api'
import type { Customer, Vehicle } from '@/lib/types'

function InspectPageInner() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const preselectedCustomer = searchParams.get('customer')

  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(preselectedCustomer)
  const [selectedVehicleId, setSelectedVehicleId] = useState<string | null>(null)
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [transcript, setTranscript] = useState<string>('')
  const [transcribing, setTranscribing] = useState(false)
  const [photos, setPhotos] = useState<File[]>([])
  const [photoPreviews, setPhotoPreviews] = useState<string[]>([])
  const [analyzing, setAnalyzing] = useState(false)
  const [analyzeError, setAnalyzeError] = useState<string | null>(null)

  const audioInputRef = useRef<HTMLInputElement>(null)
  const photoInputRef = useRef<HTMLInputElement>(null)

  const { data: customers = [] } = useQuery<Customer[]>({
    queryKey: ['customers'],
    queryFn: getCustomers,
  })

  const { data: vehicles = [] } = useQuery<Vehicle[]>({
    queryKey: ['vehicles', selectedCustomerId],
    queryFn: () => getVehicles(selectedCustomerId!),
    enabled: !!selectedCustomerId,
  })

  async function handleAudioChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setAudioFile(file)
    setTranscript('')
    setTranscribing(true)
    try {
      const text = await transcribeAudio(file)
      setTranscript(text)
    } catch {
      // Transcript preview is best-effort; analysis still works without it
      setTranscript('')
    } finally {
      setTranscribing(false)
    }
  }

  function handlePhotosChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? [])
    const remaining = 20 - photos.length
    const toAdd = files.slice(0, remaining)
    setPhotos(prev => [...prev, ...toAdd])
    setPhotoPreviews(prev => [...prev, ...toAdd.map(f => URL.createObjectURL(f))])
    e.target.value = ''
  }

  function removePhoto(index: number) {
    URL.revokeObjectURL(photoPreviews[index])
    setPhotos(prev => prev.filter((_, i) => i !== index))
    setPhotoPreviews(prev => prev.filter((_, i) => i !== index))
  }

  async function handleAnalyze() {
    if (!selectedVehicleId || !audioFile) return
    setAnalyzing(true)
    setAnalyzeError(null)
    try {
      const { session_id } = await createSession(selectedVehicleId)

      // Determine media type from file mime
      const isVideo = audioFile.type.startsWith('video/')
      await uploadSessionMedia(session_id, audioFile, isVideo ? 'video' : 'audio')

      for (const photo of photos) {
        await uploadSessionMedia(session_id, photo, 'photo')
      }

      const result = await generateReport(session_id)
      router.push(`/reports?id=${result.report_id}`)
    } catch (err) {
      setAnalyzeError(err instanceof Error ? err.message : 'Analysis failed. Please try again.')
      setAnalyzing(false)
    }
  }

  const selectedVehicle = vehicles.find(v => v.vehicle_id === selectedVehicleId)

  return (
    <AppShell>
      <div className="flex h-full overflow-hidden">
        {/* Left panel: vehicle picker */}
        <div className="w-56 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col overflow-y-auto">
          <div className="p-3 border-b border-gray-800 flex-shrink-0">
            <span className="text-sm font-semibold text-white">Pick Vehicle</span>
          </div>
          <div className="flex-1 p-2">
            {customers.map(c => (
              <div key={c.customer_id}>
                <button
                  onClick={() =>
                    setSelectedCustomerId(
                      c.customer_id === selectedCustomerId ? null : c.customer_id,
                    )
                  }
                  className="w-full flex items-center gap-1.5 px-2 py-1.5 rounded text-left hover:bg-gray-800 text-xs font-semibold text-gray-300 transition-colors"
                >
                  <span className="text-gray-500">
                    {selectedCustomerId === c.customer_id ? '▾' : '▸'}
                  </span>
                  <span className="truncate">{c.name}</span>
                </button>
                {selectedCustomerId === c.customer_id &&
                  vehicles.map(v => (
                    <button
                      key={v.vehicle_id}
                      onClick={() => setSelectedVehicleId(v.vehicle_id)}
                      className={`w-full flex items-center gap-2 pl-5 pr-2 py-1.5 rounded text-left text-xs transition-colors ${
                        selectedVehicleId === v.vehicle_id
                          ? 'bg-indigo-600/30 text-indigo-300'
                          : 'text-gray-400 hover:bg-gray-800'
                      }`}
                    >
                      <span>🚗</span>
                      <span className="truncate">
                        {v.year} {v.make} {v.model}
                      </span>
                    </button>
                  ))}
              </div>
            ))}
          </div>
        </div>

        {/* Right panel: upload flow */}
        <div className="flex-1 bg-gray-950 overflow-y-auto">
          {!selectedVehicleId ? (
            <div className="flex h-full items-center justify-center text-gray-600 text-sm">
              Select a vehicle to start an inspection
            </div>
          ) : (
            <div className="p-6 max-w-2xl space-y-6">
              <div>
                <h1 className="text-xl font-semibold text-white">
                  {selectedVehicle
                    ? `${selectedVehicle.year} ${selectedVehicle.make} ${selectedVehicle.model}`
                    : 'Inspection'}
                </h1>
                <p className="text-sm text-gray-400 mt-0.5">
                  Upload inspection recording then photos
                </p>
              </div>

              {/* Audio upload */}
              <section className="border border-gray-700 rounded-xl p-5">
                <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold mb-3">
                  Audio / Video Recording
                </p>
                {!audioFile ? (
                  <div
                    onClick={() => audioInputRef.current?.click()}
                    className="border-2 border-dashed border-gray-700 rounded-xl p-8 text-center cursor-pointer hover:border-gray-500 transition-colors"
                  >
                    <p className="text-4xl mb-3">🎙</p>
                    <p className="text-gray-400 text-sm font-medium">
                      Drop audio or video, or click to browse
                    </p>
                    <p className="text-gray-600 text-xs mt-1">MP3, M4A, MP4, MOV, WAV</p>
                    <input
                      ref={audioInputRef}
                      type="file"
                      accept="audio/*,video/mp4,video/quicktime,video/webm"
                      onChange={handleAudioChange}
                      className="hidden"
                    />
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="flex items-center gap-3 bg-gray-800 rounded-lg p-3">
                      <span className="text-xl">🎙</span>
                      <p className="text-sm text-white flex-1 truncate">{audioFile.name}</p>
                      <button
                        onClick={() => {
                          setAudioFile(null)
                          setTranscript('')
                        }}
                        className="text-gray-500 hover:text-gray-300 text-sm"
                      >
                        ✕
                      </button>
                    </div>
                    {transcribing && (
                      <p className="text-xs text-gray-500">Transcribing preview…</p>
                    )}
                    {transcript && !transcribing && (
                      <div className="bg-gray-800 rounded-lg p-3">
                        <p className="text-xs text-gray-500 mb-1.5">Transcript preview</p>
                        <p className="text-xs text-gray-300 leading-relaxed line-clamp-6">
                          {transcript}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </section>

              {/* Photo upload */}
              <section className="border border-gray-700 rounded-xl p-5">
                <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold mb-3">
                  Inspection Photos{' '}
                  <span className="normal-case font-normal text-gray-600">(optional, up to 20)</span>
                </p>
                <div className="flex flex-wrap gap-3">
                  {photoPreviews.map((src, i) => (
                    <div
                      key={i}
                      className="relative w-20 h-20 rounded-lg overflow-hidden bg-gray-800 border border-gray-700"
                    >
                      <img
                        src={src}
                        alt={`Photo ${i + 1}`}
                        className="w-full h-full object-cover"
                      />
                      <button
                        onClick={() => removePhoto(i)}
                        className="absolute top-0.5 right-0.5 bg-black/70 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center hover:bg-black"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                  {photos.length < 20 && (
                    <button
                      onClick={() => photoInputRef.current?.click()}
                      className="w-20 h-20 rounded-lg border-2 border-dashed border-gray-700 flex flex-col items-center justify-center text-gray-600 hover:text-gray-400 hover:border-gray-500 transition-colors text-xs gap-1"
                    >
                      <span className="text-xl">+</span>
                      <span>Add</span>
                      <input
                        ref={photoInputRef}
                        type="file"
                        accept="image/*"
                        multiple
                        onChange={handlePhotosChange}
                        className="hidden"
                      />
                    </button>
                  )}
                </div>
              </section>

              {analyzeError && (
                <p className="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-lg px-4 py-3">
                  {analyzeError}
                </p>
              )}

              <button
                onClick={handleAnalyze}
                disabled={!audioFile || analyzing}
                className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition-colors"
              >
                {analyzing ? '⏳ Analyzing… (~30 seconds)' : '▶ Analyze Inspection'}
              </button>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}

export default function InspectPage() {
  return (
    <Suspense>
      <InspectPageInner />
    </Suspense>
  )
}
```

- [ ] **Step 2: Verify in browser**

Navigate to http://localhost:3000/inspect.

Check:
1. Customer list shows in left panel; clicking a customer expands their vehicles
2. Clicking a vehicle activates the right panel with the upload UI
3. Click audio drop zone → file picker opens; select an MP3 or M4A → file name shows; transcript preview appears after a few seconds
4. Click "+ Add" photo zone → select 2-3 images → thumbnails appear; X button removes them
5. "▶ Analyze Inspection" button is disabled until audio is uploaded; after uploading it becomes enabled
6. Click Analyze → loading state shows ("⏳ Analyzing…"); after ~30 seconds navigates to `/reports?id={new_report_id}` with the new report auto-selected

**Note:** Full end-to-end analysis requires the backend running and media reaching S3. If testing locally without S3, the session/media upload still works but photo_urls will be `local://` and won't render. The report will still be created.

- [ ] **Step 3: Commit**

```bash
git add app/inspect/page.tsx
git commit -m "feat(web): add inspect page with upload-first inspection flow"
```

---

## Task 8: Delete old dashboard routes

**Files:**
- Delete: `app/dashboard/page.tsx`
- Delete: `app/dashboard/reports/[id]/page.tsx`

- [ ] **Step 1: Delete the old dashboard pages and old AppShell**

```bash
rm /Users/joehe/workspace/projects/pitagents/web/app/dashboard/page.tsx
rm /Users/joehe/workspace/projects/pitagents/web/app/dashboard/reports/[id]/page.tsx
rm /Users/joehe/workspace/projects/pitagents/web/components/chat/AppShell.tsx
rmdir /Users/joehe/workspace/projects/pitagents/web/app/dashboard/reports/\[id\] 2>/dev/null || true
rmdir /Users/joehe/workspace/projects/pitagents/web/app/dashboard/reports 2>/dev/null || true
rmdir /Users/joehe/workspace/projects/pitagents/web/app/dashboard 2>/dev/null || true
```

- [ ] **Step 2: Verify `/dashboard` now 404s**

Navigate to http://localhost:3000/dashboard. Expected: Next.js 404 page (the route no longer exists).

- [ ] **Step 3: Verify build compiles clean**

```bash
cd /Users/joehe/workspace/projects/pitagents/web
npm run build 2>&1 | tail -30
```

Expected: no errors about missing modules.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore(web): remove old dashboard routes replaced by /reports"
```

---

## Self-Review Checklist

Run through this after all tasks are complete.

- [ ] `/customers` — list shows, add customer works, vehicles load, vehicle card navigates to `/reports?vehicle=`
- [ ] `/reports` — list loads, vehicle filter works, clicking report shows full detail, finding photos render, estimate table shows all line items with grand total, "Open Report PDF" opens PDF in new tab
- [ ] `/inspect` — vehicle picker works, audio upload + transcript preview works, photo upload + thumbnails work, Analyze submits and redirects to new report
- [ ] `/chat` — agent list and chat panel work as before; no regression
- [ ] Top nav — all four links navigate correctly; active link highlighted; logout button works
- [ ] `/dashboard` — returns 404 (deleted)
- [ ] `/r/{token}` — public consumer report still works (no shell, no auth)
- [ ] `npm run build` — no TypeScript or module errors
