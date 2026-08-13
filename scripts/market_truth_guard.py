from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, math, statistics
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"; CFG=ROOT/"config"
def now(): return datetime.now(timezone.utc).isoformat()
def read(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return d
def write(p,x):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(x,indent=2),encoding="utf-8"); json.loads(t.read_text()); t.replace(p)
def f(x,d=None):
    try:
        v=float(x); return v if math.isfinite(v) else d
    except Exception:return d

def validate_record(symbol, price, prior_price=None, provider=None, peer_prices=None):
    reg=read(CFG/"asset_identity.json",{"assets":{}}).get("assets",{}).get(symbol,{})
    reasons=[]; severity="PASS"
    p=f(price)
    if p is None or p<=0: reasons.append("INVALID_PRICE"); severity="QUARANTINE"
    if p is not None and reg:
        lo=f(reg.get("price_floor")); hi=f(reg.get("price_ceiling"))
        if lo and p<lo: reasons.append("OUTSIDE_CANONICAL_PRICE_FLOOR"); severity="QUARANTINE"
        if hi and p>hi: reasons.append("OUTSIDE_CANONICAL_PRICE_CEILING"); severity="QUARANTINE"
    prev=f(prior_price)
    jump=None
    if p and prev and prev>0:
        jump=(p/prev-1)*100
        if abs(jump)>=25:
            reasons.append("EXTREME_CONSECUTIVE_PRICE_JUMP")
            severity="REVIEW" if severity=="PASS" else severity
    peers=[f(x) for x in (peer_prices or [])]; peers=[x for x in peers if x and x>0]
    if p and peers:
        med=statistics.median(peers); div=abs(p/med-1)*100
        if div>8:
            reasons.append("MULTI_SOURCE_PRICE_DISAGREEMENT"); severity="QUARANTINE"
    if reg.get("collision_prone") and not reg.get("canonical_id"):
        reasons.append("COLLISION_PRONE_WITHOUT_CANONICAL_ID"); severity="QUARANTINE"
    return {"symbol":symbol,"canonical_id":reg.get("canonical_id"),"price":p,"provider":provider,
            "prior_price":prev,"jump_pct":jump,"status":severity,"reasons":reasons,
            "learning_allowed":severity=="PASS","trading_allowed":severity=="PASS"}

def main():
    latest=read(DATA/"observer_latest.json",{})
    rows=latest.get("records") or latest.get("assets") or latest.get("signals") or []
    hist=read(DATA/"market_truth_history.json",{"last_prices":{}})
    last=hist.get("last_prices") or {}; out=[]; new_last=dict(last)
    for r in rows:
        s=str(r.get("symbol") or ""); p=f(r.get("price"))
        if not s or p is None: continue
        v=validate_record(s,p,last.get(s),r.get("data_source") or r.get("provider"))
        out.append(v)
        if v["status"]=="PASS": new_last[s]=p
    summary={"checked":len(out),"pass":sum(x["status"]=="PASS" for x in out),
             "review":sum(x["status"]=="REVIEW" for x in out),"quarantined":sum(x["status"]=="QUARANTINE" for x in out)}
    write(DATA/"market_truth.json",{"updated_at":now(),"summary":summary,"records":out,
          "policy":"QUARANTINE records cannot trade or teach. REVIEW records require corroboration before learning."})
    write(DATA/"market_truth_history.json",{"updated_at":now(),"last_prices":new_last})
    print(json.dumps(summary,indent=2))
if __name__=="__main__": main()
