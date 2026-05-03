# Homepage Three Pillars Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing 2×2 four-card product section on the homepage with a two-part Problem → Solution layout, and update the brand color from blue (`#2563eb`) to orange (`#d97706`) throughout.

**Architecture:** Single-file edit to `web/components/home/HomePage.tsx`. No new files, no new dependencies, no backend changes. All styles are inline (existing pattern). The product section (lines 171–265) is replaced wholesale; all other sections keep their structure and only have color values updated.

**Tech Stack:** Next.js, React, inline styles (TypeScript)

---

## File Map

| File | Change |
|------|--------|
| `web/components/home/HomePage.tsx` | Brand color swap + product section replacement |

---

### Task 1: Update brand color — blue → orange

Replace all blue color values throughout `web/components/home/HomePage.tsx`.

**Files:**
- Modify: `web/components/home/HomePage.tsx`

- [ ] **Step 1: Apply the following replacements in `web/components/home/HomePage.tsx`**

These are exact string replacements — apply each one in order. Use Edit tool with `replace_all: true` where possible.

| Old value | New value | Notes |
|-----------|-----------|-------|
| `linear-gradient(135deg, #2563eb, #1d4ed8)` | `linear-gradient(135deg, #d97706, #b45309)` | Nav + footer logo mark |
| `linear-gradient(135deg,#2563eb,#1d4ed8)` | `linear-gradient(135deg,#d97706,#b45309)` | Footer logo (no spaces) |
| `linear-gradient(135deg, #2563eb, #7c3aed)` | `linear-gradient(135deg, #d97706, #f59e0b)` | Hero H1 gradient text |
| `linear-gradient(135deg,#2563eb,#7c3aed)` | `linear-gradient(135deg,#d97706,#f59e0b)` | Testimonial avatar (no spaces) |
| `rgba(37,99,235,0.08)` | `rgba(217,119,6,0.08)` | Hero radial glow |
| `rgba(37,99,235,0.35)` | `rgba(217,119,6,0.35)` | Hero CTA shadow |
| `rgba(37,99,235,0.3)` | `rgba(217,119,6,0.3)` | Nav demo btn shadow + Get Started shadow |
| `rgba(37,99,235,0.25)` | `rgba(217,119,6,0.25)` | Nav demo btn shadow (small) |
| `rgba(37,99,235,0.1)` | `rgba(217,119,6,0.1)` | Pricing card glow |
| `background: '#2563eb'` | `background: '#d97706'` | All orange CTA buttons |
| `color: '#2563eb'` | `color: '#d97706'` | All orange text labels |
| `border: '2px solid #2563eb'` | `border: '2px solid #d97706'` | Pricing card border |
| `color: '#60a5fa'` | `color: '#fb923c'` | Metrics band stat values |
| `color: '#3b82f6'` | `color: '#f59e0b'` | Why section numbered labels |
| `background: '#eff6ff', color: '#2563eb'` | `background: '#fff7ed', color: '#d97706'` | Pricing Starter badge |
| `color: '#1d4ed8'` | `color: '#b45309'` | Dark blue text (hero sidebar active dot) |

After applying all replacements:

- [ ] **Step 2: Verify no blue values remain**

```bash
grep -n "#2563eb\|#1d4ed8\|#7c3aed\|#60a5fa\|#3b82f6\|rgba(37,99,235" web/components/home/HomePage.tsx
```

Expected: no output (zero matches).

- [ ] **Step 3: Start dev server and visually check color**

```bash
cd web && npm run dev
```

Open `http://localhost:3000`. Confirm:
- Nav logo mark is orange, not blue
- "Request Demo" button is orange
- Hero H1 gradient text is amber/orange
- Pricing section "Starter" label and border are orange
- Metrics band stat numbers are orange-ish

- [ ] **Step 4: Commit**

```bash
git add web/components/home/HomePage.tsx
git commit -m "feat(home): update brand color from blue to orange"
```

---

### Task 2: Replace product section with Problem section

