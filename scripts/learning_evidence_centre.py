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
def parse_time(v):
    try:
        s=str(v).replace("Z","+00:00")
        dt=datetime.fromisoformat(s)
        if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:return None
def hours(a,b):
    x=parse_time(a);y=parse_time(b)
    return (y-x).total_seconds()/3600 if x and y else None
def trade_key(r):
    return str(r.get("case_id") or r.get("position_id") or f"{r.get('wallet','')}_{r.get('symbol','')}_{r.get('entry_time','')}")

OUT=DATA/"learning_evidence_centre.json"
def lesson(id_,title,brain,claim,status,samples,min_samples,support,counter,metrics=None):
    enough=samples>=min_samples
    promoted=status in {"MATURE","REVIEW READY","ACCEPTED"} and enough
    return {"lesson_id":id_,"title":title,"brain":brain,"claim":claim,"status":status,
            "samples":samples,"minimum_samples":min_samples,"sample_gate_met":enough,
            "promotion_state":"ELIGIBLE / ACCEPTED" if promoted else "TESTING / WAITING",
            "supporting_evidence":support[:20],"counter_evidence":counter[:20],
            "metrics":metrics or {}}

def main():
    winners=read(DATA/"winner_school.json",{"fingerprints":{},"examples":[]})
    failures=read(DATA/"failure_school.json",{"failure_modes":{},"examples":[]})
    patterns=read(DATA/"pattern_miner.json",{"patterns":[]})
    management=read(DATA/"management_challenger.json",{"policies":[]})
    timing=read(DATA/"time_intelligence.json",{"records":[],"summary":{}})
    capture=read(DATA/"profit_capture.json",{"records":[],"summary":{}})
    integrity=read(DATA/"trade_integrity.json",{"records":[],"summary":{}})
    memory=read(DATA/"committee_memory.json",{"agents":{},"advisories":[]})
    reflections=read(DATA/"trade_reflections.json",{"records":[],"summary":{}})
    promotions=read(DATA/"lesson_promotion_board.json",{"lessons":[]})

    lessons=[]
    # Pattern Miner claims
    dna_examples=read(DATA/"trade_dna.json",{"records":[]}).get("records") or []
    for i,p in enumerate((patterns.get("patterns") or [])[:100]):
        sig=p.get("signature")
        support=[x for x in dna_examples if x.get("signature")==sig and x.get("outcome")=="WIN"]
        counter=[x for x in dna_examples if x.get("signature")==sig and x.get("outcome")!="WIN"]
        lessons.append(lesson(f"PATTERN_{i}",f"Trade DNA: {sig}","Pattern Miner",
            f"{p.get('candidate','OBSERVE')} this setup while evidence remains consistent.",
            str(p.get("status") or "EARLY"),int(p.get("samples") or 0),12,support,counter,
            {"win_rate_pct":f(p.get("win_rate_pct")),"expectancy_pct":f(p.get("expectancy_pct"))}))

    # Management challengers
    for i,p in enumerate((management.get("policies") or [])[:20]):
        lessons.append(lesson(f"MGMT_{i}",str(p.get("name") or "Management policy"),"Management Challenger",
            "Test whether this exit/profit-protection approach improves completed replay expectancy.",
            str(p.get("status") or "LEARNING"),int(p.get("samples") or 0),30,[],
            [],{"win_rate_pct":f(p.get("win_rate_pct")),"expectancy_pct":f(p.get("expectancy_pct"))}))

    # Timing lessons: descriptive only until enough samples.
    tr=timing.get("records") or []
    win=[x for x in tr if f(x.get("realised_return_pct"))>0]
    loss=[x for x in tr if f(x.get("realised_return_pct"))<0]
    if tr:
        ws=(timing.get("summary") or {})
        lessons.append(lesson("TIME_HOLD","Winning vs losing hold time","Time Intelligence",
            "Compare how long profitable and losing trades are typically held before changing live duration rules.",
            "BUILDING" if len(tr)>=30 else "EARLY",len(tr),30,win[:20],loss[:20],
            {"avg_winner_holding_hours":f(ws.get("avg_winner_holding_hours")),
             "avg_loser_holding_hours":f(ws.get("avg_loser_holding_hours")),
             "avg_winner_time_to_mfe_hours":f(ws.get("avg_winner_time_to_mfe_hours"))}))

    caprows=capture.get("records") or []
    if caprows:
        good=[x for x in caprows if f(x.get("capture_efficiency_pct"))>=70]
        bad=[x for x in caprows if f(x.get("capture_efficiency_pct"))<45]
        lessons.append(lesson("CAPTURE","Profit capture quality","Profit Capture",
            "Study what differentiates trades that bank most of their favourable excursion from trades that give it back.",
            "BUILDING" if len(caprows)>=30 else "EARLY",len(caprows),30,good,bad,
            {"avg_winner_capture_pct":f((capture.get("summary") or {}).get("avg_winner_capture_pct"))}))

    # Integrity is a gate, not a market lesson.
    invalid=[x for x in integrity.get("records") or [] if x.get("status")!="VALIDATED"]
    valid=[x for x in integrity.get("records") or [] if x.get("status")=="VALIDATED"]
    lessons.append(lesson("INTEGRITY","Learning-data integrity","Trade Integrity",
        "Only validated trade records are permitted to teach downstream learning engines.",
        "MATURE" if int((integrity.get("summary") or {}).get("reviewed") or 0)>=30 else "BUILDING",
        int((integrity.get("summary") or {}).get("reviewed") or 0),30,valid,invalid,
        {"validation_rate_pct":f((integrity.get("summary") or {}).get("validation_rate_pct"),100),
         "quarantined":len(invalid)}))

    # Reflection-derived candidate lessons.
    reflection_rows=reflections.get("records") or []
    for i,p in enumerate((promotions.get("lessons") or [])[:100]):
        clue=str(p.get("lesson_id") or "").replace("MISSED_","")
        support=[x for x in reflection_rows if clue in (x.get("missed_clues") or [])][:20]
        lessons.append(lesson("REFLECT_"+str(i),clue.replace("_"," ").title(),"Trade Reflection",
            str(p.get("claim") or ""),str(p.get("state") or "WAITING"),
            int(p.get("samples") or 0),30,support,[],
            {"loss_rate_pct":f(p.get("loss_rate_pct")),"reverse_superior_rate_pct":f(p.get("reverse_superior_rate_pct"))}))

    # Brain status with exact source.
    brains=[]
    source_map=[
      ("Trade Integrity","trade_integrity.json","Validates P/L, direction and replay before learning."),
      ("Winner School","winner_school.json","Studies repeatable profitable trade fingerprints."),
      ("Failure School","failure_school.json","Studies losses, givebacks and poor management."),
      ("Profit Capture","profit_capture.json","Measures MFE capture and profit giveback."),
      ("Time Intelligence","time_intelligence.json","Measures how trade outcomes change through time."),
      ("Move Phase","move_phase_intelligence.json","Classifies current chronological move phase."),
      ("Pattern Miner","pattern_miner.json","Finds repeated Trade DNA signatures."),
      ("Management Challenger","management_challenger.json","Tests alternative exit policies in shadow replay."),
      ("Committee Memory","committee_memory.json","Tracks specialist evidence over repeated outcomes."),
      ("Trade Reflection","trade_reflections.json","Grades process, finds first failure clues and studies whether the opposite direction was superior."),
      ("Missed Clue Miner","missed_clues.json","Finds repeated clues the engine may have overlooked before failed trades."),
      ("Experience Store","learning_experience_store.json","Separates validated experience into train, validation and locked holdout datasets."),
      ("Reward Engine","learning_rewards.json","Scores process dimensions separately instead of treating profit/loss as the only reward."),
      ("Adversarial Learning","adversarial_learning.json","Actively searches for counterexamples that can disprove candidate lessons."),
      ("Learning Curriculum","learning_curriculum.json","Locks advanced learning until foundational competencies pass measurable gates."),
      ("Learning Governor","learning_governor.json","Controls lesson maturity; V21 does not automatically promote any lesson into live trading rules."),
    ]
    for name,source,purpose in source_map:
        data=read(DATA/source,{})
        brains.append({"name":name,"source_file":source,"purpose":purpose,"summary":data.get("summary") or {},
                       "updated_at":data.get("updated_at") or data.get("generated_at")})

    payload={"updated_at":now(),"summary":{"lessons":len(lessons),
              "accepted_or_eligible":sum(x["promotion_state"]=="ELIGIBLE / ACCEPTED" for x in lessons),
              "waiting":sum(x["promotion_state"]!="ELIGIBLE / ACCEPTED" for x in lessons),
              "brains":len(brains)},
             "lessons":lessons,"brains":brains,
             "rules":{"counter_evidence_required":True,"sample_gates_visible":True,
                      "auto_promote_from_single_trade":False,"future_data_in_live_decision":False}}
    write(OUT,payload);print(json.dumps(payload["summary"],indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
