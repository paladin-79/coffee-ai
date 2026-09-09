# Scripts

## spike.py — S0 design tooling

Talks to the LLM directly. No FastAPI, no Docker, no telemetry. Its whole
purpose is to answer the only question that matters in S0: *is this game
winnable and fun?*

```bash
python spike.py --prompt "Trời Hà Nội hôm nay 38 độ, tôi cần gì đó uống nhanh."
python spike.py --suite              # replay backend/tests/fixtures/
python spike.py --repeat 10 --prompt "..."   # measure stability
```

Log every result into `docs/solution-paths.md`. The exit criteria for S0 are
numeric: three or more distinct solution paths at ≥70% success, ordinary prompts
returning egg coffee ≥90% of the time. If the numbers don't hold, keep tuning
the system prompt. Do not start S1 — this is the cheapest possible place to
discover a design problem.

Output goes to `scripts/out/`, which is gitignored because prompt experiments
are noisy and occasionally reveal answers.
