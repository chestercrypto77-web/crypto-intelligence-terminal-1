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


OUT=DATA/"lesson_promotion_board.json"
def main():
    clues=read(DATA/"missed_clues.json",{"clues":[]}).get("clues") or []
    lessons=[]
    for c in clues:
        n=int(c.get("samples") or 0);loss=f(c.get("loss_rate_pct"));rev=f(c.get("reverse_superior_rate_pct"))
        state="ELIGIBLE FOR FORMAL REVIEW" if n>=30 and loss>=65 else "TESTING" if n>=12 else "WAITING FOR EVIDENCE"
        lessons.append({"lesson_id":"MISSED_"+str(c.get("clue")),
                        "claim":"Treat "+str(c.get("clue")).replace("_"," ").lower()+" as a caution flag when context matches.",
                        "source":"Trade Reflection Engine","samples":n,"loss_rate_pct":loss,
                        "reverse_superior_rate_pct":rev,"state":state,"auto_promoted":False,
                        "requirements":{"minimum_samples":30,"minimum_loss_association_pct":65,
                                        "out_of_sample_required_before_live_rule_change":True}})
    write(OUT,{"updated_at":now(),"summary":{"lessons":len(lessons),"eligible":sum(x["state"]=="ELIGIBLE FOR FORMAL REVIEW" for x in lessons)},
               "lessons":lessons,
               "guardrail":"No reflection-derived lesson changes live rules automatically. Formal review and out-of-sample evidence are required."})
    print(json.dumps({"lessons":len(lessons)},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
