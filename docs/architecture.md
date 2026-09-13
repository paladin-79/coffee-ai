# Architecture

> Status: S1 + S2 sections filled. Telemetry rows are still forward-looking (S3).

## Request lifecycle

```
Browser
  │ HTTPS
  ▼
Backend (FastAPI)
  ├── Guardrail Engine   ── BLOCK ──▶ friendly refusal (real reason logged)
  ├── LLM Integration    ──────────▶ OpenAI-compatible provider
  └── Challenge Engine   ──────────▶ deterministic evaluation
  │
  ▼
OpenTelemetry SDK ──▶ OTel Collector ──┬──▶ Langfuse                          [S3]
                                        ├──▶ Prometheus ──▶ Grafana
                                        └──▶ Loki       ──▶ Grafana
```

As of S2 the chain is: `POST /api/chat` → session checks → `guardrails/`
(block → attempt consumed, adversary weighed, events logged, vague reply) →
`llm/` provider → `challenge/engine` → response. Telemetry is plain
`logging` behind `telemetry/events.py` until S3.

## Component boundaries

| Layer | Knows about | Must not know about |
|---|---|---|
| `api/` | request/response shapes | LLM vendor, store backend |
| `challenge/` | rules, recommendation enum | prompt text of guardrails |
| `guardrails/` | prompt text, categories, adversary signal weights | game score, leaderboard |
| `llm/` | vendor SDK, JSON parsing | game rules |
| `store/` | persistence | game rules |
| `telemetry/` | spans, metrics | everything (it observes, not decides) |

## Adversary tracking

An operator-only concern, not game logic. `guardrails/` knows which categories
carry an adversary weight and raises an `adversary_signal` event on a match;
`store/` holds the per-session running total and the blocked-prompt embeddings
used for bypass detection; `telemetry/` exports it. Nothing here touches
`score` or the leaderboard. Design rationale in `challenge-design.md` →
Adversary tracking.

## Structured output contract (S1)

The system prompt asks the model for a single JSON object:

```json
{ "recommendation": "egg_coffee" | "iced_milk_coffee" | "other", "reply": "<text>" }
```

`llm/openai_provider` sends it with `response_format={"type": "json_object"}` and
hands the body to `llm/parsing.parse_completion_body`, which returns
`(recommendation, reply)` and **never raises**. A missing / non-string
`recommendation` becomes `None`; a body that isn't a JSON object becomes
`(None, "")`.

`challenge/engine.evaluate` then maps that to an `Evaluation`:

| model returned | `readable` | `success` | player sees |
|---|---|---|---|
| a value in `recommendation_enum` | `True` | `value == target` | the model's `reply` |
| a value not in the enum, or `None` | `False` | `False` | `reply`, or a fixed fallback line if empty |

The enum is the only source of truth for winning. Prose is never searched.

## Session lifecycle and timer authority (S1)

`POST /api/session` creates a `Session` (`store/schemas.Session`) with a
server-side `created_at`. `Session.elapsed_seconds` is computed from
`created_at` (and `finished_at` once set) — a client timestamp is never trusted.
Status moves `active → won` on a target recommendation, or `active → lost` when
`attempts` reaches `public.max_attempts`. A finished session rejects further
`/api/chat` with `409`. Scoring and any displayed timer are S4; S1 only records
the clock.

Store is `InMemoryStore` behind the `store.Store` interface — a restart wipes
all sessions. Redis lands in S4.

## Where `challenge.yaml` is loaded (S1)

Once, in the `create_app` lifespan handler (`main.py`), via
`challenge.rules.load_rules` into `app.state.rules`. **No hot reload** — editing
`challenge.yaml` needs a backend restart. Path resolution: `CHALLENGE_CONFIG_PATH`
if set and the file exists, else repo-root `challenge.yaml` (`config.Settings.rules_path`).
A malformed or invalid file raises `RulesError` at startup with a message naming
the file and the problem.

## Error taxonomy (S1)

| Situation | Where caught | HTTP | Attempt consumed? |
|---|---|---|---|
| LLM network / timeout / auth / quota (`OpenAIError`) | `openai_provider` → `LLMTransportError` → route | `503` | **no** |
| Malformed JSON / missing `recommendation` / value not in enum | `parse_completion_body` + `engine.evaluate` | `200`, `success:false` | **yes** |
| Unknown `session_id` | route | `404` | n/a |
| Session already `won` / `lost`, or out of attempts | route | `409` | n/a |
| Guardrail block | `guardrails/engine` → `routes._handle_block` | `200`, `blocked:true` | **yes** |
| Embedding endpoint down / timeout (layer 2) | `guardrails/engine` → fail open, `guardrail_degraded` event | `200`, prompt proceeds | as the LLM path decides |

