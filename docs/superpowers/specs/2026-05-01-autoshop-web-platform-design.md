# AutoShop Web Platform — Full Feature Design

> **For agentic workers:** Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement features from the corresponding plan files.

**Goal:** Design and implement the full AutoShop web platform — a shop management system for independent auto repair shops, covering job lifecycle, financials, customers, inventory, and growth tools.

**Stack:** Next.js 16 + React 19 + TypeScript + Tailwind (or inline styles per current convention). Backend: FastAPI on Railway. Auth: existing token flow via `KeychainStore`.

---

## Navigation Model

**Dashboard-centric.** The main nav stays lean (max 5–8 items). Features are accessed from Dashboard tiles and can be pinned to the main nav by the shop owner. Each feature is its own dedicated page — no tab-switching between features within a shared nav bar.

Current nav items: Home, Customers, Reports, Inspect, Chat.

New features are added as Dashboard tiles first. Shops can pin up to 8 items to the main nav.

---

## Feature 1 — Job Cards

**The backbone of the shop.** Every service visit lives on a job card.

### Views
- **Kanban** (default) and **List** — toggled in the page header.
- View preference persists per user.

### Kanban columns
Default: `Drop-Off → Diagnosis → In Service → Ready for Pickup`
- Columns are fully configurable: rename, reorder (drag handles), add, delete.
- Configuration stored in shop settings. Minimum 2 columns.

### Card contents
- Customer name + vehicle (year/make/model/VIN)
- Assigned technician(s)
- Services requested (line items)
- Parts list (pulled from Inventory)
- Labor time per line item (auto-filled from Mitchell1 ProDemand if shop has M1 subscription; manual fallback)
- Status + column
- Links to Invoice, Estimate
- Notes / attachments

### Creation paths
1. **Manual** — shop staff creates directly.
2. **Auto from voice inspection** — existing inspection flow auto-populates a job card on completion.
3. **From Appointment** — one-click conversion on the appointment's drop-off day.

### Labor time lookup (Mitchell1 ProDemand)
- When a tech adds a service line item and a vehicle is selected, AutoShop queries the ProDemand API for standard labor hours.
- Auto-fills the labor field; tech can override.
- Requires shop to have active M1 subscription configured in Settings → Integrations.
- If not configured: labor time field is manual entry only.

### Inventory integration
- Parts added to a job card decrement inventory stock immediately (auto-decrement).
- If a part is below reorder threshold, a warning surfaces inline.

---

## Feature 2 — Invoices

**Auto-generated from job cards.**

- Invoice is created from a completed job card — parts and labor auto-populate.
- Branded with shop logo/name (configured in Shop Settings).
- Shareable via SMS link or email.
- PDF export.

### Payment link
- "Send payment link" generates a Stripe-hosted checkout URL texted to the customer.
- Invoice status updates automatically when Stripe confirms payment.

### Financing button
- "Offer financing" button on unpaid invoices above a configurable threshold (default $500).
- Opens a modal where the shop selects their configured financing provider.
- Generates a financing application link sent to the customer via SMS.
- Supported providers (Phase 1): **Synchrony Car Care**, **Wisetack**.
- Later: Affirm, Koalafi.
- Shop configures provider credentials once in Settings → Integrations.

---

## Feature 3 — Appointments

### Shop-side view
- Calendar with Month / Week / Day toggle.
- Color-coded by status: Confirmed (green), Pending (yellow), Blocked/unavailable (gray).
- Day sidebar shows appointment cards with a "→ Job Card" one-click conversion button.

### Customer booking
- Shop has a shareable booking URL (e.g., `autoshop.app/book/[shop-slug]`).
- 3-step flow: service selection → time slot → confirm.
- Confirmation SMS sent automatically.
- Shop configures available services, working hours, and slot duration in Settings.

### Booking widget
- **Shared link only** (Phase 1) — no embeddable widget.

### Appointment → Job Card
- On the appointment's drop-off date, a "→ Job Card" button appears on the calendar card.
- One click creates a pre-filled job card with customer, vehicle, and requested service.

---

## Feature 4 — Service Reminders

**Automated re-engagement.** Runs as a monthly background job.

### Trigger logic
- Window-based, not fixed dates: each service type has a start and end range (e.g., Oil Change: remind between 3–6 months after last service).
- Once a customer enters their service window, send a reminder every 30 days until they book or exit the window.
- Stops automatically when a job card closes for that service.

### Hard stop
- 12 months with no visit or booking → customer marked inactive. Stops all reminders.
- Reactivated manually when they return.

### Mileage enrichment
1. **Primary:** odometer reading captured from job card close (pulled from VIN/odometer scan).
2. **Fallback:** Carfax/CarMax history API for estimated mileage.
3. **Last resort:** time-only triggering.

