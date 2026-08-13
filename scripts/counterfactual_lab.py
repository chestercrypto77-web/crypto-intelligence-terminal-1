from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import copy,json,math,hashlib
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"; CFG=ROOT/"config"
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
        x=float(v); return x if math.isfinite(x) else d
    except Exception:return d
def key(r):
    return str(r.get("trade_key") or r.get("case_id") or r.get("position_id") or
               f"{r.get('wallet','')}_{r.get('symbol','')}_{r.get('entry_time','')}")
def split_for(k):
    bucket=int(hashlib.sha256(str(k).encode()).hexdigest()[:8],16)%100
    return "TRAIN" if bucket<60 else "VALIDATION" if bucket<80 else "HOLDOUT"

OUT=DATA/"counterfactual_lab.json"
def parse(v):
    try:return datetime.fromisoformat(str(v).replace("Z","+00:00"))
    except:return None
def dreturn(direction,e,p):
    if e<=0 or p<=0:return 0
    raw=(p/e-1)*100
    return raw if str(direction).upper()=="LONG" else -raw
def main():
    store=read(DATA/"learning_experience_store.json",{"records":[]})
    rows=[]
    for x in store.get("records") or []:
        if x.get("kind")!="COMPLETED_TRADE" or not x.get("learning_allowed") or x.get("split")=="HOLDOUT":continue
        r=x.get("review") or {}; path=sorted((r.get("replay") or {}).get("price_path") or [],key=lambda p:str(p.get("time") or ""))
        if not path:continue
        et=parse(r.get("entry_time")); xt=parse(r.get("exit_time")); direction=r.get("direction")
        entry=f(r.get("entry_price")); actual=f(r.get("realised_return"))
        if not et or entry<=0:continue
        variants=[]
        for delay in (5,15,30):
            target=et.timestamp()+delay*60
            pts=[]
            for p in path:
                t=parse(p.get("time")); px=f(p.get("price"))
                if t and px>0 and t.timestamp()>=target: pts.append((t,px))
            if not pts:continue
            t2,e2=pts[0]
            exit_px=f(r.get("exit_price"))
            if exit_px>0:
                rr=dreturn(direction,e2,exit_px)
                variants.append({"variant":f"ENTRY_DELAY_{delay}M","return_pct":rr,"difference_vs_actual_pct":rr-actual})
        # Simple hard-stop shadow using actual path; post-trade research only.
        for stop_pct in (2.0,3.0,5.0):
            shadow=actual;triggered=False
            for p in path:
                t=parse(p.get("time"));px=f(p.get("price"))
                if not t or px<=0 or t<et or (xt and t>xt):continue
                move=dreturn(direction,entry,px)
                if move<=-stop_pct:
                    shadow=-stop_pct;triggered=True;break
            variants.append({"variant":f"HARD_STOP_{stop_pct:.0f}PCT","return_pct":shadow,
                             "difference_vs_actual_pct":shadow-actual,"triggered":triggered})
        rows.append({"experience_id":x.get("experience_id"),"symbol":x.get("symbol"),"split":x.get("split"),
                     "actual_return_pct":actual,"variants":variants,
                     "guardrail":"Counterfactuals are post-trade research only and never rewrite the historical trade."})
    write(OUT,{"updated_at":now(),"summary":{"trades_simulated":len(rows)},"records":rows[-30000:]})
    print(json.dumps({"trades_simulated":len(rows)},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
