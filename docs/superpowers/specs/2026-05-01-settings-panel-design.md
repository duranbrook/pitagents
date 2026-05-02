# Settings Panel Design

## What We're Building

A slide-in settings panel that opens when the user clicks their avatar in the top-right nav bar. The panel slides in from the right over the current page (no navigation), has a dark overlay behind it, and contains all user and shop configuration in 7 sections organized in a sidebar.

This replaces the existing small `SettingsDropdown` and the standalone `/settings` page (which only had Appearance + Agents tabs).

---

## Architecture

**Frontend:** One new compound component `SettingsPanel` rendered inside `AppShell`. Avatar click toggles `settingsPanelOpen` state. The panel consists of a left sidebar (section nav) and a right content pane. Each section is a standalone React component.

**Backend:** Auth currently uses an in-memory dict for login; this needs to be replaced with DB-backed user lookup so the Account section's password change and profile update can work against real persisted data. Three new auth endpoints required: `GET /auth/me`, `PATCH /auth/profile`, `PATCH /auth/password`.

**The `/settings` route** is removed — all settings live in the panel. The existing `AgentsTab` and `AppearanceTab` components from `web/app/settings/page.tsx` are extracted and reused as `AgentsSection` and `AppearanceSection` in the panel.

---

## Frontend File Structure

### New files
- `web/components/settings/SettingsPanel.tsx` — outer shell: slide-in container, backdrop, sidebar nav, section router
- `web/components/settings/sections/AccountSection.tsx` — display name, email (read-only), change password
- `web/components/settings/sections/ShopProfileSection.tsx` — shop name, address, phone, labor rate
- `web/components/settings/sections/AppearanceSection.tsx` — accent color picker + background theme (migrated from existing AppearanceTab + SettingsDropdown theme picker)
- `web/components/settings/sections/BookingSection.tsx` — online booking toggle, booking link, hours, buffer
- `web/components/settings/sections/NotificationsSection.tsx` — Twilio SMS credentials, SendGrid email credentials
- `web/components/settings/sections/IntegrationsSection.tsx` — Stripe, CarMD, Mitchell1, QuickBooks, Synchrony, Wisetack keys
- `web/components/settings/sections/AgentsSection.tsx` — migrated AgentsTab (full CRUD for shop agents)

### Modified files
- `web/components/AppShell.tsx` — replace `SettingsDropdown` with `SettingsPanel`; toggle panel open/close on avatar click
- `web/lib/api.ts` — add `getMe`, `updateProfile`, `updatePassword`, `getBookingConfig`, `updateBookingConfig`
- `web/lib/types.ts` — add `UserProfile`, `BookingConfig` types
- `web/app/settings/page.tsx` — replaced with a redirect to `/` (or removed entirely)

### Deleted files
- `web/components/SettingsDropdown.tsx` — superseded by SettingsPanel

---

## Panel Visual Design

**Container:** `position: fixed`, `top: 0`, `right: 0`, `bottom: 0`, `width: 420px`. Dark background `rgba(10,10,14,0.98)`, `border-left: 1px solid rgba(255,255,255,0.1)`, `box-shadow: -20px 0 60px rgba(0,0,0,0.6)`.

**Overlay:** `position: fixed, inset: 0`, `background: rgba(0,0,0,0.4)`, `z-index: 49`. Click overlay to close panel.

**Panel z-index:** 50 (above overlay).

**Sidebar:** 140px wide, `border-right: 1px solid rgba(255,255,255,0.07)`. Section labels are small-caps with icon emoji. Active section: `background: rgba(var(--accent-rgb),0.15)`, text in accent color, `font-weight: 600`. Inactive: `color: rgba(255,255,255,0.45)`. Sign out at the bottom, separated by a divider, red-tinted text.

**Content pane:** `flex: 1`, `overflow-y: auto`, `padding: 20px`. Section heading + form fields below.

**Header row:** Section title (left) + `×` close button (right).

**Form fields:** `background: rgba(255,255,255,0.05)`, `border: 1px solid rgba(255,255,255,0.09)`, `border-radius: 6px`, `color: rgba(255,255,255,0.85)`. Labels: `font-size: 10px`, uppercase, `color: rgba(255,255,255,0.3)`. Spacing between field groups: 16px.

**Save buttons:** Accent background, black text, `font-weight: 700`. One per logical group (Profile, Security, etc.).

**Animation:** `transform: translateX(100%)` → `translateX(0)` with `transition: transform 200ms ease-out`. Same direction on close.

---

## Section-by-Section Field Mapping

### Account
- **Profile group:** Display name (text input, PATCH /auth/profile), Email (read-only, from JWT/GET /auth/me)
- **Security group:** Current password, New password, Confirm new password — PATCH /auth/password
- Save Profile button, Change Password button (separate)

### Shop Profile
- Shop name, Address, Phone number, Labor rate ($/hr) — all fields from `ShopSettings` model
- API: `GET /settings/shop`, `PATCH /settings/shop`
- Logo upload: out of scope for this implementation

