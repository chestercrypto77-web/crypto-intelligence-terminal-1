from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import copy, json, math

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
OUT=DATA/"strategy_brain_status.json"

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

PURPOSES={
 "conviction_v1":"The current baseline. Uses the normal 4-hour conviction rules that challengers must eventually beat.",
 "closed_candle_challenger":"Tests whether waiting for a completed 4-hour candle avoids premature entries.",
 "rvol_150_challenger":"Tests whether requiring stronger relative volume improves entry quality.",
 "btc_confirmed_challenger":"Tests whether altcoin trades improve when Bitcoin direction confirms the setup.",
 "micro_timing_confirmation":"Tests whether 1m/5m execution timing improves entries without changing the higher-timeframe thesis.",
}
BRAIN_PURPOSES={
 "Trade Integrity":"Checks trade data before anything is allowed to teach the AI.",
 "Winner School":"Studies profitable trades to discover repeatable characteristics worth finding again.",
 "Failure School":"Studies losses and poorly managed winners to identify behaviours worth avoiding.",
 "Profit Capture":"Measures how much of a favourable move the system actually banked.",
 "Pattern Miner":"Looks for repeated Trade DNA patterns; patterns need enough examples before becoming evidence.",
 "Management Challengers":"Replays alternative exit/profit-protection methods without changing live paper strategy.",
 "Committee Memory":"Tracks which specialist opinions are becoming useful over repeated validated trades.",
 "Market School":"Studies market behaviour and missed moves, not only trades the platform happened to take.",
 "Microstructure":"Studies 1-minute and 5-minute timing, pullbacks, local exhaustion and reversals.",
 "AI Scorecard":"Summarises evidence maturity and decision-process quality; it is not a profitability promise.",
}

def evidence_stage(closed):
    if closed<=0:return "NOT TESTED",0
    if closed<10:return "EARLY",closed/30*100
    if closed<30:return "BUILDING",closed/30*100
    return "REVIEW READY",100

def strategy_conclusion(role,closed,expectancy,win_rate,pf):
    if role=="CHAMPION":
        if closed<10:return "Current baseline; challengers must beat it after enough completed trades."
        return "Current baseline with real evidence; keep comparing challengers against this result."
    if closed==0:return "No completed trades yet — too early to judge."
    if closed<10:
        return "Very early evidence only; do not promote or reject this strategy yet."
    if closed<30:
        if expectancy>0:return "Encouraging so far, but it still needs more completed trades."
        return "Currently weak, but the sample is still too small for a final judgement."
    if expectancy>0.20 and win_rate>=55 and pf>=1.25:
        return "Evidence is strong enough for formal promotion review — not automatic promotion."
    if expectancy<=0:
        return "Enough evidence to question this approach; keep it as a challenger until reviewed."
    return "Meaningful sample reached, but results are not yet strong enough to replace the baseline."

def brain_card(name,purpose,evidence,status,finding,detail=None):
    return {"name":name,"purpose":purpose,"evidence":evidence,"status":status,"finding":finding,"detail":detail or {}}

