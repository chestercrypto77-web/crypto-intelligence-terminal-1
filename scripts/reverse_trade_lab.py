from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import copy,json,math
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
def now(): return datetime.now(timezone.utc).isoformat()
def read(path,default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception:return copy.deepcopy(default)
def write(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    t=path.with_suffix(path.suffix+".tmp")
    t.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8")
    json.loads(t.read_text(encoding="utf-8"));t.replace(path)
def f(v,d=0.0):
    try:
        x=float(v);return x if math.isfinite(x) else d
    except Exception:return d
def trade_key(r):
    return str(r.get("case_id") or r.get("position_id") or f"{r.get('wallet','')}_{r.get('symbol','')}_{r.get('entry_time','')}")
def directional(direction,entry,price):
    if entry<=0 or price<=0:return 0.0
    raw=(price/entry-1)*100
    return raw if str(direction).upper()=="LONG" else -raw

OUT=DATA/"reverse_trade_lab.json"
def main():
    reviews=read(DATA/"trade_reviews.json",{"reviews":[]}).get("reviews") or []
    integrity=read(DATA/"trade_integrity.json",{"records":[]}).get("records") or []
    valid={str(x.get("trade_key")) for x in integrity if x.get("status")=="VALIDATED"}
    rows=[]
    for r in reviews:
        key=trade_key(r)
        if valid and key not in valid: continue
        direction=str(r.get("direction") or "").upper()
        if direction not in {"LONG","SHORT"}: continue
        entry=f(r.get("entry_price")); exit_=f(r.get("exit_price"))
        if entry<=0 or exit_<=0: continue
        opposite="SHORT" if direction=="LONG" else "LONG"
        actual=f(r.get("realised_return"))
        reverse_gross=directional(opposite,entry,exit_)
        replay=(r.get("replay") or {}).get("price_path") or []
        reverse_mfe=0.0; reverse_mae=0.0
        for p in replay:
            px=f(p.get("price"))
            if px<=0: continue
            move=directional(opposite,entry,px)
            reverse_mfe=max(reverse_mfe,move)
            reverse_mae=min(reverse_mae,move)
        improvement=reverse_gross-actual
        status="REVERSE CLEARLY SUPERIOR" if reverse_gross>=2 and improvement>=4 else \
               "REVERSE BETTER" if reverse_gross>actual+1 else \
               "NO CLEAR REVERSE EDGE"
        rows.append({"trade_key":key,"symbol":r.get("symbol"),"wallet":r.get("wallet"),
                     "original_direction":direction,"opposite_direction":opposite,
                     "actual_return_pct":actual,"reverse_same_exit_gross_pct":reverse_gross,
                     "reverse_mfe_pct":reverse_mfe,"reverse_mae_pct":reverse_mae,
                     "difference_pct":improvement,"status":status,
                     "guardrail":"Hindsight research only. Opposite-direction results are never fed back into the original live decision."})
    summary={"trades_compared":len(rows),
             "reverse_clearly_superior":sum(x["status"]=="REVERSE CLEARLY SUPERIOR" for x in rows),
             "reverse_better":sum(x["status"]=="REVERSE BETTER" for x in rows)}
    write(OUT,{"updated_at":now(),"summary":summary,"records":rows[-30000:]})
    print(json.dumps(summary,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
