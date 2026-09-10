#!/usr/bin/env python3
"""spike.py — S0 design tooling.

Talks to the LLM directly. No FastAPI, no Docker, no telemetry. Its whole
purpose is to answer the only question that matters in S0: is this game
winnable and fun?

    python spike.py --prompt "Trời Hà Nội hôm nay 38 độ, cần gì đó uống nhanh."
    python spike.py --suite                      # replay backend/tests/fixtures/*.yaml
    python spike.py --repeat 10 --prompt "..."   # measure stability
    python spike.py --suite -c 12                # more calls in parallel

Use the venv's `python` (or `.venv\\Scripts\\python.exe`), not the `py` launcher
— `py` ignores the active venv.

`--suite` and `--repeat` fan calls out across threads (`-c`, default 8), so a
run is roughly one request long, not N. A single request to gpt-4o-mini is
~1–3s; from a slow link, more.

Reads challenge.yaml for the target, the enum, and the llm.* settings, and the
system prompt from backend/app/challenge/prompts/. Endpoint config comes from
.env (LLM_BASE_URL, LLM_MODEL, LLM_API_KEY).

Every run also appends JSON lines to scripts/out/, which is gitignored because
prompt experiments are noisy and occasionally reveal answers. Log the useful
results into docs/solution-paths.md by hand.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml
from dotenv import load_dotenv
from openai import OpenAI

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

# Windows consoles default to a legacy codepage (cp1252 / cp932 / …) that cannot
# print Vietnamese. Force UTF-8 on our own streams; the JSONL files are already
# written UTF-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

CHALLENGE_YAML = REPO_ROOT / "challenge.yaml"
PROMPTS_DIR = REPO_ROOT / "backend" / "app" / "challenge" / "prompts"
FIXTURES_DIR = REPO_ROOT / "backend" / "tests" / "fixtures"
OUT_DIR = REPO_ROOT / "scripts" / "out"

# Approx USD per 1M tokens. Update if you change LLM_MODEL. Used only for the
# rough cost-per-attempt estimate printed at the end of a run.
PRICE_PER_MTOK = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}


def load_config() -> dict:
    load_dotenv(REPO_ROOT / ".env")
    import os

    cfg = yaml.safe_load(CHALLENGE_YAML.read_text(encoding="utf-8"))
    prompt_file = PROMPTS_DIR / cfg["llm"]["system_prompt_file"]
    system_prompt = prompt_file.read_text(encoding="utf-8")

    base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    api_key = os.environ.get("LLM_API_KEY")
    model = os.environ.get("LLM_MODEL")
    if not api_key or not model:
        sys.exit(
            "Missing LLM_API_KEY or LLM_MODEL. Copy .env.example to .env and "
            "fill them in."
        )

    return {
        "challenge": cfg,
        "system_prompt": system_prompt,
        "client": OpenAI(base_url=base_url, api_key=api_key),
        "model": model,
    }


def run_once(ctx: dict, user_prompt: str) -> dict:
    """One attempt. Returns a result dict; never raises for a normal failure."""
    cfg = ctx["challenge"]
    target = cfg["target"]
    enum = set(cfg["recommendation_enum"])

    t0 = time.monotonic()
    try:
        resp = ctx["client"].chat.completions.create(
            model=ctx["model"],
            temperature=cfg["llm"]["temperature"],
            max_tokens=cfg["llm"]["max_tokens"],
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": ctx["system_prompt"]},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as exc:  # network / auth / rate limit
        return {
            "prompt": user_prompt,
            "error": f"{type(exc).__name__}: {exc}",
            "latency_s": round(time.monotonic() - t0, 2),
        }

    raw = resp.choices[0].message.content or ""
    usage = resp.usage
    result = {
        "prompt": user_prompt,
        "raw": raw,
        "latency_s": round(time.monotonic() - t0, 2),
        "input_tokens": usage.prompt_tokens if usage else None,
        "output_tokens": usage.completion_tokens if usage else None,
    }

    try:
        parsed = json.loads(raw)
        rec = parsed.get("recommendation")
        result["recommendation"] = rec
        result["reply"] = parsed.get("reply")
        if rec not in enum:
            result["outcome"] = "invalid_enum"
        elif rec == target:
            result["outcome"] = "WIN"
        else:
            result["outcome"] = "lose"
    except json.JSONDecodeError:
        result["outcome"] = "bad_json"

    return result


def run_batch(ctx: dict, items: list[tuple[str, str]], concurrency: int) -> list[dict]:
    """items = [(label, prompt), …]. Runs them across a thread pool, prints each
    as it lands, returns results in input order."""
    results: list[dict | None] = [None] * len(items)
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        fut_to_idx = {
            pool.submit(run_once, ctx, prompt): i
            for i, (_label, prompt) in enumerate(items)
        }
        for fut in as_completed(fut_to_idx):
            i = fut_to_idx[fut]
            res = fut.result()
            res["label"] = items[i][0]
            results[i] = res
            mark = res.get("outcome", "error")
            detail = res.get("reply") or res.get("error") or ""
            print(f"[{mark:<12}] {items[i][0]:<22} {res['latency_s']:>5}s  {str(detail)[:60]}")
    return [r for r in results if r is not None]


def write_out(rows: list[dict], label: str) -> pathlib.Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = OUT_DIR / f"spike-{stamp}-{label}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def summarise(rows: list[dict], ctx: dict, wall_s: float) -> None:
    outcomes = Counter(r.get("outcome", "error") for r in rows)
    total = len(rows)
    wins = outcomes.get("WIN", 0)
    in_tok = sum(r.get("input_tokens") or 0 for r in rows)
    out_tok = sum(r.get("output_tokens") or 0 for r in rows)
    latencies = [r["latency_s"] for r in rows if "latency_s" in r]

    print("\n" + "=" * 64)
    for outcome, n in outcomes.most_common():
        print(f"  {outcome:<14} {n:>4}  ({n / total:.0%})")
    print("-" * 64)
    print(f"  win rate       {wins / total:>5.0%}")
    if latencies:
        print(
            f"  latency        median {statistics.median(latencies):.1f}s  "
            f"max {max(latencies):.1f}s   |   wall {wall_s:.1f}s for {total} calls"
        )

    price = PRICE_PER_MTOK.get(ctx["model"])
    if price and total:
        cost = (in_tok / 1e6) * price["input"] + (out_tok / 1e6) * price["output"]
        print(
            f"  tokens         {in_tok} in / {out_tok} out"
            f"  →  ~${cost / total:.5f}/attempt  (${cost:.4f} this run)"
        )
    print("=" * 64)


def iter_fixtures() -> list[tuple[str, str]]:
    """Reads backend/tests/fixtures/*.yaml. Each file is a YAML list; an item is
    either a plain string or a mapping with a `prompt` key. Label is
    `<file>:<n>` so `neutral:4` points back to the 4th entry of neutral.yaml —
    the same files test_guardrail_balance.py will use in S2."""
    if not FIXTURES_DIR.exists():
        return []
    out = []
    for path in sorted(FIXTURES_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        for i, item in enumerate(data, 1):
            prompt = item.get("prompt") if isinstance(item, dict) else item
            if prompt and str(prompt).strip():
                out.append((f"{path.stem}:{i}", str(prompt).strip()))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--prompt", help="a single user prompt to test")
    ap.add_argument("--suite", action="store_true", help="replay backend/tests/fixtures/*.txt")
    ap.add_argument("--repeat", type=int, default=1, help="run --prompt N times (stability check)")
    ap.add_argument("-c", "--concurrency", type=int, default=8, help="parallel requests (default 8)")
    args = ap.parse_args()

    if not args.prompt and not args.suite:
        ap.error("give --prompt or --suite")

    ctx = load_config()
    t0 = time.monotonic()

    # Single prompt, single run: keep it simple and show the full reply.
    if args.prompt and not args.suite and args.repeat == 1:
        res = run_once(ctx, args.prompt)
        print(f"[{res.get('outcome', 'error'):<12}] {res['latency_s']}s  rec={res.get('recommendation')}")
        print("\n" + (res.get("reply") or res.get("raw") or res.get("error", "")))
        summarise([res], ctx, time.monotonic() - t0)
        print(f"\nwrote {write_out([res], 'single').relative_to(REPO_ROOT)}")
        return

    if args.suite:
        items = iter_fixtures()
        if not items:
            print(f"No fixtures in {FIXTURES_DIR}. Add *.txt files, one prompt each.")
            return
        label = "suite"
    else:
        items = [(f"run {i + 1}/{args.repeat}", args.prompt) for i in range(args.repeat)]
        label = "repeat"

    rows = run_batch(ctx, items, args.concurrency)
    summarise(rows, ctx, time.monotonic() - t0)
    print(f"\nwrote {write_out(rows, label).relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