## Guardrails (S2)

`app/guardrails/`, built once in the lifespan handler from `rules.guardrails`.

```
prompt ─▶ normalize ─▶ layer 1: literal / re: patterns ─▶ layer 2: embeddings ─▶ PASS
                            │ first match                     │ max cosine ≥ threshold
                            ▼                                 ▼
                          BLOCK                             BLOCK
```

- **Normalisation** (`normalize.py`, stdlib only): lowercase, strip diacritics
  (NFD + explicit `đ→d`), collapse punctuation/whitespace. Patterns go through
  the same function, so `sua da` matches `Sữa-Đá!!!`. Known trap: stripping
  accents makes distinct words collide (`tự tử` = `từ từ`) — the balance test is
  what catches this; the rejected patterns are listed in `challenge.yaml`.
- **Layer 1**: patterns are literal phrases matched on word edges; a `re:` prefix
  makes one a regex. Invalid regex → `RulesError` at startup.
- **Priority = declaration order.** First matching category wins, so the three
  signal categories are declared before the three naive ones. Otherwise
  "ignore previous instructions … iced milk coffee" would be recorded as
  `DIRECT_TARGET_REQUEST` and score 0 adversary points. Guarded by
  `test_real_rules_put_signal_categories_first`.
- **Layer 2**: `OpenAIEmbedder` (`text-embedding-3-small`, same endpoint/key as
  chat, `EMBEDDING_TIMEOUT_SECONDS`). Runs only if layer 1 passed. Example
  vectors are embedded once on first use and cached in the engine for the life
  of the process. No `LLM_API_KEY` → layer 2 inactive (warning at boot). An
  embedding error **fails open** and returns `degraded`, which the route emits as
  `guardrail_degraded`.
- **What the player sees**: `blocked: true` + `block_message_vi|en` (by
  `ChatRequest.lang`). Category, matched pattern, similarity and adversary state
  never leave the server — asserted in `test_api.py`.
- **A block consumes an attempt** (confirmed 2026-09-13). It is a move that did
  not work, unlike an LLM outage; and until S4/S5 the attempt cap is the only
  cost of probing.

Tests: `test_guardrails.py` (engine mechanics, hand-built rules),
`test_guardrail_balance.py` (real `challenge.yaml`: forbidden blocked in the
right category, solutions + neutral + `solution_paths` pass). Offline it uses
`HashingEmbedder` with its own threshold — proves wiring, not semantic
generalisation. `RUN_LIVE_TESTS=1` re-runs it against the real embedder and
threshold; do that before an event.

## Adversary state (S2)

- **Where**: on the `Session` model (`store/schemas.py`), keyed by `session_id`
  like everything else — `adversary_score`, `adversary_categories` (list, for
  `count_distinct_only`; JSON-friendly for Redis in S4), `flagged`,
  `guardrail_blocks`, `blocked_embeddings`.
- **Who decides**: `guardrails/adversary.AdversaryTracker.on_block` is pure —
  reads config + current counters, returns `AdversaryUpdate`. `store.record_block`
  only persists. The route emits `guardrail_block` (with real category and
  `label`), `adversary_signal` for every signal-category block (0 points on a
  repeat), and `session_flagged` once, when the total first reaches
  `flag_threshold`.
- **Never** in any response, never touches score. `InMemoryStore` → lost on
  restart; moves to Redis with the rest of the session in S4.

## Bypass detection (designed S2, live S3)

- **Model**: the layer-2 embedder — same vectors, no second model.
- **Cached where**: `Session.blocked_embeddings`, appended by `record_block`
  when a block carried an embedding. S2 fills it only for layer-2 blocks; S3
  must also embed signal-category (layer-1) blocks, since those are the ones
  bypass detection is about, then score each passing prompt against the list
  (`bypass_detection.similarity_threshold`, `bypass_bonus`).
- **TTL**: the session's lifetime. In memory now; in S4 they go with the session
  key in Redis and expire with it. Vectors are ~1.5k floats — bound the list
  (e.g. last N) when S3 lands if sessions run long.
