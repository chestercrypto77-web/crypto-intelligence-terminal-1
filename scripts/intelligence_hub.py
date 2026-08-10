from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import copy,json,math
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"; OUT=DATA/"intelligence_bus.json"
def now():return datetime.now(timezone.utc).isoformat()
def read(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return copy.deepcopy(d)
def write(p,x):
    t=p.with_suffix(p.suffix+".tmp"); t.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding="utf-8")
    json.loads(t.read_text(encoding="utf-8")); t.replace(p)
def f(v,d=0.0):
    try:
        n=float(v); return n if math.isfinite(n) else d
    except:return d
def current_pattern(obs):
    signal=str(obs.get("signal") or "NEUTRAL").upper().replace(" ","_")
    rv=f(obs.get("rvol")); rvb="RVOL_2PLUS" if rv>=2 else "RVOL_1_5_2" if rv>=1.5 else "RVOL_1_15_1_5" if rv>=1.15 else "RVOL_WEAK" if rv<0.75 else "RVOL_NORMAL"
    rsi=f(obs.get("rsi"),50); rsib="RSI_OVERBOUGHT" if rsi>=75 else "RSI_BULL" if rsi>=60 else "RSI_OVERSOLD" if rsi<=25 else "RSI_BEAR" if rsi<=40 else "RSI_MID"
    mh=f(obs.get("macd_histogram")); md=f(obs.get("macd_delta")); macd="MACD_UP" if mh>0 and md>=0 else "MACD_DOWN" if mh<0 and md<=0 else "MACD_MIXED"
    structure="BREAKOUT" if obs.get("breakout") else "BREAKDOWN" if obs.get("breakdown") else "RANGE"
    bull=f(obs.get("bullish_conditions")); bear=f(obs.get("bearish_conditions")); align="BULLISH" if bull-bear>=5 else "BEARISH" if bear-bull>=5 else "MIXED"
    return "|".join([signal,rvb,rsib,macd,structure,align])
def main():
    signals=read(DATA/"signals_latest.json",{"signals":[]}).get("signals") or []
    observer=read(DATA/"observer_latest.json",{"signals":[]}).get("signals") or []
    micro=read(DATA/"microstructure_latest.json",{"signals":[]}).get("signals") or []
    committee=read(DATA/"committee_latest.json",{"assets":[]})
    risk=read(DATA/"risk_guardian.json",{"asset_checks":[]})
    school=read(DATA/"market_school.json",{})
    diagnostics=read(DATA/"trade_diagnostics.json",{})
    learning=read(DATA/"learning_state.json",{})
    arena=read(DATA/"challenger_arena.json",{})
    coach=read(DATA/"trade_coach.json",{})
    confidence=read(DATA/"confidence_ledger.json",{})
    omap={str(x.get("symbol") or "").upper():x for x in observer}
    mmap={str(x.get("symbol") or "").upper():x for x in micro}
    cmap={str(x.get("symbol") or "").upper():x for x in committee.get("assets") or []}
    rmap={str(x.get("symbol") or "").upper():x for x in risk.get("asset_checks") or []}
    smap={str(x.get("symbol") or "").upper():x for x in signals}
    assets={}
    messages=[]
    for symbol,s in smap.items():
        o=omap.get(symbol,{})
        m=mmap.get(symbol,{})
        c=cmap.get(symbol,{})
        pkey=current_pattern(o) if o else None
        asset_patterns=(school.get("asset_patterns") or {}).get(symbol,{})
        pattern=(asset_patterns.get(pkey) or (school.get("global_patterns") or {}).get(pkey) or {}) if pkey else {}
        p4=pattern.get("4h") or {}
        samples=int(p4.get("samples") or 0)
        up=f(p4.get("up_rate_pct")); down=f(p4.get("down_rate_pct")); avg=f(p4.get("avg_return_pct"))
        memory_direction="LONG" if samples>=10 and up>=60 and avg>0 else "SHORT" if samples>=10 and down>=60 and avg<0 else "NEUTRAL"
        maturity="MATURE" if samples>=20 else "DEVELOPING" if samples>=10 else "EARLY"
        asset={
            "symbol":symbol,
            "hourly_signal":s.get("signal"),
            "observer_signal":o.get("signal"),
            "microstructure_signal":m.get("role_signal"),
            "microstructure_state":m.get("state"),
            "microstructure_reason":m.get("reason"),
            "committee_decision":c.get("decision") or {},
            "risk_state":(rmap.get(symbol) or {}).get("state","NORMAL"),
            "market_memory":{
                "pattern":pkey,"samples":samples,"maturity":maturity,"direction":memory_direction,
                "4h_avg_return_pct":avg,"4h_up_rate_pct":up,"4h_down_rate_pct":down,
            },
            "communication":{
                "technical_return_4h":s.get("return_4h"),"technical_return_24h":s.get("return_24h"),
                "rvol":o.get("rvol",s.get("rvol")),"rvol_delta":o.get("rvol_delta",s.get("rvol_delta")),
                "rsi":o.get("rsi"),"macd_histogram":o.get("macd_histogram"),
                "micro_1m":m.get("one_minute"),"micro_5m":m.get("five_minute"),
            }
        }
        assets[symbol]=asset
        if maturity=="MATURE" and memory_direction!="NEUTRAL":
            messages.append({"source":"MARKET_SCHOOL","symbol":symbol,"type":"MATURE_PATTERN",
                "message":f"{samples} historical matches favour {memory_direction}; 4H average {avg:+.2f}%."})
    payload={
        "updated_at":now(),
        "market_regime":(committee.get("market_regime") or {}).get("state","UNKNOWN"),
        "global_learning":learning.get("summary") or {},
        "diagnostics_summary":diagnostics.get("summary") or {},
        "challenger_leader":(arena.get("ranking") or [None])[0],
        "trade_coach_summary":coach.get("summary") or {},
        "agent_confidence":confidence.get("agents") or {},
        "assets":assets,
        "messages":messages[-1000:],
        "principle":"Agents share evidence through this bus. Mature evidence may influence decisions; immature evidence remains observational."
    }
    write(OUT,payload)
    print(json.dumps({"assets":len(assets),"messages":len(messages),"market_regime":payload["market_regime"]},indent=2))
    return 0
if __name__=="__main__":raise SystemExit(main())
