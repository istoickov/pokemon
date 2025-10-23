from __future__ import annotations

from typing import Any


def format_message(kind: str, detail: str | None = None, **context: Any) -> str:
    parts = [kind]
    if detail:
        parts.append(f": {detail}")
    if context:
        ctx = " ".join(f"{k}={v}" for k, v in context.items())
        parts.append(f" | {ctx}")
    return "".join(parts)
