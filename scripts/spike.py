#!/usr/bin/env python3
"""spike.py — S0 design tooling.

Talks to the LLM directly. No FastAPI, no Docker, no telemetry. Its whole
purpose is to answer the only question that matters in S0: is this game
winnable and fun?

    py spike.py --prompt "Trời Hà Nội hôm nay 38 độ, cần gì đó uống nhanh."
    py spike.py --suite                      # replay backend/tests/fixtures/
    py spike.py --repeat 10 --prompt "..."   # measure stability

Reads challenge.yaml for the target, the enum, and the llm.* settings, and the
system prompt from backend/app/challenge/prompts/. Config for the endpoint comes
from .env (LLM_BASE_URL, LLM_MODEL, LLM_API_KEY).

Every run also appends JSON lines to scripts/out/, which is gitignored because
prompt experiments are noisy and occasionally reveal answers. Log the useful
results into docs/solution-paths.md by hand.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
from collections import Counter

import yaml
from dotenv import load_dotenv
from openai import OpenAI

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
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
        return {"prompt": user_prompt, "error": f"{type(exc).__name__}: {exc}"}

    raw = resp.choices[0].message.content or ""
    usage = resp.usage
    result = {
        "prompt": user_prompt,
        "raw": raw,
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


def write_out(rows: list[dict], label: str) -> pathlib.Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = OUT_DIR / f"spike-{stamp}-{label}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def summarise(rows: list[dict], ctx: dict) -> None:
    outcomes = Counter(r.get("outcome", "error") for r in rows)
    total = len(rows)
    wins = outcomes.get("WIN", 0)
    in_tok = sum(r.get("input_tokens") or 0 for r in rows)
    out_tok = sum(r.get("output_tokens") or 0 for r in rows)

    print("\n" + "=" * 60)
    for outcome, n in outcomes.most_common():
        print(f"  {outcome:<14} {n:>4}  ({n / total:.0%})")
    print("-" * 60)
    print(f"  win rate       {wins / total:>5.0%}")

    price = PRICE_PER_MTOK.get(ctx["model"])
    if price and total:
        cost = (in_tok / 1e6) * price["input"] + (out_tok / 1e6) * price["output"]
        print(
            f"  tokens         {in_tok} in / {out_tok} out"
            f"  →  ~${cost / total:.5f}/attempt  (${cost:.4f} this run)"
        )
    print("=" * 60)


def iter_fixtures() -> list[tuple[str, str]]:
    if not FIXTURES_DIR.exists():
        return []
    out = []
    for path in sorted(FIXTURES_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8").strip()
        if text:
            out.append((path.stem, text))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prompt", help="a single user prompt to test")
    ap.add_argument("--suite", action="store_true", help="replay backend/tests/fixtures/*.txt")
    ap.add_argument("--repeat", type=int, default=1, help="run --prompt N times (stability check)")
    args = ap.parse_args()

    if not args.prompt and not args.suite:
        ap.error("give --prompt or --suite")

    ctx = load_config()
    rows: list[dict] = []

    if args.suite:
        for name, prompt in iter_fixtures():
            res = run_once(ctx, prompt)
            res["fixture"] = name
            rows.append(res)
            mark = res.get("outcome", "error")
            print(f"[{mark:<12}] {name}: {str(res.get('reply', res.get('error', '')))[:80]}")
        if not rows:
            print(f"No fixtures in {FIXTURES_DIR}. Add *.txt files, one prompt each.")
            return
        label = "suite"
    else:
        for i in range(args.repeat):
            res = run_once(ctx, args.prompt)
            rows.append(res)
            mark = res.get("outcome", "error")
            print(f"[{i + 1:>3}/{args.repeat}] {mark:<12} rec={res.get('recommendation')}")
            if args.repeat == 1:
                print("\n" + (res.get("reply") or res.get("raw") or res.get("error", "")))
        label = "repeat" if args.repeat > 1 else "single"

    summarise(rows, ctx)
    print(f"\nwrote {write_out(rows, label).relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
