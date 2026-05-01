'use client'
import { useState } from 'react'
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query'
import { createCampaign, updateCampaign, sendCampaign, fetchCampaignTemplates } from '@/lib/api'
import { AudienceSelector } from './AudienceSelector'
import type { Campaign, AudienceSegment } from '@/lib/types'

interface Props {
  campaign: Campaign | null
  onClose: () => void
}

const TEMPLATE_VARS = ['{first_name}', '{vehicle}', '{service}', '{booking_link}']

export function ComposePanel({ campaign, onClose }: Props) {
  const qc = useQueryClient()
  const isNew = !campaign

  const [name, setName] = useState(campaign?.name || '')
  const [body, setBody] = useState(campaign?.message_body || '')
  const [channel, setChannel] = useState<'sms' | 'email' | 'both'>(campaign?.channel || 'sms')
  const [segment, setSegment] = useState<AudienceSegment>(campaign?.audience_segment || { type: 'all_customers' })
  const [selectedTemplate, setSelectedTemplate] = useState('')

  const { data: templates = [] } = useQuery({ queryKey: ['campaign-templates'], queryFn: fetchCampaignTemplates })

  const save = useMutation({
    mutationFn: () => {
      const payload = { name, message_body: body, channel, audience_segment: segment }
      return isNew ? createCampaign(payload) : updateCampaign(campaign!.campaign_id, payload)
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['campaigns'] }); onClose() },
  })

  const send = useMutation({
    mutationFn: () => sendCampaign(campaign!.campaign_id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['campaigns'] }); onClose() },
  })

  const applyTemplate = (templateId: string) => {
    const t = templates.find(t => t.id === templateId)
    if (t) setBody(t.message_body)
  }

  const insertVar = (v: string) => setBody(prev => prev + v)

  const inputStyle = { background: '#1a1a1a', border: '1px solid #333', color: '#fff', borderRadius: '6px', padding: '8px 12px', fontSize: '14px', width: '100%', outline: 'none', boxSizing: 'border-box' as const }
  const labelStyle = { color: '#9ca3af', fontSize: '12px', fontWeight: 600 as const, textTransform: 'uppercase' as const, letterSpacing: '0.05em', display: 'block', marginBottom: '6px' }

  return (
    <div style={{ width: '360px', flexShrink: 0, background: '#111', border: '1px solid #222', borderRadius: '10px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>{isNew ? 'New Campaign' : 'Edit Campaign'}</h2>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer', fontSize: '18px' }}>×</button>
      </div>

      <div>
        <label style={labelStyle}>Campaign Name</label>
        <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Summer AC Promo" style={inputStyle} />
      </div>

      <div>
        <label style={labelStyle}>Template</label>
        <select value={selectedTemplate} onChange={e => { setSelectedTemplate(e.target.value); applyTemplate(e.target.value) }} style={{ ...inputStyle, cursor: 'pointer' }}>
          <option value="">Use a template…</option>
          {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
      </div>

      <div>
        <label style={labelStyle}>Message</label>
        <textarea
          value={body}
          onChange={e => setBody(e.target.value)}
          rows={4}
          placeholder="Hi {first_name}, …"
          style={{ ...inputStyle, resize: 'vertical' as const, fontFamily: 'inherit' }}
        />
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '6px' }}>
          {TEMPLATE_VARS.map(v => (
            <button key={v} onClick={() => insertVar(v)} style={{ background: '#1f2937', border: '1px solid #374151', color: '#93c5fd', borderRadius: '12px', padding: '2px 10px', fontSize: '11px', cursor: 'pointer' }}>
              {v}
            </button>
          ))}
        </div>
      </div>

      <AudienceSelector value={segment} onChange={setSegment} />

      <div>
        <label style={labelStyle}>Channel</label>
        <div style={{ display: 'flex', gap: '8px' }}>
          {(['sms', 'email', 'both'] as const).map(ch => (
            <button
              key={ch}
              onClick={() => setChannel(ch)}
              style={{
                flex: 1,
                background: channel === ch ? '#d97706' : '#1a1a1a',
                color: channel === ch ? '#000' : '#9ca3af',
                border: `1px solid ${channel === ch ? '#d97706' : '#333'}`,
                borderRadius: '6px',
                padding: '8px',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: channel === ch ? 600 : 400,
                textTransform: 'capitalize',
              }}
            >
              {ch}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
        <button
          onClick={() => save.mutate()}
          disabled={save.isPending || !name || !body}
          style={{ flex: 1, background: '#1a1a1a', color: '#e5e7eb', border: '1px solid #333', borderRadius: '6px', padding: '10px', cursor: 'pointer', fontSize: '14px' }}
        >
          {save.isPending ? 'Saving…' : 'Save Draft'}
        </button>
        {!isNew && campaign?.status !== 'sent' && (
          <button
            onClick={() => send.mutate()}
            disabled={send.isPending}
            style={{ flex: 1, background: '#d97706', color: '#000', border: 'none', borderRadius: '6px', padding: '10px', cursor: 'pointer', fontWeight: 700, fontSize: '14px' }}
          >
            {send.isPending ? 'Sending…' : 'Send Now'}
          </button>
        )}
      </div>
    </div>
  )
}
