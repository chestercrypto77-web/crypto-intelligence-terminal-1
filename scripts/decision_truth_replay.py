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
def f(x,d=None):
    try:return float(x)
    except:return d
def main():
    committee=read(DATA/"committee_history.json",[])
    obs=read(DATA/"observer_history.json",[])
    if isinstance(committee,dict): committee=committee.get("records") or committee.get("history") or []
    if isinstance(obs,dict): obs=obs.get("records") or obs.get("history") or []
    by={}
    for r in obs:
        s=r.get("symbol"); t=r.get("recorded_at"); p=f(r.get("price"))
        if s and t and p: by.setdefault(s,[]).append((t,p))
    for s in by: by[s].sort()
    horizons={"15m":15,"30m":30,"1h":60,"4h":240,"12h":720,"24h":1440}
    out=[]
    from datetime import datetime
    def dt(x):
        try:return datetime.fromisoformat(str(x).replace("Z","+00:00"))
        except:return None
    for c in committee:
        dec=c.get("decision") or {}; action=str(dec.get("action") or "").upper()
        if action not in {"BUY","SHORT"}: continue
        s=c.get("symbol"); t0=dt(c.get("recorded_at")); p0=f(c.get("price"))
        if not s or not t0 or not p0: continue
        row={"decision_time":c.get("recorded_at"),"symbol":s,"action":action,"entry_reference_price":p0,"horizons":{}}
        for label,mins in horizons.items():
            target=t0.timestamp()+mins*60; candidates=[]
            for ts,p in by.get(s,[]):
                d=dt(ts)
                if d and d.timestamp()>=target: candidates.append((d.timestamp()-target,ts,p))
            if not candidates: continue
            gap,ts,p=min(candidates,key=lambda x:x[0])
            if gap>max(900,mins*60*0.35): continue
            raw=(p/p0-1)*100; directional=raw if action=="BUY" else -raw
            row["horizons"][label]={"observed_at":ts,"price":p,"directional_return_pct":directional,
                "verdict":"RIGHT" if directional>0.5 else "WRONG" if directional<-0.5 else "FLAT"}
        out.append(row)
    summary={}
    for h in horizons:
        vals=[r["horizons"][h]["directional_return_pct"] for r in out if h in r["horizons"]]
        summary[h]={"samples":len(vals),"right_rate_pct":100*sum(v>0.5 for v in vals)/len(vals) if vals else 0,
                    "avg_directional_return_pct":sum(vals)/len(vals) if vals else 0}
    write(DATA/"decision_truth_replay.json",{"updated_at":now(),"summary":summary,"records":out[-50000:],
          "guardrail":"Only timestamp-forward observations are used; missing horizons remain missing rather than being invented."})
    print(json.dumps(summary,indent=2))
if __name__=="__main__": main()
