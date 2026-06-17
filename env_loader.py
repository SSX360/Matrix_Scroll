"""Minimal, dependency-free .env loader.

Loads KEY=VALUE pairs from a .env file at the repository root into os.environ.
Real environment variables always win — values from .env are only applied when a
key is not already set (os.environ.setdefault), so CI/secret managers override the
local file. Lines starting with '#' and blank lines are ignored; surrounding
single/double quotes on values are stripped.

Call env_loader.load() once near the top of an entrypoint. It is idempotent.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_ENV_PATH = ROOT / ".env"

_loaded = False


def _parse_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[len("export "):].strip()
    if "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    if not key:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return key, value


def load(path: Path | None = None, *, force: bool = False) -> bool:
    """Load .env into os.environ (setdefault). Returns True if a file was read.

    Idempotent: subsequent calls are no-ops unless force=True.
    """
    global _loaded
    if _loaded and not force:
        return False
    env_path = path or DEFAULT_ENV_PATH
    _loaded = True
    try:
        text = env_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    for raw in text.splitlines():
        parsed = _parse_line(raw)
        if parsed is None:
            continue
        key, value = parsed
        os.environ.setdefault(key, value)
    return True
