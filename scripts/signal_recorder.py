from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json, time
import numpy as np
import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BINANCE = "https://api.binance.com/api/v3/klines"
ACTIONABLE = {"STRONG BUY","BUY","BUY WATCH","SELL WATCH","SELL","STRONG SELL"}

TICKERS = {
    "BTC":"BTC-USD","SOL":"SOL-USD","AVAX":"AVAX-USD","POL":"POL-USD","DOT":"DOT-USD",
    "ZIL":"ZIL-USD","COTI":"COTI-USD","NEAR":"NEAR-USD","SUI":"SUI20947-USD",
    "SUPER":"SUPER-USD","S":"S-USD","AIOZ":"AIOZ-USD","FIL":"FIL-USD","SEI":"SEI-USD",
    "ONDO":"ONDO-USD","OM":"OM-USD","RUNE":"RUNE-USD","SAND":"SAND-USD","ONE":"ONE-USD",
    "WIN":"WIN-USD","AR":"AR-USD","BEAM":"BEAM-USD","SHIB":"SHIB-USD","ENJ":"ENJ-USD",
    "IMX":"IMX10603-USD","VET":"VET-USD","SC":"SC-USD","BTT":"BTT-USD","TLM":"TLM-USD",
    "PYR":"PYR-USD","PAAL":"PAAL-USD","SKL":"SKL-USD","AERO":"AERO29270-USD","LUNC":"LUNC-USD",
    "GALA":"GALA-USD","UOS":"UOS-USD","UFO":"UFO-USD","DENT":"DENT-USD","MEW":"MEW-USD",
    "DOGE":"DOGE-USD","GRT":"GRT-USD","VRA":"VRA-USD","VTHO":"VTHO-USD","XTZ":"XTZ-USD",
    "USDT":"USDT-USD",
}

def read(path, default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)

def yahoo4h(ticker):
    try:
        f = yf.download(ticker, period="30d", interval="1h", auto_adjust=True,
                        progress=False, threads=False)
        if f is None or f.empty: return pd.DataFrame()
        if isinstance(f.columns, pd.MultiIndex): f.columns = f.columns.get_level_values(0)
        cols = ["Open","High","Low","Close","Volume"]
        if not all(c in f.columns for c in cols): return pd.DataFrame()
        f = f[cols].dropna(subset=["Close"]).copy()
        f.index = pd.to_datetime(f.index, utc=True)
        return f.resample("4h").agg({"Open":"first","High":"max","Low":"min",
                                    "Close":"last","Volume":"sum"}).dropna(subset=["Close"])
    except Exception:
        return pd.DataFrame()

def binance4h(symbol):
    try:
        r = requests.get(BINANCE, params={"symbol":f"{symbol}USDT","interval":"4h","limit":220}, timeout=10)
        r.raise_for_status()
        rows = r.json()
        if not isinstance(rows, list) or not rows: return pd.DataFrame()
        f = pd.DataFrame(rows, columns=["t","Open","High","Low","Close","Volume","ct","q","n","tb","tq","i"])
        f.index = pd.to_datetime(f["t"], unit="ms", utc=True)
        for c in ["Open","High","Low","Close","Volume"]: f[c] = pd.to_numeric(f[c], errors="coerce")
        return f[["Open","High","Low","Close","Volume"]].dropna()
    except Exception:
        return pd.DataFrame()

