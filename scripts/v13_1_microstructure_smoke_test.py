from pathlib import Path
import importlib.util,json,pandas as pd,numpy as np
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/"app.py").read_text()
committee=(ROOT/"scripts/investment_committee.py").read_text()
hub=(ROOT/"scripts/intelligence_hub.py").read_text()
wf=(ROOT/".github/workflows/microstructure_5m.yml").read_text()

assert 'APP_VERSION = "13.1.0"' in app
assert 'def microstructure_analyst' in committee
assert '"microstructure": microstructure_analyst' in committee
assert 'microstructure_latest.json' in hub
assert '*/5 * * * *' in wf

spec=importlib.util.spec_from_file_location("micro",ROOT/"scripts/microstructure_observer.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

up={"price":110,"ema9":108,"ema21":105,"rsi":64,"rsi_delta":3,"macd":2,"macd_delta":1,"rvol":1.5,"rvol_delta":0.2,"breakout":False,"breakdown":False}
down={"price":90,"ema9":92,"ema21":95,"rsi":36,"rsi_delta":-3,"macd":-2,"macd_delta":-1,"rvol":1.5,"rvol_delta":0.2,"breakout":False,"breakdown":False}
role,state,_=m.classify(up,up)
assert role=="LONG ENTRY"
role,state,_=m.classify(down,down)
assert role=="SHORT ENTRY"

peak1=dict(up); peak1.update({"price":106,"ema9":107,"ema21":105,"rsi":74,"rsi_delta":-4,"macd":0.5,"macd_delta":-0.7,"rvol":0.9,"rvol_delta":-0.3})
peak5=dict(up); peak5.update({"rsi":76,"rvol":1.2,"rvol_delta":-0.2})
role,state,_=m.classify(peak1,peak5)
assert role=="LONG EXIT / PROFIT PROTECT"

pull1=dict(down); pull1.update({"rsi":43,"rvol":0.9,"rvol_delta":-0.1})
role,state,_=m.classify(pull1,up)
assert role=="LONG PULLBACK WATCH"

print(json.dumps({"status":"passed","tests":[
 "long entry differentiation","short entry differentiation",
 "long peak profit-protection differentiation","long pullback differentiation",
 "5-minute workflow","committee communication"
]},indent=2))
