from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/"app.py").read_text(encoding="utf-8")
runner=(ROOT/"scripts/hourly_runner.py").read_text(encoding="utf-8")
micro=(ROOT/".github/workflows/microstructure_5m.yml").read_text(encoding="utf-8")
obs=(ROOT/".github/workflows/observer_15m.yml").read_text(encoding="utf-8")
assert 'APP_VERSION = "18.0.0"' in app
for txt in ["Observer verification","Adaptive attention","Brain communication","Strategy data integrity","External intelligence"]:
    assert txt in app
assert 'cron: "*/5 * * * *"' in micro
assert 'cron: "2,17,32,47 * * * *"' in obs
for script in ["external_attention.py","adaptive_attention.py","observer_audit.py","brain_audit.py","strategy_integrity.py","collect_brain_receipts.py"]:
    assert script in runner
assert "strategy_stop_loss_pct" in (ROOT/"scripts/strategy_lab.py").read_text(encoding="utf-8")
print(json.dumps({"status":"passed","tests":["5m schedule","15m schedule","audit UI","adaptive attention","external attention","strategy risk stop","receipt wiring"]},indent=2))
