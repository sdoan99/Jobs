#!/usr/bin/env python3
"""List connected free Hermes models and optionally live-test availability.

Usage:
  /home/ubuntu/Jobs/tokens/list_free_hermes_models_v2.py
  /home/ubuntu/Jobs/tokens/list_free_hermes_models_v2.py --no-tests
  /home/ubuntu/Jobs/tokens/list_free_hermes_models_v2.py --provider openrouter --limit 5
  /home/ubuntu/Jobs/tokens/list_free_hermes_models_v2.py --json

What v2 adds:
- Keeps the original free-model inventory behavior.
- Adds tiny live chat-completion probes to classify models as AVAILABLE,
  RATE_LIMITED, UPSTREAM_LIMITED, AUTH_ERROR, UNSUPPORTED_FOR_CHAT, etc.
- Uses direct OpenAI-compatible provider APIs to keep probes cheap.

Notes:
- Reads Hermes credentials from ~/.hermes/.env if present.
- Uses the Hermes venv at ~/.hermes/hermes-agent/venv for Hermes imports.
- Live probes consume a tiny amount of quota/free allowance.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

VENV_PYTHON = Path("/home/ubuntu/.hermes/hermes-agent/venv/bin/python")
HERMES_ENV = Path("/home/ubuntu/.hermes/.env")


def _load_env() -> None:
    if not HERMES_ENV.exists():
        return
    for line in HERMES_ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def _run_python_snippet(argv: list[str]) -> int:
    snippet = r'''
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any

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


def _short(text: Any, limit: int = 220) -> str:
    s = str(text or "").replace("\n", " ").replace("\r", " ").strip()
    while "  " in s:
        s = s.replace("  ", " ")
    return s[:limit]


def _classify_error(http_status: int | None, body: str, exc_type: str = "") -> str:
    hay = f"{exc_type} {body}".lower()
    if http_status == 429:
        if any(term in hay for term in ("upstream", "provider", "capacity", "overloaded", "temporarily unavailable")):
            return "UPSTREAM_LIMITED"
        return "RATE_LIMITED"
    if http_status in (401, 403):
        return "AUTH_ERROR"
    if http_status == 404:
        return "MODEL_NOT_FOUND"
    if any(term in hay for term in ("upstream rate", "upstream", "capacity", "overloaded", "temporarily unavailable", "no endpoints", "no providers available")):
        return "UPSTREAM_LIMITED"
    if any(term in hay for term in ("rate limit", "ratelimit", "quota", "too many requests")):
        return "RATE_LIMITED"
    if any(term in hay for term in ("not a chat", "unsupported", "modality", "audio", "music", "image", "vision only")):
        return "UNSUPPORTED_FOR_CHAT"
    if any(term in hay for term in ("timed out", "timeout")):
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
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        return int(e.code), raw, None


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
            m for m, p in pricing.items()
            if p.get("prompt") == "0" and p.get("completion") == "0"
        )
        entries.extend(ModelEntry("openrouter", "OpenRouter", m, "live zero pricing") for m in openrouter_free)
    except Exception as e:
        notes.append(f"OpenRouter discovery error: {type(e).__name__}: {e}")

    try:
        payload = fetch_nous_recommended_models(
            os.environ.get("NOUS_PORTAL_URL", ""),
            force_refresh=True,
        )
        nous_free: list[str] = []
        if isinstance(payload, dict):
            for entry in payload.get("freeRecommendedModels", []) or []:
                name = entry.get("modelName")
                if name:
                    nous_free.append(name)
        entries.extend(ModelEntry("nous", "Nous", m, "portal free recommendations") for m in sorted(set(nous_free)))
        notes.append(f"Nous free tier={check_nous_free_tier()}")
    except Exception as e:
        notes.append(f"Nous discovery error: {type(e).__name__}: {e}")

    try:
        opencode_free = sorted(
            m for m, d in curated_models_for_provider("opencode-zen", force_refresh=True)
            if d == "free" or m.endswith("-free") or m.endswith(":free")
        )
        entries.extend(ModelEntry("opencode-zen", "OpenCode Zen", m, "curated free label") for m in opencode_free)
    except Exception as e:
        notes.append(f"OpenCode Zen discovery error: {type(e).__name__}: {e}")

    for provider in ["openai-codex", "copilot", "deepseek"]:
        try:
            models = curated_models_for_provider(provider, force_refresh=True)
            freeish = [m for m, d in models if d == "free" or m.endswith(":free") or m.endswith("-free")]
            if freeish:
                entries.extend(ModelEntry(provider, provider, m, "curated free label") for m in sorted(set(freeish)))
            else:
                notes.append(f"{provider}: no free models detected")
        except Exception as e:
            notes.append(f"{provider}: discovery error ({type(e).__name__}: {e})")

    return entries, notes


def should_skip_chat_probe(entry: ModelEntry) -> str | None:
    m = entry.model.lower()
    if "lyria" in m:
        return "known non-chat audio/music model"
    return None


def probe_model(entry: ModelEntry, timeout: float) -> ProbeResult:
    skip_reason = should_skip_chat_probe(entry)
    if skip_reason:
        return ProbeResult(entry.provider, entry.model, "SKIPPED_NON_CHAT", None, None, skip_reason)

    api_key, base_url = _provider_runtime(entry.provider)
    if not api_key or not base_url:
        return ProbeResult(entry.provider, entry.model, "NO_CREDENTIALS", None, None, f"missing credential for {entry.provider}")

    url = base_url.rstrip("/") + "/chat/completions"
    start = time.monotonic()
    try:
        status_code, raw, parsed = _post_json(url, api_key, _chat_payload(entry.model), timeout)
        latency_ms = int((time.monotonic() - start) * 1000)
        if 200 <= status_code < 300:
            text = ""
            try:
                text = parsed["choices"][0]["message"].get("content", "") if parsed else ""
            except Exception:
                text = raw
            return ProbeResult(entry.provider, entry.model, "AVAILABLE", latency_ms, status_code, _short(text) or "ok")
        return ProbeResult(
            entry.provider,
            entry.model,
            _classify_error(status_code, raw),
            latency_ms,
            status_code,
            _short(raw),
        )
    except Exception as e:
        latency_ms = int((time.monotonic() - start) * 1000)
        return ProbeResult(
            entry.provider,
            entry.model,
            _classify_error(None, str(e), type(e).__name__),
            latency_ms,
            None,
            _short(f"{type(e).__name__}: {e}"),
        )


def _print_inventory(entries: list[ModelEntry], notes: list[str]) -> None:
    print("CONNECTED FREE MODELS")
    by_provider: dict[str, list[ModelEntry]] = {}
    for e in entries:
        by_provider.setdefault(e.display_provider, []).append(e)
    for display in ["OpenRouter", "Nous", "OpenCode Zen", "openai-codex", "copilot", "deepseek"]:
        items = by_provider.get(display, [])
        if not items:
            continue
        suffix = ""
        if display == "Nous":
            for n in notes:
                if n.startswith("Nous free tier="):
                    suffix = f" [{n.replace('Nous ', '')}]"
        print(f"{display} ({len(items)}){suffix}")
        for e in items:
            print(f"  - {e.model}")
    for note in notes:
        if note.startswith("Nous free tier="):
            continue
        print(note)


def _print_probe_results(results: list[ProbeResult]) -> None:
    print("\nLIVE MODEL TESTS")
    print("status legend: AVAILABLE means a tiny chat request succeeded now; RATE_LIMITED/UPSTREAM_LIMITED mean not usable right now")
    widths = {
        "provider": max([8] + [len(r.provider) for r in results]),
        "model": max([5] + [len(r.model) for r in results]),
        "status": max([6] + [len(r.status) for r in results]),
    }
    header = f"{'provider':<{widths['provider']}}  {'model':<{widths['model']}}  {'status':<{widths['status']}}  ms     http  detail"
    print(header)
    print("-" * len(header))
    for r in results:
        ms = "" if r.latency_ms is None else str(r.latency_ms)
        http = "" if r.http_status is None else str(r.http_status)
        print(f"{r.provider:<{widths['provider']}}  {r.model:<{widths['model']}}  {r.status:<{widths['status']}}  {ms:<5}  {http:<4}  {r.error_summary}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List free Hermes models and live-test current availability.")
    parser.add_argument("--no-tests", action="store_true", help="Only list free models; do not send live probes.")
    parser.add_argument("--provider", action="append", help="Filter to provider(s): openrouter, nous, opencode-zen, etc. Repeatable.")
    parser.add_argument("--model", action="append", help="Filter to model substring(s). Repeatable.")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of models probed/listed after filtering.")
    parser.add_argument("--timeout", type=float, default=20.0, help="Per-model probe timeout in seconds. Default: 20.")
    parser.add_argument("--sleep", type=float, default=0.5, help="Delay between probes to avoid self-inflicted rate limits. Default: 0.5.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args(argv)

    entries, notes = discover_free_models()
    if args.provider:
        wanted = {p.lower() for p in args.provider}
        entries = [e for e in entries if e.provider.lower() in wanted or e.display_provider.lower() in wanted]
        provider_note_prefixes = {
            "openrouter": ("openrouter",),
            "nous": ("nous",),
            "opencode-zen": ("opencode zen", "opencode-zen"),
            "openai-codex": ("openai-codex",),
            "copilot": ("copilot",),
            "deepseek": ("deepseek",),
        }
        allowed_prefixes = tuple(
            prefix
            for provider in wanted
            for prefix in provider_note_prefixes.get(provider, (provider,))
        )
        notes = [n for n in notes if n.lower().startswith(allowed_prefixes)]
    if args.model:
        needles = [m.lower() for m in args.model]
        entries = [e for e in entries if any(n in e.model.lower() for n in needles)]
    if args.limit and args.limit > 0:
        entries = entries[: args.limit]

    results: list[ProbeResult] = []
    if not args.no_tests:
        for i, entry in enumerate(entries):
            results.append(probe_model(entry, timeout=args.timeout))
            if args.sleep > 0 and i < len(entries) - 1:
                time.sleep(args.sleep)

    if args.json:
        print(json.dumps({
            "models": [asdict(e) for e in entries],
            "notes": notes,
            "tests": [asdict(r) for r in results],
        }, indent=2, sort_keys=True))
        return 0

    _print_inventory(entries, notes)
    if args.no_tests:
        print("\nLIVE MODEL TESTS: skipped (--no-tests)")
    else:
        _print_probe_results(results)
        counts: dict[str, int] = {}
        for r in results:
            counts[r.status] = counts.get(r.status, 0) + 1
        if counts:
            summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
            print(f"\nSUMMARY: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.run(
        [str(VENV_PYTHON), "-c", snippet, *argv],
        env=env,
        text=True,
    )
    return proc.returncode


def main() -> int:
    _load_env()
    if not VENV_PYTHON.exists():
        print(f"Hermes venv python not found: {VENV_PYTHON}", file=sys.stderr)
        return 2
    return _run_python_snippet(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