Delete the existing 2×2 product section and replace it with the Problem section (three scenario cards).

**Files:**
- Modify: `web/components/home/HomePage.tsx` (lines 171–265, the `{/* PRODUCT SECTION */}` block)

- [ ] **Step 1: Delete the existing product section block**

In `web/components/home/HomePage.tsx`, find and delete the entire block from:
```
      {/* PRODUCT SECTION */}
      <section id="product" style={{ padding: '96px 64px', background: '#fff' }}>
```
through the closing `</section>` at the end of the 2×2 grid (around line 265). Replace it with the code in Step 2.

- [ ] **Step 2: Insert the Problem section in its place**

```tsx
      {/* PROBLEM SECTION */}
      <section id="product" style={{ padding: '80px 64px', background: '#fff', borderBottom: '1px solid #e2e8f0' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, color: '#dc2626', textTransform: 'uppercase', marginBottom: 12 }}>The Problem</div>
          <h2 style={{ fontSize: 40, fontWeight: 900, color: '#0f172a', letterSpacing: -1, lineHeight: 1.15, marginBottom: 14 }}>
            Auto shops run on skill.<br />They shouldn&apos;t run on software juggling.
          </h2>
          <p style={{ fontSize: 15, color: '#64748b', maxWidth: 560, lineHeight: 1.65, marginBottom: 52 }}>
            Every day, technicians, owners, and car owners lose time and records to tools that weren&apos;t built for them — or weren&apos;t built to work together.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 20, alignItems: 'start' }}>

            {/* Technician */}
            <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, padding: 24 }}>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase' as const, color: '#d97706', marginBottom: 14 }}>🔧 The Technician</div>
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 10 }}>
                {[
                  'After every job: 20+ minutes of manual write-ups, repair notes, and part lookups',
                  'Estimates built by hand — every time, from scratch',
                  'Time spent on paperwork is time not spent on cars',
                ].map(point => (
                  <li key={point} style={{ fontSize: 13, color: '#374151', lineHeight: 1.55, display: 'flex', gap: 10 }}>
                    <span style={{ color: '#cbd5e1', flexShrink: 0 }}>—</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Owner */}
            <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, padding: 24 }}>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase' as const, color: '#2563eb', marginBottom: 14 }}>👥 The Shop Owner</div>
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 10 }}>
                {[
                  'Running the shop means managing multiple disconnected tools — scheduling, invoicing, parts, payroll',
                  'Every new tool has a learning curve — and you still have to stitch the answers together yourself',
                  'Switching tools means retraining the whole team',
                ].map(point => (
                  <li key={point} style={{ fontSize: 13, color: '#374151', lineHeight: 1.55, display: 'flex', gap: 10 }}>
                    <span style={{ color: '#cbd5e1', flexShrink: 0 }}>—</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
              <div style={{ marginTop: 16, fontSize: 12, color: '#6b7280', background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 8, padding: '10px 12px', lineHeight: 1.55 }}>
                PitAgents works as a chat interface — just ask. But if you prefer a traditional dashboard, that&apos;s still there.
              </div>
            </div>

            {/* Car owner */}
            <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, padding: 24 }}>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase' as const, color: '#16a34a', marginBottom: 14 }}>🚗 The Car Owner</div>
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 10 }}>
                {[
                  'Every time you switch shops, your history starts over — the new shop knows nothing',
                  'Buy a used car? You have no idea what the previous owner actually maintained — or skipped',
                  'Even as the current owner, it\'s easy to forget what\'s been done and when',
                  'When you sell the car, all your maintenance records disappear with it',
                ].map(point => (
                  <li key={point} style={{ fontSize: 13, color: '#374151', lineHeight: 1.55, display: 'flex', gap: 10 }}>
                    <span style={{ color: '#cbd5e1', flexShrink: 0 }}>—</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>

          </div>
        </div>
      </section>

      {/* CONNECTOR */}
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '20px 0', background: '#f8fafc' }}>
        <div style={{ width: 34, height: 34, borderRadius: '50%', background: '#d97706', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 16, fontWeight: 700 }}>↓</div>
      </div>
```