### Channels
- SMS + email (both configurable toggles per shop).
- Message template configurable per service type. Variables: `{first_name}`, `{vehicle}`, `{service}`, `{booking_link}`.

### Service windows (defaults, all configurable)
| Service | Window |
|---------|--------|
| Oil Change | 3–6 months |
| Tire Rotation | 6–12 months |
| Full Service | 10–14 months |
| AC Check | 10–14 months (May/Jun priority) |

---

## Feature 5 — Time Tracking

**Clock employees in/out per job card task.**

### Live clock card
- Top of the page: green banner showing everyone currently clocked in, job card they're on, running timer, Stop button.

### Employee sidebar
- Lists all employees with hours this week and a green dot if currently clocked in.
- Click an employee to filter the time log to their entries.

### Time log
- Grouped by day.
- Columns: Employee, Job Card, Task Type, Start, End, Duration, QB Sync status.
- Task types: **Repair**, **Diagnosis**, **Admin**.
- Repair and Diagnosis time auto-populates labor on the job card's invoice.
- Admin time tracked for payroll, not billed.

### Clock-in method
- Web app (job card page or Time Tracking page) — Phase 1.
- Mobile (Android/iOS) — Phase 2.

### Export
- CSV export filtered by employee and date range.

---

## Feature 6 — Payments

**Tracks payment status across all invoices.**

### Summary cards
- Outstanding total, Overdue amount, Collected this month, Avg days to pay.

### Payment table
- Default filter: Unpaid.
- Columns: Customer, Invoice, Amount, Due Date, Payment Method, Status.
- Statuses: Overdue, Pending, Partial, Paid.

### Partial payments
- Supported. Multiple payment events per invoice.
- Remaining balance tracked and surfaced on the invoice.

### Payment methods
- Stripe (online link)
- Card in shop
- Cash
- Check

### Chase flow
- "Chase" action sends SMS + Stripe payment link to customer.
- Auto-stops when Stripe confirms payment received.

### Right panel
- Quick "Record Payment" form (select invoice, amount, method, date).
- Monthly breakdown by payment method (bar chart).

---

## Feature 7 — Inventory

**Real-time parts and tire stock.**

### Parts table
- Columns: Part name, SKU, Category, Stock (mini bar + number), Reorder At, Cost, Sell Price, Margin %.
- Stock colors: green (above reorder), yellow (at/below reorder), red (zero).
- Sortable columns: Stock, Cost, Sell, Margin.

### Filtering
- Search (part name, SKU, brand).
- Multi-select dropdowns: **Category**, **Stock Status**, **Vendor**.
- "More filters" button for: sell price range, margin bracket, last ordered date.
- Active filters shown as dismissible pills below the filter bar.

### Categories
Oils, Brakes, Tires, Filters, Electrical, Misc. Shop can add custom categories.

### Reorder queue
- Parts at or below reorder threshold surface in a right-panel queue.
- "Order" button opens PartsTech pre-filled with the part SKU.
- Received parts update stock automatically.

### Stock deduction
- Automatic: stock decrements when a part is added to a job card.
- Manual adjustment available for corrections, waste, returns.

### PartsTech integration
- Orders placed via PartsTech. Received parts update inventory automatically.

---

## Feature 8 — Accounting

**Financial overview: expenses, purchase orders, P&L.**

### P&L summary cards
- Revenue (from invoices), Expenses, Net Profit, Outstanding A/R.
- Period selector: MTD, QTD, YTD, 1M, custom.

### Tabs
1. **Expenses** — all shop expenses logged by date, category, vendor. QB sync status per row.
2. **Purchase Orders** — orders placed with vendors, status (Pending/Ordered/Received).
3. **P&L Report** — full income vs. expense breakdown.

### Expense categories
Parts, Labor, Utilities, Equipment, Misc.

### QuickBooks integration
- **Push only** (one-way). AutoShop → QB.
- Invoices and expenses are pushed to QuickBooks.
- Sync status shown per row (Synced / Not synced).
- Manual "Sync now" button.
- QB does not push back to AutoShop — accountant's QB-native operations (journal entries, reconciliation, depreciation) are out of scope.

---

## Feature 9 — Vendors

**Supplier directory + purchase order history.**

### Vendor list (left panel)
- Card per vendor: name, type, phone number, YTD spend, order count, last order date.
- Categories: Parts, Equipment, Utilities, Services.
- PartsTech-sourced vendors auto-appear when first ordered from.
- Manual vendors added by shop staff.

### Vendor detail (right panel)
Full contact profile:
- Phone, Email, Website, Address, Rep/Contact name + direct phone, Account number.

