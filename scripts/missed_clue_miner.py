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


from collections import defaultdict
OUT=DATA/"missed_clues.json"
def main():
    refs=read(DATA/"trade_reflections.json",{"records":[]}).get("records") or []
    groups=defaultdict(list)
    for r in refs:
        for clue in r.get("missed_clues") or []:groups[clue].append(r)
    clues=[]
    for clue,rows in groups.items():
        reverse=sum(bool((r.get("reverse_trade") or {}).get("status")=="REVERSE CLEARLY SUPERIOR") for r in rows)
        losses=sum(f(r.get("realised_return_pct"))<0 for r in rows);n=len(rows)
        status="MATURE" if n>=30 else "DEVELOPING" if n>=12 else "EARLY"
        clues.append({"clue":clue,"samples":n,"loss_cases":losses,"reverse_superior_cases":reverse,
                      "loss_rate_pct":losses/n*100 if n else 0,
                      "reverse_superior_rate_pct":reverse/n*100 if n else 0,"status":status,
                      "supporting_trades":[{"trade_key":r.get("trade_key"),"symbol":r.get("symbol"),
                                            "return_pct":r.get("realised_return_pct")} for r in rows[:20]]})
    clues.sort(key=lambda x:(x["status"]=="MATURE",x["samples"],x["loss_rate_pct"]),reverse=True)
    write(OUT,{"updated_at":now(),"summary":{"clues":len(clues),"mature":sum(x["status"]=="MATURE" for x in clues)},"clues":clues[:500]})
    print(json.dumps({"clues":len(clues)},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
