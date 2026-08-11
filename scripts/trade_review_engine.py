from __future__ import annotations
from datetime import datetime,timezone,timedelta
from pathlib import Path
import copy,json,math
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
OUT=DATA/"trade_reviews.json"

def read(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return copy.deepcopy(d)

def write(p,x):
    t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding="utf-8")
    json.loads(t.read_text(encoding="utf-8"))
    t.replace(p)

def f(v,d=0.0):
    try:
        n=float(v); return n if math.isfinite(n) else d
    except Exception:return d

def now():
    return datetime.now(timezone.utc).isoformat()

def directional(direction,entry,current):
    if not entry:return 0.0
    raw=(current/entry-1)*100
    return raw if str(direction).upper()=="LONG" else -raw

def dt(value):
    try:
        ts=pd.Timestamp(value)
        if ts.tzinfo is None: ts=ts.tz_localize("UTC")
        return ts.tz_convert("UTC")
    except Exception:
        return None

def entry_quality(p):
    e=p.get("observer_evidence") or {}
    if e:
        r=f(e.get("rvol"))
        diff=abs(int(e.get("bullish_conditions") or 0)-int(e.get("bearish_conditions") or 0))
        if r>=1.15 and diff>=6:return "SUPPORTED"
        if r<0.9 or diff<4:return "WEAK EVIDENCE"
        return "MIXED"
    c=p.get("committee_snapshot") or {}
    q=((c.get("decision") or {}).get("quality"))
    return str(q) if q else "LEGACY / UNKNOWN"

def plain_entry_reasons(p):
    reasons=[]
    evidence=p.get("observer_evidence") or {}
    if evidence:
        bull=int(evidence.get("bullish_conditions") or 0)
        bear=int(evidence.get("bearish_conditions") or 0)
        rvol=f(evidence.get("rvol"))
        r1=f(evidence.get("return_1h"))
        r4=f(evidence.get("return_4h"))
        if bull>bear: reasons.append(f"Bullish conditions led {bull} to {bear}")
        if bear>bull: reasons.append(f"Bearish conditions led {bear} to {bull}")
        if rvol>=1.15: reasons.append(f"Participation was active (RVOL {rvol:.2f})")
        if r1>0 and r4>0: reasons.append("1H and 4H momentum agreed upward")
        if r1<0 and r4<0: reasons.append("1H and 4H momentum agreed downward")
        signal=str(p.get("signal") or "")
        if signal: reasons.append(f"Observer signal was {signal}")
    committee=(p.get("committee_snapshot") or {})
    reports=committee.get("reports") or {}
    decision=committee.get("decision") or {}
    if decision:
        reasons.append(f"Committee decision: {decision.get('quality','Qualified')} {decision.get('action','')}".strip())
    for analyst in ("technical","volume_liquidity","momentum","news_fundamental","macro_regime"):
        report=reports.get(analyst) or {}
        direction=str(report.get("direction") or "")
        if direction in {"LONG","SHORT"} and int(report.get("strength") or 0)>=2:
            label=analyst.replace("_"," ").title()
            reasons.append(f"{label} supported {direction.lower()}")
    if not reasons:
        reasons.append("Legacy trade: full entry evidence was not captured at the time.")
    return reasons[:5]

def event_state(record):
    signal=str(record.get("signal") or "NEUTRAL").upper()
    if signal in {"EARLY BUY","STRONG BUY","BUY"}: return "LONG"
    if signal=="BUY WATCH": return "BUILDING LONG"
    if signal in {"EARLY SELL","STRONG SELL","SELL"}: return "SHORT"
    if signal=="SELL WATCH": return "BUILDING SHORT"
    if signal=="VOLATILITY WATCH": return "VOLATILITY"
    if signal=="HOLD": return "HOLD"
    return "NEUTRAL"

