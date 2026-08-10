from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def run(script_name: str, required: bool = True) -> bool:
    command = [sys.executable, str(ROOT / "scripts" / script_name)]
    print(f"\n=== Running {script_name} ===")
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode == 0:
        return True
    if required:
        raise subprocess.CalledProcessError(result.returncode, command)
    print(
        f"WARNING: {script_name} exited with status {result.returncode}. "
        "Core hourly records were preserved and the workflow will continue."
    )
    return False


def main() -> int:
    run("bootstrap_runtime.py")
    run("external_intelligence.py")
    run("signal_recorder.py")
    run("research_desk.py")
    run("strategy_lab.py")
    run("microstructure_observer.py", required=False)
    run("observer_15m.py", required=False)
    run("risk_guardian.py")
    run("market_school.py", required=False)
    run("confidence_ledger.py", required=False)
    run("investment_committee.py")
    run("intelligence_hub.py", required=False)
    run("portfolio_manager.py")
    run("trade_review_engine.py", required=False)
    run("trade_diagnostics.py", required=False)
    run("trade_coach.py", required=False)
    run("learning_engine.py", required=False)
    run("challenger_arena.py", required=False)
    # Feed the new evidence back upstream for the next decision cycle.
    run("market_school.py", required=False)
    run("confidence_ledger.py", required=False)
    run("intelligence_hub.py", required=False)
    run("brain_health.py", required=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
