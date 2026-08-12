from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import copy, json, math

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
OUT=DATA/"active_trade_casefiles.json"
HISTORY=DATA/"active_trade_thought_history.json"

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

def directional(direction,entry,current):
    if entry<=0 or current<=0:return 0.0
    raw=(current/entry-1)*100
    return raw if str(direction).upper()=="LONG" else -raw

def current_market():
    obs=read(DATA/"observer_latest.json",{"signals":[]}).get("signals") or []
    hourly=read(DATA/"signals_latest.json",{"signals":[]}).get("signals") or []
    micro=read(DATA/"microstructure_latest.json",{"signals":[]}).get("signals") or []
    market={}
    for x in hourly:
        market[str(x.get("symbol") or "").upper()]={"hourly":x}
    for x in obs:
        market.setdefault(str(x.get("symbol") or "").upper(),{})["observer"]=x
    for x in micro:
        market.setdefault(str(x.get("symbol") or "").upper(),{})["micro"]=x
    return market

def current_price(position,ctx):
    obs=ctx.get("observer") or {}
    micro=ctx.get("micro") or {}
    hourly=ctx.get("hourly") or {}
    for row in (micro,obs,hourly):
        for key in ("price","entry_price","current_price"):
            value=f(row.get(key))
            if value>0:return value
    return f(position.get("current_price"),f(position.get("entry_price")))

def committee_for(symbol,position):
    live=read(DATA/"committee_latest.json",{"assets":[]}).get("assets") or []
    cmap={str(x.get("symbol") or "").upper():x for x in live}
    return cmap.get(symbol) or position.get("committee_snapshot") or {}

def rule_for(book,wallet,key,default):
    return f((wallet.get("rules") or {}).get(key),default)

def mission(book,ret,mfe,risk_state,micro_signal,committee_decision):
    direction=str(committee_decision.get("direction") or "")
    quality=str(committee_decision.get("quality") or "")
    if risk_state in {"INVALIDATION RISK","DATA UNRELIABLE","SEVERE"}:
        return "REDUCE / EXIT RISK","Risk controls are warning that the position thesis may no longer be safe."
    if ret<=-1.5:
        return "DEFEND CAPITAL","Position is losing enough to require closer risk attention."
    protect=("EXIT / PROFIT PROTECT" in micro_signal) or ret>=3 or (mfe>=3 and mfe-ret>=1)
    if protect:
        return "PROTECT WINNER","The trade has earned profit; management should now focus on keeping a worthwhile share of it."
    if ret>0 and mfe>=1:
        return "LET WINNER WORK","The position is profitable and there is not yet enough exit evidence to force it closed."
    if quality in {"HIGH","VERY HIGH"}:
        return "HIGH-QUALITY HOLD","Committee evidence remains supportive while the trade develops."
    if direction in {"LONG","SHORT"}:
        return "HOLD / MONITOR","The thesis remains active, but the position still needs confirmation from price and microstructure."
    return "WAIT FOR CLARITY","The position is open but fresh evidence is mixed."

def health(ret,risk_state,committee,micro_signal,mfe):
    score=50
    decision=committee.get("decision") or {}
    quality=str(decision.get("quality") or "")
    agreement=decision.get("agreement") or {}
    direction=str(decision.get("direction") or "")
    if quality in {"HIGH","VERY HIGH"}:score+=15
    elif quality in {"LOW","REJECTED"}:score-=15
    if risk_state=="NORMAL":score+=10
    elif risk_state=="CAUTION":score-=5
    else:score-=20
    if ret>0:score+=min(15,ret*3)
    elif ret<-1:score-=min(20,abs(ret)*5)
    if "PROFIT PROTECT" in micro_signal and mfe>0:score-=5
    score=max(0,min(100,score))
    label="VERY STRONG" if score>=80 else "STRONG" if score>=65 else "NORMAL" if score>=45 else "WEAK" if score>=30 else "DANGER"
    return score,label

