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

from collections import defaultdict
OUT=DATA/"committee_memory.json"
def main():
    confidence=read(DATA/"confidence_ledger.json",{"agents":{}}).get("agents") or {}
    patterns=read(DATA/"pattern_miner.json",{"patterns":[]}).get("patterns") or []
    capture=read(DATA/"profit_capture.json",{"summary":{}}).get("summary") or {}
    agents={}
    advisories=[]
    for name,row in confidence.items():
        samples=int(row.get("samples") or 0); hit=f(row.get("hit_rate_pct")); exp=f(row.get("directional_expectancy_pct"))
        trust="MATURE POSITIVE" if samples>=30 and hit>=58 and exp>0 else "MATURE CAUTION" if samples>=30 and (hit<45 or exp<0) else "LEARNING"
        agents[name]={**row,"memory_state":trust}
        if trust!="LEARNING":advisories.append(f"{name}: {trust} across {samples} samples.")
    mature=[x for x in patterns if x.get("status")=="MATURE" and x.get("candidate")!="OBSERVE"]
    for x in mature[:20]:advisories.append(f"Trade DNA {x['candidate']}: {x['signature']} ({x['samples']} samples, {f(x['expectancy_pct']):+.2f}% expectancy).")
    if f(capture.get("avg_winner_capture_pct"))<45 and int(capture.get("validated_trades") or 0)>=20:
        advisories.append("Profit capture remains weak; management challengers deserve more weight in research.")
    payload={"updated_at":now(),"summary":{"agents":len(agents),"advisories":len(advisories),"mature_patterns":len(mature)},
             "agents":agents,"advisories":advisories[:100],
             "policy":{"advisory_only":True,"auto_change_committee_weights":False}}
    write(OUT,payload);print(json.dumps(payload["summary"],indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
