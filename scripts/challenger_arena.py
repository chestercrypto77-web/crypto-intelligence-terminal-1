from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import copy,json,math

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
OUT=DATA/"challenger_arena.json"
START=100000.0
SIZE=1000.0
COST_PCT=0.30

STRATEGIES={
    "BASE_COMMITTEE":{
        "name":"Base Committee",
        "description":"Qualified committee direction with the existing hourly actionable signal.",
    },
    "VOLUME_CONFIRM":{
        "name":"Volume Confirmation",
        "description":"Base setup plus RVOL >= 1.15 and rising participation.",
    },
    "MULTI_TF_CONFIRM":{
        "name":"Multi-Timeframe Confirmation",
        "description":"Base setup plus 4H and 24H direction agreement.",
    },
    "SELECTIVE_EDGE":{
        "name":"Selective Edge",
        "description":"High-quality committee, strong participation and multi-timeframe agreement.",
    },
}

def now():return datetime.now(timezone.utc).isoformat()
def read(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return copy.deepcopy(d)
def write(p,x):
    t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding="utf-8")
    json.loads(t.read_text(encoding="utf-8")); t.replace(p)
def f(v,d=0.0):
    try:
        n=float(v); return n if math.isfinite(n) else d
    except Exception:return d
def side(signal):
    s=str(signal or "").upper()
    if "BUY" in s:return "LONG"
    if "SELL" in s:return "SHORT"
    return None
def ret(direction,entry,current):
    if not entry:return 0.0
    raw=(current/entry-1)*100
    return (raw if direction=="LONG" else -raw)-COST_PCT

def qualifies(strategy,s,committee):
    decision=(committee.get("decision") or {})
    d=decision.get("direction")
    signal_side=side(s.get("signal"))
    if d not in {"LONG","SHORT"} or signal_side!=d:return False
    if decision.get("action") not in {"BUY","SHORT"}:return False
    rvol=f(s.get("rvol")); rvold=f(s.get("rvol_delta"))
    r4=f(s.get("return_4h")); r24=f(s.get("return_24h"))
    tf=(r4>0 and r24>0) if d=="LONG" else (r4<0 and r24<0)
    if strategy=="BASE_COMMITTEE": return True
    if strategy=="VOLUME_CONFIRM": return rvol>=1.15 and rvold>0
    if strategy=="MULTI_TF_CONFIRM": return tf
    if strategy=="SELECTIVE_EDGE":
        return decision.get("quality")=="HIGH QUALITY" and rvol>=1.15 and rvold>0 and tf
    return False

def stats(book):
    closed=book.get("closed_positions") or []
    wins=[p for p in closed if f(p.get("realised_pnl"))>0]
    losses=[p for p in closed if f(p.get("realised_pnl"))<0]
    gp=sum(f(p.get("realised_pnl")) for p in wins)
    gl=abs(sum(f(p.get("realised_pnl")) for p in losses))
    returns=[f(p.get("realised_return")) for p in closed]
    equity=f(book.get("cash"))+sum(SIZE+f(p.get("unrealised_pnl")) for p in book.get("open_positions") or [])
    return {
        "equity":equity,
        "return_pct":(equity/START-1)*100,
        "closed_trades":len(closed),
        "wins":len(wins),
        "win_rate_pct":len(wins)/len(closed)*100 if closed else 0.0,
        "expectancy_pct":sum(returns)/len(returns) if returns else 0.0,
        "profit_factor":gp/gl if gl else (999.0 if gp else 0.0),
        "net_pnl":gp-gl,
    }

