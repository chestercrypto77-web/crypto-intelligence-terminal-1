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

OUT=DATA/"brain_audit.json"
ENGINES=[
 ("5m Microstructure","microstructure_latest.json","generated_at",10),
 ("15m Observer","observer_latest.json","generated_at",30),
 ("Market School","market_school.json","updated_at",180),
 ("Move Phase","move_phase_intelligence.json","updated_at",30),
 ("External Attention","external_attention.json","updated_at",180),
 ("Investment Committee","committee_latest.json","updated_at",180),
 ("Intelligence Bus","intelligence_bus.json","updated_at",180),
 ("Trade Integrity","trade_integrity.json","updated_at",180),
 ("Winner School","winner_school.json","updated_at",360),
 ("Failure School","failure_school.json","updated_at",360),
 ("Pattern Miner","pattern_miner.json","updated_at",360),
 ("Time Intelligence","time_intelligence.json","updated_at",360),
 ("Strategy Brain","strategy_brain_status.json","updated_at",360),
 ("Learning Evidence","learning_evidence_centre.json","updated_at",360),
 ("Market Truth","market_truth.json","updated_at",60),
 ("Runtime Watchdog","runtime_watchdog.json","updated_at",30),
 ("Decision Truth Replay","decision_truth_replay.json","updated_at",360),
 ("Major Move Forensics","major_move_forensics.json","updated_at",360),
 ("Experience Store","learning_experience_store.json","updated_at",360),
 ("Reward Engine","learning_rewards.json","updated_at",360),
 ("Adversarial Learning","adversarial_learning.json","updated_at",360),
 ("Learning Curriculum","learning_curriculum.json","updated_at",360),
 ("Learning Governor","learning_governor.json","updated_at",360),
 ("Trade Reflection","trade_reflections.json","updated_at",360),
 ("Missed Clue Miner","missed_clues.json","updated_at",360),
 ("Lesson Promotion Board","lesson_promotion_board.json","updated_at",360),
]
def age_minutes(v):
    t=parse(v)
    return (datetime.now(timezone.utc)-t).total_seconds()/60 if t else None
def main():
    engines=[];alerts=[]
    for name,fn,key,maxage in ENGINES:
        data=read(DATA/fn,{})
        stamp=data.get(key) or data.get("generated_at") or data.get("updated_at")
        age=age_minutes(stamp);exists=(DATA/fn).exists()
        status="PASS" if exists and age is not None and age<=maxage else "NO VERIFIED HEARTBEAT" if exists and age is None else "STALE" if exists else "MISSING"
        if status!="PASS":
            if status=="STALE": alerts.append(f"{name}: STALE ({age:.0f} min old)")
            elif status=="NO VERIFIED HEARTBEAT": alerts.append(f"{name}: NO VERIFIED HEARTBEAT")
            else: alerts.append(f"{name}: file missing")
        engines.append({"engine":name,"source_file":fn,"last_output":stamp,"age_minutes":age,
                        "freshness_limit_minutes":maxage,"status":status})

    receipts=read(DATA/"brain_receipts.json",{"receipts":[]}).get("receipts") or []
    cutoff=datetime.now(timezone.utc)-timedelta(hours=24)
    recent=[x for x in receipts if (parse(x.get("recorded_at")) or datetime.min.replace(tzinfo=timezone.utc))>=cutoff]
    expected_links=[
      ("External Attention","Investment Committee"),
      ("Learning Feedback","Intelligence Bus"),
      ("Move Phase","Active Trade Casefiles"),
      ("Investment Committee","Portfolio Manager"),
    ]
    links=[]
    for producer,consumer in expected_links:
        hits=[x for x in recent if x.get("producer")==producer and x.get("consumer")==consumer]
        status="PASS" if hits else "UNVERIFIED"
        if status!="PASS":alerts.append(f"Communication link unverified: {producer} → {consumer}")
        links.append({"producer":producer,"consumer":consumer,"receipts_24h":len(hits),
                      "records_consumed":sum(int(x.get("records_consumed") or 0) for x in hits),"status":status,
                      "last_receipt":hits[-1].get("recorded_at") if hits else None})

    obs=read(DATA/"observer_audit.json",{"summary":{}}).get("summary") or {}
    strat=read(DATA/"strategy_integrity.json",{"summary":{}}).get("summary") or {}
    score=100
    score-=sum(10 for x in engines if x["status"]!="PASS")
    score-=sum(8 for x in links if x["status"]!="PASS")
    for mode in ("5M","15M"):
        s=obs.get(mode) or {}
        if s.get("status")=="FAIL":score-=15
        elif s.get("status")=="CAUTION":score-=7
    score-=min(20,int(strat.get("flagged_trades") or 0)*2)
    score=max(0,score)
    payload={"updated_at":now(),"summary":{"brain_health_score":score,"engines_pass":sum(x["status"]=="PASS" for x in engines),
              "engines_total":len(engines),"links_verified":sum(x["status"]=="PASS" for x in links),
              "links_total":len(links),"alerts":len(alerts)},
             "engines":engines,"links":links,"alerts":alerts[:100],
             "observer_summary":obs,"strategy_integrity_summary":strat,
             "principle":"PASS means an observable output or receipt exists. The audit does not infer communication merely because two scripts are present."}
    write(OUT,payload);print(json.dumps(payload["summary"],indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
