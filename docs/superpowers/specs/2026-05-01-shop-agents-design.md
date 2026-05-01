# Shop Agent Personas Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current two-agent chat sidebar with five role-based agents that mirror real auto shop employees, each with defined tools and shared access to the same underlying data.

**End state:** The chat window is the primary interface. Dashboard and nav exist for verification only. Every workflow — from customer intake to invoice payment — can be completed by talking to the right agent.

---

## The Five Agents

| # | Name | Physical location | Accent color |
|---|---|---|---|
| 1 | Service Advisor | Front desk | amber (#d97706) |
| 2 | Technician | Bay | blue (#3b82f6) |
| 3 | Parts Manager | Parts room | cyan (#06b6d4) |
| 4 | Bookkeeper | Back office | green (#22c55e) |
| 5 | Manager | Roaming / oversight | purple (#a855f7) |

---

## Agent Tool Definitions

Each agent is defined by a name, a system prompt, and a list of tools it can invoke. Tools map 1:1 to existing backend endpoints or frontend pages.

### Service Advisor
**Domain:** Customer-facing intake and follow-up.  
**Tools:**
- Look up / create customers and vehicles
- Book and manage appointments
- Send service reminders
- Pull inspection reports by customer or vehicle
- Create and send invoices
- Send marketing campaigns

**Key capability:** Given any customer name or vehicle, immediately surfaces the latest report the Technician generated — the primary handoff point between bay and front desk.

### Technician
**Domain:** Physical vehicle diagnosis and shop work.  
**Tools:**
- Start an inspection (manual walkthrough with photos)
- Run AI Diagnose on DTC codes (CarMD lookup — two modes, same tool)
- Open and update job cards
- Generate quotes/estimates from inspection results
- Log time against a job card

**Data contract:** Every report the Technician generates is stamped with `vehicle_id` → `customer_id`. This is the shared record the Service Advisor queries.

### Parts Manager
**Domain:** Physical stock and supplier relationships.  
**Tools:**
- Look up parts by OEM code or description
- Check and update inventory levels
- Create and manage vendor records
- Flag low-stock items

### Bookkeeper
**Domain:** Money in, records straight.  
**Tools:**
- Record and reconcile payments against invoices
- View accounting P&L summary
- Export financial data

**Note:** Bookkeeper receives invoices created by the Service Advisor. They do not create invoices — that boundary is intentional.

### Manager
**Domain:** Business visibility and team oversight.  
**Tools:**
- Pull reports across any customer, vehicle, or date range
- View time tracking across all employees
- Switch to any other agent's view (read-only oversight mode)

---

## Shared Data Model

All five agents operate on the same underlying records. There is no per-agent copy of data.

```
Customer
  └── Vehicle (one or many)
        └── Report (inspection + DTC diagnosis)
              └── Job Card
                    ├── Quote / Estimate
                    └── Time Entries

Invoice → links to Job Card + Customer
Payment → links to Invoice
```

**Critical handoff:** Technician creates `Report` on a `Vehicle`. Service Advisor retrieves `Report` via `Customer` lookup. Same record, different entry point. No manual handoff required.

---

## Sidebar UX

### Agent list
- 5 agents in the left sidebar, replacing the current "Assistant / Tom" list
- Each agent shows: avatar (initials + role color), name, role tagline, last message preview
- Active agent highlighted with accent color border

### Capability tooltip on hover
- Hovering an agent card shows a small tooltip listing that agent's tools (2–4 bullet points, short labels)
- Tooltip appears after a 400ms delay to avoid flicker on fast cursor passes
- Dismisses immediately on mouse leave

### No structural changes to ChatPanel
- `ChatPanel` already handles agentId routing — only the `AGENTS` constant and system prompts change
- `QuoteSummary` right panel is out of scope for this iteration

---

## Backend Agent Config

Each agent maps to a backend `agentId` string that the existing `/chat` streaming endpoint already routes. New agent IDs:

| agentId | System prompt focus |
|---|---|
| `service-advisor` | Customer records, reports, invoices, appointments, marketing |
| `technician` | Inspect, diagnose, job cards, quotes, time |
| `parts-manager` | Inventory, parts lookup, vendors |
| `bookkeeper` | Payments, accounting |
| `manager` | Cross-agent read access, reports, time tracking |

System prompts for each agent must:
1. Define the agent's role and physical location in the shop
2. List the tools available (names match backend tool definitions)
3. State clearly which records it can read vs. write
4. Include the shared data model so the agent understands the Customer → Vehicle → Report chain

---

## Agent Configurability

The five agents above are the defaults — seeded on first run. The system must support creating, editing, and deleting agents without code changes.

### Tool registry
A fixed list of all available tools the system knows about. Each tool has:
- `id` — machine key (e.g. `customers`, `inspect`, `invoices`)
- `label` — human label shown in the builder UI
- `description` — one sentence, shown in the hover tooltip

New tools are added to the registry by developers. Shop owners cannot invent new tools — they can only assign existing ones to agents.

### Agent record (stored in DB, per shop)
```
Agent {
  id          UUID
  shop_id     UUID
  name        String          -- e.g. "Service Advisor"
  role_tagline String         -- e.g. "Front desk · Customer intake"
  accent_color String         -- hex, drives sidebar avatar color
  system_prompt String        -- editable free-text; seeded from default template
  tools       String[]        -- list of tool IDs from the registry
  sort_order  Int             -- controls sidebar position
  created_at  DateTime
}
```

### Builder UI (in Settings)
- **Agent list** — shows all agents for this shop, drag-to-reorder
- **Create agent** — name, tagline, color picker, then tool assignment
- **Edit agent** — same form; system prompt is an expandable advanced field
- **Delete agent** — only allowed if agent has no recent chat history (soft guard)
- **Tool assignment** — checkbox grid of all registry tools; checked = enabled for this agent

### Sidebar reflects DB
The `AgentList` component fetches agents from the backend at load time instead of using a hardcoded constant. The five default agents are seeded into the DB on shop creation — not hardcoded in frontend code.

---

## What This Is Not

- **Not a permissions system.** Any user can talk to any agent. Role boundaries are semantic (what the agent knows), not access-controlled.
- **Not a multi-user system.** One shop owner talks to all five agents. The personas are knowledge domains, not separate accounts.
- **Not replacing the dashboard yet.** Dashboard tiles still link to full pages. Chat is the primary path; pages are the verification fallback.
- **Not a free-form AI builder.** Shop owners pick tools from a fixed registry. They cannot write arbitrary code or connect external APIs.
