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

OUT=DATA/"learning_governor.json"
def main():
    policy=read(CFG/"learning_policy.json",{})
    gates=policy.get("promotion_gates") or {}
    challenged={str(x.get("lesson_id")):x for x in read(DATA/"adversarial_learning.json",{"records":[]}).get("records") or []}
    board=read(DATA/"lesson_promotion_board.json",{"lessons":[]}).get("lessons") or []
    lessons=[]
    for l in board:
        lid=str(l.get("lesson_id") or ""); c=challenged.get(lid,{})
        tr=int(c.get("train_samples") or 0); va=int(c.get("validation_samples") or 0)
        vr=f(c.get("validation_support_rate_pct"))
        if tr<int(gates.get("minimum_train_examples",20)): state="DISCOVERY"
        elif va<int(gates.get("minimum_validation_examples",8)): state="NEEDS VALIDATION DATA"
        elif vr<f(gates.get("minimum_validation_support_rate_pct"),60): state="VALIDATION FAILED"
        elif c.get("challenge_result")!="SURVIVES SO FAR": state="ADVERSARIAL CHALLENGE FAILED"
        else: state="HOLDOUT REVIEW ELIGIBLE"
        lessons.append({"lesson_id":lid,"claim":l.get("claim"),"state":state,
            "train_samples":tr,"validation_samples":va,"validation_support_rate_pct":vr,
            "holdout_status":"LOCKED — not available to discovery engines",
            "live_policy_status":"NOT PROMOTED","automatic_live_change":False})
    summary={"lessons":len(lessons),"holdout_review_eligible":sum(x["state"]=="HOLDOUT REVIEW ELIGIBLE" for x in lessons),
             "live_promoted":0}
    write(OUT,{"updated_at":now(),"summary":summary,"lessons":lessons,
      "rules":policy.get("rules") or {},
      "principle":"The learning system may discover aggressively, but no V21 lesson can automatically modify live trading behaviour."})
    print(json.dumps(summary,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
