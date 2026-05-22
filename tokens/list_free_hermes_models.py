#!/usr/bin/env python3
"""List currently connected free Hermes model providers/models, grouped by provider.

Usage:
  /home/ubuntu/Jobs/tokens/list_free_hermes_models.py

Notes:
- Reads Hermes credentials from ~/.hermes/.env if present.
- Uses the Hermes venv at ~/.hermes/hermes-agent/venv for imports.
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


def _run_python_snippet() -> str:
    snippet = r'''
from hermes_cli.models import (
    check_nous_free_tier,
    curated_models_for_provider,
    fetch_models_with_pricing,
    fetch_nous_recommended_models,
)
import os

providers = ["openrouter", "nous", "opencode-zen", "openai-codex", "copilot", "deepseek"]

print("CONNECTED FREE MODELS")

# OpenRouter: identify all models whose live pricing is zero/zero.
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
    print(f"OpenRouter ({len(openrouter_free)})")
    for m in openrouter_free:
        print(f"  - {m}")
except Exception as e:
    print(f"OpenRouter (error: {type(e).__name__}: {e})")

# Nous: use the live Portal free-recommendations endpoint.
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
    nous_free = sorted(set(nous_free))
    print(f"Nous ({len(nous_free)}) [free tier={check_nous_free_tier()}]")
    for m in nous_free:
        print(f"  - {m}")
except Exception as e:
    print(f"Nous (error: {type(e).__name__}: {e})")

# OpenCode Zen: currently surfaced free-labeled catalog entries.
try:
    opencode_free = sorted(
        m for m, d in curated_models_for_provider("opencode-zen", force_refresh=True)
        if d == "free" or m.endswith("-free") or m.endswith(":free")
    )
    print(f"OpenCode Zen ({len(opencode_free)})")
    for m in opencode_free:
        print(f"  - {m}")
except Exception as e:
    print(f"OpenCode Zen (error: {type(e).__name__}: {e})")

# Providers checked but not currently showing free models.
for provider in ["openai-codex", "copilot", "deepseek"]:
    try:
        models = curated_models_for_provider(provider, force_refresh=True)
        freeish = [m for m, d in models if d == "free" or m.endswith(":free") or m.endswith("-free")]
        if freeish:
            print(f"{provider} ({len(freeish)})")
            for m in freeish:
                print(f"  - {m}")
        else:
            print(f"{provider}: no free models detected")
    except Exception as e:
        print(f"{provider}: error ({type(e).__name__}: {e})")
'''

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.run(
        [str(VENV_PYTHON), "-c", snippet],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}")
    return proc.stdout


def main() -> int:
    _load_env()
    out = _run_python_snippet()
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
