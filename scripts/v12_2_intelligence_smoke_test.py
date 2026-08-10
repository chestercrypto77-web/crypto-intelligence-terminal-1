from pathlib import Path
import importlib.util,json,tempfile
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/"app.py").read_text(encoding="utf-8")
runner=(ROOT/"scripts/hourly_runner.py").read_text(encoding="utf-8")
pm=(ROOT/"scripts/portfolio_manager.py").read_text(encoding="utf-8")

assert 'APP_VERSION = "14.0.0"' in app
assert 'trade_diagnostics.py' in runner
assert 'challenger_arena.py' in runner
assert 'Challenger arena' in app
assert 'Best while held' in app and 'Worst while held' in app
assert "'entry_snapshot':" in pm

spec=importlib.util.spec_from_file_location("diag",ROOT/"scripts/trade_diagnostics.py")
diag=importlib.util.module_from_spec(spec); spec.loader.exec_module(diag)
r={"position_id":"X","symbol":"X","wallet":"TEST","direction":"LONG","realised_return":-1.2,
   "realised_pnl":-12,"maximum_favourable_excursion_pct":0.1,
   "maximum_adverse_excursion_pct":-1.4,"exit_reason":"EXIT",
   "post_exit":{"best_directional_move_pct":1.0},"assessment":{"entry_quality":"MIXED"}}
d=diag.diagnose(r)
assert d["category"]=="ENTRY NEVER WORKED"

r2=dict(r); r2.update({"realised_return":-0.5,"maximum_favourable_excursion_pct":4.5})
d2=diag.diagnose(r2)
assert d2["category"]=="WINNER GIVEN BACK"

spec2=importlib.util.spec_from_file_location("arena",ROOT/"scripts/challenger_arena.py")
arena=importlib.util.module_from_spec(spec2); spec2.loader.exec_module(arena)
s={"signal":"STRONG BUY","rvol":1.5,"rvol_delta":0.3,"return_4h":2,"return_24h":4}
c={"decision":{"direction":"LONG","action":"BUY","quality":"HIGH QUALITY"}}
assert arena.qualifies("BASE_COMMITTEE",s,c)
assert arena.qualifies("VOLUME_CONFIRM",s,c)
assert arena.qualifies("MULTI_TF_CONFIRM",s,c)
assert arena.qualifies("SELECTIVE_EDGE",s,c)

print(json.dumps({"status":"passed","tests":[
 "small loss diagnosis","winner given back diagnosis","entry snapshot persistence",
 "base challenger","volume challenger","multi-timeframe challenger","selective challenger"
]},indent=2))