def indicators(f):
    x = f.copy()
    c,h,l,v = x.Close.astype(float),x.High.astype(float),x.Low.astype(float),x.Volume.fillna(0).astype(float)
    x["EMA9"],x["EMA21"],x["EMA55"] = c.ewm(span=9,adjust=False).mean(),c.ewm(span=21,adjust=False).mean(),c.ewm(span=55,adjust=False).mean()
    d = c.diff(); g=d.clip(lower=0); loss=-d.clip(upper=0)
    rs=g.ewm(alpha=1/14,adjust=False,min_periods=14).mean()/loss.ewm(alpha=1/14,adjust=False,min_periods=14).mean().replace(0,np.nan)
    x["RSI"]=100-100/(1+rs); x["RSI_D"]=x.RSI-x.RSI.shift(3)
    macd=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean()
    hist=macd-macd.ewm(span=9,adjust=False).mean()
    x["HIST"],x["HIST_D"]=hist,hist-hist.shift(2)
    x["RVOL"]=v/v.rolling(20).mean().replace(0,np.nan); x["RVOL_D"]=x.RVOL-x.RVOL.shift(3)
    x["R1"],x["R3"],x["R6"]=c.pct_change()*100,c.pct_change(3)*100,c.pct_change(6)*100
    x["G6"],x["D6"]=(c>x.Open).rolling(6).sum(),(c<x.Open).rolling(6).sum()
    x["PH"],x["PL"]=h.shift(1).rolling(6).max(),l.shift(1).rolling(6).min()
    x["BO"],x["BD"]=c>x.PH,c<x.PL
    x["HH"]=h.rolling(3).max()>h.shift(3).rolling(3).max()
    x["HL"]=l.rolling(3).min()>l.shift(3).rolling(3).min()
    x["LH"]=h.rolling(3).max()<h.shift(3).rolling(3).max()
    x["LL"]=l.rolling(3).min()<l.shift(3).rolling(3).min()
    return x

def evaluate(f, btc24=0):
    x=indicators(f).dropna(subset=["EMA9","EMA21","EMA55","RSI","HIST","RVOL","R3","R6"])
    if x.empty: return None
    r=x.iloc[-1]; close=float(r.Close)
    checks=[
      ("Price above EMA 9",close>r.EMA9,close<r.EMA9,"Trend"),
      ("EMA 9 above EMA 21",r.EMA9>r.EMA21,r.EMA9<r.EMA21,"Trend"),
      ("EMA 21 above EMA 55",r.EMA21>r.EMA55,r.EMA21<r.EMA55,"Trend"),
      ("MACD positive",r.HIST>0,r.HIST<0,"Momentum"),
      ("MACD accelerating",r.HIST_D>0,r.HIST_D<0,"Momentum"),
      ("RSI strengthening",50<=r.RSI<=78 and r.RSI_D>0,r.RSI<45 and r.RSI_D<0,"Momentum"),
      ("RVOL above normal",r.RVOL>=1.15,r.RVOL<.70,"Volume"),
      ("RVOL increasing",r.RVOL_D>.10,r.RVOL_D<-.10,"Volume"),
      ("Most recent candles green",r.G6>=4,r.D6>=4,"Volume"),
      ("12-hour direction positive",r.R3>0,r.R3<0,"Structure"),
      ("Higher highs",bool(r.HH),bool(r.LH),"Structure"),
      ("Higher lows",bool(r.HL),bool(r.LL),"Structure"),
      ("Breakout",bool(r.BO),bool(r.BD),"Structure"),
      ("Outperforming Bitcoin",r.R6>btc24+1,r.R6<btc24-1,"Relative strength"),
    ]
    bull=sum(bool(b) for _,b,_,_ in checks); bear=sum(bool(s) for _,_,s,_ in checks)
    tb=sum(bool(b) for _,b,_,g in checks if g=="Trend"); ts=sum(bool(s) for _,_,s,g in checks if g=="Trend")
    vb=sum(bool(b) for _,b,_,g in checks if g=="Volume"); vs=sum(bool(s) for _,_,s,g in checks if g=="Volume")
    if bull>=10 and bear<=2 and tb>=2 and vb>=2: signal="STRONG BUY"
    elif bull>=8 and bear<=3 and tb>=2: signal="BUY"
    elif bull>=6 and bear<=4: signal="BUY WATCH"
    elif bear>=10 and bull<=2 and ts>=2 and vs>=2: signal="STRONG SELL"
    elif bear>=8 and bull<=3 and ts>=2: signal="SELL"
    elif bear>=6 and bull<=4: signal="SELL WATCH"
    else: signal="HOLD"
    t=pd.Timestamp(x.index[-1]); t=t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    return {"signal":signal,"bullish":bull,"bearish":bear,"entry_price":close,
            "return_4h":float(r.R1),"return_12h":float(r.R3),"return_24h":float(r.R6),
            "rvol":float(r.RVOL),"rvol_delta":float(r.RVOL_D),"rsi":float(r.RSI),
            "checks":[{"name":n,"group":g,"state":"bull" if b else "bear" if s else "neutral"} for n,b,s,g in checks],
            "candle_time":t.isoformat()}