def plain_thoughts(position,ctx,committee,risk_state,mission_name,ret,mfe):
    thoughts=[]
    direction=str(position.get("direction") or "")
    micro=str((ctx.get("micro") or {}).get("role_signal") or "NO ACTION")
    obs=ctx.get("observer") or {}
    rvol=f(obs.get("rvol"))
    rvold=f(obs.get("rvol_delta"))
    decision=committee.get("decision") or {}
    cdir=str(decision.get("direction") or "NEUTRAL")
    if cdir==direction:thoughts.append(f"Committee still supports the {direction.lower()} direction.")
    elif cdir in {"LONG","SHORT"} and cdir!=direction:thoughts.append("Committee direction now conflicts with the open trade.")
    else:thoughts.append("Committee is not giving strong fresh directional confirmation.")
    if rvol>=1.15:thoughts.append("Market participation remains active.")
    elif rvol>0:thoughts.append("Participation is not especially strong.")
    if rvold>0.08:thoughts.append("Relative volume is increasing.")
    elif rvold<-0.08:thoughts.append("Relative volume is fading.")
    if micro!="NO ACTION":thoughts.append(f"1m/5m microstructure currently says {micro.lower()}.")
    if ret>0 and mfe-ret>=1:thoughts.append(f"The trade has given back about {mfe-ret:.2f}% from its best move.")
    thoughts.append(f"Current mission: {mission_name.lower()}.")
    if risk_state!="NORMAL":thoughts.append(f"Risk Guardian state is {risk_state.lower()}.")
    return thoughts[:6]

def active_signature(position):
    snap=position.get("entry_snapshot") or {}
    d=str(position.get("direction") or "").upper()
    r4=f(snap.get("return_4h"));r24=f(snap.get("return_24h"));rv=f(snap.get("rvol"));rvd=f(snap.get("rvol_delta"))
    alignment="WITH TREND" if (d=="LONG" and r4>=0 and r24>=0) or (d=="SHORT" and r4<=0 and r24<=0) else "COUNTER / MIXED"
    participation="HIGH" if rv>=1.5 else "ACTIVE" if rv>=1.15 else "WEAK" if rv<0.8 else "NORMAL"
    accel="RISING" if rvd>0.1 else "FADING" if rvd<-0.1 else "FLAT"
    bull=f(snap.get("bullish"));bear=f(snap.get("bearish"))
    conditions="BULLISH" if bull-bear>=4 else "BEARISH" if bear-bull>=4 else "MIXED"
    return {"direction":d,"alignment":alignment,"participation":participation,"volume_acceleration":accel,"conditions":conditions}

def winner_similarity(position):
    active=active_signature(position)
    winners=read(DATA/"winner_school.json",{"examples":[]}).get("examples") or []
    matches=[]
    for w in winners:
        feat=w.get("features") or {}
        candidate={
            "direction":str(w.get("direction") or ""),
            "alignment":feat.get("alignment"),
            "participation":feat.get("participation"),
            "volume_acceleration":feat.get("volume_acceleration"),
            "conditions":feat.get("conditions"),
        }
        keys=["direction","alignment","participation","volume_acceleration","conditions"]
        same=sum(active.get(k)==candidate.get(k) for k in keys)
        similarity=same/len(keys)*100
        matches.append({"symbol":w.get("symbol"),"return_pct":f(w.get("return_pct")),"similarity_pct":similarity,
                        "signature":w.get("signature")})
    matches.sort(key=lambda x:(x["similarity_pct"],x["return_pct"]),reverse=True)
    best=matches[0] if matches else None
    return best,matches[:3]

def failure_warnings(position):
    active=active_signature(position)
    failures=read(DATA/"failure_school.json",{"examples":[]}).get("examples") or []
    warnings=[]
    for x in failures:
        feat=x.get("features") or {}
        keys=["alignment","participation","volume_acceleration","conditions"]
        same=sum(active.get(k)==feat.get(k) for k in keys)
        similarity=same/len(keys)*100
        if similarity>=75:
            warnings.append({"failure_mode":x.get("failure_mode"),"symbol":x.get("symbol"),"similarity_pct":similarity})
    warnings.sort(key=lambda x:x["similarity_pct"],reverse=True)
    return warnings[:3]

