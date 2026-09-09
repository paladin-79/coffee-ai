# Architecture

> Status: stub. Fill in during S1.

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
OpenTelemetry SDK ──▶ OTel Collector ──┬──▶ Langfuse
                                        ├──▶ Prometheus ──▶ Grafana
                                        └──▶ Loki       ──▶ Grafana
```

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

## To document in S1

- [ ] Structured output contract and failure handling
- [ ] Session lifecycle and timer authority
- [ ] Where `challenge.yaml` is loaded and how hot-reload works (or doesn't)
- [ ] Error taxonomy: LLM timeout vs. malformed JSON vs. guardrail block

## To document in S2

- [ ] Where the per-session adversary state lives and how it is keyed
- [ ] Bypass detection: which embedding model, where vectors are cached, TTL
