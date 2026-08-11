from pathlib import Path
import importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/"app.py").read_text(encoding="utf-8")
runner=(ROOT/"scripts/hourly_runner.py").read_text(encoding="utf-8")
wf=(ROOT/".github/workflows/observer_15m.yml").read_text(encoding="utf-8")
assert 'APP_VERSION = "16.0.0"' in app
for text in ["Planned max loss","Current Engine Thinking","Closest Winner School match","Trade Lifecycle","AI operations centre"]:
    assert text in app
assert 'run("active_trade_casefiles.py"' in runner
assert "python scripts/active_trade_casefiles.py" in wf
assert "active_trade_thought_history.json" in wf
assert "active_trade_casefiles.json" in (ROOT/"config/persistent_data.json").read_text()
print(json.dumps({"status":"passed","tests":["V16 UI","hourly wiring","15m thought capture","persistent case files"]},indent=2))
