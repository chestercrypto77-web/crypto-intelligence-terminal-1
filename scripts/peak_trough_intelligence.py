from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import copy, json, math
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
def now(): return datetime.now(timezone.utc).isoformat()
def read(path, default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return copy.deepcopy(default)
def write(path, payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8")
    json.loads(temp.read_text(encoding="utf-8"))
    temp.replace(path)
def f(v,d=0.0):
    try:
        x=float(v)
        return x if math.isfinite(x) else d
    except Exception: return d
def trade_key(r):
    return str(r.get("position_id") or r.get("case_id") or f"{r.get('wallet','')}_{r.get('symbol','')}_{r.get('entry_time','')}")

OUT=DATA/"peak_trough_intelligence.json"
def local_extrema(path):
    pts=[x for x in path if f(x.get("price"))>0]
    peaks=[]; troughs=[]
    for i in range(2,len(pts)-2):
        p=f(pts[i]["price"]); before=[f(pts[j]["price"]) for j in range(i-2,i)]; after=[f(pts[j]["price"]) for j in range(i+1,i+3)]
        if p>=max(before+after):
            left=min(before); right=min(after)
            prominence=(p-max(left,right))/p*100 if p else 0
            if prominence>=0.3: peaks.append({"time":pts[i].get("time"),"price":p,"prominence_pct":prominence})
        if p<=min(before+after):
            left=max(before); right=max(after)
            prominence=(min(left,right)-p)/p*100 if p else 0
            if prominence>=0.3: troughs.append({"time":pts[i].get("time"),"price":p,"prominence_pct":prominence})
    return peaks,troughs
def main():
    reviews=read(DATA/"trade_reviews.json",{"reviews":[]}).get("reviews") or []
    integrity=read(DATA/"trade_integrity.json",{"records":[]}); valid={x.get("trade_key") for x in integrity.get("records") or [] if x.get("status")=="VALIDATED"}
    peaks=[]; troughs=[]
    for r in reviews:
        if trade_key(r) not in valid:continue
        path=(r.get("replay") or {}).get("price_path") or []
        ps,ts=local_extrema(path)
        for x in ps:peaks.append({**x,"trade_key":trade_key(r),"symbol":r.get("symbol"),"direction":r.get("direction")})
        for x in ts:troughs.append({**x,"trade_key":trade_key(r),"symbol":r.get("symbol"),"direction":r.get("direction")})
    micro=read(DATA/"microstructure_history.json",[])
    role_counts={}
    for m in micro:
        role=str(m.get("role_signal") or "NO ACTION"); role_counts[role]=role_counts.get(role,0)+1
    payload={"updated_at":now(),"summary":{"validated_trades_scanned":len(valid),"peaks_found":len(peaks),"troughs_found":len(troughs),"microstructure_snapshots":len(micro)},
             "peaks":peaks[-10000:],"troughs":troughs[-10000:],"microstructure":{"role_counts":role_counts},
             "principle":"Extrema are historical labels for learning. Live decisions use only evidence available before the current candle."}
    write(OUT,payload); print(json.dumps(payload["summary"],indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
