from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def run(script_name: str) -> None:
    command = [sys.executable, str(ROOT / "scripts" / script_name)]
    print(f"\n=== Running {script_name} ===")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    run("bootstrap_runtime.py")
    run("external_intelligence.py")
    run("signal_recorder.py")
    run("research_desk.py")
    run("strategy_lab.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
