import Link from 'next/link'
import type { TileConfig } from './tiles'

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

const TILE_BASE: React.CSSProperties = {
  width: 108,
  padding: '14px 8px 12px',
  borderRadius: 12,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  gap: 9,
  textAlign: 'center',
  position: 'relative',
  textDecoration: 'none',
}

interface Props {
  tile: TileConfig
  accentColor: string
}

export function FeatureTile({ tile, accentColor }: Props) {
  const Icon = tile.icon

  const iconBgStyle: React.CSSProperties = {
    width: 40, height: 40, borderRadius: 10,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: tile.status === 'live' ? hexToRgba(accentColor, 0.18) : 'rgba(255,255,255,0.05)',
    opacity: tile.status === 'soon' ? 0.35 : 1,
    color: tile.status === 'live' ? accentColor : 'rgba(255,255,255,0.4)',
  }

  const labelStyle: React.CSSProperties = {
    fontSize: 11, fontWeight: 500, lineHeight: 1.3,
    color: tile.status === 'live' ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.32)',
  }

  const badge = tile.status === 'soon' ? (
    <span style={{
      position: 'absolute', top: 8, right: 8,
      fontSize: 8, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase' as const,
      padding: '2px 5px', borderRadius: 4,
      background: 'rgba(255,255,255,0.05)',
      color: 'rgba(255,255,255,0.25)',
      border: '1px solid rgba(255,255,255,0.07)',
    }}>Soon</span>
  ) : null

  if (tile.status === 'soon') {
    return (
      <div style={{ ...TILE_BASE, background: 'rgba(0,0,0,0.20)', border: '1px solid rgba(255,255,255,0.04)', cursor: 'default' }}>
        {badge}
        <div style={iconBgStyle}><Icon /></div>
        <span style={labelStyle}>{tile.label}</span>
      </div>
    )
  }

  return (
    <Link
      href={tile.route!}
      style={{ ...TILE_BASE, background: 'rgba(0,0,0,0.38)', backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)', border: '1px solid rgba(255,255,255,0.10)', transition: 'background 0.15s, border-color 0.15s, transform 0.15s' }}
      onMouseEnter={e => {
        const el = e.currentTarget as HTMLElement
        el.style.background = 'rgba(255,255,255,0.08)'
        el.style.borderColor = 'rgba(255,255,255,0.20)'
        el.style.transform = 'translateY(-1px)'
      }}
      onMouseLeave={e => {
        const el = e.currentTarget as HTMLElement
        el.style.background = 'rgba(0,0,0,0.38)'
        el.style.borderColor = 'rgba(255,255,255,0.10)'
        el.style.transform = 'translateY(0)'
      }}
    >
      <div style={iconBgStyle}><Icon /></div>
      <span style={labelStyle}>{tile.label}</span>
    </Link>
  )
}
