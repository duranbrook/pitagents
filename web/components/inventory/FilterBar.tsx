'use client'
import { useState } from 'react'

const CATEGORIES = ['Oils', 'Brakes', 'Tires', 'Filters', 'Electrical', 'Misc']
const STOCK_OPTIONS = [
  { value: 'ok', label: 'In stock' },
  { value: 'low', label: 'Low' },
  { value: 'out', label: 'Out of stock' },
]

interface Filters {
  search: string
  categories: string[]
  stockStatuses: string[]
}

interface Props {
  filters: Filters
  onChange: (f: Filters) => void
}

function MultiSelectDropdown({
  label, options, selected, onToggle,
}: {
  label: string
  options: { value: string; label?: string }[]
  selected: string[]
  onToggle: (v: string) => void
}) {
  const [open, setOpen] = useState(false)
  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          height: 32, padding: '0 12px', borderRadius: 7, cursor: 'pointer', fontSize: 12, fontWeight: 600,
          background: selected.length > 0 ? 'rgba(217,119,6,0.12)' : 'rgba(255,255,255,0.06)',
          border: `1px solid ${selected.length > 0 ? 'rgba(217,119,6,0.3)' : 'rgba(255,255,255,0.1)'}`,
          color: selected.length > 0 ? '#fbbf24' : 'rgba(255,255,255,0.65)',
          display: 'flex', alignItems: 'center', gap: 4,
        }}
      >
        {label}{selected.length > 0 ? ` (${selected.length})` : ''} ▾
      </button>
      {open && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, marginTop: 4, zIndex: 20,
          background: '#1e1e1e', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 8,
          padding: 6, minWidth: 160,
        }}>
          {options.map(opt => (
            <div
              key={opt.value}
              onClick={() => onToggle(opt.value)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px',
                cursor: 'pointer', borderRadius: 5, fontSize: 12,
                background: selected.includes(opt.value) ? 'rgba(217,119,6,0.1)' : 'transparent',
                color: selected.includes(opt.value) ? '#fbbf24' : 'rgba(255,255,255,0.7)',
              }}
            >
              <span style={{ width: 14, height: 14, borderRadius: 3, border: `1.5px solid ${selected.includes(opt.value) ? '#d97706' : 'rgba(255,255,255,0.25)'}`, background: selected.includes(opt.value) ? '#d97706' : 'transparent', display: 'inline-block', flexShrink: 0 }} />
              {opt.label ?? opt.value}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function FilterBar({ filters, onChange }: Props) {
  const toggleCategory = (v: string) =>
    onChange({ ...filters, categories: filters.categories.includes(v) ? filters.categories.filter(c => c !== v) : [...filters.categories, v] })
  const toggleStock = (v: string) =>
    onChange({ ...filters, stockStatuses: filters.stockStatuses.includes(v) ? filters.stockStatuses.filter(s => s !== v) : [...filters.stockStatuses, v] })

  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
      <input
        placeholder="Search part name or SKU…"
        value={filters.search}
        onChange={e => onChange({ ...filters, search: e.target.value })}
        style={{
          height: 32, padding: '0 12px', borderRadius: 7, border: '1px solid rgba(255,255,255,0.1)',
          background: 'rgba(255,255,255,0.05)', color: '#fff', fontSize: 12, minWidth: 200,
        }}
      />
      <MultiSelectDropdown
        label="Category"
        options={CATEGORIES.map(c => ({ value: c }))}
        selected={filters.categories}
        onToggle={toggleCategory}
      />
      <MultiSelectDropdown
        label="Stock"
        options={STOCK_OPTIONS}
        selected={filters.stockStatuses}
        onToggle={toggleStock}
      />
    </div>
  )
}
