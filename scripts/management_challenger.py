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

OUT=DATA/"management_challenger.json"
POLICIES={
 "ACTUAL":{"name":"Actual Recorded Exit"},
 "PROTECT_50_AFTER_2":{"name":"Protect 50% of MFE after +2%"},
 "TRAIL_1_AFTER_2":{"name":"1% trailing protection after +2%"},
 "TARGET_4":{"name":"Take +4% target"},
}
def directional(direction,entry,price):
    if entry<=0:return 0
    raw=(price/entry-1)*100
    return raw if str(direction).upper()=="LONG" else -raw
def simulate(r,pid):
    if pid=="ACTUAL":return f(r.get("realised_return"))
    entry=f(r.get("entry_price")); direction=r.get("direction")
    path=(r.get("replay") or {}).get("price_path") or []
    moves=[directional(direction,entry,f(x.get("price"))) for x in path if f(x.get("price"))>0]
    if not moves:return None
    mfe=0
    for move in moves:
        mfe=max(mfe,move)
        if pid=="TARGET_4" and move>=4:return 4.0
        if pid=="PROTECT_50_AFTER_2" and mfe>=2 and move<=mfe*0.5:return move
        if pid=="TRAIL_1_AFTER_2" and mfe>=2 and move<=mfe-1:return move
    return moves[-1]
def main():
    reviews=read(DATA/"trade_reviews.json",{"reviews":[]}).get("reviews") or []
    integrity=read(DATA/"trade_integrity.json",{"records":[]}); valid={x.get("trade_key") for x in integrity.get("records") or [] if x.get("status")=="VALIDATED"}
    rows=[]
    for pid,meta in POLICIES.items():
        results=[]
        for r in reviews:
            if trade_key(r) not in valid:continue
            v=simulate(r,pid)
            if v is not None:results.append(v)
        n=len(results); wins=sum(x>0 for x in results)
        rows.append({"policy_id":pid,"name":meta["name"],"samples":n,"win_rate_pct":wins/n*100 if n else 0,
                     "expectancy_pct":sum(results)/n if n else 0,"status":"REVIEW ELIGIBLE" if n>=30 else "LEARNING"})
    rows.sort(key=lambda x:(x["status"]=="REVIEW ELIGIBLE",x["expectancy_pct"]),reverse=True)
    write(OUT,{"updated_at":now(),"summary":{"policies":len(rows),"samples_required":30},"policies":rows,
               "warning":"Shadow replay only. No policy changes live trading automatically."})
    print(json.dumps({"leader":rows[0] if rows else None},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
