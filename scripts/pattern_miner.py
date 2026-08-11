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
OUT=DATA/"pattern_miner.json"
def main():
    dna=read(DATA/"trade_dna.json",{"records":[]}).get("records") or []
    groups=defaultdict(list)
    for x in dna:groups[x.get("signature","UNKNOWN")].append(x)
    patterns=[]
    for sig,g in groups.items():
        returns=[f(x.get("return_pct")) for x in g]; wins=sum(x.get("outcome")=="WIN" for x in g)
        n=len(g); exp=sum(returns)/n if n else 0; wr=wins/n*100 if n else 0
        status="MATURE" if n>=30 else "DEVELOPING" if n>=12 else "EARLY"
        candidate=n>=12 and abs(exp)>=0.35
        patterns.append({"signature":sig,"samples":n,"win_rate_pct":wr,"expectancy_pct":exp,"status":status,
                         "candidate":"FAVOUR" if candidate and exp>0 else "AVOID / REDUCE" if candidate else "OBSERVE"})
    patterns.sort(key=lambda x:(x["status"]=="MATURE",abs(x["expectancy_pct"]),x["samples"]),reverse=True)
    write(OUT,{"updated_at":now(),"summary":{"patterns":len(patterns),"candidate_patterns":sum(x["candidate"]!="OBSERVE" for x in patterns)},
               "patterns":patterns[:500],"guardrails":{"minimum_samples_candidate":12,"minimum_samples_mature":30,"auto_modify_rules":False}})
    print(json.dumps({"patterns":len(patterns)},indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
