'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getShopSettings, updateShopSettings } from '@/lib/api'
import type { ShopSettingsUpdate } from '@/lib/types'

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 10, fontWeight: 600,
  textTransform: 'uppercase', letterSpacing: '.06em',
  color: 'rgba(255,255,255,0.3)', marginBottom: 5,
}

const fieldStyle: React.CSSProperties = {
  width: '100%', background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.09)', borderRadius: 6,
  padding: '7px 10px', fontSize: 11, color: 'rgba(255,255,255,0.85)',
  outline: 'none', boxSizing: 'border-box', fontFamily: 'monospace',
}

const saveBtnStyle: React.CSSProperties = {
  background: 'var(--accent)', color: '#000', border: 'none',
  borderRadius: 6, padding: '6px 14px', fontSize: 11, fontWeight: 700, cursor: 'pointer',
}

function StatusBadge({ connected }: { connected: boolean }) {
  return (
    <span style={{
      fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 4,
      background: connected ? 'rgba(74,222,128,0.12)' : 'rgba(255,255,255,0.06)',
      color: connected ? 'rgba(74,222,128,0.9)' : 'rgba(255,255,255,0.35)',
      border: connected ? '1px solid rgba(74,222,128,0.25)' : '1px solid rgba(255,255,255,0.08)',
    }}>
      {connected ? 'Connected' : 'Not connected'}
    </span>
  )
}

function IntegrationCard({
  title, connected, children,
}: { title: string; connected: boolean; children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <div style={{
      background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
      borderRadius: 8, marginBottom: 8, overflow: 'hidden',
    }}>
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          width: '100%', padding: '12px 14px', background: 'none', border: 'none', cursor: 'pointer',
        }}
      >
        <span style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>{title}</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <StatusBadge connected={connected} />
          <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>{open ? '▲' : '▼'}</span>
        </div>
      </button>
      {open && (
        <div style={{ padding: '0 14px 14px' }}>
          {children}
        </div>
      )}
    </div>
  )
}

