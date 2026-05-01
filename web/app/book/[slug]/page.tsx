'use client'
import { useState } from 'react'
import { useParams } from 'next/navigation'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { BookingConfig } from '@/lib/types'

export default function BookingPage() {
  const params = useParams()
  const slug = Array.isArray(params.slug) ? params.slug[0] : params.slug as string

  return <BookingForm slug={slug} />
}

function toDatetimeLocal(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function BookingForm({ slug }: { slug: string }) {
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [form, setForm] = useState({
    customer_name: '',
    customer_phone: '',
    customer_email: '',
    service_requested: '',
    starts_at: '',
    ends_at: '',
  })
  const [submitted, setSubmitted] = useState(false)

  const { data: config, isLoading, error } = useQuery<BookingConfig>({
    queryKey: ['booking-config', slug],
    queryFn: () => api.get(`/book/${slug}`).then(r => r.data),
  })

  const submit = useMutation({
    mutationFn: () => api.post(`/book/${slug}`, form).then(r => r.data),
    onSuccess: () => setSubmitted(true),
  })

  if (isLoading) return <div style={{ minHeight: '100vh', background: '#0d0d0d', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)' }}>Loading…</div>
  if (error || !config) return <div style={{ minHeight: '100vh', background: '#0d0d0d', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#f87171' }}>Shop not found</div>
  if (submitted) return (
    <div style={{ minHeight: '100vh', background: '#0d0d0d', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
      <div style={{ textAlign: 'center', maxWidth: 400, padding: 24 }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>✓</div>
        <div style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Booking received!</div>
        <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.5)' }}>We'll confirm your appointment shortly via SMS.</div>
      </div>
    </div>
  )

  return (
    <div style={{ minHeight: '100vh', background: '#0d0d0d', color: '#fff', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '40px 16px' }}>
      <div style={{ width: '100%', maxWidth: 480 }}>
        <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>Book an Appointment</div>
        <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.4)', marginBottom: 32 }}>Step {step} of 3</div>

        {step === 1 && (
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>What service do you need?</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {(config.available_services.length > 0 ? config.available_services : ['Oil Change', 'Tire Rotation', 'Brake Inspection', 'Full Service']).map(svc => (
                <div key={svc} onClick={() => { setForm(f => ({ ...f, service_requested: svc })); setStep(2) }} style={{
                  padding: '14px 16px', borderRadius: 10, cursor: 'pointer', fontSize: 14, fontWeight: 600,
                  border: `1px solid ${form.service_requested === svc ? '#d97706' : 'rgba(255,255,255,0.1)'}`,
                  background: form.service_requested === svc ? 'rgba(217,119,6,0.08)' : 'rgba(255,255,255,0.02)',
                }}>{svc}</div>
              ))}
              <input placeholder="Other (type here)" value={form.service_requested} onChange={e => setForm(f => ({ ...f, service_requested: e.target.value }))} style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '12px 14px', color: '#fff', fontSize: 13, marginTop: 8 }} />
            </div>
            <button disabled={!form.service_requested} onClick={() => setStep(2)} style={{ marginTop: 20, width: '100%', height: 44, borderRadius: 10, border: 'none', background: form.service_requested ? '#d97706' : 'rgba(255,255,255,0.1)', color: '#fff', fontWeight: 700, fontSize: 14, cursor: form.service_requested ? 'pointer' : 'default' }}>Next</button>
          </div>
        )}

        {step === 2 && (
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>When works for you?</div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginBottom: 6 }}>PREFERRED DATE & TIME</div>
              <input type="datetime-local" value={form.starts_at} onChange={e => {
                const start = new Date(e.target.value)
                const durationMs = (parseInt(config.slot_duration_minutes, 10) || 60) * 60000
                const end = new Date(start.getTime() + durationMs)
                setForm(f => ({ ...f, starts_at: e.target.value, ends_at: toDatetimeLocal(end) }))
              }} style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '12px 14px', color: '#fff', fontSize: 13 }} />
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
              <button onClick={() => setStep(1)} style={{ flex: 1, height: 44, borderRadius: 10, border: '1px solid rgba(255,255,255,0.1)', background: 'transparent', color: 'rgba(255,255,255,0.6)', cursor: 'pointer' }}>Back</button>
              <button disabled={!form.starts_at} onClick={() => setStep(3)} style={{ flex: 2, height: 44, borderRadius: 10, border: 'none', background: form.starts_at ? '#d97706' : 'rgba(255,255,255,0.1)', color: '#fff', fontWeight: 700, cursor: form.starts_at ? 'pointer' : 'default' }}>Next</button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Your details</div>
            {(['customer_name', 'customer_phone', 'customer_email'] as const).map(key => (
              <div key={key} style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginBottom: 6 }}>{key.replace('customer_', '').replace('_', ' ').toUpperCase()}</div>
                <input type={key === 'customer_email' ? 'email' : key === 'customer_phone' ? 'tel' : 'text'} value={form[key]} onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))} style={{ width: '100%', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '12px 14px', color: '#fff', fontSize: 13 }} />
              </div>
            ))}
            <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
              <button onClick={() => setStep(2)} style={{ flex: 1, height: 44, borderRadius: 10, border: '1px solid rgba(255,255,255,0.1)', background: 'transparent', color: 'rgba(255,255,255,0.6)', cursor: 'pointer' }}>Back</button>
              <button disabled={!form.customer_name || !form.customer_phone || submit.isPending} onClick={() => submit.mutate()} style={{ flex: 2, height: 44, borderRadius: 10, border: 'none', background: (form.customer_name && form.customer_phone) ? '#d97706' : 'rgba(255,255,255,0.1)', color: '#fff', fontWeight: 700, cursor: (form.customer_name && form.customer_phone) ? 'pointer' : 'default' }}>
                {submit.isPending ? 'Booking…' : 'Confirm Booking'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
