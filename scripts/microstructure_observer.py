from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import copy,json,math,time
from typing import Any
import numpy as np
import pandas as pd
import requests
import yfinance as yf

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
BINANCE="https://api.binance.com/api/v3/klines"
LATEST=DATA/"microstructure_latest.json"
HISTORY=DATA/"microstructure_history.json"
HEALTH=DATA/"engine_health.json"

YAHOO_TICKERS={
    "BTC":"BTC-USD","SOL":"SOL-USD","AVAX":"AVAX-USD","POL":"POL28321-USD","DOT":"DOT-USD",
    "ZIL":"ZIL-USD","COTI":"COTI-USD","NEAR":"NEAR-USD","SUI":"SUI20947-USD","SUPER":"SUPER8290-USD",
    "AIOZ":"AIOZ-USD","FIL":"FIL-USD","SEI":"SEI-USD","ONDO":"ONDO-USD","OM":"OM-USD","RUNE":"RUNE-USD",
    "SAND":"SAND-USD","ONE":"ONE-USD","WIN":"WIN-USD","AR":"AR-USD","BEAM":"BEAM-USD","SHIB":"SHIB-USD",
    "ENJ":"ENJ-USD","IMX":"IMX10603-USD","VET":"VET-USD","SC":"SC-USD","BTT":"BTT-USD","TLM":"TLM-USD",
    "PYR":"PYR-USD","PAAL":"PAAL-USD","SKL":"SKL-USD","AERO":"AERO29270-USD","LUNC":"LUNC-USD",
    "GALA":"GALA-USD","UOS":"UOS-USD","UFO":"UFO-USD","DENT":"DENT-USD","MEW":"MEW-USD",
    "DOGE":"DOGE-USD","GRT":"GRT-USD","VRA":"VRA-USD","VTHO":"VTHO-USD","XTZ":"XTZ-USD",
}

