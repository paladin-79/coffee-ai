# Observability

> Status: stub. Fill in during S3. Config-level detail lives in
> `observability/README.md`.

## Order of work

Langfuse first. Its SDK integrates fastest and gives immediate debugging value
while S2 guardrails are still being tuned — which is exactly when you most need
to see what the model actually did.

Then OTel SDK, then collector, then Prometheus/Loki, then Grafana dashboards.

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
- [ ] Redaction approach when `LOG_PROMPTS=false`
- [ ] Cardinality review: which labels are safe, which would explode
- [ ] Adversary panel: the exact query, the threshold, and how a flagged session gets reviewed after the event
