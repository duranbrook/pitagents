# Enterprise AI Architecture Design

## Goal

Upgrade PitAgents from a single-stage Sonnet ReAct loop to a full enterprise AI architecture borrowing patterns from the Ask Data AI Service: intent classification, dynamic prompt assembly, semantic parts search via Qdrant, validation layer, and a feedback loop with an AND-gated critic.

## Architecture Overview

```
User Message
    ↓
[1] Guardrails (sync, no LLM) ← chat.py
    ↓ blocked → HTTP 400
[2] classify_intent (Haiku) ← new LangGraph node
    ↓ intent label
[3] assemble_prompt ← new LangGraph node
    → static IF_LABEL blocks + semantic few-shots from Qdrant
    ↓ assembled system prompt
[4] call_llm (Sonnet) + execute_tools ← existing nodes, unchanged
    ↓ final response
[5] validate_response (Haiku) ← new LangGraph node
    ↓ done event → SSE stream
[6] Feedback storage → Qdrant feedback_bank ← chat.py post-stream
```

**Multi-agent routing is unchanged.** The user selects "Assistant" or "Tom" in the UI, which sets `agent_id` in `POST /chat/{agent_id}/message`. Guardrails and the new nodes apply to both agents identically.

**UI changes are minimal.** No layout changes. Only addition: thumbs up/down buttons on each assistant message in `ChatPanel.tsx`.

## Components

### 1. Guardrails (chat.py — synchronous, no LLM)

Runs before `graph.astream()`. Checks the user message against a blocklist of regex patterns. If any pattern matches, raises HTTP 400 immediately — no LangGraph graph is invoked, no tokens consumed.

**Blocked patterns (intentionally narrow):**
- Medical advice unrelated to vehicles: `\b(medical|doctor|prescription)\b`
- Legal advice: `\b(legal advice|lawsuit|sue)\b`
- Financial advice: `\b(stock|crypto|invest)\b`
- Prompt injection: `ignore (previous|all) instructions`

False positives here are hard failures for the user, so the blocklist stays narrow. Legitimate edge cases pass through; the validation layer catches quality issues downstream.

### 2. Intent Classifier Node (`classify_intent`)

**Model:** Claude Haiku (non-streaming, ~100 tokens per call)

**Position:** First node in both Assistant and Tom LangGraph graphs, replacing the static `system_prompt` as the entry point.

**Behaviour:** Extracts the last user message from `state["messages"]`, makes a single Haiku call with a strict classification prompt, stores the result in `state["intent"]`. Returns exactly one label.

**Assistant intent labels:**
- `VIN_LOOKUP` — user provides a VIN or asks to look one up
- `QUOTE_BUILD` — user wants to create or add items to a quote
- `QUOTE_REVIEW` — user wants to see, modify, or finalize an existing quote
- `PARTS_LOOKUP` — user asks about parts availability or pricing
- `LABOR_ESTIMATE` — user asks about labor time or cost
- `DIAGNOSTIC` — user describes a symptom or asks what's wrong with a vehicle
- `GENERAL` — anything else

**Tom intent labels:**
- `ANALYTICS_SESSIONS` — questions about inspection sessions, volume, trends
- `ANALYTICS_REVENUE` — questions about revenue, quotes, totals
- `ANALYTICS_TECHNICIAN` — questions about technician performance or activity
- `GENERAL`

**Fallback:** If Haiku call fails or returns an unrecognized label, default to `GENERAL`. The graph continues — intent-specific tuning is skipped, but the agent still responds.

**AgentState additions:**
```python
class AgentState(TypedDict):
    messages: Annotated[list[dict], operator.add]
    tool_calls_log: Annotated[list[dict], operator.add]
    stop_reason: str
    intent: str           # set by classify_intent
    assembled_prompt: str # set by assemble_prompt
```

### 3. Dynamic Prompt Assembly Node (`assemble_prompt`)

**Position:** Second node, after `classify_intent`, before `call_llm`.

**Part A — Static IF_LABEL blocks:**

The base system prompt is split into a base section (always included) and intent-specific sections. The node selects relevant blocks based on `state["intent"]` and concatenates them into `state["assembled_prompt"]`.

Example structure for the Assistant prompt:

```
[BASE — always included]
You are PitAgents, an AI assistant for auto repair shops...

[IF: QUOTE_BUILD or QUOTE_REVIEW]
When building quotes: always call lookup_part_price or semantic_parts_search
before create_quote_item. Never guess prices. Finalize only when the user
confirms all items are correct.

[IF: VIN_LOOKUP or DIAGNOSTIC]
When a VIN is provided, always call lookup_vin first before any diagnosis.
Cross-reference vehicle year/make/model against reported symptoms.

[IF: PARTS_LOOKUP]
Use semantic_parts_search for all part lookups. Return part number,
description, and price. If multiple matches, list top 3 and ask the user
to confirm which they want.
```

**Part B — Semantic few-shots from Qdrant:**

