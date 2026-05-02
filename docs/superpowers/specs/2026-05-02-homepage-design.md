# Homepage, Login & Request Demo — Design Spec

**Date:** 2026-05-02  
**Scope:** Public-facing marketing pages (homepage, login, request demo). App theme switch is out of scope — separate project.

---

## 1. Overview

AutoShop currently has no public-facing marketing site. The root route (`/`) renders the logged-in dashboard. This spec covers three new/updated pages:

1. **Homepage** (`/`) — marketing page replacing the dashboard at root
2. **Login** (`/login`) — updated with Google OAuth as primary sign-in method
3. **Request Demo** (`/demo`) — full-page form to request a product demo

The dashboard moves from `/` to `/dashboard`. All other app routes stay unchanged.

---

## 2. Visual Style

**Palette:** Clean light theme — white backgrounds, `#f8fafc` section backgrounds, `#0f172a` dark text.  
**Accent:** `#2563eb` (blue) with `linear-gradient(135deg, #2563eb, #1d4ed8)` for logo and CTAs.  
**Dark sections:** `linear-gradient(160deg, #0f172a, #1e3a5f)` for the "Why AutoShop" band, login left panel, and demo left panel.  
**Typography:** System font stack (`-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif`). Headlines are heavy (font-weight 900), letter-spacing -1px to -2px for large sizes.  
**Reference mockups:** `.superpowers/brainstorm/49676-1777747077/content/`
- `homepage-v2.html` — approved homepage
- `login-page.html` — approved login
- `demo-page.html` — approved demo page

---

## 3. Routing Changes

| Before | After |
|--------|-------|
| `/` → DashboardPage | `/` → new HomepageSection (public) |
| `/login` → LoginPage (email/password only) | `/login` → updated LoginPage (Google + email/password) |
| *(none)* | `/demo` → new DemoPage |
| *(none)* | `/dashboard` → DashboardPage (moved from `/`) |

The existing `AppShell` and all authenticated routes (`/chat`, `/inspect`, `/quotes`, etc.) are unchanged. No auth middleware is added to `/` — the homepage is fully public and does not redirect logged-in users.

---

## 4. Homepage (`/`)

### 4.1 Navigation
- Sticky, white background with `backdrop-filter: blur(12px)`, bottom border `#f1f5f9`
- Left: logo (blue gradient icon + "AutoShop" wordmark)
- Center: "Product" and "Pricing" anchor links (scroll to sections on same page)
- Right: "Sign In" ghost link → `/login`, "Request Demo" blue button → `/demo`

### 4.2 Hero
- Background: `linear-gradient(160deg, #f0f7ff, #ffffff, #f8faff)` with a radial blue glow behind the headline
- Badge: "Now live for independent auto shops" (green dot + pill)
- Headline: `Give your shop <em>AI superpowers</em>` — "AI superpowers" in blue-to-purple gradient text
- Subtext: "Automate inspections, empower technicians, and keep every customer connected — across every shop they visit."
- CTAs: "Request a Demo" (primary blue) → `/demo`, "Sign in →" (ghost outline) → `/login`
- Product preview: browser-chrome mockup showing the dashboard with sidebar, stats cards, and an AI chat snippet

### 4.3 Metrics Band
Full-width dark band (`#0f172a`) immediately below the hero. Four metrics side by side:
- **2×** — Faster inspections
- **40% less admin** — Per technician daily
- **100%** — Repair history coverage
- **$0** — For your customers

### 4.4 Product Section
Eyebrow: "Product". Heading: "Built for every role in your shop."

Four feature cards in a 2×2 grid. Each card has a mini product UI preview at the top and a title + description below.

| Card | Preview | Title | Description summary |
|------|---------|-------|---------------------|
| Owner | Stats grid (revenue, jobs, satisfaction) | Owner Intelligence | Ask any question about your shop via AI agents |
| Technician | AI chat bubbles (complaint → diagnosis) | AI Technician Assistant | AI co-pilot for inspections, repair notes, parts lookup |
| Consumer | Repair history list across shops | Consumer Vehicle History | Complete cross-shop repair timeline |
| Ecosystem | Node diagram (Owner ⇄ Technician ⇄ Consumer) | Connected Ecosystem | Records and updates flow between all parties |

### 4.5 Why AutoShop Section
Dark gradient band. Two cards side by side:
- **01 — Superpower every shop:** Enterprise-grade AI for independent shops; automate quotes, inspections, scheduling.
- **02 — Connect every consumer:** First-ever cross-shop repair history for customers.