def main():
    state=read(OUT,{"updated_at":None,"starting_equity":START,"strategies":{},
        "promotion_policy":{"minimum_closed_trades":30,"minimum_win_rate_pct":55.0,
        "minimum_profit_factor":1.25,"minimum_expectancy_pct":0.20,"auto_promote":False}})
    signals=read(DATA/"signals_latest.json",{"signals":[]}).get("signals") or []
    committee=read(DATA/"committee_latest.json",{"assets":[]}).get("assets") or []
    cmap={str(x.get("symbol") or "").upper():x for x in committee}
    smap={str(x.get("symbol") or "").upper():x for x in signals}
    timestamp=now()

    for sid,meta in STRATEGIES.items():
        book=state.setdefault("strategies",{}).setdefault(sid,{
            **meta,"cash":START,"open_positions":[],"closed_positions":[],"equity_history":[],
        })
        keep=[]
        for p in book.get("open_positions") or []:
            s=smap.get(p.get("symbol"))
            if not s:
                keep.append(p); continue
            price=f(s.get("entry_price"))
            rr=ret(p["direction"],f(p["entry_price"]),price)
            p["current_price"]=price
            p["unrealised_return"]=rr
            p["unrealised_pnl"]=SIZE*rr/100
            p["mfe"]=max(f(p.get("mfe")),rr)
            p["mae"]=min(f(p.get("mae")),rr)
            # Common management so the entry filters are what compete.
            reason=None
            if rr<=-2.25: reason="SHADOW STOP"
            elif rr>=4.0: reason="SHADOW TARGET"
            elif f(p.get("mfe"))>=3 and f(p.get("mfe"))-rr>=2: reason="SHADOW PROFIT PROTECTION"
            current_side=side(s.get("signal"))
            if current_side and current_side!=p["direction"]: reason="SHADOW REVERSAL"
            if reason:
                p.update({"status":"CLOSED","exit_time":timestamp,"exit_price":price,"exit_reason":reason,
                    "realised_return":rr,"realised_pnl":SIZE*rr/100})
                book["cash"]+=SIZE+p["realised_pnl"]
                book.setdefault("closed_positions",[]).append(p)
            else: keep.append(p)
        book["open_positions"]=keep
        open_symbols={p.get("symbol") for p in keep}

        ranked=[]
        for s in signals:
            symbol=str(s.get("symbol") or "").upper()
            c=cmap.get(symbol) or {}
            if symbol in open_symbols or not qualifies(sid,s,c):continue
            agreement=((c.get("decision") or {}).get("agreement") or {})
            strength=max(f(agreement.get("long_votes")),f(agreement.get("short_votes")))
            ranked.append((strength,s,c))
        ranked.sort(key=lambda x:x[0],reverse=True)

        for _,s,c in ranked:
            if len(book["open_positions"])>=4 or f(book.get("cash"))<SIZE:break
            symbol=str(s.get("symbol") or "").upper()
            if symbol in {p.get("symbol") for p in book["open_positions"]}:continue
            entry=f(s.get("entry_price")); direction=(c.get("decision") or {}).get("direction")
            if entry<=0 or direction not in {"LONG","SHORT"}:continue
            p={"position_id":f"{sid}_{symbol}_{timestamp}","symbol":symbol,"direction":direction,
                "entry_time":timestamp,"entry_price":entry,"current_price":entry,"allocated_cash":SIZE,
                "status":"OPEN","unrealised_return":-COST_PCT,"unrealised_pnl":-SIZE*COST_PCT/100,
                "mfe":0.0,"mae":-COST_PCT,"entry_snapshot":{
                    "rvol":s.get("rvol"),"rvol_delta":s.get("rvol_delta"),"return_4h":s.get("return_4h"),
                    "return_24h":s.get("return_24h"),"signal":s.get("signal"),
                    "committee_quality":(c.get("decision") or {}).get("quality")}}
            book["cash"]-=SIZE
            book["open_positions"].append(p)

        m=stats(book)
        book["metrics"]=m
        book.setdefault("equity_history",[]).append({"recorded_at":timestamp,"equity":m["equity"]})
        book["equity_history"]=book["equity_history"][-10000:]
        book["closed_positions"]=book.get("closed_positions",[])[-20000:]

    policy=state.get("promotion_policy") or {}
    ranking=[]
    for sid,book in state.get("strategies",{}).items():
        m=book.get("metrics") or stats(book)
        eligible=(int(m.get("closed_trades") or 0)>=int(policy.get("minimum_closed_trades",30))
            and f(m.get("win_rate_pct"))>=f(policy.get("minimum_win_rate_pct"),55)
            and f(m.get("profit_factor"))>=f(policy.get("minimum_profit_factor"),1.25)
            and f(m.get("expectancy_pct"))>=f(policy.get("minimum_expectancy_pct"),0.20))
        ranking.append({"strategy_id":sid,"name":book.get("name"),**m,
            "promotion_status":"ELIGIBLE FOR REVIEW" if eligible else "LEARNING"})
    ranking.sort(key=lambda x:(x["promotion_status"]=="ELIGIBLE FOR REVIEW",f(x.get("expectancy_pct")),
        f(x.get("profit_factor")),f(x.get("win_rate_pct"))),reverse=True)
    state["updated_at"]=timestamp
    state["ranking"]=ranking
    state["note"]="Shadow competition only. No challenger changes main trading rules or capital automatically."
    write(OUT,state)
    print(json.dumps({"strategies":len(ranking),"leader":ranking[0] if ranking else None},indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
