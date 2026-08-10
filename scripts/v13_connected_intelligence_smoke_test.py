from pathlib import Path
import importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/"app.py").read_text(encoding="utf-8")
runner=(ROOT/"scripts/hourly_runner.py").read_text(encoding="utf-8")
committee=(ROOT/"scripts/investment_committee.py").read_text(encoding="utf-8")
pm=(ROOT/"scripts/portfolio_manager.py").read_text(encoding="utf-8")
wf=(ROOT/".github/workflows/observer_15m.yml").read_text(encoding="utf-8")

assert 'APP_VERSION = "13.0.0"' in app
assert 'market_school.py' in runner and 'intelligence_hub.py' in runner
assert runner.index('run("market_school.py"') < runner.index('run("investment_committee.py")')
assert runner.index('run("investment_committee.py")') < runner.index('run("intelligence_hub.py"')
assert runner.index('run("intelligence_hub.py"') < runner.index('run("portfolio_manager.py"')
assert 'def market_memory_analyst' in committee
assert '"market_memory": market_memory_analyst' in committee
assert 'intelligence_bus.json' in pm
assert "'shared_intelligence':" in pm and "'case_id':" in pm
assert 'python scripts/market_school.py' in wf and 'python scripts/intelligence_hub.py' in wf

spec=importlib.util.spec_from_file_location("school",ROOT/"scripts/market_school.py")
school=importlib.util.module_from_spec(spec); spec.loader.exec_module(school)
row={"signal":"EARLY BUY","rvol":1.7,"rsi":65,"macd_histogram":1,"macd_delta":0.2,
     "breakout":True,"bullish_conditions":8,"bearish_conditions":1}
key=school.pattern_key(row)
assert "EARLY_BUY" in key and "BREAKOUT" in key and "BULLISH" in key

spec2=importlib.util.spec_from_file_location("committee",ROOT/"scripts/investment_committee.py")
cm=importlib.util.module_from_spec(spec2); spec2.loader.exec_module(cm)
obs={"signal":"EARLY BUY","rvol":1.7,"rsi":65,"macd_histogram":1,"macd_delta":0.2,
     "breakout":True,"bullish_conditions":8,"bearish_conditions":1}
stats={"asset_patterns":{"XYZ":{key:{"4h":{"samples":25,"avg_return_pct":2.1,"up_rate_pct":72,"down_rate_pct":28}}}}}
vote=cm.market_memory_analyst({"symbol":"XYZ"},obs,stats)
assert vote["direction"]=="LONG" and vote["strength"]==2

print(json.dumps({"status":"passed","tests":[
 "market school before committee","committee before intelligence bus","bus before portfolio",
 "market memory analyst","mature analogue vote","shared trade evidence","15m intelligence refresh"
]},indent=2))
