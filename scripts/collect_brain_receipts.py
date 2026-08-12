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

OUT=DATA/"brain_receipts.json"
def add(rows,producer,consumer,source,count):
    rows.append({"recorded_at":now(),"producer":producer,"consumer":consumer,"source":source,"records_consumed":int(count or 0)})
def main():
    data=read(OUT,{"receipts":[]});rows=data.get("receipts") or []
    committee=read(DATA/"committee_latest.json",{})
    cr=committee.get("input_receipts") or {}
    if cr:add(rows,"External Attention","Investment Committee","external_attention.json",cr.get("external_attention_events"))
    hub=read(DATA/"intelligence_bus.json",{})
    hr=hub.get("input_receipts") or {}
    if hr:add(rows,"Learning Feedback","Intelligence Bus","intelligence_feedback.json",hr.get("learning_feedback_messages"))
    cf=read(DATA/"active_trade_casefiles.json",{})
    rr=cf.get("input_receipts") or {}
    if rr:add(rows,"Move Phase","Active Trade Casefiles","move_phase_intelligence.json",rr.get("move_phase_assets"))
    pm=read(DATA/"portfolio_manager.json",{})
    pr=pm.get("input_receipts") or {}
    if pr:add(rows,"Investment Committee","Portfolio Manager","committee_latest.json",pr.get("committee_assets"))
    write(OUT,{"updated_at":now(),"receipts":rows[-20000:]})
    print(json.dumps({"receipts_total":len(rows)},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
