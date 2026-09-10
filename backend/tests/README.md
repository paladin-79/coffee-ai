# Tests

## test_guardrail_balance.py — the important one

Lands in S2 and asserts three properties simultaneously:

```
forbidden_prompts  → every one must BLOCK
solution_paths     → every one must PASS
neutral_prompts    → every one must PASS
```

The second assertion is the reason this file exists. A guardrail that blocks the
intended ways to win makes the game unwinnable, and nothing else in the test
suite would notice. Run it after every change to `guardrails/` or
`challenge.yaml`.

Fixtures live in `fixtures/`: `forbidden.yaml`, `solutions.yaml`,
`neutral.yaml`. Each is a YAML list; an entry is a plain string or a mapping
with a `prompt` key. `scripts/spike.py --suite` replays the same files in S0.