def planned_risk(book,wallet,position,ret,mfe):
    alloc=f(position.get("allocated_cash"))
    stop=rule_for(book,wallet,"stop_loss_pct",1.25 if book=="SCALP" else 3.0 if book=="SWING" else 8.0)
    planned_loss=alloc*stop/100
    # Distance from today's marked P/L to the original stop threshold. This is not a guaranteed execution value.
    downside_to_original_stop=max(0,ret+stop)
    current_downside=alloc*downside_to_original_stop/100
    trail_active=False; protected_floor_pct=None
    if book=="SWING":
        trigger=rule_for(book,wallet,"profit_protection_trigger_pct",3.0)
        draw=rule_for(book,wallet,"trailing_drawdown_from_peak_pct",2.0)
        if mfe>=trigger:
            trail_active=True;protected_floor_pct=max(0,mfe-draw)
    elif book=="CORE":
        draw=rule_for(book,wallet,"trailing_drawdown_from_peak_pct",6.0)
        if mfe>=10:
            trail_active=True;protected_floor_pct=max(0,mfe-draw)
    elif book=="SCALP":
        target=rule_for(book,wallet,"take_profit_pct",2.25)
        if mfe>=target:
            trail_active=True;protected_floor_pct=max(0,target)
    protected=alloc*protected_floor_pct/100 if protected_floor_pct is not None else 0.0
    return {"stop_loss_pct":stop,"planned_max_loss_usd":planned_loss,
            "downside_from_mark_to_original_stop_pct":downside_to_original_stop,
            "downside_from_mark_to_original_stop_usd":current_downside,
            "profit_protection_active":trail_active,"estimated_protected_floor_pct":protected_floor_pct,
            "estimated_protected_profit_usd":protected,
            "note":"Risk and protected-profit figures are rule-based estimates; actual fills can differ."}