### Appearance
- Accent color: 6 presets + custom color picker + hex input (reuse existing AppearanceTab logic)
- Background theme: Dark / Moody / Vivid — three buttons (migrate from SettingsDropdown)
- No save button needed — changes apply live via CSS variables

### Booking
- Booking link (read-only display: `slug` field, shown as `<backend-url>/book/<slug>`)
- Working hours: start time, end time (text inputs in HH:MM format → `working_hours_start`, `working_hours_end`)
- Slot duration (minutes, select or number input → `slot_duration_minutes`)
- API: `GET /appointments/my-config`, `PATCH /appointments/my-config` (new authenticated endpoints — see Backend Changes)

### Notifications
- **Twilio:** Account SID, Auth Token, From number
- **SendGrid:** API key
- Service reminder defaults: Oil change interval (miles), Tire rotation interval (miles), Annual service flag
- All stored in `ShopSettings` model — same API as Shop Profile: `GET /settings/shop`, `PATCH /settings/shop`

### Integrations
- **Stripe:** Publishable key, Secret key
- **CarMD:** API key
- **Mitchell1:** Shop key, Zip code
- **QuickBooks:** Realm ID, Access token, Refresh token
- **Synchrony/Wisetack:** Merchant ID
- All stored in `ShopSettings` model — same `GET/PATCH /settings/shop`
- Each integration shown as a collapsible card with a "Connected" / "Not connected" status badge

### Agents & AI
- Full agent CRUD: list, create, edit, delete (migrated from existing AgentsTab)
- Same API: `GET /agents`, `POST /agents`, `PATCH /agents/{id}`, `DELETE /agents/{id}`

---

## Backend Changes

### Switch auth to DB-backed users

`auth.py` currently uses a `_TEST_USERS` in-memory dict. Change login to:
1. `SELECT * FROM users WHERE email = $1`
2. `bcrypt.verify(request.password, user.hashed_password)`
3. Return JWT with same payload as before (`sub`, `shop_id`, `role`, `email`)

Keep the seeded test users `owner@shop.com` / `testpass` working — they already exist in the DB from the seed script.

### New auth endpoints

```
GET  /auth/me
  → returns: { id, email, name, role, shop_id }
  → reads from users table by user_id from JWT

PATCH /auth/profile
  body: { name: string }
  → UPDATE users SET name = $1 WHERE id = $2
  → returns updated user profile

PATCH /auth/password
  body: { current_password: string, new_password: string }
  → verify current_password against hashed_password
  → hash new_password with bcrypt
  → UPDATE users SET hashed_password = $1 WHERE id = $2
  → 400 if current_password is wrong
```

No new DB migrations — the `users` table already has `name` and `hashed_password` columns.

### BookingConfig authenticated endpoints (new)

The existing `/book/{slug}` route is public-only. Need two new owner-facing endpoints on the `/appointments` router:

```
GET  /appointments/my-config
  → SELECT * FROM booking_configs WHERE shop_id = $1 (shop_id from JWT)
  → returns: { slug, working_hours_start, working_hours_end, slot_duration_minutes }

PATCH /appointments/my-config
  body: { working_hours_start?, working_hours_end?, slot_duration_minutes? }
  → UPDATE booking_configs SET ... WHERE shop_id = $1
  → returns updated BookingConfigResponse
  → 404 if no BookingConfig row exists for shop (seed script creates one)
```

These must be registered **before** `/{appt_id}` routes in `appointments.py` to avoid route collision.

---

## Data Flow

1. User opens app → AppShell renders, `settingsPanelOpen = false`
2. User clicks avatar → `settingsPanelOpen = true` → SettingsPanel mounts
3. SettingsPanel defaults to `activeSection = 'account'`
4. AccountSection calls `GET /auth/me` → shows email, name
5. User types new name → clicks "Save Profile" → `PATCH /auth/profile` → success toast
6. User types password fields → clicks "Change Password" → `PATCH /auth/password` → success toast or error
7. User switches to Shop Profile tab → `GET /settings/shop` (cached by TanStack Query) → form populates
8. User saves → `PATCH /settings/shop` → invalidate cache → re-fetch
9. User clicks overlay or `×` → `settingsPanelOpen = false` → panel slides out

---

## Error Handling

- Form validation: required fields highlighted on empty submit attempt
- API errors: inline error message below the relevant button (not a toast) for form errors
- Success: brief green checkmark / "Saved" text that fades after 2s
- Password mismatch (new ≠ confirm): client-side validation, no API call
- Wrong current password: 400 from API → "Current password is incorrect" inline error
- Network errors: generic "Something went wrong — try again" inline

---

## What Is Explicitly Out of Scope

- Profile photo upload (logo/avatar)
- Multi-user management (adding new team members)
- Billing / subscription settings
- Notification delivery history
- OAuth flows for QuickBooks (token management shown, not OAuth initiation)
