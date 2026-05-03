# Homepage Product Section — Three Pillars Redesign
**Date:** 2026-05-02  
**File:** `web/components/home/HomePage.tsx`

---

## What We're Building

Replace the existing 2×2 four-card product section with a two-part **Problem → Solution** layout that leads with audience-specific pain points and resolves each one with the corresponding product pillar. Also align the homepage brand color from blue (`#2563eb`) to orange (`#d97706`) to match the rest of the app.

---

## Problem Section

**Label:** "The Problem" (red, `#dc2626`)  
**Heading:** "Auto shops run on skill. They shouldn't run on software juggling."  
**Subheading:** "Every day, technicians, owners, and car owners lose time and records to tools that weren't built for them — or weren't built to work together."

Three side-by-side scenario cards (equal 3-column grid), each with:
- Audience label (color-coded: amber for tech, blue for owner, green for consumer)
- Bullet list of pain points (2–4 per card, em-dashed)

### Technician pain points
- After every job: 20+ minutes of manual write-ups, repair notes, and part lookups
- Estimates built by hand — every time, from scratch
- Time spent on paperwork is time not spent on cars

### Shop owner pain points
- Running the shop means managing multiple disconnected tools — scheduling, invoicing, parts, payroll
- Every new tool has a learning curve — and you still have to stitch the answers together yourself
- Switching tools means retraining the whole team
- *(note tag below the list):* "PitAgents works as a chat interface — just ask. But if you prefer a traditional dashboard, that's still there."

### Car owner pain points
- Every time you switch shops, your history starts over — the new shop knows nothing
- Buy a used car? You have no idea what the previous owner actually maintained — or skipped
- Even as the current owner, it's easy to forget what's been done and when
- When you sell the car, all your maintenance records disappear with it

---

## Connector

A small orange downward-arrow circle (`#d97706`) sits between the two sections as a visual bridge.

---

## Solution Section

**Label:** "The Solution" (amber, `#d97706`)  
**Heading:** "One tool. Three problems solved."  
**Subheading:** "PitAgents puts an AI on every role — technician, shop owner, and car owner — each one built for exactly the job they need to do."

Three equal-width cards in a 3-column grid. Each card has:

1. **Color-coded banner** — one-sentence bridge from pain to solution
2. **Chat preview** — mini conversation showing the AI in action (2–4 bubbles)
3. **Icon + title + description** below

### Card 1 — AI Technician Assistant (amber)
- Banner: "Handles the write-ups so your technician can stay on the car."
- Preview: technician describes a brake squeal → AI diagnoses and drafts repair note → technician adds a line → AI confirms and marks ready
- Description: "Guides inspections, drafts repair notes, looks up parts, handles paperwork — so techs stay under the hood, not behind a desk."

### Card 2 — Owner AI Crew (blue)
- Banner: "Replace the tool stack with one conversation."
- Preview: crew chips (Service Advisor / Bookkeeper / Manager, Bookkeeper active) → owner asks about revenue → AI returns week-over-week numbers with breakdown
- Description: "A crew of specialists for service, books, and ops. Ask any question in plain language. Dashboard still available when you want it."

### Card 3 — Your Vehicle History (green)
- Banner: "The car's full history — current owner, previous owners, every shop."
- Preview: consumer asks "What's been done on my Civic — including before I bought it?" → AI returns cross-shop, cross-owner timeline with repair names + prices
- Lock note below rows: "🔒 Your view only — shops cannot see each other's records"
- Description: "Every repair, every price, current and previous owners — all in one place. Follows the car forever. Know exactly what's been done, and what hasn't."

---

## Privacy Model

The consumer's history view is **consumer-only**:
- A consumer can see all repairs on their vehicle across all shops, including records from a previous owner
- Shops can **only** see their own records — they have no visibility into records created by other shops
- Pricing is visible to the consumer, not shared cross-shop
- This must be stated explicitly in the UI (lock note in the preview) and reinforced in the card description

---

## Brand Color Update

The homepage currently uses blue (`#2563eb`) as the primary brand color throughout. Update to orange (`#d97706`) to match the app.

Affected elements:
- Section labels ("Product", "Why", "Pricing") → change to `#d97706`
- Nav logo mark background → `#d97706`
- CTA buttons ("Request Demo", "Get Started") → `#d97706`
- Pricing card border + checkmarks → `#d97706`
- Footer logo mark → `#d97706`
- Gradient text in hero H1 → update to amber/orange tones
- Metrics band → keep dark background, change stat color from `#60a5fa` to `#fb923c` (orange-400)

---

## Sections Not Changed

All other homepage sections retain their current **structure and copy**:
- Nav
- Hero
- Metrics band
- Why AutoShop (dark section)
- Testimonial
- Pricing
- Footer

The product section (currently lines 171–265 in `HomePage.tsx`) is the only section replaced wholesale. Brand color elements within all sections are updated in-place (color values only — no structural changes).

---

## Implementation Notes

- The existing 2×2 `<div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr' }}` block at the product section is deleted entirely and replaced with the two-section layout described above
- All inline styles (no CSS modules or Tailwind in this file — match the existing pattern)
- The `id="product"` anchor stays on the outer section wrapper so the nav link still works
- No new dependencies required