export function IntegrationsSection() {
  const qc = useQueryClient()
  const { data: settings } = useQuery({ queryKey: ['shop-settings'], queryFn: getShopSettings })

  const [stripe, setStripe] = useState({ pub: '', secret: '' })
  const [carmd, setCarmd] = useState('')
  const [mitchell, setMitchell] = useState<boolean | null>(null)
  const [qb, setQb] = useState<boolean | null>(null)
  const [synchrony, setSynchrony] = useState({ enabled: null as boolean | null, dealer_id: '' })
  const [wisetack, setWisetack] = useState({ enabled: null as boolean | null, merchant_id: '' })
  const [msg, setMsg] = useState<string | null>(null)

  const save = useMutation({
    mutationFn: (data: ShopSettingsUpdate) => updateShopSettings(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shop-settings'] })
      setMsg('Saved')
      setTimeout(() => setMsg(null), 2500)
    },
    onError: (e: Error) => {
      setMsg(`Error: ${e.message}`)
      setTimeout(() => setMsg(null), 3000)
    },
  })

  if (!settings) {
    return <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>Loading…</div>
  }

  return (
    <div>
      <IntegrationCard title="Stripe" connected={settings.has_stripe_secret}>
        <div style={{ marginBottom: 10 }}>
          <label htmlFor="stripe-pub" style={labelStyle}>Publishable key</label>
          <input
            id="stripe-pub"
            value={stripe.pub || settings.stripe_publishable_key || ''}
            onChange={e => setStripe(s => ({ ...s, pub: e.target.value }))}
            style={fieldStyle}
            placeholder="pk_live_..."
          />
        </div>
        <div style={{ marginBottom: 10 }}>
          <label htmlFor="stripe-secret" style={labelStyle}>
            Secret key {settings.has_stripe_secret && '(already set — enter new to replace)'}
          </label>
          <input
            id="stripe-secret"
            type="password"
            value={stripe.secret}
            onChange={e => setStripe(s => ({ ...s, secret: e.target.value }))}
            style={fieldStyle}
            placeholder={settings.has_stripe_secret ? '••••••••' : 'sk_live_...'}
          />
        </div>
        <button
          type="button"
          onClick={() => save.mutate({
            stripe_publishable_key: stripe.pub || undefined,
            stripe_secret_key: stripe.secret || undefined,
          })}
          style={saveBtnStyle}
        >
          Save
        </button>
      </IntegrationCard>

      <IntegrationCard title="CarMD Diagnostics" connected={!!settings.carmd_api_key}>
        <div style={{ marginBottom: 10 }}>
          <label htmlFor="carmd-key" style={labelStyle}>API key</label>
          <input
            id="carmd-key"
            value={carmd || settings.carmd_api_key || ''}
            onChange={e => setCarmd(e.target.value)}
            style={fieldStyle}
            placeholder="carmd-api-key"
          />
        </div>
        <button
          type="button"
          onClick={() => save.mutate({ carmd_api_key: carmd || undefined })}
          style={saveBtnStyle}
        >
          Save
        </button>
      </IntegrationCard>

      <IntegrationCard title="Mitchell1" connected={settings.mitchell1_enabled}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12, color: 'rgba(255,255,255,0.7)', marginBottom: 10 }}>
          <input
            type="checkbox"
            checked={mitchell ?? settings.mitchell1_enabled}
            onChange={e => setMitchell(e.target.checked)}
          />
          Enable Mitchell1 integration
        </label>
        <button
          type="button"
          onClick={() => save.mutate({ mitchell1_enabled: mitchell ?? settings.mitchell1_enabled })}
          style={saveBtnStyle}
        >
          Save
        </button>
      </IntegrationCard>

      <IntegrationCard title="QuickBooks" connected={settings.quickbooks_enabled}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12, color: 'rgba(255,255,255,0.7)', marginBottom: 10 }}>
          <input
            type="checkbox"
            checked={qb ?? settings.quickbooks_enabled}
            onChange={e => setQb(e.target.checked)}
          />
          Enable QuickBooks sync
        </label>
        <button
          type="button"
          onClick={() => save.mutate({ quickbooks_enabled: qb ?? settings.quickbooks_enabled })}
          style={saveBtnStyle}
        >
          Save
        </button>
      </IntegrationCard>

      <IntegrationCard title="Synchrony Financing" connected={settings.synchrony_enabled}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12, color: 'rgba(255,255,255,0.7)', marginBottom: 8 }}>
          <input
            type="checkbox"
            checked={synchrony.enabled ?? settings.synchrony_enabled}
            onChange={e => setSynchrony(s => ({ ...s, enabled: e.target.checked }))}
          />
          Enable Synchrony
        </label>
        <div style={{ marginBottom: 10 }}>
          <label htmlFor="synchrony-dealer" style={labelStyle}>Dealer ID</label>
          <input
            id="synchrony-dealer"
            value={synchrony.dealer_id || settings.synchrony_dealer_id || ''}
            onChange={e => setSynchrony(s => ({ ...s, dealer_id: e.target.value }))}
            style={fieldStyle}
            placeholder="dealer-id"
          />
        </div>
        <button
          type="button"
          onClick={() => save.mutate({
            synchrony_enabled: synchrony.enabled ?? settings.synchrony_enabled,
            synchrony_dealer_id: synchrony.dealer_id || undefined,
          })}
          style={saveBtnStyle}
        >
          Save
        </button>
      </IntegrationCard>

      <IntegrationCard title="Wisetack Financing" connected={settings.wisetack_enabled}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12, color: 'rgba(255,255,255,0.7)', marginBottom: 8 }}>
          <input
            type="checkbox"
            checked={wisetack.enabled ?? settings.wisetack_enabled}
            onChange={e => setWisetack(s => ({ ...s, enabled: e.target.checked }))}
          />
          Enable Wisetack
        </label>
        <div style={{ marginBottom: 10 }}>
          <label htmlFor="wisetack-merchant" style={labelStyle}>Merchant ID</label>
          <input
            id="wisetack-merchant"
            value={wisetack.merchant_id || settings.wisetack_merchant_id || ''}
            onChange={e => setWisetack(s => ({ ...s, merchant_id: e.target.value }))}
            style={fieldStyle}
            placeholder="merchant-id"
          />
        </div>
        <button
          type="button"
          onClick={() => save.mutate({
            wisetack_enabled: wisetack.enabled ?? settings.wisetack_enabled,
            wisetack_merchant_id: wisetack.merchant_id || undefined,
          })}
          style={saveBtnStyle}
        >
          Save
        </button>
      </IntegrationCard>

      {msg && (
        <div style={{ fontSize: 11, marginTop: 8, color: msg.startsWith('Error') ? 'rgba(239,68,68,0.9)' : 'rgba(74,222,128,0.9)' }}>
          {msg}
        </div>
      )}
    </div>
  )
}