def source(symbol,ticker):
    choices=[]
    y=yahoo4h(ticker)
    if not y.empty: choices.append(("Yahoo Finance",y))
    b=binance4h(symbol)
    if not b.empty: choices.append(("Binance",b))
    if not choices: return "",pd.DataFrame()
    choices.sort(key=lambda z:pd.Timestamp(z[1].index[-1]),reverse=True)
    return choices[0]

def sid(symbol,signal,candle):
    return f"{symbol}_{signal.replace(' ','_')}_{candle.replace('-','').replace(':','').replace('+','').replace('T','_')}"


def parse_time(value):
    try:
        t=pd.Timestamp(value)
        return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    except Exception:
        return None

def directional_return(direction,entry,current):
    if not entry or not current or float(entry)<=0: return None
    raw=(float(current)/float(entry)-1)*100
    return raw if direction=="LONG" else -raw

def update_trade_outcomes(trades,snapshots,now):
    now_ts=parse_time(now)
    checkpoints=[1,4,12,24,72,168]
    for trade in trades:
        if trade.get("status") not in {"OPEN","CLOSED"}: continue
        snap=snapshots.get(str(trade.get("symbol","")).upper())
        if not snap: continue
        current=float(snap.get("price") or 0); entry=float(trade.get("entry_price") or 0)
        result=directional_return(trade.get("direction"),entry,current)
        if result is None: continue
        trade["current_price"]=current; trade["current_return"]=result; trade["last_updated"]=now
        trade["best_return"]=max(float(trade.get("best_return") or result),result)
        trade["worst_return"]=min(float(trade.get("worst_return") or result),result)
        trade.setdefault("returns",{})
        entered=parse_time(trade.get("entry_time"))
        if entered is None or now_ts is None: continue
        elapsed=max(0.0,(now_ts-entered).total_seconds()/3600); trade["hours_open"]=elapsed
        for hours in checkpoints:
            key=f"{hours}h" if hours<24 else f"{hours//24}d"
            if elapsed>=hours and key not in trade["returns"]:
                trade["returns"][key]={"return":result,"price":current,"recorded_at":now}
        if trade.get("status")=="OPEN" and elapsed>=168:
            trade["status"]="CLOSED"; trade["exit_time"]=now; trade["exit_price"]=current
            trade["exit_reason"]="Automatic 7-day evaluation"; trade["final_return"]=result
            trade["outcome"]="WIN" if result>.25 else "LOSS" if result<-.25 else "FLAT"
    return trades

def ingest_external_calls(calls,trades,snapshots,now):
    existing={str(t.get("trade_id")) for t in trades}
    for call in calls:
        if not isinstance(call,dict) or call.get("status","ACTIVE")!="ACTIVE": continue
        call_id=str(call.get("call_id") or "").strip(); symbol=str(call.get("symbol") or "").upper().strip()
        direction=str(call.get("direction") or "").upper().strip()
        if not call_id or not symbol or direction not in {"LONG","SHORT"}: continue
        trade_id=f"EXTERNAL_{call_id}"
        if trade_id in existing: continue
        entry=float(call.get("entry_price") or snapshots.get(symbol,{}).get("price") or 0)
        if entry<=0: continue
        trades.append({
          "trade_id":trade_id,"source":str(call.get("source") or "EXTERNAL"),"symbol":symbol,
          "name":str(call.get("name") or symbol),"narrative":str(call.get("narrative") or ""),
          "tier":"EXTERNAL","direction":direction,
          "call":str(call.get("call") or ("BUY" if direction=="LONG" else "SELL")),
          "entry_time":str(call.get("entry_time") or now),"candle_time":str(call.get("entry_time") or now),
          "entry_price":entry,"status":"OPEN","target_price":call.get("target_price"),
          "invalidation_price":call.get("invalidation_price"),"exit_time":None,"exit_price":None,
          "exit_reason":None,"bullish_conditions":None,"bearish_conditions":None,"checks":[],
          "source_data":str(call.get("source_link") or "Manual external call"),
          "notes":str(call.get("notes") or ""),"timeframe":str(call.get("timeframe") or ""),
          "returns":{},"best_return":0.0,"worst_return":0.0
        }); existing.add(trade_id)
    return trades

