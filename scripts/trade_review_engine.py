from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import copy,json,math
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"; OUT=DATA/"trade_reviews.json"
def read(p,d):
 try:return json.loads(p.read_text())
 except Exception:return copy.deepcopy(d)
def write(p,x):
 t=p.with_suffix(p.suffix+".tmp"); t.write_text(json.dumps(x,indent=2)); json.loads(t.read_text()); t.replace(p)
def f(v,d=0.0):
 try:
  n=float(v); return n if math.isfinite(n) else d
 except:return d
def now(): return datetime.now(timezone.utc).isoformat()
def directional(direction,entry,current):
 if not entry:return 0.0
 raw=(current/entry-1)*100
 return raw if str(direction).upper()=="LONG" else -raw
def entry_quality(p):
 e=p.get("observer_evidence") or {}
 if e:
  r=f(e.get("rvol")); diff=abs(int(e.get("bullish_conditions") or 0)-int(e.get("bearish_conditions") or 0))
  return "SUPPORTED" if r>=1.15 and diff>=6 else "WEAK EVIDENCE" if r<0.9 or diff<4 else "MIXED"
 c=p.get("committee_snapshot") or {}; q=((c.get("decision") or {}).get("quality"))
 return str(q) if q else "LEGACY / UNKNOWN"
def review_trade(wallet,p,current,reviewed_at=None):
 ts=reviewed_at or now(); symbol=str(p.get("symbol") or "").upper(); item=current.get(symbol) or {}
 current_price=f(item.get("price") or item.get("entry_price"),f(p.get("exit_price"))); exit_price=f(p.get("exit_price"))
 direction=str(p.get("direction") or ""); move=directional(direction,exit_price,current_price)
 try: hours=(pd.Timestamp(ts)-pd.Timestamp(p.get("exit_time"))).total_seconds()/3600
 except Exception: hours=0.0
 reason=str(p.get("exit_reason") or "Unknown"); pnl=f(p.get("realised_pnl")); signal=str(item.get("signal") or "UNKNOWN").upper()
 same=(direction=="LONG" and "BUY" in signal) or (direction=="SHORT" and "SELL" in signal)
 exit_quality="NEUTRAL EXIT — REVIEW" if reason=="Observer returned neutral" else "RISK EXIT" if "STOP" in reason.upper() else "PROFIT EXIT" if "PROFIT" in reason.upper() else "REVERSAL EXIT" if "REVERS" in reason.upper() else "PENDING"
 if hours<=72 and move>=5 and same: reentry="MISSED / ACTIVE RE-ENTRY"
 elif hours<=72 and move>=3: reentry="RE-ENTRY WATCH"
 elif move<=-3: reentry="EXIT PROTECTED CAPITAL"
 else: reentry="MONITORING"
 if reason=="Observer returned neutral" and move>=5:
  process="POOR"; lesson="Neutral alone was not enough reason to close. Require actual invalidation and keep the asset under active re-entry surveillance."
 elif "STOP" in reason.upper() and move<=-3:
  process="GOOD"; lesson="The risk exit protected capital as price continued against the position."
 elif pnl<0 and move>=5:
  process="REVIEW"; lesson="The first trade lost, but a later favourable move emerged. Separate entry error from re-entry opportunity."
 elif pnl>0:
  process="GOOD"; lesson="Profitable outcome. Review whether profit protection captured enough of the available move."
 else:
  process="PENDING"; lesson="Collecting post-exit evidence before judging the process."
 return {"position_id":p.get("position_id"),"wallet":wallet,"symbol":symbol,"direction":direction,"entry_price":p.get("entry_price"),"exit_price":p.get("exit_price"),"realised_return":p.get("realised_return"),"realised_pnl":p.get("realised_pnl"),"exit_reason":reason,"maximum_favourable_excursion_pct":f(p.get("maximum_favourable_excursion_pct")),"maximum_adverse_excursion_pct":f(p.get("maximum_adverse_excursion_pct")),"assessment":{"entry_quality":entry_quality(p),"exit_quality":exit_quality,"process_quality":process,"lesson":lesson},"post_exit":{"current_price":current_price,"directional_move_since_exit_pct":move,"hours_since_exit":hours,"current_signal":signal},"reentry":{"status":reentry,"same_direction_signal_now":same},"reviewed_at":ts}
def main():
 observer=read(DATA/"observer_latest.json",{"signals":[]}); hourly=read(DATA/"signals_latest.json",{"signals":[]}); current={}
 for x in hourly.get("signals") or []: current[str(x.get("symbol") or "").upper()]={"price":x.get("entry_price"),"signal":x.get("signal")}
 for x in observer.get("signals") or []: current[str(x.get("symbol") or "").upper()]=x
 wallets=[("15M Observer",read(DATA/"observer_wallet.json",{})),("Core",read(DATA/"core_wallet.json",{})),("Swing",read(DATA/"swing_wallet.json",{})),("Scalp",read(DATA/"scalp_wallet.json",{}))]
 reviews=[review_trade(name,p,current) for name,w in wallets for p in (w.get("closed_positions") or [])]
 payload={"updated_at":now(),"reviews":reviews[-20000:],"summary":{"reviewed":len(reviews),"missed_reentry":sum("MISSED" in str((r.get("reentry") or {}).get("status")) for r in reviews),"poor_process":sum((r.get("assessment") or {}).get("process_quality")=="POOR" for r in reviews)}}
 write(OUT,payload); print(json.dumps(payload["summary"],indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
