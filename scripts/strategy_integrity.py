from __future__ import annotations
from datetime import datetime, timezone, timedelta
from pathlib import Path
import copy,json,math,os
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
def now():return datetime.now(timezone.utc).isoformat()
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
def parse(v):
    try:
        x=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        if x.tzinfo is None:x=x.replace(tzinfo=timezone.utc)
        return x.astimezone(timezone.utc)
    except Exception:return None

OUT=DATA/"strategy_integrity.json"
def main():
    lab=read(DATA/"strategy_lab.json",{"strategies":{}})
    strategies=[];flagged=[]
    for sid,w in (lab.get("strategies") or {}).items():
        closed=w.get("closed_positions") or []
        vals=[]
        for p in closed:
            ret=f(p.get("realised_return"))
            vals.append(ret)
            reasons=[]
            alloc=f(p.get("allocated_cash"))
            pnl=f(p.get("realised_pnl"))
            if abs(ret)>100:reasons.append("Return magnitude >100%: inspect leverage/gap/stop behaviour")
            if alloc>0 and pnl < -alloc*1.02:reasons.append("Loss exceeded allocated capital in non-leveraged Strategy Lab simulation")
            if reasons:
                flagged.append({"strategy_id":sid,"symbol":p.get("symbol"),"position_id":p.get("position_id"),
                                "realised_return":ret,"realised_pnl":pnl,"allocated_cash":alloc,"reasons":reasons})
        clean=[x for x in vals if abs(x)<=100]
        strategies.append({"strategy_id":sid,"name":w.get("name") or sid,"closed_trades":len(closed),
                           "raw_average_return_pct":sum(vals)/len(vals) if vals else 0,
                           "audited_average_return_pct":sum(clean)/len(clean) if clean else 0,
                           "flagged_trades":sum(x["strategy_id"]==sid for x in flagged),
                           "evidence_status":"QUARANTINED / REVIEW" if any(x["strategy_id"]==sid for x in flagged) else "CLEAN"})
    payload={"updated_at":now(),"summary":{"strategies":len(strategies),"flagged_trades":len(flagged),
              "strategies_quarantined":sum(x["evidence_status"]!="CLEAN" for x in strategies)},
             "strategies":strategies,"flagged_trades":flagged[-5000:],
             "rule":"Extreme strategy-return records remain visible but are quarantined from trustworthy Strategy Lab conclusions until reviewed."}
    write(OUT,payload);print(json.dumps(payload["summary"],indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
