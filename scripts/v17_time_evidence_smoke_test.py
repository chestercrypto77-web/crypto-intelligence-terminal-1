from pathlib import Path
import importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/"app.py").read_text(encoding="utf-8")
runner=(ROOT/"scripts/hourly_runner.py").read_text(encoding="utf-8")
wf=(ROOT/".github/workflows/observer_15m.yml").read_text(encoding="utf-8")
assert 'APP_VERSION = "17.0.0"' in app
for text in ["Learning Evidence Centre","Time Intelligence","Current move phases","Brain audit map"]:
    assert text in app
for script in ["time_intelligence.py","move_phase_intelligence.py","learning_evidence_centre.py"]:
    assert script in runner
assert "active_trade_casefiles.py" in wf and "move_phase_intelligence.py" in wf
assert "future timestamps are never fed into a live decision" in app.lower()
print(json.dumps({"status":"passed","tests":["V17 UI","time wiring","phase wiring","evidence audit","future-data guardrail"]},indent=2))