Order history:
- Purchase orders table: PO number, items, date, total, status (Pending/Ordered/Received).
- "Mark received" updates inventory stock.
- "+ New Order" creates a new PO for that vendor.

---

## Feature 10 — Diagnose

**Vehicle diagnostic lookup powered by CarMD API.** No AI/LLM layer in Phase 1.

### Input bar
- Vehicle selector (pre-filled from job card context, or manually selected).
- DTC code input (manual entry or "Read OBD" if OBD dongle connected — Phase 2).
- "Analyze" button triggers API lookup.

### Active DTCs
- Displayed as dismissible pills below the input bar.

### Recall banner
- If the vehicle has an open NHTSA safety recall, a prominent red banner appears above the tabs. Always visible regardless of active tab.

### Result tabs
1. **Diagnosis** — ranked probable causes with probability %, layman description, and technical detail. Source: CarMD Diagnosis API.
2. **Repair Plan** — ranked repair options with labor time, confidence level. Source: CarMD Repair Report API.
3. **TSB** — Technical Service Bulletins for this vehicle, categorized. Source: CarMD TSB API.
4. **Recalls** — full recall list with NHTSA reference numbers. Source: CarMD Safety Recalls API.
5. **Maintenance** — upcoming maintenance due within ±10,000 miles of current odometer. Source: CarMD Maintenance API.

### Right action panel
- **Parts needed** — parts identified from the repair plan, checked against inventory (in stock / low / out of stock). One-click add to job card.
- **Labor estimate** — standard hours from CarMD Repair Report.
- **Add to job card** — pushes diagnosis findings (causes, repair plan, parts) into the linked job card.
- **Send summary to customer** — generates a plain-English summary SMS for the customer.

### VIN Decode
- Runs silently when a job card is created. No separate UI.

---

## Feature 11 — Labor Guides (embedded)

**Not a standalone page.** Embedded in Job Card line items.

When a tech adds a service line item to a job card:
1. AutoShop queries Mitchell1 ProDemand API with vehicle (year/make/model/engine) + service type.
2. Standard labor hours auto-fill the labor time field.
3. Tech can override.

**Requires:** active Mitchell1 subscription. Shop enters M1 credentials in Settings → Integrations. If not configured, labor time is manual entry only.

---

## Feature 12 — Marketing

**SMS + email campaign manager.**

### Campaign states
Draft → Scheduled → Active → Sent.

### Audience segments
Built automatically from job card data:
- By service history (e.g., "had AC service")
- By last visit window (e.g., "no visit in 9–12 months")
- By vehicle type
- All customers

Segment counts update live as filters are selected.

### Compose panel
- Campaign name, message body (with template variables: `{first_name}`, `{vehicle}`), audience filter checkboxes, channel toggles (SMS / Email), send time (immediate or scheduled).

### Stats per campaign
Sent, Opened, Booked (linked appointments), Revenue attributed.

### Templates
Pre-built templates for common campaigns (seasonal promos, win-back, maintenance reminders).

---

## Feature 13 — Financing (Invoice button)

**Not a standalone page.** A button on unpaid invoices.

### Trigger
"Offer financing" button appears on invoice detail when balance ≥ configurable threshold (default $500).

### Flow
1. Shop clicks "Offer financing" on an invoice.
2. Modal: select configured financing provider.
3. System generates a financing application link.
4. Link sent to customer via SMS.
5. Customer completes application with the provider.
6. Provider notifies shop of approval and funds.

### Phase 1 providers
- **Synchrony Car Care**
- **Wisetack**

### Phase 2 providers
- Affirm
- Koalafi

### Configuration
Shop enters provider credentials/API keys once in Settings → Integrations. Can configure multiple providers.

---

## External Integrations Summary

| Integration | Used by | Type |
|---|---|---|
| Stripe | Invoices, Payments | Payment processing |
| PartsTech | Inventory | Parts ordering |
| QuickBooks | Accounting | Push-only export |
| CarMD API | Diagnose | Vehicle diagnostics |
| Mitchell1 ProDemand | Job Cards (labor time) | Labor time lookup |
| Carfax / CarMax | Service Reminders | Mileage enrichment |
| Synchrony Car Care | Financing | Consumer financing |
| Wisetack | Financing | Consumer financing |
| NHTSA (via CarMD) | Diagnose | Safety recalls |

---

## Dropped / Deferred Features

| Feature | Decision |
|---|---|
| Reviews | Dropped — not needed in current scope |
| Leads | Dropped — not needed in current scope |
| OBD Scanner | Deferred — hardware-dependent, mobile-first |
| AI Labor Guides | Deferred — Mitchell1 first, AI layer later |
| Tom / AI Diagnose layer | Deferred — dedicated AI session later |