Embeds the user's message, queries the `few_shots` Qdrant collection filtered by `intent == state["intent"]`, retrieves top 3 most similar examples, appends them as `<example>` blocks to the assembled prompt.

```python
hits = qdrant_client.search(
    collection_name="few_shots",
    query_vector=embed(last_user_message),
    query_filter=Filter(must=[FieldCondition(key="intent", match=MatchValue(value=intent))]),
    limit=3,
)
```

If Qdrant is unavailable or returns no results, the node falls back to the base prompt with IF_LABEL blocks only — no hard failure.

### 4. call_llm + execute_tools (unchanged)

Existing nodes from `graph_factory.py`. The only change: `call_llm` uses `state["assembled_prompt"]` as the `system=` parameter instead of the hardcoded `system_prompt` argument passed at graph construction time.

If `assembled_prompt` is empty (classifier or assembly failed), fall back to the original static `system_prompt`.

### 5. Validation Layer Node (`validate_response`)

**Model:** Claude Haiku (non-streaming, ~500 tokens per call)

**Position:** Final node, after `call_llm` produces its terminal response (stop_reason != tool_use).

**What it checks:**

```
You are a QA reviewer for an auto shop AI assistant.
The assistant responded to a user with intent: {intent}

User message: "{user_message}"
Assistant response: "{response_text}"

Check all that apply:
- MATH_ERROR: quote total doesn't match line items
- OFF_TOPIC: discusses non-automotive subjects
- INCOHERENT: doesn't address what the user asked
- HALLUCINATED_PART: references a part not in the tool results

If none apply, reply: PASS
If any apply, reply: FAIL: <code(s)>
```

**Retry logic:**
1. `PASS` → emit `done` event as normal
2. `FAIL` → call the Anthropic API directly within the `validate_response` node (not a LangGraph re-route — re-routing would re-trigger intent classification). The retry appends the failure codes to the assembled prompt as a correction hint: `"Previous response was rejected for: {codes}. Correct these issues."` Then re-runs the Haiku QA check on the new response.
3. Second `FAIL` → emit `done` with an extra `validation_warning: true` field in the payload. Response still goes to the client — no hard block on second failure.

**AND-gated feedback critic:**

After the Haiku QA check, if `feedback_bank` has ≥ 50 entries, run a second check:
1. Embed the response text
2. Search `feedback_bank` for top-3 most similar responses with `rating == -1` (bad)
3. Search `feedback_bank` for top-3 most similar responses with `rating == +1` (good)
4. If similarity to a bad response > 0.92 AND similarity to good responses < 0.70 → treat as `FAIL` and follow the same retry path

This gate is dormant (skipped) until the feedback bank reaches 50 entries.

### 6. Qdrant Collections

**Embedding model:** `text-embedding-3-small` (OpenAI, 1536 dimensions). Same model used consistently across all three collections.

**`parts` collection:**

| Field | Type | Notes |
|---|---|---|
| vector | float[1536] | embedding of `"{description} {category} {part_name}"` |
| part_number | string | |
| description | string | |
| brand | string | |
| category | string | top-level category |
| sub_category | string | |
| unit_price | float | |
| make | string | vehicle make filter |
| model | string | optional |

Populated by ingestion script (see below). Replaces the hardcoded `PARTS_CATALOG` dict for semantic lookups.

**`few_shots` collection:**

| Field | Type | Notes |
|---|---|---|
| vector | float[1536] | embedding of user question |
| intent | string | intent label |
| question | string | example user message |
| ideal_response | string | expected assistant response |
| agent_id | string | "assistant" or "tom" |

Seeded with 5–10 hand-written examples per intent label. Over time, responses with `rating == +1` in the feedback bank can be promoted here manually or via a curation script.

**`feedback_bank` collection:**

| Field | Type | Notes |
|---|---|---|
| vector | float[1536] | embedding of assistant response text |
| intent | string | |
| user_message | string | |
| response_text | string | |
| rating | int | +1 or -1 |
| agent_id | string | |
| message_id | string | UUID, FK to ChatMessage |
| created_at | datetime | |

Written by `POST /chat/{agent_id}/feedback`.

### 7. Parts Ingestion Pipeline

**CLI script:** `python -m src.scripts.ingest_parts --file <path> --mapping <mapping.json>`

Accepts any structured CSV. Field mapping is configurable via a JSON file so future OEM data sources (BMW AOS export, etc.) can be ingested without changing the script.

Example mapping file:
```json
{
  "description": "part_name",
  "part_number": "manufacturer_number",
  "brand": "brand",
  "category": "category",
  "unit_price": "regular_price",
  "make": null
}
```

Batches records (500 per batch), embeds descriptions, upserts to Qdrant. Idempotent — re-running with the same file overwrites existing vectors by `part_number`.

**Fallback:** The existing `PARTS_CATALOG` list in `quote_tools.py` remains. `semantic_parts_search` falls back to it if Qdrant is unavailable or returns no results.