def main():
    lab=read(DATA/"strategy_lab.json",{"strategies":{}})
    registry=read(DATA/"strategy_registry.json",{"strategies":[]})
    reg={str(x.get("strategy_id")):x for x in registry.get("strategies") or []}
    strategy_rows=[]
    for sid,w in (lab.get("strategies") or {}).items():
        m=w.get("metrics") or {}
        closed=len(w.get("closed_positions") or [])
        open_n=len(w.get("open_positions") or [])
        evidence=w.get("evidence") or {}
        stage,progress=evidence_stage(closed)
        exp=f(m.get("average_return"))
        wr=f(m.get("win_rate"))
        pf=f(m.get("profit_factor"))
        if pf>100:pf_display="∞"
        else:pf_display=f"{pf:.2f}"
        role=str(w.get("role") or "CHALLENGER")
        strategy_rows.append({
            "strategy_id":sid,"name":w.get("name") or sid,"role":role,
            "purpose":w.get("description") or (reg.get(sid) or {}).get("description") or PURPOSES.get(sid,"Tests an alternative decision rule against the current baseline."),
            "evidence_stage":stage,"evidence_progress_pct":min(100,progress),
            "completed_trades":closed,"open_positions":open_n,
            "market_snapshots":int(evidence.get("market_snapshots") or 0),
            "signals_checked":int(evidence.get("signals_checked") or 0),
            "filtered_by_strategy":int(evidence.get("filtered_by_strategy") or 0),
            "entries_opened":int(evidence.get("entries_opened") or 0),
            "paper_equity":f(w.get("equity"),100000),"paper_return_pct":f(m.get("return_pct")),
            "win_rate_pct":wr if closed else None,"expectancy_pct":exp if closed else None,
            "profit_factor":pf if closed else None,"profit_factor_display":pf_display if closed else "—",
            "max_drawdown_pct":f(m.get("max_drawdown")),
            "current_conclusion":strategy_conclusion(role,closed,exp,wr,pf),
            "promotion_status":"BASELINE" if role=="CHAMPION" else "ELIGIBLE FOR REVIEW" if closed>=30 and exp>0.20 and wr>=55 and pf>=1.25 else "LEARNING",
        })
    # Champion is always visible first. Challengers sort by evidence maturity, not tiny open-equity differences.
    strategy_rows.sort(key=lambda x:(x["role"]!="CHAMPION",-x["completed_trades"],-(x["expectancy_pct"] or -999)))

    integrity=read(DATA/"trade_integrity.json",{"summary":{}}).get("summary") or {}
    winner=read(DATA/"winner_school.json",{"summary":{},"fingerprints":{}})
    failure=read(DATA/"failure_school.json",{"summary":{},"failure_modes":{}})
    capture=read(DATA/"profit_capture.json",{"summary":{},"records":[]})
    patterns=read(DATA/"pattern_miner.json",{"summary":{},"patterns":[]})
    management=read(DATA/"management_challenger.json",{"policies":[]})
    memory=read(DATA/"committee_memory.json",{"summary":{},"agents":{},"advisories":[]})
    market_school=read(DATA/"market_school.json",{"summary":{}})
    micro=read(DATA/"microstructure_history.json",[])
    score=read(DATA/"ai_scorecard.json",{"status":"LEARNING","metrics":{}})
    health=read(DATA/"brain_health.json",{"engines":{}})

    discoveries=[]
    # Only describe evidence that actually exists; don't manufacture weekly findings.
    mature_patterns=[x for x in patterns.get("patterns") or [] if int(x.get("samples") or 0)>=12 and x.get("candidate")!="OBSERVE"]
    if mature_patterns:
        p=mature_patterns[0]
        discoveries.append({"type":"PATTERN","status":p.get("status"),"title":"Trade pattern worth testing",
                            "finding":f"{p.get('candidate')} · {p.get('signature')} · {int(p.get('samples') or 0)} samples · {f(p.get('expectancy_pct')):+.2f}% expectancy."})
    policies=[x for x in management.get("policies") or [] if int(x.get("samples") or 0)>0]
    if policies:
        p=policies[0]
        discoveries.append({"type":"MANAGEMENT","status":p.get("status"),"title":"Best exit challenger so far",
                            "finding":f"{p.get('name')} · {int(p.get('samples') or 0)} replays · {f(p.get('expectancy_pct')):+.2f}% expectancy. Shadow research only."})
    capsum=capture.get("summary") or {}
    if int(capsum.get("validated_trades") or 0)>0:
        avg=f(capsum.get("avg_winner_capture_pct"))
        discoveries.append({"type":"CAPTURE","status":"LEARNING","title":"Profit capture",
                            "finding":f"Validated winners are currently banking about {avg:.1f}% of their maximum favourable move on average."})
    winsum=winner.get("summary") or {}
    if int(winsum.get("winners") or 0)>0:
        discoveries.append({"type":"WINNERS","status":"LEARNING","title":"Winner School",
                            "finding":f"{int(winsum.get('winners') or 0)} profitable trades studied; {int(winsum.get('repeatable_fingerprints') or 0)} fingerprints have at least five examples."})
    failsum=failure.get("summary") or {}
    modes=failsum.get("failure_modes") or {}
    if modes:
        top=sorted(modes.items(),key=lambda x:x[1],reverse=True)[0]
        discoveries.append({"type":"FAILURES","status":"LEARNING","title":"Most common current failure",
                            "finding":f"{top[0]} is currently the largest recorded failure category ({top[1]} cases)."})
    for a in (memory.get("advisories") or [])[:3]:
        discoveries.append({"type":"COMMITTEE","status":"EVIDENCE","title":"Committee memory","finding":str(a)})

    # Brain control-centre status.
    valid=int(integrity.get("validated") or 0); reviewed=int(integrity.get("reviewed") or 0)
    integrity_rate=f(integrity.get("validation_rate_pct"),100)
    cap_n=int(capsum.get("validated_trades") or 0)
    pattern_n=int((patterns.get("summary") or {}).get("patterns") or 0)
    cand_n=int((patterns.get("summary") or {}).get("candidate_patterns") or 0)
    agent_n=int((memory.get("summary") or {}).get("agents") or 0)
    market_n=int((market_school.get("summary") or {}).get("observations") or (market_school.get("summary") or {}).get("observer_snapshots") or 0)

    brains=[
      brain_card("Trade Integrity",BRAIN_PURPOSES["Trade Integrity"],f"{valid}/{reviewed} validated" if reviewed else "Waiting for completed trades",
                 "HEALTHY" if reviewed and integrity_rate>=98 else "LEARNING" if reviewed else "WAITING",
                 f"{integrity_rate:.1f}% of reviewed trades currently pass the learning gate." if reviewed else "No completed trade evidence has reached the validator yet."),
      brain_card("Winner School",BRAIN_PURPOSES["Winner School"],f"{int(winsum.get('winners') or 0)} winners",
                 "BUILDING" if int(winsum.get("winners") or 0)>=10 else "EARLY" if int(winsum.get("winners") or 0)>0 else "WAITING",
                 f"{int(winsum.get('repeatable_fingerprints') or 0)} winner fingerprints currently have repeated examples."),
      brain_card("Failure School",BRAIN_PURPOSES["Failure School"],f"{int(failsum.get('cases') or 0)} review cases",
                 "BUILDING" if int(failsum.get("cases") or 0)>=10 else "EARLY" if int(failsum.get("cases") or 0)>0 else "WAITING",
                 f"{len(modes)} different failure categories are being tracked."),
      brain_card("Profit Capture",BRAIN_PURPOSES["Profit Capture"],f"{cap_n} validated trades",
                 "BUILDING" if cap_n>=20 else "EARLY" if cap_n>0 else "WAITING",
                 f"Average winner capture is {f(capsum.get('avg_winner_capture_pct')):.1f}%." if cap_n else "Waiting for validated completed trades."),
      brain_card("Pattern Miner",BRAIN_PURPOSES["Pattern Miner"],f"{pattern_n} fingerprints",
                 "MATURE EVIDENCE" if any(str(x.get("status"))=="MATURE" for x in patterns.get("patterns") or []) else "BUILDING" if cand_n else "EARLY" if pattern_n else "WAITING",
                 f"{cand_n} patterns currently have enough evidence to be considered candidates."),
      brain_card("Management Challengers",BRAIN_PURPOSES["Management Challengers"],f"{max([int(x.get('samples') or 0) for x in policies],default=0)} max replays",
                 "REVIEW READY" if any(int(x.get("samples") or 0)>=30 for x in policies) else "LEARNING" if policies else "WAITING",
                 (f"Current shadow leader: {policies[0].get('name')}." if policies else "No replay evidence yet.")),
      brain_card("Committee Memory",BRAIN_PURPOSES["Committee Memory"],f"{agent_n} agents tracked",
                 "BUILDING" if any(int((x or {}).get("samples") or 0)>=30 for x in (memory.get("agents") or {}).values()) else "EARLY" if agent_n else "WAITING",
                 f"{int((memory.get('summary') or {}).get('advisories') or 0)} evidence-based advisories currently recorded."),
      brain_card("Market School",BRAIN_PURPOSES["Market School"],f"{market_n} chart observations" if market_n else "Accumulating market history",
                 "LEARNING","Studies both traded and missed market moves so trade history is not the only teacher."),
      brain_card("Microstructure",BRAIN_PURPOSES["Microstructure"],f"{len(micro)} 1m/5m snapshots",
                 "BUILDING" if len(micro)>=100 else "EARLY" if micro else "WAITING",
                 "Separates entry, profit-protection, pullback and reversal timing rather than treating every turn as a new trade."),
      brain_card("AI Scorecard",BRAIN_PURPOSES["AI Scorecard"],f"{f(score.get('decision_quality_score')):.0f}/100 process score",
                 str(score.get("status") or "LEARNING"),
                 "This grades evidence/process maturity, not whether the next trade will win."),
    ]

    mature=sum(x["status"] in {"MATURE EVIDENCE","REVIEW READY","HEALTHY"} for x in brains)
    active=sum(x["status"]!="WAITING" for x in brains)
    payload={
      "updated_at":now(),
      "summary":{
        "strategies":len(strategy_rows),
        "strategies_review_ready":sum(x["promotion_status"]=="ELIGIBLE FOR REVIEW" for x in strategy_rows),
        "brains_active":active,"brains_total":len(brains),"brains_mature_or_healthy":mature,
        "discoveries":len(discoveries),
      },
      "strategies":strategy_rows,
      "discoveries":discoveries[:20],
      "brains":brains,
      "network":{
        "flow":"Market observation → specialist agents → committee → trade → integrity gate → replay → Winner/Failure School → pattern/management challengers → committee memory → shared feedback",
        "principle":"Small samples stay labelled EARLY/LEARNING. No challenger or lesson automatically replaces the current strategy."
      }
    }
    write(OUT,payload)
    print(json.dumps(payload["summary"],indent=2))
    return 0

if __name__=="__main__":raise SystemExit(main())
