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

OUT=DATA/"ai_scorecard.json"
def main():
    integrity=read(DATA/"trade_integrity.json",{"summary":{}}).get("summary") or {}
    capture=read(DATA/"profit_capture.json",{"summary":{}}).get("summary") or {}
    winner=read(DATA/"winner_school.json",{"summary":{}}).get("summary") or {}
    failure=read(DATA/"failure_school.json",{"summary":{}}).get("summary") or {}
    pattern=read(DATA/"pattern_miner.json",{"summary":{}}).get("summary") or {}
    memory=read(DATA/"committee_memory.json",{"summary":{}}).get("summary") or {}
    arena=read(DATA/"challenger_arena.json",{"ranking":[]})
    valid=f(integrity.get("validation_rate_pct"),100)
    cap=f(capture.get("avg_winner_capture_pct"))
    reviewed=int(integrity.get("reviewed") or 0)
    score=(min(100,valid)*0.35 + min(100,max(0,cap))*0.25 +
           min(100,reviewed/50*100)*0.15 +
           min(100,int(pattern.get("candidate_patterns") or 0)*10)*0.10 +
           min(100,int(memory.get("agents") or 0)*10)*0.15)
    status="MATURE" if reviewed>=200 and score>=75 else "DEVELOPING" if reviewed>=50 else "LEARNING"
    metrics={"data_integrity_pct":valid,"avg_winner_capture_pct":cap,"validated_trade_count":int(integrity.get("validated") or 0),
             "quarantined_trade_count":int(integrity.get("quarantined") or 0),
             "winner_cases":int(winner.get("winners") or 0),"failure_cases":int(failure.get("cases") or 0),
             "candidate_patterns":int(pattern.get("candidate_patterns") or 0),"calibrated_agents":int(memory.get("agents") or 0)}
    write(OUT,{"updated_at":now(),"status":status,"decision_quality_score":score,"summary":{"reviewed":reviewed},"metrics":metrics,
               "note":"Score measures process/evidence maturity, not guaranteed profitability."})
    print(json.dumps({"status":status,"score":round(score,1),**metrics},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
