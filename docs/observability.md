# Observability

> Status: stub. Fill in during S3. Config-level detail lives in
> `observability/README.md`.

## Order of work

Langfuse first. Its SDK integrates fastest and gives immediate debugging value
while S2 guardrails are still being tuned — which is exactly when you most need
to see what the model actually did.

Then OTel SDK, then collector, then Prometheus/Loki, then Grafana dashboards.

## Langfuse tracing (done)

`app/telemetry/tracing.py` builds the process-wide Langfuse client at startup
(`main.py`'s `create_app`). Credentials go through `Settings`
(`langfuse_public_key`/`langfuse_secret_key`/`langfuse_base_url`, sourced from
`.env`) rather than the SDK's own `os.environ` lookup — pydantic-settings
parses `.env` into `Settings` only, it never populates the process
environment, so the SDK would otherwise see nothing and silently trace with a
disabled client.

One `/api/chat` attempt is one trace (`process-chat-attempt`), with
`session_id`/`user_id` propagated to every child observation:

```
process-chat-attempt          (span, root)
├── check-guardrails          (span)
│   └── embed-guardrail-prompt (embedding, layer-2 only)
├── generate-completion       (generation — via langfuse.openai, skipped on a block)
└── evaluate-challenge        (span, skipped on a block)
```

`app/llm/openai_provider.py` and `app/guardrails/embeddings.py` both use
`langfuse.openai`'s drop-in `AsyncOpenAI` in place of the bare SDK, so model,
token usage, and cost land on the `generation`/`embedding` observations
automatically.

Redaction: `tracing._mask_otel_spans` (a Langfuse `mask_otel_spans` hook) wipes
the `input`/`output` attributes on every exported span when
`LOG_PROMPTS`/`LOG_RESPONSES` are off, matching the flags `telemetry/events.py`
already uses for structured logs. It's a coarse, whole-attribute redaction
(the entire input or output object, not per-field) — verified by toggling both
flags off and confirming a trace's `input`/`output` both come back
`[redacted]` via `langfuse-cli api observations list`.

## Structured log events

```
challenge_started    prompt_received      guardrail_pass
guardrail_block      llm_request          llm_response
challenge_success    challenge_failed     session_finished
adversary_signal     session_flagged
```

All JSON, all carrying `session_id` and `trace_id` so a Loki query joins to a
trace.

`guardrail_block` on a signal category (`PROMPT_INJECTION`,
`SYSTEM_PROMPT_EXTRACTION`, `SENSITIVE_REQUEST`) also carries `adversary: true`
and `label: unsafe`. `adversary_signal` fires whenever the session's score
changes (category first seen, or bypass detected) and carries the running
total. `session_flagged` fires once, when the total first crosses
`flag_threshold`.

## Dashboard intent

Three dashboards, each answering a distinct question:

**game.json** — *Is the event going well?*
Active players, total attempts, successes, average attempts to success, fastest
completion.

**llm.json** — *Is the AI healthy and affordable?*
Request rate, latency percentiles, token usage, error rate.

**guardrails.json** — *What are players trying? Who is attacking?*
Block rate, blocks by category, injection attempts over time, and a **Potential
adversaries** table — sessions ranked by `adversary_tracking` score, flagged
rows highlighted. See `challenge-design.md` → Adversary tracking.

The guardrail dashboard is the interesting one during a live event. It shows in
real time which shortcuts players reach for first, and which sessions are
probing rather than playing.

## To document in S3

- [ ] Collector pipeline diagram with actual processor list
- [ ] Sampling decision (all-on is fine at this scale — say so and why)
- [x] Redaction approach when `LOG_PROMPTS=false` — done for Langfuse, see above; still open for the OTel/Loki path once that lands
- [ ] Cardinality review: which labels are safe, which would explode
- [ ] Adversary panel: the exact query, the threshold, and how a flagged session gets reviewed after the event
