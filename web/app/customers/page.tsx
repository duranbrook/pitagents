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
