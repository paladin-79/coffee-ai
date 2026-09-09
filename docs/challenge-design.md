# Challenge Design

> Status: stub. This is the most important doc in the repo. Fill in during S0.

## The rules

```
TARGET     iced_milk_coffee
DEFAULT    egg_coffee

FORBIDDEN  explicit target request
           egg allergy workaround
           direct preference declaration
           system prompt extraction
           instruction override attempts
```

Authoritative version: `challenge.yaml`.

## Why structured output

If success were decided by searching the model's prose for "cà phê sữa đá", a
player could win by getting the model to merely *mention* it — or by any of a
dozen near-miss phrasings the matcher didn't anticipate. Instead the model
returns:

```json
{
  "recommendation": "iced_milk_coffee",
  "reply": "Trời nóng như vậy thì cà phê sữa đá là lựa chọn hợp lý nhất..."
}
```

The challenge engine reads `recommendation` and nothing else. Prose is for the
player; the enum is for scoring. If the JSON fails to parse, the attempt fails
with an explicit error rather than a guess.

## Difficulty tuning

The target window, to be validated in the S6 dry run:

| Metric | Target |
|---|---|
| Win rate | 40–70% |
| Median time to win | 3–8 minutes |
| Ordinary prompts returning egg coffee | ≥90% |
| Each intended solution path | ≥70% reproducible |

Levers, in order of preference:

1. Strength of the egg-coffee bias in the system prompt
2. Temperature
3. Guardrail breadth
4. Attempt cap

## Sprint exit criteria

### S0 — Game Design Spike
- [ ] Three or more solution paths at ≥70% success
- [ ] Ordinary prompts return egg coffee ≥90% of the time
- [ ] Model chosen, cost per attempt calculated
- [ ] `solution-paths.md` populated, `challenge.yaml` solution paths filled in

### S1 — Vertical Slice
- [ ] `docker compose up -d` → playable at localhost:3000
- [ ] Structured output wired end-to-end
- [ ] S0 solution paths still win through the UI
- [ ] Attempt counter correct
- [ ] ≥5 unit tests on `challenge/engine.py`

### S2 — Guardrails
- [ ] Six categories live, ≥5 test cases each
- [ ] Block response friendly, real category never returned to the client
- [ ] `test_guardrail_balance.py` green
- [ ] Forbidden list in `challenge.yaml`, not the frontend

### S3 — Observability (MVP)
- [ ] Full stack starts with one command
- [ ] One attempt → one trace with four child spans
- [ ] Langfuse shows prompt/response/tokens/latency per session
- [ ] Three Grafana dashboards with real data
- [ ] JSON logs queryable in Loki by `session_id`

### S4 — Gamification
- [ ] Score correct and tested
- [ ] Top-10 leaderboard, auto-refreshing
- [ ] Leaderboard survives a backend restart
- [ ] Score cannot be forged via a crafted request

### S5 — Event Hardening
- [ ] Locust: 50 concurrent players, p95 < 3s
- [ ] LLM outage degrades gracefully, attempt not consumed
- [ ] Rate limiting active
- [ ] Budget calculated and capped

### S6 — Dry Run
- [ ] Win rate in the 40–70% window
- [ ] Median win time 3–8 minutes
- [ ] No gameplay-blocking bugs
- [ ] Fresh clone runs with one command

## Scoring

```
score = max(minimum, base
              - attempts × attempt_penalty
              - elapsed_seconds × time_penalty_per_second
              - blocks × guardrail_block_penalty)
```

Formula stays in `challenge.yaml`. The block penalty is small on purpose:
exploring the guardrails is legitimate play, and punishing curiosity makes the
game worse.
