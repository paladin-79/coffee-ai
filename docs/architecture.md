# Architecture

> Status: S1 sections filled. Guardrail / telemetry rows are still forward-looking.

## Request lifecycle

```
Browser
  │ HTTPS
  ▼
Backend (FastAPI)
  ├── Guardrail Engine   ── BLOCK ──▶ friendly refusal (real reason logged)   [S2]
  ├── LLM Integration    ──────────▶ OpenAI-compatible provider
  └── Challenge Engine   ──────────▶ deterministic evaluation
  │
  ▼
OpenTelemetry SDK ──▶ OTel Collector ──┬──▶ Langfuse                          [S3]
                                        ├──▶ Prometheus ──▶ Grafana
                                        └──▶ Loki       ──▶ Grafana
```

As of S1 the chain is: `POST /api/chat` → session checks → `llm/` provider →
`challenge/engine` → response. No guardrail, no telemetry yet.

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
| Guardrail block | — | — | — (S2) |

## To document in S2

- [ ] Where the per-session adversary state lives and how it is keyed
- [ ] Bypass detection: which embedding model, where vectors are cached, TTL
