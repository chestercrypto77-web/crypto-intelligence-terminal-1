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

OUT=DATA/"learning_curriculum.json"
def main():
    integ=read(DATA/"trade_integrity.json",{"summary":{}}).get("summary") or {}
    rewards=read(DATA/"learning_rewards.json",{"records":[]}).get("records") or []
    decision=read(DATA/"decision_truth_replay.json",{"summary":{}}).get("summary") or {}
    capture=read(DATA/"profit_capture.json",{"summary":{}}).get("summary") or {}
    reflections=read(DATA/"trade_reflections.json",{"summary":{}}).get("summary") or {}
    valid=int(integ.get("validated") or integ.get("validated_trades") or integ.get("reviewed") or 0)
    avg_comp=sum(f(x.get("composite_reward")) for x in rewards)/len(rewards) if rewards else 0
    four=decision.get("4h") or {}
    stages=[
      {"level":1,"name":"TRUST THE DATA","passed":valid>=30,"evidence":f"{valid} validated trades","goal":"Prove data integrity before advanced learning."},
      {"level":2,"name":"PROTECT CAPITAL","passed":valid>=30 and sum((x.get("reward_vector") or {}).get("risk_discipline",0)>0 for x in rewards)>=20,
       "evidence":"Risk discipline repeatedly positive","goal":"Stops and capital protection are reliable."},
      {"level":3,"name":"READ DIRECTION","passed":int(four.get("samples") or 0)>=50 and f(four.get("right_rate_pct"))>=52,
       "evidence":f"4h directional truth {f(four.get('right_rate_pct')):.1f}% over {int(four.get('samples') or 0)} cases","goal":"Beat random directional behaviour out of sample."},
      {"level":4,"name":"MANAGE WINNERS","passed":f(capture.get("avg_winner_capture_pct"))>=55 and int(capture.get("validated_trades") or 0)>=30,
       "evidence":f"Winner capture {f(capture.get('avg_winner_capture_pct')):.1f}%","goal":"Improve exit and holding efficiency."},
      {"level":5,"name":"REVERSAL / RE-ENTRY","passed":int(reflections.get("reflections") or 0)>=75,
       "evidence":f"{int(reflections.get('reflections') or 0)} reflections","goal":"Recognise failed thesis, reverse opportunities and re-entry."},
      {"level":6,"name":"CONTEXT INTELLIGENCE","passed":False,"evidence":"Not yet formally validated","goal":"Breadth, rotation, external events and historical analogues."},
      {"level":7,"name":"CAPITAL ALLOCATION","passed":False,"evidence":"Locked","goal":"Only after prior competencies are reliable."}
    ]
    highest=0
    for s in stages:
        if s["passed"] and s["level"]==highest+1:highest=s["level"]
        else:
            if s["level"]==highest+1:break
    write(OUT,{"updated_at":now(),"summary":{"current_level":highest,"current_name":next((s["name"] for s in stages if s["level"]==max(1,highest)),stages[0]["name"]),
              "average_process_reward":avg_comp},"stages":stages,
              "rule":"Advanced autonomy stays locked until earlier competencies have measurable evidence."})
    print(json.dumps({"current_level":highest},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
