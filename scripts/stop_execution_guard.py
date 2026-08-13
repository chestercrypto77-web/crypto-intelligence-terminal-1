from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, math
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"
def now(): return datetime.now(timezone.utc).isoformat()
def read(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return d
def write(p,x):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(x,indent=2),encoding="utf-8"); json.loads(t.read_text()); t.replace(p)
def f(x,d=0):
    try:return float(x)
    except:return d
def breached(pos, price):
    e=f(pos.get("entry_price")); p=f(price); d=str(pos.get("direction") or "").upper()
    stop=f(pos.get("stop_price"))
    if stop<=0:
        pct=f(pos.get("stop_loss_pct"),3.0)/100
        stop=e*(1-pct) if d=="LONG" else e*(1+pct)
    return (d=="LONG" and p<=stop) or (d=="SHORT" and p>=stop), stop
def main():
    truth=read(DATA/"market_truth.json",{"records":[]})
    prices={x.get("symbol"):x for x in truth.get("records",[]) if x.get("status")=="PASS"}
    events=[]
    for fn in ["observer_wallet.json","scalp_wallet.json","swing_wallet.json","core_wallet.json"]:
        doc=read(DATA/fn,{})
        positions=doc.get("positions") or doc.get("open_positions") or []
        for p in positions:
            if str(p.get("status","OPEN")).upper()!="OPEN": continue
            tr=prices.get(p.get("symbol"))
            if not tr: continue
            hit,stop=breached(p,tr.get("price"))
            if hit:
                events.append({"time":now(),"wallet":fn,"position_id":p.get("position_id"),
                    "symbol":p.get("symbol"),"direction":p.get("direction"),"entry_price":p.get("entry_price"),
                    "validated_price":tr.get("price"),"stop_price":stop,"action":"FORCE_EXIT_REQUIRED",
                    "priority":"P0","reason":"Validated market price breached hard stop. Signal/committee logic may not override this."})
    write(DATA/"stop_execution_alerts.json",{"updated_at":now(),"summary":{"force_exit_required":len(events)},"events":events})
    print(json.dumps({"force_exit_required":len(events)},indent=2))
if __name__=="__main__": main()
