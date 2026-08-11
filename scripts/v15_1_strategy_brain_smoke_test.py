from pathlib import Path
import importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/"app.py").read_text(encoding="utf-8")
runner=(ROOT/"scripts/hourly_runner.py").read_text(encoding="utf-8")
assert 'APP_VERSION = "15.1.0"' in app
assert "What the AI has discovered" in app
assert "Connected brain status" in app
assert "Evidence maturity:" in app
assert 'run("strategy_brain_status.py"' in runner
assert runner.index('run("ai_scorecard.py"') < runner.index('run("strategy_brain_status.py"') < runner.index('run("cross_learning_bus.py"')
assert "strategy_brain_status.json" in (ROOT/"config/persistent_data.json").read_text()
print(json.dumps({"status":"passed","tests":["new Strategy Lab UI","strategy synthesis wiring","persistent template","cross-learning order"]},indent=2))
