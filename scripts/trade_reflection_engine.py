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


OUT=DATA/"trade_reflections.json"

def first_warning(r):
    history=r.get("management_thought_history") or []
    entry_dir=str(r.get("direction") or "").upper()
    warning_terms=("conflict","fading","reversal","profit protect","risk","weak","exhaust","defend","exit")
    for row in history:
        joined=" ".join(str(x) for x in (row.get("thoughts") or [])).lower()
        committee=str(row.get("committee_direction") or "").upper()
        risk=str(row.get("risk_state") or "").upper()
        micro=str(row.get("microstructure_signal") or "").upper()
        reasons=[]
        if committee in {"LONG","SHORT"} and committee!=entry_dir: reasons.append("Committee direction conflicted with the open thesis.")
        if risk not in {"","NORMAL"}: reasons.append(f"Risk Guardian moved to {risk}.")
        if "REVERS" in micro or ("SHORT ENTRY" in micro and entry_dir=="LONG") or ("LONG ENTRY" in micro and entry_dir=="SHORT"):
            reasons.append(f"Microstructure showed {micro}.")
        for term in warning_terms:
            if term in joined:
                reasons.append("Engine thought history contained an early warning: "+term+".")
                break
        if reasons:
            return {"time":row.get("recorded_at"),"price":row.get("price"),
                    "return_pct":f(row.get("return_pct")),"reasons":list(dict.fromkeys(reasons))}
    return None

def missed_clues(r,reverse):
    clues=[]
    entry=r.get("entry_snapshot") or r.get("observer_evidence") or {}
    direction=str(r.get("direction") or "").upper()
    rvol=f(entry.get("rvol"));rvd=f(entry.get("rvol_delta"))
    r4=f(entry.get("return_4h"));r24=f(entry.get("return_24h"))
    bull=f(entry.get("bullish"));bear=f(entry.get("bearish"))
    if rvd<-0.10: clues.append("RVOL_FADING_AT_ENTRY")
    if direction=="LONG" and r4<0: clues.append("LONG_AGAINST_4H")
    if direction=="SHORT" and r4>0: clues.append("SHORT_AGAINST_4H")
    if direction=="LONG" and r24<0: clues.append("LONG_AGAINST_24H")
    if direction=="SHORT" and r24>0: clues.append("SHORT_AGAINST_24H")
    if direction=="LONG" and bear>bull+3: clues.append("BEARISH_CONDITION_IMBALANCE")
    if direction=="SHORT" and bull>bear+3: clues.append("BULLISH_CONDITION_IMBALANCE")
    if rvol<0.8: clues.append("WEAK_PARTICIPATION")
    if reverse and reverse.get("status")=="REVERSE CLEARLY SUPERIOR": clues.append("OPPOSITE_DIRECTION_OUTPERFORMED")
    warning=first_warning(r)
    if warning:
        for reason in warning.get("reasons") or []:
            low=reason.lower()
            if "committee direction conflicted" in low: clues.append("COMMITTEE_FLIPPED")
            if "risk guardian" in low: clues.append("RISK_STATE_DEGRADED")
            if "microstructure" in low: clues.append("MICROSTRUCTURE_REVERSAL")
            if "fading" in low: clues.append("MOMENTUM_OR_VOLUME_FADING")
            if "exhaust" in low: clues.append("EXHAUSTION_WARNING")
    return list(dict.fromkeys(clues)),warning

def process_grade(r,capture,reverse):
    ret=f(r.get("realised_return"))
    reason=str(r.get("exit_reason") or "").upper()
    entry_quality=str((r.get("assessment") or {}).get("entry_quality") or "")
    stop=("STOP" in reason)
    mfe=f(r.get("maximum_favourable_excursion_pct"))
    cap=f((capture or {}).get("capture_efficiency_pct"))
    risk_grade="EXCELLENT" if ret<0 and stop else "REVIEW" if ret<0 else "GOOD"
    market_grade="WEAK" if reverse and reverse.get("status")=="REVERSE CLEARLY SUPERIOR" else "GOOD" if ret>0 else "REVIEW"
    management_grade="EXCELLENT" if ret<0 and stop else "GOOD" if ret>0 and cap>=60 else "REVIEW" if mfe>1 and cap<40 else "NORMAL"
    if risk_grade=="EXCELLENT" and market_grade=="WEAK": overall="GOOD PROCESS / WRONG DIRECTION"
    elif ret>0 and management_grade in {"EXCELLENT","GOOD"}: overall="GOOD PROCESS"
    elif ret<0 and not stop: overall="POOR PROCESS REVIEW"
    else: overall="MIXED PROCESS"
    return {"overall":overall,"risk_management":risk_grade,"market_reading":market_grade,
            "trade_management":management_grade,"entry_quality":entry_quality or "UNKNOWN"}