def dedupe_path(records):
    seen=set(); out=[]
    for row in sorted(records,key=lambda x:str(x.get("time") or "")):
        key=(row.get("time"),round(f(row.get("price")),10),row.get("state"))
        if key in seen: continue
        seen.add(key); out.append(row)
    # Bound one trade replay so persistent review files stay practical.
    if len(out)<=500:return out
    step=max(1,len(out)//480)
    sampled=out[::step]
    if out[-1] not in sampled: sampled.append(out[-1])
    return sampled[:500]

def build_replay(p, observer_history, signal_history, current_item):
    symbol=str(p.get("symbol") or "").upper()
    entry_t=dt(p.get("entry_time"))
    exit_t=dt(p.get("exit_time"))
    if entry_t is None or exit_t is None:
        return {"price_path":[],"events":[],"post_exit":{},"decision_path":[]}

    window_start=entry_t-pd.Timedelta(hours=12)
    window_end=exit_t+pd.Timedelta(hours=48)
    rows=[]
    decisions=[]
    for source,history in (("15M",observer_history),("4H",signal_history)):
        for rec in history:
            if str(rec.get("symbol") or "").upper()!=symbol: continue
            ts=dt(rec.get("recorded_at") or rec.get("candle_time"))
            if ts is None or ts<window_start or ts>window_end: continue
            price=f(rec.get("price"),f(rec.get("entry_price")))
            if price<=0: continue
            state=event_state(rec)
            rows.append({
                "time":ts.isoformat(),
                "price":price,
                "state":state,
                "source":source,
                "signal":rec.get("signal"),
            })
            if source=="15M":
                decisions.append({
                    "time":ts.isoformat(),
                    "state":state,
                    "signal":rec.get("signal"),
                    "price":price,
                })

    # Guarantee entry and exit appear even when the history window is sparse.
    rows.extend([
        {"time":entry_t.isoformat(),"price":f(p.get("entry_price")),"state":"ENTRY","source":"TRADE","signal":p.get("signal")},
        {"time":exit_t.isoformat(),"price":f(p.get("exit_price")),"state":"EXIT","source":"TRADE","signal":p.get("exit_reason")},
    ])
    current_price=f(current_item.get("price") or current_item.get("entry_price"))
    current_time=dt(current_item.get("recorded_at") or current_item.get("candle_time"))
    if current_price>0 and current_time is not None and current_time<=window_end:
        rows.append({"time":current_time.isoformat(),"price":current_price,"state":event_state(current_item),"source":"CURRENT","signal":current_item.get("signal")})

    path=dedupe_path(rows)
    decisions=dedupe_path(decisions)

    post=[r for r in path if dt(r.get("time")) is not None and dt(r.get("time"))>=exit_t]
    post_prices=[f(r.get("price")) for r in post if f(r.get("price"))>0]
    exit_price=f(p.get("exit_price"))
    direction=str(p.get("direction") or "").upper()
    best_after=0.0; worst_after=0.0
    if exit_price>0 and post_prices:
        moves=[directional(direction,exit_price,x) for x in post_prices]
        best_after=max(moves); worst_after=min(moves)

    events=[
        {"time":entry_t.isoformat(),"price":f(p.get("entry_price")),"event":"ENTRY","label":"Entry"},
        {"time":exit_t.isoformat(),"price":f(p.get("exit_price")),"event":"EXIT","label":"Exit"},
    ]
    # Identify first fresh same-direction decision after exit as the earliest re-entry evidence.
    for d in decisions:
        ts=dt(d.get("time"))
        if ts is None or ts<=exit_t: continue
        state=str(d.get("state") or "")
        if (direction=="LONG" and state in {"BUILDING LONG","LONG"}) or (direction=="SHORT" and state in {"BUILDING SHORT","SHORT"}):
            events.append({"time":d.get("time"),"price":d.get("price"),"event":"REENTRY","label":"Re-entry evidence"})
            break

    return {
        "window":{"start":window_start.isoformat(),"entry":entry_t.isoformat(),"exit":exit_t.isoformat(),"end":window_end.isoformat()},
        "price_path":path,
        "decision_path":decisions[-250:],
        "events":events,
        "post_exit":{
            "best_directional_move_pct":best_after,
            "worst_directional_move_pct":worst_after,
        },
    }

def review_trade(wallet,p,current,observer_history=None,signal_history=None,reviewed_at=None):
    observer_history=observer_history or []
    signal_history=signal_history or []
    ts=reviewed_at or now()
    symbol=str(p.get("symbol") or "").upper()
    item=current.get(symbol) or {}
    current_price=f(item.get("price") or item.get("entry_price"),f(p.get("exit_price")))
    exit_price=f(p.get("exit_price"))
    direction=str(p.get("direction") or "")
    move=directional(direction,exit_price,current_price)
    try: hours=(pd.Timestamp(ts)-pd.Timestamp(p.get("exit_time"))).total_seconds()/3600
    except Exception: hours=0.0
    reason=str(p.get("exit_reason") or "Unknown")
    pnl=f(p.get("realised_pnl"))
    signal=str(item.get("signal") or "UNKNOWN").upper()
    same=(direction=="LONG" and "BUY" in signal) or (direction=="SHORT" and "SELL" in signal)

    exit_quality="NEUTRAL EXIT — REVIEW" if reason=="Observer returned neutral" else \
        "RISK EXIT" if "STOP" in reason.upper() else \
        "PROFIT EXIT" if "PROFIT" in reason.upper() else \
        "REVERSAL EXIT" if "REVERS" in reason.upper() else "PENDING"

    if hours<=72 and move>=5 and same: reentry="MISSED / ACTIVE RE-ENTRY"
    elif hours<=72 and move>=3: reentry="RE-ENTRY WATCH"
    elif move<=-3: reentry="EXIT PROTECTED CAPITAL"
    else: reentry="MONITORING"

    if reason=="Observer returned neutral" and move>=5:
        process="POOR"
        lesson="Neutral alone was not enough reason to close. Require actual invalidation and keep the asset under active re-entry surveillance."
    elif "STOP" in reason.upper() and move<=-3:
        process="GOOD"
        lesson="The risk exit protected capital as price continued against the position."
    elif pnl<0 and move>=5:
        process="REVIEW"
        lesson="The first trade lost, but a later favourable move emerged. Separate entry error from re-entry opportunity."
    elif pnl>0:
        process="GOOD"
        lesson="Profitable outcome. Review whether profit protection captured enough of the available move."
    else:
        process="PENDING"
        lesson="Collecting post-exit evidence before judging the process."

    replay=build_replay(p,observer_history,signal_history,item)
    best_after=f((replay.get("post_exit") or {}).get("best_directional_move_pct"))
    allocated=f(p.get("allocated_cash"))
    missed_dollars=allocated*max(0,best_after)/100 if allocated else 0.0

    aftermath=(
        f"After exit, the best same-direction move reached {best_after:+.2f}%."
        if best_after else
        f"Current same-direction move since exit is {move:+.2f}%."
    )

    return {
        "position_id":p.get("position_id"),
        "case_id":p.get("case_id") or p.get("position_id"),
        "wallet":wallet,
        "entry_snapshot":p.get("entry_snapshot") or {},
        "committee_snapshot":p.get("committee_snapshot") or {},
        "shared_intelligence":p.get("shared_intelligence") or {},
        "symbol":symbol,
        "direction":direction,
        "entry_price":p.get("entry_price"),
        "exit_price":p.get("exit_price"),
        "entry_time":p.get("entry_time"),
        "exit_time":p.get("exit_time"),
        "allocated_cash":p.get("allocated_cash"),
        "realised_return":p.get("realised_return"),
        "realised_pnl":p.get("realised_pnl"),
        "exit_reason":reason,
        "maximum_favourable_excursion_pct":f(p.get("maximum_favourable_excursion_pct")),
        "maximum_adverse_excursion_pct":f(p.get("maximum_adverse_excursion_pct")),
        "decision_replay":{
            "why_entered":plain_entry_reasons(p),
            "why_exited":[reason],
            "what_happened_next":aftermath,
            "original_signal":p.get("signal"),
        },
        "assessment":{
            "entry_quality":entry_quality(p),
            "exit_quality":exit_quality,
            "process_quality":process,
            "lesson":lesson,
        },
        "post_exit":{
            "current_price":current_price,
            "directional_move_since_exit_pct":move,
            "hours_since_exit":hours,
            "current_signal":signal,
            "best_directional_move_pct":best_after,
            "missed_move_value_on_original_capital":missed_dollars,
        },
        "reentry":{"status":reentry,"same_direction_signal_now":same},
        "replay":replay,
        "reviewed_at":ts,
    }

def main():
    observer=read(DATA/"observer_latest.json",{"signals":[]})
    hourly=read(DATA/"signals_latest.json",{"signals":[]})
    observer_history=read(DATA/"observer_history.json",[])
    signal_history=read(DATA/"signal_history.json",[])
    current={}
    for x in hourly.get("signals") or []:
        current[str(x.get("symbol") or "").upper()]={"price":x.get("entry_price"),"signal":x.get("signal"),
            "recorded_at":x.get("recorded_at"),"candle_time":x.get("candle_time")}
    for x in observer.get("signals") or []:
        current[str(x.get("symbol") or "").upper()]=x

    wallets=[
        ("15M Observer",read(DATA/"observer_wallet.json",{})),
        ("Core",read(DATA/"core_wallet.json",{})),
        ("Swing",read(DATA/"swing_wallet.json",{})),
        ("Scalp",read(DATA/"scalp_wallet.json",{})),
    ]
    reviews=[
        review_trade(name,p,current,observer_history,signal_history)
        for name,w in wallets for p in (w.get("closed_positions") or [])
    ]
    thought_history=read(DATA/"active_trade_thought_history.json",{"records":[]}).get("records") or []
    thoughts_by_case={}
    for row in thought_history:
        key=str(row.get("case_id") or row.get("position_id") or "")
        if key:thoughts_by_case.setdefault(key,[]).append(row)
    for review in reviews:
        key=str(review.get("case_id") or review.get("position_id") or "")
        review["management_thought_history"]=(thoughts_by_case.get(key) or [])[-600:]
        review["decision_replay"]["management_observations"]=len(review["management_thought_history"])
    payload={
        "updated_at":now(),
        "reviews":reviews[-20000:],
        "summary":{
            "reviewed":len(reviews),
            "missed_reentry":sum("MISSED" in str((r.get("reentry") or {}).get("status")) for r in reviews),
            "poor_process":sum((r.get("assessment") or {}).get("process_quality")=="POOR" for r in reviews),
            "replays_with_price_history":sum(bool((r.get("replay") or {}).get("price_path")) for r in reviews),
        },
    }
    write(OUT,payload)
    print(json.dumps(payload["summary"],indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
