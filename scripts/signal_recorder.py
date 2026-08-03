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

def main():
    holdings=read(ROOT/"holdings.json",[])
    previous=read(DATA/"signals_latest.json",{"signals":[]})
    prev={x.get("symbol"):x for x in previous.get("signals",[])}
    history=read(DATA/"signal_history.json",[]); trades=read(DATA/"paper_trades.json",[])
    history=history if isinstance(history,list) else []; trades=trades if isinstance(trades,list) else []
    seen={x.get("signal_id") for x in history}; trade_ids={x.get("trade_id") for x in trades}
    _,bf=source("BTC",TICKERS["BTC"]); be=evaluate(bf,0) if not bf.empty else None
    btc24=be["return_24h"] if be else 0
    now=datetime.now(timezone.utc).isoformat(); latest=[]; nh=nt=0
    for h in holdings:
        sym=str(h["symbol"]).upper(); provider,f=source(sym,TICKERS.get(sym,f"{sym}-USD"))
        if f.empty: continue
        result=evaluate(f,0 if sym=="BTC" else btc24)
        if not result: continue
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
    write(DATA/"signals_latest.json",{"generated_at":now,"btc_reference_return_24h":btc24,
          "signals":latest,"new_history_records":nh,"new_paper_trades":nt})
    write(DATA/"signal_history.json",history[-10000:]); write(DATA/"paper_trades.json",trades)
    print(json.dumps({"signals":len(latest),"new_history":nh,"new_trades":nt},indent=2))

if __name__=="__main__": main()
