#!/usr/bin/env python3
"""List connected free Hermes models and optionally live-test availability."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from hermes_env import HERMES_VENV_PYTHON, load_env


def _running_in_hermes_venv() -> bool:
    return Path(sys.executable).resolve() == HERMES_VENV_PYTHON.resolve()


def _reexec_in_hermes_venv() -> None:
    if _running_in_hermes_venv() or not HERMES_VENV_PYTHON.exists():
        return

    load_env()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.run(
        [str(HERMES_VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]],
        env=env,
        text=True,
        check=False,
    )
    raise SystemExit(proc.returncode)


_reexec_in_hermes_venv()

from hermes_cli.models import (
    check_nous_free_tier,
    curated_models_for_provider,
    fetch_models_with_pricing,
    fetch_nous_recommended_models,
)


@dataclass
class ModelEntry:
    provider: str
    display_provider: str
    model: str
    source: str


@dataclass
class ProbeResult:
    provider: str
    model: str
    status: str
    latency_ms: int | None
    http_status: int | None
    error_summary: str


BENCH_DATA: dict[str, dict[str, str]] = {
    # ── Connected / Available ──
    "arcee-ai/trinity-large-thinking":                 {"provider": "OpenRouter",   "ctx": "262K–512K", "tb": "—",       "swe": "63.2% †",  "lcb": "—"},
    "baidu/cobuddy":                                   {"provider": "OpenRouter",   "ctx": "?",          "tb": "—",       "swe": "—",        "lcb": "—"},
    "liquid/lfm-2.5-1.2b-instruct":                    {"provider": "OpenRouter",   "ctx": "32K",        "tb": "—",       "swe": "—",        "lcb": "—"},
    "liquid/lfm-2.5-1.2b-thinking":                    {"provider": "OpenRouter",   "ctx": "32K",        "tb": "0.0%",    "swe": "—",        "lcb": "—"},
    "minimax/minimax-m2.5":                            {"provider": "OpenRouter",   "ctx": "200K",       "tb": "51.7%",   "swe": "80.2%",    "lcb": "—"},
    "nvidia/nemotron-3-nano-30b-a3b":                  {"provider": "OpenRouter",   "ctx": "1M",         "tb": "8.5%",    "swe": "—",        "lcb": "68.3%"},
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning":   {"provider": "OpenRouter",   "ctx": "256K",       "tb": "8.3%",    "swe": "—",        "lcb": "—"},
    "nvidia/nemotron-3-super-120b-a12b":               {"provider": "OpenRouter",   "ctx": "1M",         "tb": "31.0%",   "swe": "60.5% *",  "lcb": "78.7%"},
    "nvidia/nemotron-nano-12b-v2-vl":                  {"provider": "OpenRouter",   "ctx": "128K",       "tb": "—",       "swe": "—",        "lcb": "69.4%"},
    "nvidia/nemotron-nano-9b-v2":                      {"provider": "OpenRouter",   "ctx": "128K",       "tb": "0.8%",    "swe": "—",        "lcb": "71.1%"},
    "openai/gpt-oss-120b":                             {"provider": "OpenRouter",   "ctx": "131K",       "tb": "—",       "swe": "62.4% ‡",  "lcb": "81.9%"},
    "openai/gpt-oss-20b":                              {"provider": "OpenRouter",   "ctx": "131K",       "tb": "—",       "swe": "60.7% ‡",  "lcb": "—"},
    "openrouter/free":                                 {"provider": "OpenRouter",   "ctx": "200K",       "tb": "—",       "swe": "—",        "lcb": "—"},
    "openrouter/owl-alpha":                            {"provider": "OpenRouter",   "ctx": "1M",         "tb": "—",       "swe": "—",        "lcb": "—"},
    "poolside/laguna-m.1":                             {"provider": "OpenRouter",   "ctx": "131K",       "tb": "40.7%",  "swe": "72.5% †",  "lcb": "—"},
    "poolside/laguna-xs.2":                            {"provider": "OpenRouter",   "ctx": "131K",       "tb": "30.1%",  "swe": "68.2% †",  "lcb": "—"},
    "z-ai/glm-4.5-air":                                {"provider": "OpenRouter",   "ctx": "128K",       "tb": "30.0%",  "swe": "57.6%",    "lcb": "70.7%"},
    "stepfun/step-3.5-flash":                          {"provider": "Nous",         "ctx": "256K",       "tb": "51.0%",  "swe": "74.4%",    "lcb": "86.4%"},
    "nemotron-3-super":                                {"provider": "OpenCode Zen", "ctx": "1M",         "tb": "31.0%",  "swe": "60.5% *",  "lcb": "78.7%"},
    # ── Upstream Limited ──
    "cognitivecomputations/dolphin-mistral-24b-venice-edition": {"provider": "OpenRouter", "ctx": "32K",   "tb": "—",     "swe": "—",     "lcb": "—"},
    "google/gemma-4-26b-a4b-it":                       {"provider": "OpenRouter",   "ctx": "256K",       "tb": "—",       "swe": "~63%",    "lcb": "77.1%"},
    "google/gemma-4-31b-it":                           {"provider": "OpenRouter",   "ctx": "256K",       "tb": "—",       "swe": "~63%",    "lcb": "80.0%"},
    "meta-llama/llama-3.2-3b-instruct":                {"provider": "OpenRouter",   "ctx": "128K",       "tb": "—",       "swe": "—",       "lcb": "—"},
    "meta-llama/llama-3.3-70b-instruct":               {"provider": "OpenRouter",   "ctx": "128K",       "tb": "—",       "swe": "~72%",    "lcb": "—"},
    "nousresearch/hermes-3-llama-3.1-405b":            {"provider": "OpenRouter",   "ctx": "131K",       "tb": "—",       "swe": "—",       "lcb": "—"},
    "qwen/qwen3-coder":                                {"provider": "OpenRouter",   "ctx": "256K",       "tb": "37.5%",  "swe": "69.6%",    "lcb": "70.7%"},
    "qwen/qwen3-next-80b-a3b-instruct":                {"provider": "OpenRouter",   "ctx": "262K",       "tb": "—",       "swe": "—",       "lcb": "56.6%"},
    # ── Rate Limited ──
    "deepseek/deepseek-v4-flash":                      {"provider": "OpenRouter",   "ctx": "1M",         "tb": "56.9%",  "swe": "79.0%",   "lcb": "91.6%"},
    "deepseek-v4-flash":                               {"provider": "OpenCode Zen", "ctx": "1M",         "tb": "49.1%",  "swe": "73.7%",   "lcb": "55.2%"},
    # ── Auth Error / Expired ──
    "minimax-m2.5":                                    {"provider": "OpenCode Zen", "ctx": "200K",       "tb": "51.7%",  "swe": "80.2%",   "lcb": "—"},
    "qwen3.6-plus":                                    {"provider": "OpenCode Zen", "ctx": "1M",         "tb": "61.6%",  "swe": "78.8%",   "lcb": "87.1%"},
}


def _resolve_bench_data(model: str) -> dict[str, str]:
    key = model.removesuffix(":free").removesuffix("-free")
    for candidate in (model, key, key.rsplit("/", 1)[-1] if "/" in key else key):
        if candidate in BENCH_DATA:
            return BENCH_DATA[candidate]
    return {"provider": "?", "ctx": "?", "tb": "—", "swe": "—", "lcb": "—"}


def _short(text: Any, limit: int = 220) -> str:
    summary = str(text or "").replace("\n", " ").replace("\r", " ").strip()
    while "  " in summary:
        summary = summary.replace("  ", " ")
    return summary[:limit]


def _is_free_model(model: str, descriptor: str) -> bool:
    return descriptor == "free" or model.endswith("-free") or model.endswith(":free")


def _classify_error(http_status: int | None, body: str, exc_type: str = "") -> str:
    haystack = f"{exc_type} {body}".lower()
    if http_status == 429:
        if any(term in haystack for term in ("upstream", "provider", "capacity", "overloaded", "temporarily unavailable")):
            return "UPSTREAM_LIMITED"
        return "RATE_LIMITED"
    if http_status in (401, 403):
        return "AUTH_ERROR"
    if http_status == 404:
        return "MODEL_NOT_FOUND"
    if any(term in haystack for term in ("upstream rate", "upstream", "capacity", "overloaded", "temporarily unavailable", "no endpoints", "no providers available")):
        return "UPSTREAM_LIMITED"
    if any(term in haystack for term in ("rate limit", "ratelimit", "quota", "too many requests")):
        return "RATE_LIMITED"
    if any(term in haystack for term in ("not a chat", "unsupported", "modality", "audio", "music", "image", "vision only")):
        return "UNSUPPORTED_FOR_CHAT"
    if any(term in haystack for term in ("timed out", "timeout")):
        return "TIMEOUT"
    if http_status is not None and 500 <= http_status <= 599:
        return "TRANSIENT_ERROR"
    return "ERROR"


def _chat_payload(model: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with OK only."}],
        "temperature": 0,
        "max_tokens": 3,
    }


def _post_json(url: str, api_key: str, payload: dict[str, Any], timeout: float) -> tuple[int, str, dict[str, Any] | None]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Hermes-Agent-Free-Model-Probe/1.0",
            "HTTP-Referer": "https://github.com/NousResearch/hermes-agent",
            "X-Title": "Hermes free model availability probe",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = None
            return int(resp.status), raw, parsed
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return int(exc.code), raw, None


def _resolve_nous_runtime() -> tuple[str | None, str]:
    env_key = (os.environ.get("NOUS_API_KEY") or "").strip()
    env_base = (os.environ.get("NOUS_INFERENCE_BASE_URL") or "https://inference.nousresearch.com/v1").strip().rstrip("/")
    if env_key:
        return env_key, env_base
    try:
        from hermes_cli.auth import resolve_nous_runtime_credentials

        creds = resolve_nous_runtime_credentials(
            min_key_ttl_seconds=60,
            timeout_seconds=float(os.getenv("HERMES_NOUS_TIMEOUT_SECONDS", "15")),
        )
        key = str(creds.get("api_key") or "").strip()
        base = str(creds.get("base_url") or env_base).strip().rstrip("/")
        return (key or None), base
    except Exception:
        return None, env_base


def _provider_runtime(provider: str) -> tuple[str | None, str | None]:
    if provider == "openrouter":
        return (os.environ.get("OPENROUTER_API_KEY") or "").strip() or None, "https://openrouter.ai/api/v1"
    if provider == "opencode-zen":
        return (os.environ.get("OPENCODE_ZEN_API_KEY") or "").strip() or None, "https://opencode.ai/zen/v1"
    if provider == "nous":
        return _resolve_nous_runtime()
    return None, None


def discover_free_models() -> tuple[list[ModelEntry], list[str]]:
    entries: list[ModelEntry] = []
    notes: list[str] = []

    try:
        pricing = fetch_models_with_pricing(
            api_key=os.environ.get("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api",
            force_refresh=True,
        )
        openrouter_free = sorted(
            model for model, price in pricing.items()
            if price.get("prompt") == "0" and price.get("completion") == "0"
        )
        entries.extend(ModelEntry("openrouter", "OpenRouter", model, "live zero pricing") for model in openrouter_free)
    except Exception as exc:
        notes.append(f"OpenRouter discovery error: {type(exc).__name__}: {exc}")

    try:
        payload = fetch_nous_recommended_models(
            os.environ.get("NOUS_PORTAL_URL", ""),
            force_refresh=True,
        )
        nous_free = []
        if isinstance(payload, dict):
            for entry in payload.get("freeRecommendedModels", []) or []:
                name = entry.get("modelName")
                if name:
                    nous_free.append(name)
        entries.extend(ModelEntry("nous", "Nous", model, "portal free recommendations") for model in sorted(set(nous_free)))
        notes.append(f"Nous free tier={check_nous_free_tier()}")
    except Exception as exc:
        notes.append(f"Nous discovery error: {type(exc).__name__}: {exc}")

    try:
        opencode_free = sorted(
            model for model, descriptor in curated_models_for_provider("opencode-zen", force_refresh=True)
            if _is_free_model(model, descriptor)
        )
        entries.extend(ModelEntry("opencode-zen", "OpenCode Zen", model, "curated free label") for model in opencode_free)
    except Exception as exc:
        notes.append(f"OpenCode Zen discovery error: {type(exc).__name__}: {exc}")

    for provider in ["openai-codex", "copilot", "deepseek"]:
        try:
            freeish = sorted(
                model for model, descriptor in curated_models_for_provider(provider, force_refresh=True)
                if _is_free_model(model, descriptor)
            )
            if freeish:
                entries.extend(ModelEntry(provider, provider, model, "curated free label") for model in freeish)
            else:
                notes.append(f"{provider}: no free models detected")
        except Exception as exc:
            notes.append(f"{provider}: discovery error ({type(exc).__name__}: {exc})")

    return entries, notes


def should_skip_chat_probe(entry: ModelEntry) -> str | None:
    if "lyria" in entry.model.lower():
        return "known non-chat audio/music model"
    return None


def probe_model(entry: ModelEntry, timeout: float) -> ProbeResult:
    skip_reason = should_skip_chat_probe(entry)
    if skip_reason:
        return ProbeResult(entry.provider, entry.model, "SKIPPED_NON_CHAT", None, None, skip_reason)

    api_key, base_url = _provider_runtime(entry.provider)
    if not api_key or not base_url:
        return ProbeResult(entry.provider, entry.model, "NO_CREDENTIALS", None, None, f"missing credential for {entry.provider}")

    start = time.monotonic()
    try:
        status_code, raw, parsed = _post_json(f"{base_url.rstrip('/')}/chat/completions", api_key, _chat_payload(entry.model), timeout)
        latency_ms = int((time.monotonic() - start) * 1000)
        if 200 <= status_code < 300:
            try:
                text = parsed["choices"][0]["message"].get("content", "") if parsed else ""
            except Exception:
                text = raw
            return ProbeResult(entry.provider, entry.model, "AVAILABLE", latency_ms, status_code, _short(text) or "ok")
        return ProbeResult(entry.provider, entry.model, _classify_error(status_code, raw), latency_ms, status_code, _short(raw))
    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        return ProbeResult(
            entry.provider,
            entry.model,
            _classify_error(None, str(exc), type(exc).__name__),
            latency_ms,
            None,
            _short(f"{type(exc).__name__}: {exc}"),
        )


def _filter_notes(notes: list[str], providers: list[str]) -> list[str]:
    note_prefixes = {
        "openrouter": ("openrouter",),
        "nous": ("nous",),
        "opencode-zen": ("opencode zen", "opencode-zen"),
        "openai-codex": ("openai-codex",),
        "copilot": ("copilot",),
        "deepseek": ("deepseek",),
    }
    wanted = {provider.lower() for provider in providers}
    allowed_prefixes = tuple(
        prefix
        for provider in wanted
        for prefix in note_prefixes.get(provider, (provider,))
    )
    return [note for note in notes if note.lower().startswith(allowed_prefixes)]


def _print_inventory(entries: list[ModelEntry], notes: list[str]) -> None:
    print("CONNECTED FREE MODELS")
    by_provider: dict[str, list[ModelEntry]] = {}
    for entry in entries:
        by_provider.setdefault(entry.display_provider, []).append(entry)

    for display in ["OpenRouter", "Nous", "OpenCode Zen", "openai-codex", "copilot", "deepseek"]:
        items = by_provider.get(display, [])
        if not items:
            continue
        suffix = ""
        if display == "Nous":
            suffix = next((f" [{note.replace('Nous ', '')}]" for note in notes if note.startswith("Nous free tier=")), "")
        print(f"{display} ({len(items)}){suffix}")
        for entry in items:
            print(f"  - {entry.model}")

    for note in notes:
        if not note.startswith("Nous free tier="):
            print(note)


def _print_probe_results(results: list[ProbeResult]) -> None:
    print("\nLIVE MODEL TESTS")
    print("status legend: AVAILABLE means a tiny chat request succeeded now; RATE_LIMITED/UPSTREAM_LIMITED mean not usable right now")
    widths = {
        "provider": max([8] + [len(result.provider) for result in results]),
        "model": max([5] + [len(result.model) for result in results]),
        "status": max([6] + [len(result.status) for result in results]),
    }
    header = f"{'provider':<{widths['provider']}}  {'model':<{widths['model']}}  {'status':<{widths['status']}}  ms     http  detail"
    print(header)
    print("-" * len(header))
    for result in results:
        ms = "" if result.latency_ms is None else str(result.latency_ms)
        http = "" if result.http_status is None else str(result.http_status)
        print(f"{result.provider:<{widths['provider']}}  {result.model:<{widths['model']}}  {result.status:<{widths['status']}}  {ms:<5}  {http:<4}  {result.error_summary}")


BENCH_STATUS_TITLES = {
    "AVAILABLE": "CONNECTED",
    "UPSTREAM_LIMITED": "UPSTREAM LIMITED",
    "RATE_LIMITED": "RATE LIMITED",
    "AUTH_ERROR": "AUTH ERROR / EXPIRED",
}

BENCH_FOOTNOTES = {
    "†": "Harness-dependent score (proprietary / custom scaffold — not directly comparable).",
    "‡": "OpenAI proprietary scaffold (~26% on open harness).",
    "*": "OpenHands harness (not SWE-Bench Verified subset).",
}


def _print_bench_tables(results: list[ProbeResult]) -> None:
    SEP = "  "
    COLS = ["Provider", "Model", "Context Window", "Terminal Bench", "SWE-Bench Verified", "LiveCode Bench"]

    seen_footnotes: set[str] = set()

    for status, title in BENCH_STATUS_TITLES.items():
        group = [r for r in results if r.status == status]
        if not group:
            continue

        rows: list[dict[str, str]] = []
        for r in group:
            b = _resolve_bench_data(r.model)
            rows.append({
                "Provider": b["provider"] if b["provider"] != "?" else r.provider,
                "Model": r.model,
                "Context Window": b["ctx"],
                "Terminal Bench": b["tb"],
                "SWE-Bench Verified": b["swe"],
                "LiveCode Bench": b["lcb"],
            })
            for ch in b["tb"] + b["swe"] + b["lcb"]:
                if ch in BENCH_FOOTNOTES:
                    seen_footnotes.add(ch)

        widths = {c: max(len(c), max(len(r[c]) for r in rows)) for c in COLS}
        hdr = SEP.join(f"{c:<{widths[c]}}" for c in COLS)
        rule = "-" * len(hdr)

        print(f"\n{title}")
        print(hdr)
        print(rule)
        for row in rows:
            print(SEP.join(f"{row[c]:<{widths[c]}}" for c in COLS))

    if seen_footnotes:
        print()
        for ch in sorted(seen_footnotes):
            print(f"  {ch} {BENCH_FOOTNOTES[ch]}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List free Hermes models and live-test current availability.")
    parser.add_argument("--no-tests", action="store_true", help="Only list free models; do not send live probes.")
    parser.add_argument("--provider", action="append", help="Filter to provider(s): openrouter, nous, opencode-zen, etc. Repeatable.")
    parser.add_argument("--model", action="append", help="Filter to model substring(s). Repeatable.")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of models probed/listed after filtering.")
    parser.add_argument("--timeout", type=float, default=20.0, help="Per-model probe timeout in seconds. Default: 20.")
    parser.add_argument("--sleep", type=float, default=0.5, help="Delay between probes to avoid self-inflicted rate limits. Default: 0.5.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument("--quiet-no-tests", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_env()
    args = parse_args(argv)

    entries, notes = discover_free_models()
    if args.provider:
        wanted = {provider.lower() for provider in args.provider}
        entries = [
            entry for entry in entries
            if entry.provider.lower() in wanted or entry.display_provider.lower() in wanted
        ]
        notes = _filter_notes(notes, args.provider)
    if args.model:
        needles = [model.lower() for model in args.model]
        entries = [entry for entry in entries if any(needle in entry.model.lower() for needle in needles)]
    if args.limit and args.limit > 0:
        entries = entries[: args.limit]

    results: list[ProbeResult] = []
    if not args.no_tests:
        for index, entry in enumerate(entries):
            results.append(probe_model(entry, timeout=args.timeout))
            if args.sleep > 0 and index < len(entries) - 1:
                time.sleep(args.sleep)

    if args.json:
        print(json.dumps({
            "models": [asdict(entry) for entry in entries],
            "notes": notes,
            "tests": [asdict(result) for result in results],
        }, indent=2, sort_keys=True))
        return 0

    _print_inventory(entries, notes)
    if args.no_tests:
        if not args.quiet_no_tests:
            print("\nLIVE MODEL TESTS: skipped (--no-tests)")
    else:
        _print_probe_results(results)
        _print_bench_tables(results)
        counts: dict[str, int] = {}
        for result in results:
            counts[result.status] = counts.get(result.status, 0) + 1
        if counts:
            summary = ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
            print(f"\nSUMMARY: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
