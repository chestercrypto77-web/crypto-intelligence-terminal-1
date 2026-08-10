from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from collections import defaultdict
import copy,json,math
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
OUT=DATA/"market_school.json"
HORIZONS={"1h":1,"4h":4,"12h":12,"24h":24}

def now(): return datetime.now(timezone.utc).isoformat()
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
def ts(v):
    try:
        x=pd.Timestamp(v)
        if x.tzinfo is None:x=x.tz_localize("UTC")
        return x.tz_convert("UTC")
    except Exception:return None
def bucket_rvol(x):
    x=f(x)
    if x>=2:return "RVOL_2PLUS"
    if x>=1.5:return "RVOL_1_5_2"
    if x>=1.15:return "RVOL_1_15_1_5"
    if x<0.75:return "RVOL_WEAK"
    return "RVOL_NORMAL"
def bucket_rsi(x):
    x=f(x,50)
    if x>=75:return "RSI_OVERBOUGHT"
    if x>=60:return "RSI_BULL"
    if x<=25:return "RSI_OVERSOLD"
    if x<=40:return "RSI_BEAR"
    return "RSI_MID"
def structure(r):
    if bool(r.get("breakout")):return "BREAKOUT"
    if bool(r.get("breakdown")):return "BREAKDOWN"
    return "RANGE"
def alignment(r):
    bull=f(r.get("bullish_conditions"),f(r.get("bullish")))
    bear=f(r.get("bearish_conditions"),f(r.get("bearish")))
    if bull-bear>=5:return "BULLISH"
    if bear-bull>=5:return "BEARISH"
    return "MIXED"
def pattern_key(r):
    signal=str(r.get("signal") or "NEUTRAL").upper().replace(" ","_")
    macd="MACD_UP" if f(r.get("macd_histogram"))>0 and f(r.get("macd_delta"))>=0 else "MACD_DOWN" if f(r.get("macd_histogram"))<0 and f(r.get("macd_delta"))<=0 else "MACD_MIXED"
    return "|".join([signal,bucket_rvol(r.get("rvol")),bucket_rsi(r.get("rsi")),macd,structure(r),alignment(r)])
def forward_price(rows,i,hours):
    start=rows[i]["_ts"]; target=start+pd.Timedelta(hours=hours)
    for j in range(i+1,len(rows)):
        if rows[j]["_ts"]>=target:
            return f(rows[j].get("price")),rows[j]["_ts"]
    return 0.0,None
def summarize(samples):
    out={"samples":len(samples)}
    for label in HORIZONS:
        vals=[f(x.get(f"forward_{label}")) for x in samples if x.get(f"forward_{label}") is not None]
        if not vals:
            out[label]={"samples":0,"avg_return_pct":0.0,"up_rate_pct":0.0,"down_rate_pct":0.0,"large_up_rate_pct":0.0,"large_down_rate_pct":0.0}
            continue
        out[label]={
            "samples":len(vals),
            "avg_return_pct":sum(vals)/len(vals),
            "up_rate_pct":sum(v>0 for v in vals)/len(vals)*100,
            "down_rate_pct":sum(v<0 for v in vals)/len(vals)*100,
            "large_up_rate_pct":sum(v>=5 for v in vals)/len(vals)*100,
            "large_down_rate_pct":sum(v<=-5 for v in vals)/len(vals)*100,
        }
    return out

def build_micro_learning(history):
    """Retrospective labels for 1m/5m states. Future movement labels old examples only."""
    by={}
    for r in history:
        sym=str(r.get('symbol') or '').upper()
        if not sym:continue
        by.setdefault(sym,[]).append(r)
    groups={}
    events=[]
    for sym,rows in by.items():
        rows=sorted(rows,key=lambda x:str(x.get('recorded_at') or ''))
        for i,r in enumerate(rows):
            price=f(r.get('price'))
            if price<=0:continue
            role=str(r.get('role_signal') or 'NO ACTION')
            future=None
            if i+3<len(rows):future=f(rows[i+3].get('price'))
            if not future:continue
            move=(future/price-1)*100
            g=groups.setdefault(role,{'samples':0,'sum_15m':0.0,'up':0,'down':0})
            g['samples']+=1; g['sum_15m']+=move; g['up']+=1 if move>0 else 0; g['down']+=1 if move<0 else 0
            if abs(move)>=3:events.append({'symbol':sym,'recorded_at':r.get('recorded_at'),'role_signal':role,'forward_15m_pct':move,'state':r.get('state')})
    summary={}
    for role,g in groups.items():
        n=g['samples']; summary[role]={'samples':n,'avg_forward_15m_pct':g['sum_15m']/n if n else 0,'up_rate_pct':g['up']/n*100 if n else 0,'down_rate_pct':g['down']/n*100 if n else 0}
    return {'patterns':summary,'large_15m_moves':sorted(events,key=lambda x:abs(f(x.get('forward_15m_pct'))),reverse=True)[:1000],'snapshots':len(history)}

