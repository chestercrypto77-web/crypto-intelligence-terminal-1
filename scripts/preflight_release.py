from __future__ import annotations

from pathlib import Path
import ast
import json
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    required = [
        "app.py",
        "requirements.txt",
        "holdings.json",
        "config/external_sources.json",
        "config/persistent_data.json",
        "scripts/bootstrap_runtime.py",
        "scripts/hourly_runner.py",
        "scripts/external_intelligence.py",
        "scripts/signal_recorder.py",
        ".github/workflows/hourly_signal_recorder.yml",
    ]

    missing = [name for name in required if not (ROOT / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing required files: {missing}")

    for path in ROOT.rglob("*.py"):
        if "__pycache__" not in path.parts:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    json.loads((ROOT / "holdings.json").read_text(encoding="utf-8"))
    json.loads((ROOT / "config" / "external_sources.json").read_text(encoding="utf-8"))
    contract = json.loads((ROOT / "config" / "persistent_data.json").read_text(encoding="utf-8"))

    live_runtime_names = set(contract["files"])
    release_runtime_files = {
        path.name for path in (ROOT / "data").glob("*.json")
        if path.is_file()
    }
    unsafe = sorted(live_runtime_names & release_runtime_files)
    if unsafe:
        raise RuntimeError(
            "Release contains live runtime filenames and could overwrite records: "
            + ", ".join(unsafe)
        )

    print(json.dumps({
        "status": "passed",
        "required_files": len(required),
        "python_files_checked": len(list(ROOT.rglob("*.py"))),
        "persistent_files_protected": sorted(live_runtime_names),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