def stop_value_saved(r):
    ret=f(r.get("realised_return"))
    path=(r.get("replay") or {}).get("price_path") or []
    entry=f(r.get("entry_price"));direction=r.get("direction")
    worst=0.0
    for p in path:
        px=f(p.get("price"))
        if px<=0: continue
        worst=min(worst,directional(direction,entry,px))
    avoided=max(0,ret-worst)
    alloc=f((r.get("source_position") or {}).get("allocated_cash"),f(r.get("allocated_cash")))
    return {"worst_observed_same_direction_pct":worst,"loss_avoided_pct":avoided,
            "estimated_capital_saved_usd":alloc*avoided/100 if alloc>0 else None,
            "note":"Historical replay estimate only; it measures observed downside avoided after the actual exit."}

def main():
    reviews=read(DATA/"trade_reviews.json",{"reviews":[]}).get("reviews") or []
    reverse_rows={str(x.get("trade_key")):x for x in read(DATA/"reverse_trade_lab.json",{"records":[]}).get("records") or []}
    captures={str(x.get("trade_key")):x for x in read(DATA/"profit_capture.json",{"records":[]}).get("records") or []}
    integrity=read(DATA/"trade_integrity.json",{"records":[]}).get("records") or []
    valid={str(x.get("trade_key")) for x in integrity if x.get("status")=="VALIDATED"}
    rows=[]
    for r in reviews:
        key=trade_key(r)
        if valid and key not in valid:continue
        rev=reverse_rows.get(key);cap=captures.get(key,{})
        clues,warning=missed_clues(r,rev)
        grade=process_grade(r,cap,rev)
        stop_saved=stop_value_saved(r)
        lesson_value="HIGH" if rev and rev.get("status")=="REVERSE CLEARLY SUPERIOR" else \
                     "HIGH" if grade["overall"] in {"GOOD PROCESS / WRONG DIRECTION","POOR PROCESS REVIEW"} else \
                     "MEDIUM" if clues else "LOW"
        rows.append({"trade_key":key,"symbol":r.get("symbol"),"wallet":r.get("wallet"),"direction":r.get("direction"),
                     "entry_time":r.get("entry_time"),"exit_time":r.get("exit_time"),
                     "realised_return_pct":f(r.get("realised_return")),"realised_pnl":f(r.get("realised_pnl")),
                     "exit_reason":r.get("exit_reason"),"process_grade":grade,
                     "first_failure_warning":warning,"missed_clues":clues,
                     "reverse_trade":rev,"stop_loss_value":stop_saved,"lesson_value":lesson_value,
                     "reflection_questions":{"was_execution_correct":grade["risk_management"] in {"EXCELLENT","GOOD"},
                         "what_was_first_failure_clue":warning,
                         "would_opposite_trade_have_been_better":bool(rev and rev.get("status") in {"REVERSE BETTER","REVERSE CLEARLY SUPERIOR"}),
                         "has_repeat_pattern_been_proven":False,"is_lesson_ready_for_promotion":False}})
    summary={"reflections":len(rows),
             "good_process_wrong_direction":sum((x.get("process_grade") or {}).get("overall")=="GOOD PROCESS / WRONG DIRECTION" for x in rows),
             "high_value_lessons":sum(x.get("lesson_value")=="HIGH" for x in rows),
             "stop_losses_praised":sum((x.get("process_grade") or {}).get("risk_management")=="EXCELLENT" for x in rows)}
    write(OUT,{"updated_at":now(),"summary":summary,"records":rows[-30000:],
               "principle":"A losing trade can receive a good process grade. Market reading and risk management are evaluated separately."})
    print(json.dumps(summary,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
