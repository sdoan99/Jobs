#!/usr/bin/env python3
"""Shared paths and environment loading for local Hermes utility scripts."""

from __future__ import annotations

import os
from pathlib import Path

HERMES_HOME = Path.home() / ".hermes"
HERMES_ENV = HERMES_HOME / ".env"
HERMES_VENV_PYTHON = HERMES_HOME / "hermes-agent" / "venv" / "bin" / "python"


def load_env(path: Path = HERMES_ENV) -> None:
    """Load simple KEY=VALUE entries from a Hermes .env file into os.environ."""
    if not path.exists():
        return

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