### 8. New Tool: `semantic_parts_search`

Replaces `lookup_part_price` in the Assistant's tool list.

```python
{
    "name": "semantic_parts_search",
    "description": (
        "Search the parts catalog by natural language description. "
        "Returns top matching parts with part number, description, brand, and price. "
        "Use this for any parts lookup — prefer it over guessing prices."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language description of the part (e.g. 'front brake pads for BMW 3 series')"
            },
            "make": {
                "type": "string",
                "description": "Optional: vehicle make to filter results (e.g. 'BMW', 'Toyota')"
            },
            "top_k": {
                "type": "integer",
                "default": 3,
                "description": "Number of results to return (default 3)"
            }
        },
        "required": ["query"]
    }
}
```

### 9. Feedback API

**New endpoint:** `POST /chat/{agent_id}/feedback`

```python
class FeedbackRequest(BaseModel):
    message_id: str   # UUID of ChatMessage row
    rating: int       # +1 or -1
    comment: str | None = None
```

On receipt:
1. Load `ChatMessage` row from Postgres by `message_id`
2. Verify `message.user_id == current_user["sub"]` (can only rate own messages)
3. Embed `message.content` (assistant response text)
4. Upsert to `feedback_bank` Qdrant collection
5. Write `rating` field back to `ChatMessage` row in Postgres
6. Return 204

**Postgres schema change:** Add `rating: int | None` column to `chat_messages` table (new Alembic migration).

### 10. Frontend Changes

**`ChatPanel.tsx`** — only change: add thumbs up / thumbs down buttons below each assistant message bubble. On click, call `POST /chat/{agent_id}/feedback`. Buttons show selected state after click (no undo).

No other frontend changes. Agent list, chat layout, capability cards, image upload — all unchanged.

## Data Flow Summary (per turn)

1. User sends message → `POST /chat/{agent_id}/message`
2. Guardrails sync check → blocked: HTTP 400; pass: continue
3. `classify_intent` node → Haiku call → `state["intent"]`
4. `assemble_prompt` node → IF_LABEL blocks + Qdrant few-shot RAG → `state["assembled_prompt"]`
5. `call_llm` node → Sonnet with `assembled_prompt` → streams tokens via SSE
6. `execute_tools` node (0 or more times) → tool results back to LLM
7. `validate_response` node → Haiku QA check + feedback critic → retry once if fail
8. `done` SSE event → client receives response
9. `_save_messages` → Postgres + Qdrant feedback_bank (on user rating)

## LLM Cost Per Turn

| Call | Model | Approx tokens | Purpose |
|---|---|---|---|
| Intent classifier | Haiku | ~150 in / 5 out | Label detection |
| Few-shot embed | text-embedding-3-small | ~50 | Qdrant query |
| Main agent | Sonnet | ~2000–6000 | ReAct loop |
| Validation | Haiku | ~600 in / 10 out | QA check |

Total added cost vs today: ~$0.002–0.004 per turn (Haiku calls + embedding).

## Files to Create or Modify

**New files:**
- `src/agents/nodes/classify_intent.py` — Haiku intent classifier node
- `src/agents/nodes/assemble_prompt.py` — IF_LABEL assembly + Qdrant few-shot RAG
- `src/agents/nodes/validate_response.py` — Haiku QA + feedback critic node
- `src/agents/prompts/assistant_blocks.py` — IF_LABEL prompt blocks for Assistant
- `src/agents/prompts/tom_blocks.py` — IF_LABEL prompt blocks for Tom
- `src/agents/tools/parts_tools.py` — `semantic_parts_search` tool
- `src/scripts/ingest_parts.py` — CLI ingestion pipeline
- `src/scripts/seed_few_shots.py` — seed initial few-shot examples
- `src/db/qdrant.py` — Qdrant client singleton + collection setup
- `src/api/feedback.py` — `POST /chat/{agent_id}/feedback` endpoint
- `alembic/versions/0004_add_chat_message_rating.py`

**Modified files:**
- `src/agents/state.py` — add `intent`, `assembled_prompt`
- `src/agents/graph_factory.py` — add 3 new nodes, update graph edges
- `src/agents/assistant.py` — swap `lookup_part_price` → `semantic_parts_search`
- `src/api/chat.py` — add guardrails check, wire feedback endpoint
- `src/config.py` — add `QDRANT_URL`, `QDRANT_API_KEY`, `OPENAI_API_KEY` (for embeddings)
- `frontend/src/components/ChatPanel.tsx` — add thumbs up/down UI
- `docker-compose.yml` — add Qdrant service

## Testing Strategy

- Unit tests for each new node (mock Haiku + Qdrant)
- Integration test: full turn with real Qdrant (local Docker) + mocked Anthropic
- Ingestion script test: small CSV fixture → verify Qdrant collection populated correctly
- Feedback endpoint test: rate a message → verify Qdrant upsert + Postgres write
- Guardrails test: blocked patterns return 400, edge cases pass through