- [ ] **Step 3: Verify it compiles**

```bash
cd web && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Check visually in browser**

With the dev server still running, open `http://localhost:3000`. Scroll to the product section. Confirm:
- Three cards side by side (Technician / Owner / Car Owner)
- Bullet lists with em-dash prefix
- Owner card has the gray note tag at the bottom
- Orange arrow connector below the section

- [ ] **Step 5: Commit**

```bash
git add web/components/home/HomePage.tsx
git commit -m "feat(home): add problem section with three audience pain points"
```

---

### Task 3: Add Solution section with three pillar cards

Insert the Solution section immediately after the connector (right after what was inserted in Task 2).

**Files:**
- Modify: `web/components/home/HomePage.tsx`

- [ ] **Step 1: Insert the Solution section after the connector block from Task 2**

Find the `{/* CONNECTOR */}` closing `</div>` you added in Task 2 and insert this block immediately after it:

```tsx
      {/* SOLUTION SECTION */}
      <section style={{ padding: '80px 64px', background: '#f8fafc' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, color: '#d97706', textTransform: 'uppercase', marginBottom: 12 }}>The Solution</div>
          <h2 style={{ fontSize: 40, fontWeight: 900, color: '#0f172a', letterSpacing: -1, lineHeight: 1.15, marginBottom: 14 }}>
            One tool. Three problems solved.
          </h2>
          <p style={{ fontSize: 15, color: '#64748b', maxWidth: 560, lineHeight: 1.65, marginBottom: 52 }}>
            PitAgents puts an AI on every role — technician, shop owner, and car owner — each one built for exactly the job they need to do.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 20 }}>

            {/* Pillar 1 — AI Technician */}
            <div style={{ border: '1px solid #e2e8f0', borderRadius: 16, overflow: 'hidden', background: '#fff', display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '10px 16px', fontSize: 11, fontWeight: 600, lineHeight: 1.5, background: '#fff7ed', color: '#92400e', borderBottom: '1px solid #fed7aa' }}>
                Handles the write-ups so your technician can stay on the car.
              </div>
              <div style={{ padding: '14px 16px', background: '#f8fafc', borderBottom: '1px solid #f1f5f9', minHeight: 160, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', gap: 6 }}>
                <div style={{ fontSize: 10, padding: '6px 10px', borderRadius: 8, background: '#fff7ed', color: '#92400e', alignSelf: 'flex-end', maxWidth: '92%', lineHeight: 1.45 }}>Brakes squeal at low speed — 2021 Camry</div>
                <div style={{ fontSize: 10, padding: '6px 10px', borderRadius: 8, background: '#fff', border: '1px solid #fed7aa', color: '#0f172a', maxWidth: '92%', lineHeight: 1.45 }}>Likely glazed pads. Under 3mm → recommend replacement. Drafting repair note now.</div>
                <div style={{ fontSize: 10, padding: '6px 10px', borderRadius: 8, background: '#fff7ed', color: '#92400e', alignSelf: 'flex-end', maxWidth: '92%', lineHeight: 1.45 }}>Add a rotor inspection line</div>
                <div style={{ fontSize: 10, padding: '6px 10px', borderRadius: 8, background: '#fff', border: '1px solid #fed7aa', color: '#0f172a', maxWidth: '92%', lineHeight: 1.45 }}>Done. Ready to send to the customer.</div>
              </div>
              <div style={{ padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <div style={{ width: 28, height: 28, borderRadius: 7, background: '#fff7ed', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, flexShrink: 0 }}>🔧</div>
                  <div style={{ fontSize: 13, fontWeight: 800, color: '#0f172a' }}>AI Technician Assistant</div>
                </div>
                <p style={{ fontSize: 12, color: '#64748b', lineHeight: 1.6 }}>Guides inspections, drafts repair notes, looks up parts, handles paperwork — so techs stay under the hood, not behind a desk.</p>
              </div>
            </div>

            {/* Pillar 2 — Owner AI Crew */}
            <div style={{ border: '1px solid #e2e8f0', borderRadius: 16, overflow: 'hidden', background: '#fff', display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '10px 16px', fontSize: 11, fontWeight: 600, lineHeight: 1.5, background: '#eff6ff', color: '#1e3a5f', borderBottom: '1px solid #bfdbfe' }}>
                Replace the tool stack with one conversation.
              </div>
              <div style={{ padding: '14px 16px', background: '#f8fafc', borderBottom: '1px solid #f1f5f9', minHeight: 160, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', gap: 6 }}>
                <div style={{ display: 'flex', gap: 5, marginBottom: 2 }}>
                  {['Service Advisor', 'Bookkeeper', 'Manager'].map(name => (
                    <span key={name} style={{
                      fontSize: 8, fontWeight: 700, padding: '3px 8px', borderRadius: 99,
                      ...(name === 'Bookkeeper'
                        ? { background: '#1d4ed8', color: '#fff' }
                        : { background: '#f1f5f9', color: '#64748b', border: '1px solid #e2e8f0' }),
                    }}>{name}</span>
                  ))}
                </div>
                <div style={{ fontSize: 10, padding: '6px 10px', borderRadius: 8, background: '#eff6ff', color: '#1d4ed8', alignSelf: 'flex-end', maxWidth: '92%', lineHeight: 1.45 }}>Revenue this week vs last?</div>
                <div style={{ fontSize: 10, padding: '6px 10px', borderRadius: 8, background: '#fff', border: '1px solid #bfdbfe', color: '#0f172a', maxWidth: '92%', lineHeight: 1.45 }}>$18,400 across 34 jobs — up 22% vs last week&apos;s $15,080. Brake jobs drove most of the gain.</div>
              </div>
              <div style={{ padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <div style={{ width: 28, height: 28, borderRadius: 7, background: '#eff6ff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, flexShrink: 0 }}>👥</div>
                  <div style={{ fontSize: 13, fontWeight: 800, color: '#0f172a' }}>Owner AI Crew</div>
                </div>
                <p style={{ fontSize: 12, color: '#64748b', lineHeight: 1.6 }}>A crew of specialists for service, books, and ops. Ask any question in plain language. Dashboard still available when you want it.</p>
              </div>
            </div>

            {/* Pillar 3 — Vehicle History */}
            <div style={{ border: '1px solid #e2e8f0', borderRadius: 16, overflow: 'hidden', background: '#fff', display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '10px 16px', fontSize: 11, fontWeight: 600, lineHeight: 1.5, background: '#f0fdf4', color: '#14532d', borderBottom: '1px solid #bbf7d0' }}>
                The car&apos;s full history — current owner, previous owners, every shop.
              </div>
              <div style={{ padding: '14px 16px', background: '#f8fafc', borderBottom: '1px solid #f1f5f9', minHeight: 160, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', gap: 6 }}>
                <div style={{ fontSize: 10, padding: '6px 10px', borderRadius: 8, background: '#f0fdf4', color: '#166534', alignSelf: 'flex-end', maxWidth: '92%', lineHeight: 1.45 }}>What&apos;s been done on my Civic — including before I bought it?</div>
                <div style={{ fontSize: 10, padding: '6px 10px', borderRadius: 8, background: '#fff', border: '1px solid #bbf7d0', color: '#0f172a', maxWidth: '92%', lineHeight: 1.45 }}>Full history across all owners and 3 shops:</div>
                {[
                  { label: 'City Auto — Brake replacement', date: 'Mar 2026', price: '$480', muted: false },
                  { label: 'Previous owner — Oil change', date: 'Jun 2024', price: '$65', muted: true },
                ].map(row => (
                  <div key={row.label} style={{ fontSize: 9, padding: '5px 8px', borderRadius: 6, background: '#fff', border: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 600, color: row.muted ? '#94a3b8' : '#0f172a' }}>{row.label}</span>
                    <span style={{ display: 'flex', gap: 6 }}>
                      <span style={{ color: '#94a3b8' }}>{row.date}</span>
                      <span style={{ color: '#166534', fontWeight: 700 }}>{row.price}</span>
                    </span>
                  </div>
                ))}
                <div style={{ fontSize: 8, color: '#94a3b8', padding: '2px 4px' }}>🔒 Your view only — shops cannot see each other&apos;s records</div>
              </div>
              <div style={{ padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <div style={{ width: 28, height: 28, borderRadius: 7, background: '#f0fdf4', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, flexShrink: 0 }}>🚗</div>
                  <div style={{ fontSize: 13, fontWeight: 800, color: '#0f172a' }}>Your Vehicle History</div>
                </div>
                <p style={{ fontSize: 12, color: '#64748b', lineHeight: 1.6 }}>Every repair, every price, current and previous owners — all in one place. Follows the car forever. Know exactly what&apos;s been done, and what hasn&apos;t.</p>
              </div>
            </div>

          </div>
        </div>
      </section>
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd web && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Visual check in browser**

Open `http://localhost:3000` and scroll past the Problem section. Confirm:
- Orange arrow connector between Problem and Solution
- "The Solution" label in orange
- Three equal cards with colored banners at top
- Technician card: amber colors, 4-message chat preview
- Owner card: blue colors, crew chips (Bookkeeper highlighted blue), revenue answer
- Vehicle History card: green colors, history rows with prices, grayed-out "Previous owner" row, lock note at bottom

