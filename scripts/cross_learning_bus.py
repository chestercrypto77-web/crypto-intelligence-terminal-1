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

OUT=DATA/"intelligence_feedback.json"
def main():
    integrity=read(DATA/"trade_integrity.json",{"summary":{}})
    winners=read(DATA/"winner_school.json",{"summary":{}})
    failures=read(DATA/"failure_school.json",{"summary":{}})
    capture=read(DATA/"profit_capture.json",{"summary":{}})
    patterns=read(DATA/"pattern_miner.json",{"patterns":[],"summary":{}})
    management=read(DATA/"management_challenger.json",{"policies":[]})
    memory=read(DATA/"committee_memory.json",{"advisories":[]})
    strategy_brain=read(DATA/"strategy_brain_status.json",{"discoveries":[],"summary":{}})
    messages=[]
    for x in (strategy_brain.get("discoveries") or [])[:10]:
        messages.append({"source":"STRATEGY_BRAIN","message":str(x.get("finding") or "")})
    for x in (memory.get("advisories") or [])[:30]:messages.append({"source":"COMMITTEE_MEMORY","message":x})
    for x in (patterns.get("patterns") or [])[:20]:
        if x.get("candidate")!="OBSERVE" and int(x.get("samples") or 0)>=12:
            messages.append({"source":"PATTERN_MINER","message":f"{x['candidate']} {x['signature']} | n={x['samples']} | expectancy {f(x['expectancy_pct']):+.2f}%"})
    policies=management.get("policies") or []
    if policies:messages.append({"source":"MANAGEMENT_CHALLENGER","message":f"Current shadow leader: {policies[0].get('name')} ({f(policies[0].get('expectancy_pct')):+.2f}% expectancy)."})
    payload={"updated_at":now(),"summary":{
        "integrity_validation_rate_pct":f((integrity.get("summary") or {}).get("validation_rate_pct"),100),
        "winner_cases":int((winners.get("summary") or {}).get("winners") or 0),
        "failure_cases":int((failures.get("summary") or {}).get("cases") or 0),
        "avg_winner_capture_pct":f((capture.get("summary") or {}).get("avg_winner_capture_pct")),
        "candidate_patterns":int((patterns.get("summary") or {}).get("candidate_patterns") or 0),
    },"messages":messages[:100],
    "principle":"Feedback is advisory and sample-gated. It informs future specialist decisions without rewriting live rules automatically."}
    write(OUT,payload);print(json.dumps(payload["summary"],indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