def now():return datetime.now(timezone.utc).isoformat()
def read(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return copy.deepcopy(d)
def write(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(sanitise(x),indent=2,ensure_ascii=False),encoding="utf-8")
    json.loads(t.read_text(encoding="utf-8")); t.replace(p)
def sanitise(v):
    if isinstance(v,dict):return {str(k):sanitise(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [sanitise(x) for x in v]
    if isinstance(v,(np.bool_,)):return bool(v)
    if isinstance(v,(np.integer,)):return int(v)
    if isinstance(v,(np.floating,)):return float(v) if math.isfinite(float(v)) else None
    if isinstance(v,(pd.Timestamp,datetime)):
        x=pd.Timestamp(v); x=x.tz_localize("UTC") if x.tzinfo is None else x.tz_convert("UTC"); return x.isoformat()
    if isinstance(v,float) and not math.isfinite(v):return None
    return v
def f(v,d=0.0):
    try:
        n=float(v); return n if math.isfinite(n) else d
    except Exception:return d

def binance_1m(symbol):
    try:
        r=requests.get(BINANCE,params={"symbol":f"{symbol}USDT","interval":"1m","limit":500},timeout=10)
        r.raise_for_status(); rows=r.json()
        if not isinstance(rows,list) or not rows:return pd.DataFrame()
        x=pd.DataFrame(rows,columns=["t","Open","High","Low","Close","Volume","ct","q","n","tb","tq","i"])
        x.index=pd.to_datetime(x["t"],unit="ms",utc=True)
        for c in ["Open","High","Low","Close","Volume"]:x[c]=pd.to_numeric(x[c],errors="coerce")
        return x[["Open","High","Low","Close","Volume"]].dropna()
    except Exception:return pd.DataFrame()

def yahoo_1m(ticker):
    try:
        x=yf.download(ticker,period="1d",interval="1m",auto_adjust=True,progress=False,threads=False)
        if x is None or x.empty:return pd.DataFrame()
        if isinstance(x.columns,pd.MultiIndex):x.columns=x.columns.get_level_values(0)
        need=["Open","High","Low","Close","Volume"]
        if not all(c in x.columns for c in need):return pd.DataFrame()
        x=x[need].dropna(subset=["Close"]).copy(); x.index=pd.to_datetime(x.index,utc=True)
        return x
    except Exception:return pd.DataFrame()

def fetch(symbol,ticker):
    x=binance_1m(symbol)
    if not x.empty:return "Binance 1m",x
    x=yahoo_1m(ticker)
    if not x.empty:return "Yahoo 1m",x
    return "",pd.DataFrame()

def resample5(x):
    return x.resample("5min").agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}).dropna(subset=["Close"])

def enrich(x,scale=1):
    v=x.copy(); c=v["Close"].astype(float); vol=v["Volume"].fillna(0).astype(float)
    v["EMA9"]=c.ewm(span=9,adjust=False).mean(); v["EMA21"]=c.ewm(span=21,adjust=False).mean()
    d=c.diff(); gain=d.clip(lower=0); loss=-d.clip(upper=0)
    rs=gain.ewm(alpha=1/14,adjust=False,min_periods=14).mean()/loss.ewm(alpha=1/14,adjust=False,min_periods=14).mean().replace(0,np.nan)
    v["RSI"]=100-100/(1+rs); v["RSID"]=v["RSI"]-v["RSI"].shift(3)
    macd=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean()
    hist=macd-macd.ewm(span=9,adjust=False).mean(); v["MACD"]=hist; v["MACDD"]=hist-hist.shift(3)
    v["RVOL"]=vol/vol.rolling(20).mean().replace(0,np.nan); v["RVOLD"]=v["RVOL"]-v["RVOL"].shift(3)
    v["R1"]=c.pct_change()*100; v["R5"]=c.pct_change(5)*100
    v["ATR"]=(v["High"]-v["Low"]).rolling(14).mean()/c*100
    v["PH"]=v["High"].shift(1).rolling(12).max(); v["PL"]=v["Low"].shift(1).rolling(12).min()
    v["BREAKOUT"]=c>v["PH"]; v["BREAKDOWN"]=c<v["PL"]
    return v

def snapshot(x):
    v=enrich(x).dropna(subset=["EMA9","EMA21","RSI","MACD","RVOL","ATR"])
    if v.empty:return {}
    r=v.iloc[-1]; c=f(r["Close"])
    return {
        "price":c,"ema9":f(r["EMA9"]),"ema21":f(r["EMA21"]),
        "rsi":f(r["RSI"],50),"rsi_delta":f(r["RSID"]),
        "macd":f(r["MACD"]),"macd_delta":f(r["MACDD"]),
        "rvol":f(r["RVOL"]),"rvol_delta":f(r["RVOLD"]),
        "return_bar":f(r["R1"]),"return_5bars":f(r["R5"]),
        "atr_pct":f(r["ATR"]),"breakout":bool(r["BREAKOUT"]),"breakdown":bool(r["BREAKDOWN"]),
        "time":pd.Timestamp(v.index[-1]).isoformat(),
    }

def trend(s):
    if not s:return "UNKNOWN"
    bull=sum([s["price"]>s["ema9"],s["ema9"]>s["ema21"],s["macd"]>0,s["macd_delta"]>0,s["rsi"]>=52,s["rsi_delta"]>0])
    bear=sum([s["price"]<s["ema9"],s["ema9"]<s["ema21"],s["macd"]<0,s["macd_delta"]<0,s["rsi"]<=48,s["rsi_delta"]<0])
    return "UP" if bull>=5 else "DOWN" if bear>=5 else "MIXED"

def classify(one,five):
    """Role-aware signal: distinguish entry, exit/profit protection, reversal and pullback."""
    t1=trend(one); t5=trend(five)
    price=f(one.get("price"))
    strong_vol=max(f(one.get("rvol")),f(five.get("rvol")))>=1.15
    vol_fading=f(one.get("rvol_delta"))<0 and f(five.get("rvol_delta"))<0
    overbought=max(f(one.get("rsi"),50),f(five.get("rsi"),50))>=72
    oversold=min(f(one.get("rsi"),50),f(five.get("rsi"),50))<=28

    # Confirmed continuation / entry
    if t1=="UP" and t5=="UP" and strong_vol:
        return "LONG ENTRY","CONFIRMED","1m and 5m trend/participation agree upward"
    if t1=="DOWN" and t5=="DOWN" and strong_vol:
        return "SHORT ENTRY","CONFIRMED","1m and 5m trend/participation agree downward"

    # Peak / trough exhaustion should be management information, not automatically a reverse trade.
    if t5=="UP" and overbought and t1!="UP" and vol_fading:
        return "LONG EXIT / PROFIT PROTECT","EXHAUSTION","1m rolled over while 5m trend remains up; possible local peak"
    if t5=="DOWN" and oversold and t1!="DOWN" and vol_fading:
        return "SHORT EXIT / PROFIT PROTECT","EXHAUSTION","1m bounced while 5m trend remains down; possible local trough"

    # Pullback: higher micro timeframe intact while 1m countertrend.
    if t5=="UP" and t1=="DOWN":
        return "LONG PULLBACK WATCH","PULLBACK","5m uptrend intact while 1m retraces"
    if t5=="DOWN" and t1=="UP":
        return "SHORT PULLBACK WATCH","PULLBACK","5m downtrend intact while 1m rebounds"

    # Genuine reversal requires 5m participation/structure joining the 1m move.
    if t1=="UP" and t5=="MIXED" and five.get("breakout") and strong_vol:
        return "LONG REVERSAL WATCH","REVERSAL BUILDING","1m turned up and 5m breakout is forming"
    if t1=="DOWN" and t5=="MIXED" and five.get("breakdown") and strong_vol:
        return "SHORT REVERSAL WATCH","REVERSAL BUILDING","1m turned down and 5m breakdown is forming"

    return "NO ACTION","NEUTRAL","1m/5m evidence is not aligned enough"

def analyse(frame):
    one=snapshot(frame); five=snapshot(resample5(frame))
    if not one or not five:return {}
    role,state,reason=classify(one,five)
    return {"role_signal":role,"state":state,"reason":reason,"price":one["price"],"one_minute":one,"five_minute":five}

def main():
    holdings=read(ROOT/"holdings.json",[])
    prior=read(LATEST,{"signals":[]})
    history=read(HISTORY,[])
    timestamp=now(); signals=[]; unavailable=[]; providers={}
    for h in holdings:
        symbol=str(h.get("symbol") or "").upper()
        provider,frame=fetch(symbol,YAHOO_TICKERS.get(symbol,f"{symbol}-USD"))
        if frame.empty:
            unavailable.append(symbol); continue
        a=analyse(frame)
        if not a:
            unavailable.append(symbol); continue
        providers[provider]=providers.get(provider,0)+1
        rec={"recorded_at":timestamp,"symbol":symbol,"name":h.get("name") or symbol,
             "narrative":h.get("narrative") or "","data_source":provider,**a}
        signals.append(rec)
        history.append(rec)
        time.sleep(0.02)
    payload={"generated_at":timestamp,"timeframe":"1m/5m","signals":signals,
             "health":{"assets_requested":len(holdings),"assets_analysed":len(signals),
                       "unavailable_assets":unavailable,"providers":providers}}
    write(LATEST,payload); write(HISTORY,history[-100000:])
    health=read(HEALTH,{})
    health["microstructure_observer"]={"updated_at":timestamp,**payload["health"]}
    write(HEALTH,health)
    print(json.dumps(payload["health"],indent=2)); return 0
if __name__=="__main__":raise SystemExit(main())
