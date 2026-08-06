from pathlib import Path
import importlib.util,sys,types,pandas as pd,json
ROOT=Path(__file__).resolve().parents[1]
if "yfinance" not in sys.modules:
 s=types.ModuleType("yfinance"); s.download=lambda *a,**k:pd.DataFrame(); sys.modules["yfinance"]=s
spec=importlib.util.spec_from_file_location("o",ROOT/"scripts"/"observer_15m.py"); o=importlib.util.module_from_spec(spec); spec.loader.exec_module(o)
def sig(symbol,call,price): return {"symbol":symbol,"signal":call,"price":price,"return_1h":5.0 if "BUY" in call else -5.0,"return_4h":6 if "BUY" in call else -6,"rvol":2.4,"rvol_delta":.8,"bullish_conditions":10 if "BUY" in call else 0,"bearish_conditions":10 if "SELL" in call else 0,"candle_time":"2026-08-06T00:00:00Z"}
w={}; cp=[]; w,cp=o.update_scalp(w,cp,[sig("BTC","EARLY BUY",100)],"2026-08-06T00:00:00Z"); assert len(w["open_positions"])==1 and w["open_positions"][0]["allocated_cash"]==250
w,cp=o.update_scalp(w,cp,[sig("BTC","EARLY BUY",103)],"2026-08-06T00:15:00Z"); assert w["closed_positions"][-1]["realised_pnl"]>0
w={}; cp=[]; w,cp=o.update_scalp(w,cp,[sig("SOL","EARLY SELL",100)],"2026-08-06T00:00:00Z"); w,cp=o.update_scalp(w,cp,[sig("SOL","EARLY SELL",97)],"2026-08-06T00:15:00Z"); assert w["closed_positions"][-1]["realised_pnl"]>0
bad=sig("X","EARLY BUY",100); bad.update({"rvol":.8,"rvol_delta":-.2,"return_1h":.1,"return_4h":.2,"bullish_conditions":5,"bearish_conditions":4}); assert not o.scalp_edge(bad,wallet_template if False else {"fee_pct_per_side":.1,"slippage_pct_per_side":.05,"stop_loss_pct":1.25,"minimum_expected_net_move_pct":.6,"minimum_reward_risk":1.5})["eligible"]
print(json.dumps({"status":"passed","tests":["long scalp","short scalp","profit gate","small allocation"]}))
