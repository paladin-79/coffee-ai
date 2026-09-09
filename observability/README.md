# Observability

The application exports to the OpenTelemetry Collector and nothing else. The
collector fans out to Langfuse, Prometheus, and Loki. Adding Datadog later is a
change to `otel/otel-collector-config.yaml` — not to application code.

```
Application ──▶ OTel SDK ──▶ Collector ──┬──▶ Langfuse
                                          ├──▶ Prometheus
                                          └──▶ Loki
```

## Contents

| Path | Purpose |
|---|---|
| `otel/otel-collector-config.yaml` | Receivers, processors, exporters |
| `prometheus/prometheus.yml` | Scrape config |
| `loki/loki-config.yaml` | Log store config |
| `grafana/provisioning/` | Datasources + dashboard providers, as code |
| `grafana/dashboards/` | `game.json`, `llm.json`, `guardrails.json` |

## Provision dashboards as code

Dashboards are JSON files in this repo, loaded by Grafana's provisioning
directory at startup. Do not build them by clicking in the UI — one
`docker compose down -v` and the work is gone. Edit in the UI if you like, then
export the JSON back into `grafana/dashboards/`.

## Span structure

One attempt produces one trace:

```
POST /api/chat                    (auto — FastAPIInstrumentor)
├── guardrail.evaluate            (manual)
├── llm.generate                  (manual)
└── challenge.evaluate            (manual)
```

Attributes follow OTel `gen_ai.*` semantic conventions where they exist:

```
session.id, player.id, challenge.id, attempt.number
guardrail.status, guardrail.category
gen_ai.request.model, gen_ai.usage.input_tokens, gen_ai.usage.output_tokens
challenge.recommendation, challenge.success
```

## Metrics

Prefer labels over separate metric names — far easier to query:

```
coffee_challenge_attempts_total{result, guardrail_status}
coffee_challenge_success_total
coffee_challenge_guardrail_blocks_total{category}
llm_requests_total{model, status}
llm_request_duration_seconds          (histogram)
```
