'use client'

import { AppShell } from '@/components/AppShell'
import { GroupSection } from './GroupSection'
import { GROUPS } from './tiles'

export function DashboardPage() {
  return (
    <AppShell>
      <div style={{
        height: '100%',
        overflowY: 'auto',
        padding: '24px 28px 40px',
      }}>
        <h1 style={{
          fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em',
          color: 'rgba(255,255,255,0.92)', marginBottom: 4,
        }}>
          Home
        </h1>
        <p style={{
          fontSize: 13, color: 'rgba(255,255,255,0.40)', marginBottom: 28,
        }}>
          Everything your shop needs, in one place.
        </p>

        {GROUPS.map(group => (
          <GroupSection key={group.id} group={group} />
        ))}
      </div>
    </AppShell>
  )
}
