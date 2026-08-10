from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/"app.py").read_text(encoding="utf-8")
runner=(ROOT/"scripts/hourly_runner.py").read_text(encoding="utf-8")
workflow=(ROOT/".github/workflows/observer_15m.yml").read_text(encoding="utf-8")
assert 'APP_VERSION = "13.0.0"' in app
assert 'LEARNING_STATE_FILE' in app
assert 'learning_engine.py' in runner and 'learning_engine.py' in workflow
strategy=app[app.index('elif selection=="Strategy Lab":'):app.index('elif selection=="Performance Lab":')]
assert 'Wallet equity comparison' not in strategy
assert 'No trade is currently good enough' in strategy
assert '<b>Performance Lab:</b> replay the trade, understand the AI decision' in app
assert 'Missed re-entry' in app
assert 'Waiting is a valid decision' in app
print(json.dumps({"status":"passed","tests":["learning wired","Strategy Lab simplified","Performance Lab lesson-first","Trading Desk simplified"]},indent=2))