### 4.6 Testimonial Section
Light gray background (`#f8fafc`). Centered single quote:
> "AutoShop cut our inspection write-up time in half. My technicians actually enjoy using it — and customers love seeing their full vehicle history in one place."
> — Marcus T., Owner, City Auto Center

*(Placeholder quote — replace with real customer quote once available.)*

### 4.7 Pricing Section
Eyebrow: "Pricing". Heading: "Simple, transparent pricing."

Two-column pricing cards:

**Starter** (featured, blue border):
- $39/month
- 1 shop location
- Up to 5 staff accounts
- AI Technician Assistant
- Owner Intelligence Dashboard
- Consumer vehicle history
- CTA: "Get started" → `/login`

**Enterprise** (no featured styling):
- "Let's talk" (no fixed price)
- Multiple shop locations
- Unlimited staff accounts
- Everything in Starter
- Priority support & onboarding
- Custom integrations (DMS, fleet)
- CTA: "Request a Demo →" → `/demo`

### 4.8 Footer
Dark (`#0f172a`). Three columns: logo left, links center (Privacy, Terms, Contact), copyright right.

---

## 5. Login Page (`/login`)

**Layout:** Two-panel full-viewport. Left panel dark (branding), right panel white (form).

### 5.1 Left Panel
- Background: `linear-gradient(160deg, #0f172a, #1e3a5f)` with bottom-right radial glow
- Logo at top
- Tagline: "Your shop's AI team is waiting."
- Supporting text: sign-in context
- Three stats at bottom: 2× faster inspections, 40% less admin, $0 for customers

### 5.2 Right Panel — Form
1. **"Continue with Google"** button (Google SVG icon, white background, border) — primary option
2. **Divider:** "or sign in with email"
3. Email + Password fields
4. **"Sign in"** blue submit button
5. Footer: "Don't have an account? Contact us" → `/demo`

### 5.3 Google OAuth Flow
- Frontend: Google Identity Services (`accounts.google.com/gsi/client`) renders the sign-in button
- On success, the Google ID token is POSTed to `POST /auth/google`
- Backend creates or finds the user by Google sub/email, returns a JWT access token identical in shape to the existing `/auth/login` response
- Frontend stores `access_token` in `localStorage` and redirects to `/chat` (same as existing email/password flow)

### 5.4 Backend Changes
New endpoint: `POST /auth/google`
- Input: `{ id_token: string }`
- Verifies token with Google's public keys (via `google-auth-library` or equivalent)
- Upserts user record (creates if first sign-in, finds by email if returning)
- Returns `{ access_token: string }` (same JWT shape as `/auth/login`)
- Requires `GOOGLE_CLIENT_ID` env var on the backend

New env vars needed:
- Backend: `GOOGLE_CLIENT_ID`
- Frontend: `NEXT_PUBLIC_GOOGLE_CLIENT_ID`

---

## 6. Request Demo Page (`/demo`)

**Layout:** Two-panel, same structure as login. Left panel dark (context), right panel white (form).

### 6.1 Left Panel
- Eyebrow: "Request a Demo"
- Heading: "See AutoShop in action"
- Subtext: 30-minute walkthrough, no pressure
- "What to expect" bullet list:
  1. Live walkthrough of owner dashboard and AI agents
  2. AI Technician demo — inspection reports generated in seconds
  3. Pricing & onboarding discussion
  4. Open Q&A

### 6.2 Right Panel — Form
Fields:
- First name + Last name (side by side)
- Work email
- Shop name
- Number of locations (dropdown: 1 / 2–5 / 6–20 / 20+)
- Message (optional textarea)
- Submit: "Request Demo →"

### 6.3 Form Submission
On submit, `POST /demo/request` (new backend endpoint):
- Input: `{ first_name, last_name, email, shop_name, locations, message? }`
- Stores the request in a new `demo_requests` DB table
- Returns `{ ok: true }`
- On success: show a confirmation state ("We'll be in touch within 1 business day.")
- No email sending in v1 — manual follow-up by the team

### 6.4 Backend Changes
New endpoint: `POST /demo/request`  
New DB table: `demo_requests` (id, first_name, last_name, email, shop_name, locations, message, created_at)

---

## 7. Out of Scope

- App-wide light theme switch (separate project)
- Email notifications for demo requests (v2)
- Self-serve signup / account creation flow
- Pro and Max pricing tiers (not yet built)

---

## 8. Success Criteria

- `/` renders the marketing homepage (public, no auth required)
- `/dashboard` renders the existing DashboardPage
- `/login` shows Google sign-in button; Google OAuth flow completes and lands on `/chat`
- `/demo` form submits successfully and shows confirmation
- All existing authenticated routes (`/chat`, `/inspect`, etc.) continue to work unchanged