def main():
    holdings=read(ROOT/"holdings.json",[])
    previous=read(DATA/"signals_latest.json",{"signals":[]})
    prev={x.get("symbol"):x for x in previous.get("signals",[])}
    history=read(DATA/"signal_history.json",[]); trades=read(DATA/"paper_trades.json",[]); external=read(DATA/"external_calls.json",[])
    history=history if isinstance(history,list) else []; trades=trades if isinstance(trades,list) else []; external=external if isinstance(external,list) else []
    seen={x.get("signal_id") for x in history}; trade_ids={x.get("trade_id") for x in trades}
    _,bf=source("BTC",TICKERS["BTC"]); be=evaluate(bf,0) if not bf.empty else None
    btc24=be["return_24h"] if be else 0
    now=datetime.now(timezone.utc).isoformat(); latest=[]; snapshots={}; nh=nt=0
    for h in holdings:
        sym=str(h["symbol"]).upper(); provider,f=source(sym,TICKERS.get(sym,f"{sym}-USD"))
        if f.empty: continue
        result=evaluate(f,0 if sym=="BTC" else btc24)
        if not result: continue
        snapshots[sym]={"price":result["entry_price"],"source":provider,"recorded_at":now}
        old=prev.get(sym,{}).get("signal"); changed=old is not None and old!=result["signal"]
        rec={"signal_id":sid(sym,result["signal"],result["candle_time"]),"recorded_at":now,
             "symbol":sym,"name":h.get("name",sym),"narrative":h.get("narrative",""),
             "tier":h.get("tier",""),"previous_signal":old,"changed":changed,
             "data_source":provider,**result}
        latest.append(rec)
        if rec["signal_id"] not in seen:
            history.append(rec); seen.add(rec["signal_id"]); nh+=1
        if result["signal"] in ACTIONABLE and result["signal"]!=old and rec["signal_id"] not in trade_ids:
            trades.append({"trade_id":rec["signal_id"],"source":"OUR ENGINE","symbol":sym,
              "name":rec["name"],"narrative":rec["narrative"],"tier":rec["tier"],
              "direction":"LONG" if "BUY" in result["signal"] else "SHORT","call":result["signal"],
              "entry_time":now,"candle_time":result["candle_time"],"entry_price":result["entry_price"],
              "status":"OPEN","target_price":None,"invalidation_price":None,"exit_time":None,
              "exit_price":None,"exit_reason":None,"bullish_conditions":result["bullish"],
              "bearish_conditions":result["bearish"],"checks":result["checks"],
              "source_data":provider,"returns":{},"best_return":0.0,"worst_return":0.0})
            trade_ids.add(rec["signal_id"]); nt+=1
        time.sleep(.1)
    trades=ingest_external_calls(external,trades,snapshots,now)
    trades=update_trade_outcomes(trades,snapshots,now)
    write(DATA/"signals_latest.json",{"generated_at":now,"scan_frequency":"hourly","signal_timeframe":"4h","btc_reference_return_24h":btc24,
          "signals":latest,"new_history_records":nh,"new_paper_trades":nt})
    write(DATA/"signal_history.json",history[-10000:]); write(DATA/"paper_trades.json",trades)
    print(json.dumps({"signals":len(latest),"new_history":nh,"new_trades":nt},indent=2))

if __name__=="__main__": main()
