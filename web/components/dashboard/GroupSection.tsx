import type { GroupConfig } from './tiles'
import { FeatureTile } from './FeatureTile'

interface Props {
  group: GroupConfig
}

export function GroupSection({ group }: Props) {
  return (
    <div style={{ marginBottom: 30 }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        fontSize: 10, fontWeight: 700, letterSpacing: '0.09em', textTransform: 'uppercase' as const,
        color: 'rgba(255,255,255,0.36)',
        marginBottom: 12, paddingBottom: 7,
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}>
        <span style={{
          width: 6, height: 6, borderRadius: '50%',
          background: group.accent, flexShrink: 0,
        }} />
        {group.label}
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {group.tiles.map(tile => (
          <FeatureTile key={tile.id} tile={tile} accentColor={group.accent} />
        ))}
      </div>
    </div>
  )
}
