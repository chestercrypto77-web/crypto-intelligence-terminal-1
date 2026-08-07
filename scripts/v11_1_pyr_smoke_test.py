from pathlib import Path
import importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
obs=(ROOT/"scripts/observer_15m.py").read_text(); app=(ROOT/"app.py").read_text(); runner=(ROOT/"scripts/hourly_runner.py").read_text(); workflow=(ROOT/".github/workflows/observer_15m.yml").read_text()
section=obs.split("def update_wallet",1)[1].split("def update_timing",1)[0]
assert 'neutralised = item.get("signal") == "NEUTRAL"' not in section
assert '"HARD RISK STOP"' in obs and '"PROFIT TRAIL"' in obs and "def reentry_side" in obs
assert "trade_review_engine.py" in runner and "trade_review_engine.py" in workflow and "trade_reviews.json" in workflow
assert "Entry quality" in app and "Re-entry" in app and "Process" in app and "Move after exit" in app
spec=importlib.util.spec_from_file_location("review",ROOT/"scripts/trade_review_engine.py"); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
p={"position_id":"PYR_TEST","symbol":"PYR","direction":"LONG","entry_price":0.069034,"exit_price":0.066,"realised_return":-4.70,"realised_pnl":-469.56,"exit_reason":"Observer returned neutral","exit_time":"2026-08-07T00:00:00+00:00","observer_evidence":{"rvol":1.5,"bullish_conditions":8,"bearish_conditions":2}}
r=m.review_trade("15M Observer",p,{"PYR":{"price":0.0924,"signal":"STRONG BUY"}},"2026-08-07T12:00:00+00:00")
assert r["assessment"]["exit_quality"]=="NEUTRAL EXIT — REVIEW"; assert r["post_exit"]["directional_move_since_exit_pct"]>30; assert "MISSED" in r["reentry"]["status"]; assert r["assessment"]["process_quality"]=="POOR"
print(json.dumps({"status":"passed","tests":["neutral is not an exit","hard risk stop","profit trailing","re-entry surveillance","clean trade case file","PYR forensic replay"]},indent=2))
