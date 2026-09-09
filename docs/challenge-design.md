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

## Model and cost

**Model:** `gpt-4o-mini` via the OpenAI API (any OpenAI-compatible endpoint
works — the provider is swappable). Chosen for solid Vietnamese, low latency,
and low price. Revisit if Vietnamese quality on solution paths proves weak in
the S0 spike.

**Cost per attempt** (estimate — `spike.py` prints the real token counts):

| | tokens | |
|---|---|---|
| Input | ~600 | system prompt (~550) + user prompt (~50) |
| Output | ~150 | one JSON object, `reply` a few sentences |

At `gpt-4o-mini` pricing ($0.15 / 1M input, $0.60 / 1M output):

```
per attempt   ≈ 600/1e6·0.15 + 150/1e6·0.60  ≈ $0.0002
per player    ≈ $0.0002 × 30 attempts        ≈ $0.006
500 players   ≈ $3
```

Negligible at event scale. The attempt cap (`challenge.yaml` →
`public.max_attempts`) and `LLM_TIMEOUT_SECONDS` are the real cost guards; a
hard budget cap with alerting lands in S5. Update the numbers here once the
spike has real data.

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
- [ ] `adversary_tracking` signal score computed per session (weights from `challenge.yaml`, bypass detection deferred to S3)
- [ ] Signal-category blocks emit an `adversary` flag / `unsafe` label in telemetry

### S3 — Observability (MVP)
- [ ] Full stack starts with one command
- [ ] One attempt → one trace with four child spans
- [ ] Langfuse shows prompt/response/tokens/latency per session
- [ ] Three Grafana dashboards with real data
- [ ] JSON logs queryable in Loki by `session_id`
- [ ] Bypass detection live: blocked prompt embeddings retained per session, passing prompts scored against them
- [ ] "Potential adversaries" panel on the guardrail dashboard, sessions ranked by signal score, flagged rows highlighted

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

## Adversary tracking

Scoring answers *how well did this player do?* A separate, quieter mechanism
answers a different question: *is this player attacking the model rather than
playing the game?*

At an event this is the signal worth having. A player who reaches for `sua da`,
an egg allergy, or "tôi chỉ uống…" is playing naively. A player who tries to
override the system prompt, extract it, or smuggle in new instructions is doing
something else — and those are the people to talk to afterwards.

### What it is not

- **Not shown to the player.** No badge, no "hidden challenge unlocked" message.
  The block response stays deliberately vague.
- **Not on the public leaderboard.**
- **Not part of `score`.** It never moves the number the player sees.

It is an operator-only view, surfaced in Grafana and Langfuse, ranking sessions
by how deliberately adversarial they look. Config lives in `challenge.yaml`
under `adversary_tracking`.

### How the signal is built

| Input | Weight | Why it counts |
|---|---|---|
| `PROMPT_INJECTION` triggered | 3 | Direct attempt to override instructions |
| `SYSTEM_PROMPT_EXTRACTION` triggered | 3 | Trying to read the hidden prompt |
| `SENSITIVE_REQUEST` triggered | 2 | Off-topic / probing content |
| Bypass detected | +5 | Blocked on a signal category, then landed a semantically similar prompt past the guardrail in the same session |

The three naive categories — `DIRECT_TARGET_REQUEST`, `ALLERGY_WORKAROUND`,
`PREFERENCE_DECLARATION` — contribute nothing. Each signal category counts once
per session (`count_distinct_only: true`), so repetition is not rewarded. A
session reaching `flag_threshold` (default 6) is flagged and listed on the
operator dashboard.

### Bypass detection

The highest-value signal is adaptation: blocked on `PROMPT_INJECTION`, the
player rephrases and gets a prompt with the same intent through. The backend
retains the embeddings of blocked prompts for the session and compares every
*passing* prompt against them; cosine similarity above
`bypass_detection.similarity_threshold` (0.80) adds `bypass_bonus`.

This is where the two embedding uses meet: guardrail layer 2 decides *block or
pass*; adversary tracking reuses the same vectors to decide *was this the
blocked idea in disguise?*
