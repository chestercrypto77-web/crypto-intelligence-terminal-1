from __future__ import annotations

from pathlib import Path
import json
from typing import Any


def read_json(path: Path, default: Any) -> Any:
    """Read JSON safely and return a caller-supplied default on failure."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json_atomic(path: Path, payload: Any) -> None:
    """Write JSON through a temporary file to reduce partial-write risk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(path)