def main():
    history=read(DATA/"observer_history.json",[])
    micro_history=read(DATA/"microstructure_history.json",[])
    by_symbol=defaultdict(list)
    for raw in history:
        symbol=str(raw.get("symbol") or "").upper()
        t=ts(raw.get("recorded_at") or raw.get("candle_time"))
        price=f(raw.get("price"))
        if not symbol or t is None or price<=0:continue
        row=dict(raw); row["_ts"]=t
        by_symbol[symbol].append(row)

    global_groups=defaultdict(list)
    asset_groups=defaultdict(lambda:defaultdict(list))
    large_moves=[]
    asset_memory={}
    labelled=0

    for symbol,rows in by_symbol.items():
        rows.sort(key=lambda x:x["_ts"])
        asset_samples=[]
        for i,row in enumerate(rows):
            sample={
                "symbol":symbol,
                "time":row["_ts"].isoformat(),
                "price":f(row.get("price")),
                "pattern":pattern_key(row),
                "signal":row.get("signal"),
                "rvol":f(row.get("rvol")),
                "rvol_delta":f(row.get("rvol_delta")),
                "rsi":f(row.get("rsi"),50),
                "rsi_delta":f(row.get("rsi_delta")),
                "macd_histogram":f(row.get("macd_histogram")),
                "macd_delta":f(row.get("macd_delta")),
                "return_1h":f(row.get("return_1h")),
                "return_4h":f(row.get("return_4h")),
                "bullish_conditions":f(row.get("bullish_conditions")),
                "bearish_conditions":f(row.get("bearish_conditions")),
                "breakout":bool(row.get("breakout")),
                "breakdown":bool(row.get("breakdown")),
            }
            available=False
            for label,hours in HORIZONS.items():
                future,_=forward_price(rows,i,hours)
                if future>0:
                    sample[f"forward_{label}"]=(future/sample["price"]-1)*100
                    available=True
                else:
                    sample[f"forward_{label}"]=None
            if not available:continue
            labelled+=1
            key=sample["pattern"]
            global_groups[key].append(sample)
            asset_groups[symbol][key].append(sample)
            asset_samples.append(sample)

            for label in ("4h","24h"):
                move=sample.get(f"forward_{label}")
                if move is not None and abs(move)>=8:
                    large_moves.append({
                        "symbol":symbol,"start_time":sample["time"],"horizon":label,
                        "move_pct":move,"direction":"UP" if move>0 else "DOWN",
                        "pattern":key,"signal":sample["signal"],
                        "lead_evidence":{
                            "rvol":sample["rvol"],"rvol_delta":sample["rvol_delta"],
                            "rsi":sample["rsi"],"rsi_delta":sample["rsi_delta"],
                            "macd_histogram":sample["macd_histogram"],"macd_delta":sample["macd_delta"],
                            "bullish_conditions":sample["bullish_conditions"],
                            "bearish_conditions":sample["bearish_conditions"],
                            "breakout":sample["breakout"],"breakdown":sample["breakdown"],
                        }
                    })
        if asset_samples:
            ups=[x for x in asset_samples if x.get("forward_4h") is not None and f(x.get("forward_4h"))>0]
            downs=[x for x in asset_samples if x.get("forward_4h") is not None and f(x.get("forward_4h"))<0]
            asset_memory[symbol]={
                "labelled_snapshots":len(asset_samples),
                "4h_up_rate_pct":len(ups)/len(asset_samples)*100,
                "4h_down_rate_pct":len(downs)/len(asset_samples)*100,
                "large_moves_found":sum(1 for x in large_moves if x["symbol"]==symbol),
            }

    global_patterns={k:summarize(v) for k,v in global_groups.items() if len(v)>=3}
    asset_patterns={
        symbol:{k:summarize(v) for k,v in groups.items() if len(v)>=3}
        for symbol,groups in asset_groups.items()
    }
    large_moves=sorted(large_moves,key=lambda x:abs(f(x.get("move_pct"))),reverse=True)[:2000]
    payload={
        "updated_at":now(),
        "summary":{
            "assets_studied":len(by_symbol),
            "labelled_snapshots":labelled,
            "global_patterns":len(global_patterns),
            "large_moves_studied":len(large_moves),
            "purpose":"Study every recorded tracked chart, not only trades."
        },
        "global_patterns":global_patterns,
        "asset_patterns":asset_patterns,
        "large_moves":large_moves,
        "asset_memory":asset_memory,
        "microstructure_learning": build_micro_learning(micro_history),
        "method":{
            "source":"observer_history.json",
            "horizons":["1h","4h","12h","24h"],
            "minimum_pattern_samples":3,
            "decision_rule":"Historical labels are learning evidence only; no future data is exposed to live decisions."
        }
    }
    write(OUT,payload)
    print(json.dumps(payload["summary"],indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
