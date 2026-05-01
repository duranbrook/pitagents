'use client'
import { useState } from 'react'
import { CampaignList } from '@/components/marketing/CampaignList'
import { ComposePanel } from '@/components/marketing/ComposePanel'
import type { Campaign } from '@/lib/types'

export default function MarketingPage() {
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null)
  const [composing, setComposing] = useState(false)

  const handleNew = () => {
    setSelectedCampaign(null)
    setComposing(true)
  }

  const handleSelect = (c: Campaign) => {
    setSelectedCampaign(c)
    setComposing(true)
  }

  const handleClose = () => {
    setComposing(false)
    setSelectedCampaign(null)
  }

  return (
    <div style={{ background: '#0d0d0d', minHeight: '100vh', padding: '32px', color: '#fff', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#f9fafb', marginBottom: '4px' }}>Marketing</h1>
      <p style={{ color: '#6b7280', fontSize: '14px', marginBottom: '24px' }}>SMS & email campaigns for your customers</p>

      <div style={{ display: 'flex', gap: '32px', alignItems: 'flex-start' }}>
        <CampaignList
          selectedId={selectedCampaign?.campaign_id ?? null}
          onSelect={handleSelect}
          onNew={handleNew}
        />
        {composing && (
          <ComposePanel
            campaign={selectedCampaign}
            onClose={handleClose}
          />
        )}
      </div>
    </div>
  )
}
