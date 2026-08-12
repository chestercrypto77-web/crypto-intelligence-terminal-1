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

OUT=DATA/"time_intelligence.json"
def directional(direction,entry,price):
    if entry<=0 or price<=0:return 0.0
    raw=(price/entry-1)*100
    return raw if str(direction).upper()=="LONG" else -raw

def trade_timing(r):
    entry_time=r.get("entry_time");exit_time=r.get("exit_time")
    duration=hours(entry_time,exit_time)
    replay=r.get("replay") or {}
    path=sorted(replay.get("price_path") or [],key=lambda x:str(x.get("time") or ""))
    entry=f(r.get("entry_price")); direction=r.get("direction")
    points=[]
    for p in path:
        t=parse_time(p.get("time"));price=f(p.get("price"))
        if t and price>0:
            move=directional(direction,entry,price)
            points.append((t,price,move))
    et=parse_time(entry_time);xt=parse_time(exit_time)
    held=[x for x in points if et and xt and et<=x[0]<=xt]
    if not held and et and xt:
        held=[(et,entry,0),(xt,f(r.get("exit_price")),f(r.get("realised_return")))]
    mfe=max((x[2] for x in held),default=f(r.get("maximum_favourable_excursion_pct")))
    mae=min((x[2] for x in held),default=f(r.get("maximum_adverse_excursion_pct")))
    max_point=max(held,key=lambda x:x[2]) if held else None
    min_point=min(held,key=lambda x:x[2]) if held else None
    time_to_mfe=(max_point[0]-et).total_seconds()/3600 if max_point and et else None
    time_to_mae=(min_point[0]-et).total_seconds()/3600 if min_point and et else None
    peak_to_exit=(xt-max_point[0]).total_seconds()/3600 if max_point and xt else None

    first_profit=None
    profitable_points=0
    for t,price,move in held:
        if move>0:
            profitable_points+=1
            if first_profit is None:first_profit=(t-et).total_seconds()/3600 if et else None
    profitable_share=profitable_points/len(held)*100 if held else None

    events=replay.get("events") or []
    reentry_time=None
    for ev in events:
        if str(ev.get("event") or "").upper()=="REENTRY":
            reentry_time=ev.get("time");break
    reentry_delay=hours(exit_time,reentry_time) if reentry_time else None

    ret=f(r.get("realised_return"))
    efficiency={
      "entry_timing":"UNSCORED",
      "holding_time":"UNSCORED",
      "exit_timing":"UNSCORED"
    }
    # Descriptive, not hindsight-driven live score.
    if duration is not None:
        efficiency["holding_time"]="EFFICIENT" if ret>0 and peak_to_exit is not None and peak_to_exit<=max(0.5,duration*0.25) else \
                                   "OVER-HELD REVIEW" if peak_to_exit is not None and peak_to_exit>max(1.0,duration*0.45) else "REVIEW"
    capture=f((r.get("capture") or {}).get("capture_efficiency_pct"))
    if capture<=0:
        mfe_stored=f(r.get("maximum_favourable_excursion_pct"))
        capture=max(0,ret)/mfe_stored*100 if mfe_stored>0 else 0
    efficiency["exit_timing"]="STRONG" if capture>=70 else "FAIR" if capture>=45 else "WEAK" if mfe>0.75 else "UNSCORED"

    return {
      "trade_key":trade_key(r),"symbol":r.get("symbol"),"wallet":r.get("wallet"),"direction":r.get("direction"),
      "entry_time":entry_time,"exit_time":exit_time,"holding_hours":duration,
      "first_profit_hours":first_profit,"time_to_mfe_hours":time_to_mfe,"time_to_mae_hours":time_to_mae,
      "peak_to_exit_hours":peak_to_exit,"profitable_observation_share_pct":profitable_share,
      "reentry_time":reentry_time,"exit_to_reentry_hours":reentry_delay,
      "mfe_pct":mfe,"mae_pct":mae,"realised_return_pct":ret,
      "capture_efficiency_pct":capture,"timing_assessment":efficiency,
    }

def main():
    reviews=read(DATA/"trade_reviews.json",{"reviews":[]}).get("reviews") or []
    integrity=read(DATA/"trade_integrity.json",{"records":[]}).get("records") or []
    valid={str(x.get("trade_key")) for x in integrity if x.get("status")=="VALIDATED"}
    captures={str(x.get("trade_key")):x for x in read(DATA/"profit_capture.json",{"records":[]}).get("records") or []}
    rows=[]
    for r in reviews:
        if valid and trade_key(r) not in valid:continue
        rr=dict(r);rr["capture"]=captures.get(trade_key(r),{})
        rows.append(trade_timing(rr))
    wins=[x for x in rows if f(x.get("realised_return_pct"))>0 and x.get("holding_hours") is not None]
    losses=[x for x in rows if f(x.get("realised_return_pct"))<0 and x.get("holding_hours") is not None]
    def avg(items,key):
        vals=[f(x.get(key)) for x in items if x.get(key) is not None]
        return sum(vals)/len(vals) if vals else 0
    summary={
      "trades_timed":len(rows),
      "avg_winner_holding_hours":avg(wins,"holding_hours"),
      "avg_loser_holding_hours":avg(losses,"holding_hours"),
      "avg_winner_time_to_mfe_hours":avg(wins,"time_to_mfe_hours"),
      "avg_peak_to_exit_hours":avg(rows,"peak_to_exit_hours"),
      "overheld_reviews":sum((x.get("timing_assessment") or {}).get("holding_time")=="OVER-HELD REVIEW" for x in rows),
      "reentry_delays_measured":sum(x.get("exit_to_reentry_hours") is not None for x in rows),
    }
    write(OUT,{"updated_at":now(),"summary":summary,"records":rows[-30000:],
               "principle":"Timing labels are historical evidence. Future timestamps never influence a live trade decision."})
    print(json.dumps(summary,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
