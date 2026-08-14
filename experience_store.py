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

OUT=DATA/"learning_experience_store.json"
def main():
    integrity=read(DATA/"trade_integrity.json",{"records":[]}).get("records") or []
    validated={str(x.get("trade_key")) for x in integrity if x.get("status")=="VALIDATED"}
    quarantine=set(read(DATA/"learning_quarantine.json",{}).get("quarantined_symbols") or [])
    audit=read(DATA/"observer_audit.json",{"summary":{}}).get("summary") or {}
    five=(audit.get("5M") or {}); fifteen=(audit.get("15M") or {})
    continuity_ok=f(five.get("schedule_completion_pct"))>=70 and f(fifteen.get("schedule_completion_pct"))>=70
    reviews=read(DATA/"trade_reviews.json",{"reviews":[]}).get("reviews") or []
    reflections={str(x.get("trade_key")):x for x in read(DATA/"trade_reflections.json",{"records":[]}).get("records") or []}
    captures={str(x.get("trade_key")):x for x in read(DATA/"profit_capture.json",{"records":[]}).get("records") or []}
    timing={str(x.get("trade_key")):x for x in read(DATA/"time_intelligence.json",{"records":[]}).get("records") or []}
    rows=[]
    for r in reviews:
        k=key(r); sym=str(r.get("symbol") or "")
        if k not in validated: continue
        replay_points=len(((r.get("replay") or {}).get("price_path")) or [])
        allowed=sym not in quarantine and replay_points>=4
        rows.append({"experience_id":k,"kind":"COMPLETED_TRADE","split":split_for(k),
            "learning_allowed":allowed,"continuity_evidence":{"replay_points":replay_points,"minimum":4},"symbol":sym,"wallet":r.get("wallet"),"direction":r.get("direction"),
            "entry_time":r.get("entry_time"),"exit_time":r.get("exit_time"),
            "realised_return_pct":f(r.get("realised_return")),"realised_pnl":f(r.get("realised_pnl")),
            "review":r,"reflection":reflections.get(k,{}),"capture":captures.get(k,{}),"timing":timing.get(k,{})})
    decisions=read(DATA/"decision_truth_replay.json",{"records":[]}).get("records") or []
    for i,d in enumerate(decisions):
        k=f"DECISION|{d.get('symbol')}|{d.get('decision_time')}|{d.get('action')}|{i}"
        horizon_count=len(d.get("horizons") or {})
        rows.append({"experience_id":k,"kind":"COMMITTEE_DECISION","split":split_for(k),
                     "learning_allowed":str(d.get("symbol") or "") not in quarantine and continuity_ok and horizon_count>=2,
                     "continuity_evidence":{"observer_24h_gate":continuity_ok,"forward_horizons":horizon_count},"decision":d})
    moves=read(DATA/"major_move_forensics.json",{"cases":[]}).get("cases") or []
    for i,m in enumerate(moves):
        k=f"MOVE|{m.get('symbol')}|{m.get('start_time')}|{m.get('move_pct')}|{i}"
        rows.append({"experience_id":k,"kind":"MAJOR_MOVE","split":split_for(k),
                     "learning_allowed":str(m.get("symbol") or "") not in quarantine and continuity_ok,
                     "continuity_evidence":{"observer_24h_gate":continuity_ok},"move":m})
    counts={s:sum(x["split"]==s and x["learning_allowed"] for x in rows) for s in ("TRAIN","VALIDATION","HOLDOUT")}
    payload={"updated_at":now(),"summary":{"experiences":len(rows),"allowed":sum(x["learning_allowed"] for x in rows),
             "quarantined":sum(not x["learning_allowed"] for x in rows),"observer_continuity_gate":continuity_ok,**{k.lower():v for k,v in counts.items()}},
             "records":rows[-100000:],
             "guardrail":"HOLDOUT experiences are stored for final evaluation but discovery engines must not inspect them."}
    write(OUT,payload);print(json.dumps(payload["summary"],indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
