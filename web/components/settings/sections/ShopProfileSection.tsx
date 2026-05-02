'use client'
import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getShopProfile, updateShopProfile } from '@/lib/api'

const fieldStyle: React.CSSProperties = {
  width: '100%', background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.09)', borderRadius: 6,
  padding: '8px 10px', fontSize: 12, color: 'rgba(255,255,255,0.85)',
  outline: 'none', boxSizing: 'border-box',
}

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 10, fontWeight: 600,
  textTransform: 'uppercase', letterSpacing: '.06em',
  color: 'rgba(255,255,255,0.3)', marginBottom: 5,
}

export function ShopProfileSection() {
  const qc = useQueryClient()
  const { data: shop } = useQuery({ queryKey: ['shop-profile'], queryFn: getShopProfile })

  const [form, setForm] = useState({ name: '', address: '', labor_rate: '' })
  const [msg, setMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)
  const clearTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => () => { if (clearTimer.current) clearTimeout(clearTimer.current) }, [])

  useEffect(() => {
    if (shop) {
      setForm({
        name: shop.name,
        address: shop.address ?? '',
        labor_rate: shop.labor_rate,
      })
    }
  }, [shop])

  const save = useMutation({
    mutationFn: () => updateShopProfile({
      name: form.name,
      address: form.address || undefined,
      labor_rate: form.labor_rate,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shop-profile'] })
      if (clearTimer.current) clearTimeout(clearTimer.current)
      setMsg({ type: 'ok', text: 'Saved' })
      clearTimer.current = setTimeout(() => setMsg(null), 2500)
    },
    onError: (e: Error) => setMsg({ type: 'err', text: e.message }),
  })

  function field(key: keyof typeof form, label: string, placeholder?: string) {
    return (
      <div style={{ marginBottom: 12 }}>
        <label htmlFor={`shop-${key}`} style={labelStyle}>{label}</label>
        <input
          id={`shop-${key}`}
          value={form[key]}
          onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
          style={fieldStyle}
          placeholder={placeholder}
        />
      </div>
    )
  }

  return (
    <form onSubmit={e => {
      e.preventDefault()
      if (!form.name.trim()) {
        setMsg({ type: 'err', text: 'Shop name is required' })
        return
      }
      if (form.labor_rate && isNaN(parseFloat(form.labor_rate))) {
        setMsg({ type: 'err', text: 'Labor rate must be a valid number' })
        return
      }
      save.mutate()
    }}>
      {field('name', 'Shop name', 'AutoShop')}
      {field('address', 'Address', '123 Main St')}
      {field('labor_rate', 'Labor rate ($/hr)', '120.00')}
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button
          type="submit"
          disabled={save.isPending}
          style={{
            background: 'var(--accent)', color: '#000', border: 'none',
            borderRadius: 6, padding: '7px 16px', fontSize: 12, fontWeight: 700,
            cursor: save.isPending ? 'not-allowed' : 'pointer', opacity: save.isPending ? 0.6 : 1,
          }}
        >
          {save.isPending ? 'Saving…' : 'Save'}
        </button>
      </div>
      {msg && (
        <div style={{ fontSize: 11, marginTop: 8, color: msg.type === 'ok' ? 'rgba(74,222,128,0.9)' : 'rgba(239,68,68,0.9)' }}>
          {msg.text}
        </div>
      )}
    </form>
  )
}