def main():
    market=current_market()
    phases=read(DATA/"move_phase_intelligence.json",{"records":[]}).get("records") or []
    phase_map={str(x.get("symbol") or "").upper():x for x in phases}
    risks=read(DATA/"risk_guardian.json",{"asset_checks":[]}).get("asset_checks") or []
    riskmap={str(x.get("symbol") or "").upper():x for x in risks}
    wallets=[
        ("CORE",read(DATA/"core_wallet.json",{})),
        ("SWING",read(DATA/"swing_wallet.json",{})),
        ("SCALP",read(DATA/"scalp_wallet.json",{})),
    ]
    positions=[]
    thought_history=read(HISTORY,{"records":[]})
    history=thought_history.get("records") or []
    timestamp=now()

    total_cash=0; total_equity=0
    for book,wallet in wallets:
        total_cash+=f(wallet.get("cash"))
        total_equity+=f(wallet.get("equity"),f(wallet.get("starting_cash")))
        for p in wallet.get("open_positions") or []:
            symbol=str(p.get("symbol") or "").upper()
            ctx=market.get(symbol,{})
            price=current_price(p,ctx)
            entry=f(p.get("entry_price"))
            # Preserve known trading friction where the wallet does; this view is an approximate live directional mark.
            gross=directional(p.get("direction"),entry,price)
            stored=f(p.get("unrealised_return"),gross)
            ret=stored if abs(price-f(p.get("current_price")))<max(1e-12,price*0.00001) else gross-0.30
            alloc=f(p.get("allocated_cash"))
            pnl=alloc*ret/100
            mfe=max(f(p.get("maximum_favourable_excursion_pct")),ret)
            peak_usd=max(0,alloc*mfe/100)
            giveback=max(0,peak_usd-pnl)
            riskrow=riskmap.get(symbol) or {}
            risk_state=str(riskrow.get("state") or "NORMAL").upper()
            committee=committee_for(symbol,p)
            decision=committee.get("decision") or {}
            micro_signal=str((ctx.get("micro") or {}).get("role_signal") or
                             ((p.get("shared_intelligence") or {}).get("microstructure_signal") or "NO ACTION"))
            mission_name,mission_reason=mission(book,ret,mfe,risk_state,micro_signal,decision)
            health_score,health_label=health(ret,risk_state,committee,micro_signal,mfe)
            risk=planned_risk(book,wallet,p,ret,mfe)
            best,similar=winner_similarity(p)
            warnings=failure_warnings(p)
            thoughts=plain_thoughts(p,ctx,committee,risk_state,mission_name,ret,mfe)
            phase_now=(phase_map.get(symbol) or {}).get("phase")
            held_hours=hours(p.get("entry_time"),timestamp)
            if phase_now: thoughts.insert(0,f"Timed move phase is {str(phase_now).lower()}.")
            if held_hours is not None: thoughts.append(f"Trade has been open for {held_hours:.1f} hours.")
            thoughts=thoughts[:7]
            case={
              "case_id":p.get("case_id") or p.get("position_id"),
              "position_id":p.get("position_id"),"symbol":symbol,"name":p.get("name") or symbol,
              "book":book,"direction":p.get("direction"),"signal":p.get("signal"),
              "entry_time":p.get("entry_time"),"entry_price":entry,"current_price":price,
              "allocated_cash":alloc,"book_equity":f(wallet.get("equity")),
              "allocation_pct_of_book":alloc/f(wallet.get("equity"),1)*100 if f(wallet.get("equity"))>0 else 0,
              "return_pct":ret,"pnl_usd":pnl,"mfe_pct":mfe,
              "mae_pct":f(p.get("maximum_adverse_excursion_pct")),
              "peak_profit_usd":peak_usd,"profit_giveback_usd":giveback,
              "mission":mission_name,"mission_reason":mission_reason,
              "health_score":health_score,"health":health_label,
              "risk_state":risk_state,"risk":risk,
              "committee":{"decision":decision,"reports":committee.get("reports") or {}},
              "microstructure_signal":micro_signal,
              "current_thinking":thoughts,
              "winner_school":{"best_match":best,"similar_trades":similar},
              "failure_school":{"warnings":warnings},
              "stage":"PROTECT" if mission_name=="PROTECT WINNER" else "RISK REVIEW" if "RISK" in mission_name or "DEFEND" in mission_name else "MANAGE",
              "move_phase":phase_map.get(symbol,{}) or {},
              "holding_hours":hours(p.get("entry_time"),timestamp),
              "recorded_at":timestamp,
            }
            positions.append(case)
            history.append({
              "recorded_at":timestamp,"case_id":case["case_id"],"position_id":case["position_id"],
              "symbol":symbol,"book":book,"direction":p.get("direction"),"price":price,
              "return_pct":ret,"pnl_usd":pnl,"mfe_pct":mfe,"mission":mission_name,
              "health":health_label,"risk_state":risk_state,"microstructure_signal":micro_signal,
              "committee_direction":decision.get("direction"),"committee_quality":decision.get("quality"),
              "thoughts":thoughts
            })

    # Bound history per case and globally.
    grouped={}
    for r in history:
        grouped.setdefault(str(r.get("case_id") or r.get("position_id")),[]).append(r)
    bounded=[]
    for rows in grouped.values():
        bounded.extend(rows[-600:])
    bounded=sorted(bounded,key=lambda x:str(x.get("recorded_at") or ""))[-30000:]
    write(HISTORY,{"updated_at":timestamp,"records":bounded})

    capital_working=sum(x["allocated_cash"] for x in positions)
    portfolio_planned_risk=sum(f((x.get("risk") or {}).get("planned_max_loss_usd")) for x in positions)
    open_pnl=sum(x["pnl_usd"] for x in positions)
    protected=sum(f((x.get("risk") or {}).get("estimated_protected_profit_usd")) for x in positions)
    peak=sum(x["peak_profit_usd"] for x in positions)
    missions={}
    for x in positions:missions[x["mission"]]=missions.get(x["mission"],0)+1
    payload={
      "updated_at":timestamp,
      "summary":{"active_positions":len(positions),"capital_working":capital_working,
                 "available_cash":total_cash,"total_equity":total_equity,
                 "planned_max_loss_usd":portfolio_planned_risk,"open_pnl_usd":open_pnl,
                 "estimated_protected_profit_usd":protected,"aggregate_peak_profit_usd":peak},
      "portfolio":{"missions":missions},
      "positions":sorted(positions,key=lambda x:x["pnl_usd"],reverse=True)
    }
    write(OUT,payload)
    print(json.dumps(payload["summary"],indent=2));return 0

if __name__=="__main__":raise SystemExit(main())
