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

OUT=DATA/"learning_rewards.json"
def score_label(v):
    return "STRONG POSITIVE" if v>=0.7 else "POSITIVE" if v>=0.2 else "NEUTRAL" if v>-0.2 else "NEGATIVE" if v>-0.7 else "STRONG NEGATIVE"
def main():
    store=read(DATA/"learning_experience_store.json",{"records":[]})
    policy=read(CFG/"learning_policy.json",{})
    weights=policy.get("reward_weights") or {}
    rows=[]
    for x in store.get("records") or []:
        if x.get("kind")!="COMPLETED_TRADE" or not x.get("learning_allowed"):continue
        r=x.get("review") or {}; ref=x.get("reflection") or {}; cap=x.get("capture") or {}; tim=x.get("timing") or {}
        ret=f(x.get("realised_return_pct"))
        grade=(ref.get("process_grade") or {})
        direction=max(-1,min(1,ret/3.0))
        risk=1.0 if grade.get("risk_management")=="EXCELLENT" else 0.5 if grade.get("risk_management")=="GOOD" else -0.5 if ret<0 else 0
        exit_reason=str(x.get("review",{}).get("exit_reason") or "").upper()
        stop=1.0 if "STOP" in exit_reason and ret<0 else 0.5 if ret>=0 else -0.5
        mfe=max(0,f(r.get("maximum_favourable_excursion_pct")))
        mae=f(r.get("maximum_adverse_excursion_pct"))
        entry=0.8 if ret>0 and mae>-1 else 0.2 if ret>0 else -0.7 if mae<-3 else -0.3
        capture=max(-1,min(1,(f(cap.get("capture_efficiency_pct"))-50)/50)) if mfe>0 else 0
        hold_assess=(tim.get("timing_assessment") or {}).get("holding_time")
        holding=0.7 if hold_assess=="EFFICIENT" else -0.6 if hold_assess=="OVER-HELD REVIEW" else 0
        reentry=0.3 if tim.get("exit_to_reentry_hours") is not None else 0
        integrity=1.0
        vector={"direction_accuracy":direction,"risk_discipline":risk,"stop_compliance":stop,
                "entry_quality":entry,"profit_capture":capture,"holding_time":holding,
                "reentry_recognition":reentry,"data_integrity":integrity}
        denom=sum(abs(f(weights.get(k),1)) for k in vector) or 1
        total=sum(vector[k]*f(weights.get(k),1) for k in vector)/denom
        rows.append({"experience_id":x.get("experience_id"),"symbol":x.get("symbol"),"split":x.get("split"),
                     "reward_vector":vector,"composite_reward":total,"label":score_label(total),
                     "note":"Composite reward is diagnostic only; promotion gates use component evidence and out-of-sample results."})
    summary={"rewarded_trades":len(rows),"positive_process":sum(x["composite_reward"]>0.2 for x in rows),
             "negative_process":sum(x["composite_reward"]<-0.2 for x in rows)}
    write(OUT,{"updated_at":now(),"summary":summary,"records":rows[-50000:]})
    print(json.dumps(summary,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