- [ ] **Step 4: Commit**

```bash
git add web/components/home/HomePage.tsx
git commit -m "feat(home): add solution section with three pillar cards"
```

---

### Task 4: Final review and cleanup

- [ ] **Step 1: Full page scroll-through**

Open `http://localhost:3000`. Scroll through the entire homepage top to bottom and verify:
- [ ] Nav: orange logo mark, orange "Request Demo" button
- [ ] Hero: orange gradient on "AI superpowers", orange CTA buttons
- [ ] Metrics band: orange-tinted stat numbers
- [ ] Problem section: 3 cards, colored audience labels, bullet lists, note tag on Owner card
- [ ] Orange connector arrow between sections
- [ ] Solution section: 3 pillar cards, banners, chat previews, correct colors per pillar
- [ ] Why AutoShop: section numbers in amber
- [ ] Testimonial: avatar circle in orange gradient
- [ ] Pricing: orange Starter badge, orange border, orange checkmarks, orange "Let's talk"
- [ ] Footer: orange logo mark

- [ ] **Step 2: Check mobile layout at 375px**

In browser DevTools, switch to mobile view (375px width). Verify:
- Problem cards stack vertically (grid falls to single column at narrow widths — note: this file uses inline styles so no responsive breakpoints exist; document any overflow issues)
- Solution cards stack vertically similarly
- No horizontal scroll on the page

If you see overflow issues, add `overflowX: 'hidden'` to the section wrappers and note it in the commit message.

- [ ] **Step 3: Final commit if any cleanup**

```bash
git add web/components/home/HomePage.tsx
git commit -m "chore(home): final review cleanup"
```

---

## Self-Review Checklist (pre-execution)

| Spec requirement | Task |
|-----------------|------|
| Replace 2×2 product section | Task 2 (delete) + Task 3 (insert) |
| Problem section with 3 scenario cards | Task 2 |
| Technician: 3 pain points | Task 2 |
| Owner: 3 pain points + note tag | Task 2 |
| Consumer: 4 pain points | Task 2 |
| Orange connector arrow | Task 2 |
| Solution section heading + subhead | Task 3 |
| 3 pillar cards with banner + chat preview + info | Task 3 |
| Previous-owner row in Vehicle History preview | Task 3 |
| Lock note in Vehicle History card | Task 3 |
| Privacy model stated in card description | Task 3 |
| `id="product"` anchor preserved | Task 2 (kept on new section) |
| Brand color blue → orange throughout | Task 1 |
| No new dependencies | All tasks |
| Inline styles pattern maintained | All tasks |
