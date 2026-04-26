# API Contract — pitagents Backend

Authoritative reference for the REST API consumed by the iOS, Android, and web clients. Promoted from a P2 to a P1 doc by the 2026-04-25 mobile build, which surfaced enum drift between backend and clients (`"out"/"in"` vs. `"outbound"`, `"wa"/"email"` vs. `"sms"`). The intent of this doc is to keep that drift from recurring as new clients are added.

> **Source of truth.** Code is the source of truth. The line references below point at where each enum / route / shape is defined. If this doc disagrees with the code, the code wins; please update this doc.

Backend base path: served at root `/`. CORS allows the deployed web client + simulator/emulator origins (see `backend/src/api/main.py:25`).

---

## Authentication

All routes require a `Bearer <jwt>` `Authorization` header except where noted as **PUBLIC**.

- **JWT payload claims** (decoded by clients):
  - `sub` — user id (UUID, string)
  - `email` — string
  - `role` — `"owner"` \| `"technician"` (see `backend/src/models/user.py:15`)
  - `shop_id` — UUID (string)
  - `exp` — standard JWT expiry
- **JWT algorithm:** HS256.
- **JWT encoding:** standard URL-safe base64 (`-` and `_`). **iOS clients must convert to standard base64 before `Data(base64Encoded:)` decoding** (see `mobile-code-review-2026-04-26.md` P0 #1).
- **401 handling:** clients should clear the stored token and redirect to login on any 401 from any endpoint. Login itself returns 401 only for invalid credentials.

---

## Enum reference (cross-client critical)

These are the values the backend stores and returns. Clients must use the **exact** strings — no synonyms, no longer forms.

| Domain | Field | Allowed values | Source |
|--------|-------|---------------|--------|
| Customer message | `direction` | `"out"`, `"in"` | `backend/src/models/customer_message.py:23` |
| Customer message | `channel` | `"wa"`, `"email"` | `backend/src/models/customer_message.py:24` |
| User | `role` | `"owner"`, `"technician"` | `backend/src/models/user.py:15` |
| Quote | `status` | `"draft"`, `"final"`, `"sent"` | `backend/src/models/quote.py:15` |
| Inspection session | `status` | `"recording"`, `"processing"`, `"complete"`, `"failed"` | `backend/src/models/session.py:15` |
| Report | `status` | `"draft"` (default), plus values used by report generator | `backend/src/models/report.py:21` (free-form `String(10)`, not enum-constrained at DB level) |

**Notes:**
- `direction` is **not** `"outbound"`/`"inbound"` (the abbreviated form is the canonical one — abbreviated specifically because of WhatsApp UX precedent).
- `channel` is **not** `"sms"`. SMS is *not* a supported channel today; do not surface that option in any client picker.
- Report `status` is a `String(10)` column, so values are theoretically unconstrained, but in practice the report-generator writes a small set of values; clients should treat unknown values as a default/neutral state rather than crashing.

---

## Endpoint catalog

Grouped by router. `🔒` = JWT required. `📂` = multipart form. Path is the full URL path including the prefix that the router mounts under.

### Auth

| Method | Path | Auth | Body | Response |
|--------|------|------|------|----------|
| POST | `/auth/login` | PUBLIC | `LoginRequest` `{ email, password }` | `TokenResponse` `{ access_token, token_type }` |

Source: `backend/src/api/auth.py`.

### Customers

| Method | Path | Auth | Body | Response |
|--------|------|------|------|----------|
| GET | `/customers` | 🔒 | — | `list[CustomerResponse]` (filtered by JWT `shop_id`) |
| POST | `/customers` | 🔒 | `CustomerCreate` `{ name, email?, phone? }` | `CustomerResponse` (201) |
| DELETE | `/customers/{customer_id}` | 🔒 | — | 204 |

`CustomerResponse`: `{ customer_id, shop_id, name, email?, phone?, created_at }`. Source: `backend/src/api/customers.py`.

### Vehicles

| Method | Path | Auth | Body | Response |
|--------|------|------|------|----------|
| GET | `/customers/{customer_id}/vehicles` | 🔒 | — | `list[VehicleResponse]` |
| POST | `/customers/{customer_id}/vehicles` | 🔒 | `VehicleCreate` `{ year, make, model, trim?, vin?, color? }` | `VehicleResponse` |
| DELETE | `/vehicles/{vehicle_id}` | 🔒 | — | 204 |
| GET | `/vehicles/{vehicle_id}/reports` | 🔒 | — | `list[ReportSummary]` |

`VehicleResponse`: `{ vehicle_id, customer_id, year, make, model, trim?, vin?, color?, created_at }`. Source: `backend/src/api/vehicles.py`.

### Customer messages

| Method | Path | Auth | Body | Response |
|--------|------|------|------|----------|
| GET | `/vehicles/{vehicle_id}/messages` | 🔒 | — | `list[MessageResponse]` |
| POST | `/vehicles/{vehicle_id}/messages` | 🔒 | `CreateMessageRequest` `{ body, channel ∈ {"wa","email"}, subject? }` | `MessageResponse` |
| POST | `/twilio/webhook` | PUBLIC (Twilio-signed) | form params | 200 |

`MessageResponse`: `{ message_id, vehicle_id, direction ∈ {"out","in"}, channel ∈ {"wa","email"}, body, external_id?, sent_at?, created_at }`. Source: `backend/src/api/customer_messages.py`.

**Ordering:** confirm before relying on optimistic insert at index 0 — see mobile review item P1 #7.

### Inspection sessions

| Method | Path | Auth | Body | Response |
|--------|------|------|------|----------|
| POST | `/sessions` | 🔒 | `CreateSessionRequest` | `CreateSessionResponse` |
| POST | `/sessions/{session_id}/media` | 🔒 📂 | `file: UploadFile`, plus form fields | `UploadMediaResponse` |
| GET | `/sessions/{session_id}` | 🔒 | — | session detail |

Source: `backend/src/api/sessions.py`.

### Reports

| Method | Path | Auth | Body | Response |
|--------|------|------|------|----------|
| GET | `/reports` | 🔒 | — | list of reports for shop |
| GET | `/reports/{report_id}` | 🔒 | — | report detail |
| GET | `/r/{share_token}` | PUBLIC | — | shared (read-only) report view |
| POST | `/reports/{report_id}/send` | 🔒 | send config | dispatch result |

Source: `backend/src/api/reports.py`.

### Quotes

| Method | Path | Auth | Body | Response |
|--------|------|------|------|----------|
| GET | `/quotes` | 🔒 | — | `list[QuoteResponse]` |
| POST | `/quotes` | 🔒 | quote create payload | `CreateQuoteResponse` (201) |
| GET | `/quotes/{quote_id}` | 🔒 | — | `QuoteResponse` |
| PUT | `/quotes/{quote_id}/finalize` | 🔒 | — | `FinalizeQuoteResponse` |
| GET | `/sessions/{session_id}/quote` | 🔒 | — | `QuoteResponse` (the quote bound to a recorded inspection session) |

Source: `backend/src/api/quotes.py`.

### Chat (assistant + per-agent)

| Method | Path | Auth | Body | Response |
|--------|------|------|------|----------|
| GET | `/chat/{agent_id}/history` | 🔒 | — | `list[ChatHistoryItem]` |
| POST | `/chat/{agent_id}/message` | 🔒 | `ChatMessageRequest` | SSE stream |
| POST | `/chat/{agent_id}/message/sync` | 🔒 | `ChatMessageRequest` | `SyncMessageResponse` `{ text }` |
| POST | `/chat/{agent_id}/feedback` | 🔒 | feedback payload | 204 |

`agent_id` known values today: `"assistant"` (default for the mobile clients), plus per-feature agents (`"tom"`, `"quote"`, etc.). Clients can pass any string; backend dispatches.

`ChatHistoryItem`: `{ id, role, content: list[ContentBlock], created_at? }` — **`created_at` is nullable** (`backend/src/api/chat.py:115`). iOS schema must mark it optional (currently broken — see review P0 #2).

`ContentBlock`: `{ type, text? }`. `type` known values: `"text"`. (Future: `"image"`.)

`ChatMessageRequest`: `{ message, image_url? }`.

Source: `backend/src/api/chat.py`, `backend/src/api/feedback.py`.

### Media

| Method | Path | Auth | Body | Response |
|--------|------|------|------|----------|
| POST | `/upload` | 🔒 📂 | `file: UploadFile` | `UploadResponse` `{ image_url }` |
| POST | `/transcribe` | 🔒 | raw audio body (set `Content-Type` to the audio MIME) | `TranscribeResponse` `{ transcript }` |

Source: `backend/src/api/upload.py`, `backend/src/api/transcribe.py`.

---

## Wire-format conventions

- Field names are **snake_case** in JSON (`customer_id`, `created_at`, `image_url`). All client SDKs need to map to their idiomatic case (Swift `CodingKeys`, Gson `@SerializedName`).
- Timestamps are ISO-8601 strings (`2026-04-26T12:34:56.789012`). No timezone suffix on naive timestamps; treat as UTC.
- IDs are stringified UUIDs.
- Money: doubles in major units (e.g., `estimate_total: 1234.56` is $1,234.56). No currency code today — single-tenant USD assumed.
- `null` vs. omitted: backend may return `null` for nullable fields rather than omitting the key. **Clients MUST treat all `?`-marked fields as nullable on the wire**, not just absent.

## Adding a new client / new endpoint

When adding any of the following, update this doc *in the same PR*:

1. New endpoint, new field, or shape change (add a row, mention the source file).
2. New enum value, or rename of an existing enum value (update the table).
3. New `agent_id` value that is meaningful for the chat router.

If the change is breaking (renamed field, removed enum value, changed shape), bump a version note at the top with the date and what to migrate.

## Open questions

- **Refresh tokens.** Today JWT expiry → user is bounced to login. No refresh flow. If we add one, this doc gets a new `/auth/refresh` row and clients gain a 401-retry interceptor.
- **`channel = "sms"`.** Will probably be added when Twilio Programmable Messaging is wired up in a phase 2.
- **`role` granularity.** Today `"owner"` / `"technician"`. If we add `"front_desk"` or per-shop fine-grained perms, the JWT shape changes.
- **Report status enum.** Currently a free-form `String(10)`. Should be normalized to an enum when the report generator stabilizes its state machine.
