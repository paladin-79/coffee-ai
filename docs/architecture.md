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
| `guardrails/` | prompt text, categories | scoring |
| `llm/` | vendor SDK, JSON parsing | game rules |
| `store/` | persistence | game rules |
| `telemetry/` | spans, metrics | everything (it observes, not decides) |

## To document in S1

- [ ] Structured output contract and failure handling
- [ ] Session lifecycle and timer authority
- [ ] Where `challenge.yaml` is loaded and how hot-reload works (or doesn't)
- [ ] Error taxonomy: LLM timeout vs. malformed JSON vs. guardrail block
