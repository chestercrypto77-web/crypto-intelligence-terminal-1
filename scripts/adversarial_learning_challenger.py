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

OUT=DATA/"adversarial_learning.json"
def main():
    board=read(DATA/"lesson_promotion_board.json",{"lessons":[]}).get("lessons") or []
    store=read(DATA/"learning_experience_store.json",{"records":[]}).get("records") or []
    train=[x for x in store if x.get("split")=="TRAIN" and x.get("kind")=="COMPLETED_TRADE" and x.get("learning_allowed")]
    validation=[x for x in store if x.get("split")=="VALIDATION" and x.get("kind")=="COMPLETED_TRADE" and x.get("learning_allowed")]
    rows=[]
    for l in board:
        lesson_id=str(l.get("lesson_id") or ""); clue=lesson_id.replace("MISSED_","")
        def cases(dataset):
            return [x for x in dataset if clue in (((x.get("reflection") or {}).get("missed_clues")) or [])]
        tr=cases(train); va=cases(validation)
        support=[x for x in tr if f(x.get("realised_return_pct"))<0]
        counters=[x for x in tr if f(x.get("realised_return_pct"))>=0]
        vs=[x for x in va if f(x.get("realised_return_pct"))<0]; vc=[x for x in va if f(x.get("realised_return_pct"))>=0]
        train_rate=100*len(support)/len(tr) if tr else 0
        val_rate=100*len(vs)/len(va) if va else 0
        rows.append({"lesson_id":lesson_id,"claim":l.get("claim"),"train_samples":len(tr),
                     "train_support":len(support),"train_counterexamples":len(counters),"train_support_rate_pct":train_rate,
                     "validation_samples":len(va),"validation_support":len(vs),"validation_counterexamples":len(vc),
                     "validation_support_rate_pct":val_rate,
                     "challenge_result":"SURVIVES SO FAR" if len(tr)>=20 and len(va)>=8 and train_rate>=60 and val_rate>=60 else "NOT PROVEN",
                     "counterexamples":[{"experience_id":x.get("experience_id"),"symbol":x.get("symbol"),
                                         "return_pct":x.get("realised_return_pct")} for x in (counters+vc)[:20]]})
    write(OUT,{"updated_at":now(),"summary":{"lessons_challenged":len(rows),
              "surviving":sum(x["challenge_result"]=="SURVIVES SO FAR" for x in rows)},"records":rows})
    print(json.dumps({"lessons_challenged":len(rows)},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
