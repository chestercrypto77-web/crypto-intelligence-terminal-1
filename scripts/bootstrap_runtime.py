from __future__ import annotations

from pathlib import Path
import json
import shutil


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TEMPLATES = DATA / "templates"
CONTRACT = ROOT / "config" / "persistent_data.json"


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    created = []
    preserved = []

    for filename in contract["files"]:
        destination = DATA / filename
        template = TEMPLATES / filename.replace(".json", ".template.json")

        if destination.exists():
            # Validate that the existing file is readable JSON, but never overwrite it.
            json.loads(destination.read_text(encoding="utf-8"))
            preserved.append(filename)
            continue

        if not template.exists():
            raise FileNotFoundError(f"Missing template: {template}")

        shutil.copyfile(template, destination)
        created.append(filename)

    print(json.dumps({
        "created": created,
        "preserved": preserved,
        "policy": "existing runtime records are never overwritten",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
