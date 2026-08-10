from pathlib import Path
import importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/"app.py").read_text(encoding="utf-8")
assert 'APP_VERSION = "12.2.0"' in app
assert 'st.vega_lite_chart' in app
assert 'Why the AI entered' in app
assert 'What happened afterwards' in app
assert 'AI decision path' in app
assert 'Best after exit' in app

spec=importlib.util.spec_from_file_location("review",ROOT/"scripts/trade_review_engine.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

p={"position_id":"PYR_CASE","symbol":"PYR","direction":"LONG","signal":"EARLY BUY",
   "entry_time":"2026-08-07T00:00:00+00:00","exit_time":"2026-08-07T02:00:00+00:00",
   "entry_price":0.069034,"exit_price":0.066,"realised_return":-4.70,"realised_pnl":-469.56,
   "allocated_cash":10000,"exit_reason":"Observer returned neutral",
   "observer_evidence":{"rvol":1.5,"bullish_conditions":8,"bearish_conditions":2,"return_1h":1.0,"return_4h":2.0}}
history=[
 {"recorded_at":"2026-08-06T23:00:00+00:00","symbol":"PYR","price":0.067,"signal":"BUY WATCH"},
 {"recorded_at":"2026-08-07T00:00:00+00:00","symbol":"PYR","price":0.069034,"signal":"EARLY BUY"},
 {"recorded_at":"2026-08-07T01:00:00+00:00","symbol":"PYR","price":0.068,"signal":"BUY WATCH"},
 {"recorded_at":"2026-08-07T02:00:00+00:00","symbol":"PYR","price":0.066,"signal":"NEUTRAL"},
 {"recorded_at":"2026-08-07T04:00:00+00:00","symbol":"PYR","price":0.071,"signal":"BUY WATCH"},
 {"recorded_at":"2026-08-07T08:00:00+00:00","symbol":"PYR","price":0.0924,"signal":"EARLY BUY"}
]
r=m.review_trade("15M Observer",p,{"PYR":{"price":0.0924,"signal":"EARLY BUY","recorded_at":"2026-08-07T08:00:00+00:00"}},history,[],"2026-08-07T12:00:00+00:00")
assert len((r.get("replay") or {}).get("price_path") or [])>=5
events=(r.get("replay") or {}).get("events") or []
assert any(e.get("event")=="ENTRY" for e in events)
assert any(e.get("event")=="EXIT" for e in events)
assert any(e.get("event")=="REENTRY" for e in events)
assert (r.get("post_exit") or {}).get("best_directional_move_pct",0)>30
assert (r.get("post_exit") or {}).get("missed_move_value_on_original_capital",0)>3000
assert len((r.get("decision_replay") or {}).get("why_entered") or [])>=2
print(json.dumps({"status":"passed","tests":["price replay","entry marker","exit marker","re-entry marker","post-exit opportunity","plain-English decision replay"]},indent=2))
