# AutoShop Web — Dashboard (Home) Page Design
**Date:** 2026-05-01  
**Status:** Approved

---

## Overview

Add a **Home** tab to the AutoShop web app that serves as a feature launchpad. It shows every feature the app supports — current and planned — grouped into six labelled sections. Live features are clickable tiles that navigate to their page; coming-soon features are visible but non-interactive, giving users a clear picture of the product roadmap.

---

## 1. Navigation Change

- Add **Home** as the first nav tab, with a house SVG icon.
- Route: `/` (root, currently redirects to `/customers`) becomes the dashboard page.
- The existing redirect from `/` to `/customers` is removed; `/` renders the dashboard directly.
- Nav order: **Home · Customers · Reports · Inspect · Chat**

---

## 2. Page Layout

The page follows the existing `AppShell` pattern (frosted-glass nav + `AppBackground` photo layer).

```
AppShell
└── /  (DashboardPage)
    └── scrollable content area (padding: 24px 28px 40px)
        ├── page title "Home"
        ├── subtitle "Everything your shop needs, in one place."
        └── 6 × GroupSection
            ├── group header (coloured dot + uppercase label + divider)
            └── tile row (flex-wrap, gap 8px)
                └── N × FeatureTile (live or soon)
```

The content area is `overflow-y: auto` within the fixed-height shell (`calc(100vh - 48px)`).

---

## 3. Feature Groups & Tiles

### 3.1 Customers & Vehicles  *(accent: amber #d97706)*
| Tile | Status | Route |
|---|---|---|
| Customers | **Live** | `/customers` |
| Vehicles | **Live** | `/customers` (vehicles are accessed through customer detail) |
| Appointments | Coming Soon | — |
| Service Reminders | Coming Soon | — |

### 3.2 Shop Work  *(accent: blue #3b82f6)*
| Tile | Status | Route |
|---|---|---|
| Inspect | **Live** | `/inspect` |
| Reports | **Live** | `/reports` |
| Job Cards | Coming Soon | — |
| Time Tracking | Coming Soon | — |

### 3.3 Financials  *(accent: green #22c55e)*
| Tile | Status | Route |
|---|---|---|
| Quotes & Estimates | **Live** | `/reports` (quotes are accessed via report detail) |
| Invoices | Coming Soon | — |
| Payments | Coming Soon | — |
| Accounting | Coming Soon | — |

### 3.4 AI Tools  *(accent: purple #a855f7)*
| Tile | Status | Route |
|---|---|---|
| AI Chat | **Live** | `/chat` |
| OBD Scanner | Coming Soon | — |
| AI Diagnose | Coming Soon | — |
| Labor Guides | Coming Soon | — |

### 3.5 Growth & Marketing  *(accent: red #ef4444)*
| Tile | Status | Route |
|---|---|---|
| Marketing | Coming Soon | — |
| Reviews | Coming Soon | — |
| Leads | Coming Soon | — |
| Financing | Coming Soon | — |

### 3.6 Inventory & Parts  *(accent: cyan #06b6d4)*
| Tile | Status | Route |
|---|---|---|
| Parts Lookup | **Live** | `/chat` (parts lookup is via AI Chat with Tom agent) |
| Inventory | Coming Soon | — |
| Vendors | Coming Soon | — |

---

## 4. Component Specs

### FeatureTile

```
width: 108px
padding: 14px 8px 12px
border-radius: 12px
display: flex flex-col, align-items: center, gap: 9px
```

**Live tile:**
- `background: rgba(0,0,0,0.38)`, `backdrop-filter: blur(20px)`
- `border: 1px solid rgba(255,255,255,0.10)`
- Hover: background lifts to `rgba(255,255,255,0.08)`, border to `rgba(255,255,255,0.20)`, `translateY(-1px)`
- Click: `router.push(route)`

**Coming-soon tile:**
- `background: rgba(0,0,0,0.20)`, `border: 1px solid rgba(255,255,255,0.04)`
- Icon opacity: `0.35`; label color: `rgba(255,255,255,0.32)`
- `cursor: default` — not clickable
- "Soon" badge: top-right corner, `font-size: 8px`, `background: rgba(255,255,255,0.05)`, `color: rgba(255,255,255,0.25)`

### Tile icon

- Size: `40×40px`, `border-radius: 10px`
- Background tinted with the group's accent color at 18% opacity (e.g. amber group: `rgba(217,119,6,0.18)`)
- Coming-soon icons use `rgba(255,255,255,0.05)` (muted)
- Icon glyphs: inline SVG (no emoji in production — use same SVG style as nav icons)

### GroupSection header

- Font: `10px`, weight `700`, `letter-spacing: 0.09em`, `text-transform: uppercase`
- Color: `rgba(255,255,255,0.36)`
- 6px coloured dot (group accent colour) + label text
- Divider: `border-bottom: 1px solid rgba(255,255,255,0.06)`, `padding-bottom: 7px`, `margin-bottom: 12px`

---

## 5. File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `web/app/page.tsx` | Root route — renders `DashboardPage` (replaces redirect) |
| Create | `web/components/dashboard/DashboardPage.tsx` | Page layout: title + 6 `GroupSection` components |
| Create | `web/components/dashboard/GroupSection.tsx` | Section header + tile row |
| Create | `web/components/dashboard/FeatureTile.tsx` | Individual tile (live or coming-soon variant) |
| Create | `web/components/dashboard/tiles.ts` | Static data: group definitions, tile list, routes, status |
| Modify | `web/components/AppShell.tsx` | Add Home nav item (first position) with house SVG icon |

---

## 6. Data Shape (`tiles.ts`)

```typescript
export type TileStatus = 'live' | 'soon'

export interface TileConfig {
  id: string
  label: string
  icon: React.ComponentType   // inline SVG component (same pattern as AppShell nav icons)
  status: TileStatus
  route?: string              // only present when status === 'live'
}

export interface GroupConfig {
  id: string
  label: string
  accent: string              // CSS color string, e.g. '#d97706'
  tiles: TileConfig[]
}

// GROUPS is a const array of 6 GroupConfig objects matching Section 3 exactly.
// Each tile's icon is a local SVG function component (no emoji, no external icon lib).
export const GROUPS: GroupConfig[] = [ /* defined in tiles.ts */ ]
```

All tile and group data lives in `tiles.ts`. No hardcoded content in the React components.

---

## 7. Out of Scope

- Analytics / stats strip (deferred — will need its own design)
- Background video for dashboard page
- Drag-to-reorder tiles
- Admin-configurable tile visibility
