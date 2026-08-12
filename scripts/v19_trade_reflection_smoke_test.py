from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/"app.py").read_text(encoding="utf-8")
runner=(ROOT/"scripts/hourly_runner.py").read_text(encoding="utf-8")
assert 'APP_VERSION = "19.0.0"' in app
for x in ["reverse_trade_lab.py","trade_reflection_engine.py","missed_clue_miner.py","lesson_promotion_board.py"]:
    assert x in runner
assert "GOOD PROCESS / WRONG DIRECTION" in (ROOT/"scripts/trade_reflection_engine.py").read_text(encoding="utf-8")
assert "auto_promoted" in (ROOT/"scripts/lesson_promotion_board.py").read_text(encoding="utf-8")
print(json.dumps({"status":"passed","tests":["V19 wiring","separate process grade","reverse-trade research","sample-gated promotion"]},indent=2))
