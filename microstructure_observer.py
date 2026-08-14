from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import copy,json,math,time
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; LATEST=DATA/'microstructure_latest.json'; HISTORY=DATA/'microstructure_history.json'; HEALTH=DATA/'engine_health.json'
BINANCE='https://api.binance.com/api/v3/klines'

def now():return datetime.now(timezone.utc).isoformat()
def read(p,d):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return copy.deepcopy(d)
def clean(v):
    if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [clean(x) for x in v]
    if isinstance(v,np.bool_):return bool(v)
    if isinstance(v,np.integer):return int(v)
    if isinstance(v,np.floating):return float(v) if math.isfinite(float(v)) else None
    if isinstance(v,float) and not math.isfinite(v):return None
    if isinstance(v,(pd.Timestamp,datetime)):
        x=pd.Timestamp(v); x=x.tz_localize('UTC') if x.tzinfo is None else x.tz_convert('UTC'); return x.isoformat()
    return v
def write(p,x):
    t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(clean(x),indent=2,ensure_ascii=False),encoding='utf-8'); json.loads(t.read_text()); t.replace(p)
def f(v,d=0.0):
    try:
        n=float(v); return n if math.isfinite(n) else d
    except Exception:return d

def fetch_binance(symbol):
    try:
        r=requests.get(BINANCE,params={'symbol':f'{symbol}USDT','interval':'1m','limit':500},timeout=5); r.raise_for_status(); rows=r.json()
        if not isinstance(rows,list) or not rows:return pd.DataFrame()
        x=pd.DataFrame(rows,columns=['t','Open','High','Low','Close','Volume','ct','q','n','tb','tq','i'])
        x.index=pd.to_datetime(x['t'],unit='ms',utc=True)
        for c in ['Open','High','Low','Close','Volume']:x[c]=pd.to_numeric(x[c],errors='coerce')
        return x[['Open','High','Low','Close','Volume']].dropna(subset=['Close'])
    except Exception:return pd.DataFrame()

def fetch_yahoo(symbol):
    # Lazy optional fallback: keeps local validation independent of yfinance while GitHub can use it.
    try:
        import yfinance as yf
        ticker=f'{symbol}-USD'
        x=yf.download(ticker,period='1d',interval='1m',auto_adjust=True,progress=False,threads=False)
        if x is None or x.empty:return pd.DataFrame()
        if isinstance(x.columns,pd.MultiIndex):x.columns=x.columns.get_level_values(0)
        need=['Open','High','Low','Close','Volume']
        if not all(c in x.columns for c in need):return pd.DataFrame()
        x=x[need].dropna(subset=['Close']).copy(); x.index=pd.to_datetime(x.index,utc=True); return x
    except Exception:return pd.DataFrame()

def fetch(symbol):
    x=fetch_binance(symbol)
    if not x.empty:return 'Binance 1m',x
    x=fetch_yahoo(symbol)
    if not x.empty:return 'Yahoo 1m',x
    return '',pd.DataFrame()

def enrich(x):
    v=x.copy(); c=v.Close.astype(float); vol=v.Volume.fillna(0).astype(float)
    v['EMA9']=c.ewm(span=9,adjust=False).mean(); v['EMA21']=c.ewm(span=21,adjust=False).mean()
    d=c.diff(); gain=d.clip(lower=0); loss=-d.clip(upper=0)
    rs=gain.ewm(alpha=1/14,adjust=False,min_periods=14).mean()/loss.ewm(alpha=1/14,adjust=False,min_periods=14).mean().replace(0,np.nan)
    v['RSI']=100-100/(1+rs); v['RSID']=v.RSI-v.RSI.shift(3)
    macd=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean(); hist=macd-macd.ewm(span=9,adjust=False).mean()
    v['MACD']=hist; v['MACDD']=hist-hist.shift(3)
    v['RVOL']=vol/vol.rolling(20).mean().replace(0,np.nan); v['RVOLD']=v.RVOL-v.RVOL.shift(3)
    tr=pd.concat([(v.High-v.Low).abs(),(v.High-c.shift()).abs(),(v.Low-c.shift()).abs()],axis=1).max(axis=1)
    v['ATR']=tr.rolling(14).mean()/c*100
    v['PH']=v.High.shift(1).rolling(12).max(); v['PL']=v.Low.shift(1).rolling(12).min(); v['BREAKOUT']=c>v.PH; v['BREAKDOWN']=c<v.PL
    v['R5']=c.pct_change(5)*100
    return v

def snap(x):
    v=enrich(x).dropna(subset=['EMA9','EMA21','RSI','MACD','RVOL','ATR'])
    if v.empty:return {}
    r=v.iloc[-1]
    return {'time':pd.Timestamp(v.index[-1]).isoformat(),'price':f(r.Close),'ema9':f(r.EMA9),'ema21':f(r.EMA21),'rsi':f(r.RSI,50),'rsi_delta':f(r.RSID),'macd':f(r.MACD),'macd_delta':f(r.MACDD),'rvol':f(r.RVOL),'rvol_delta':f(r.RVOLD),'atr_pct':f(r.ATR),'return_5bars':f(r.R5),'breakout':bool(r.BREAKOUT),'breakdown':bool(r.BREAKDOWN)}

def trend(s):
    if not s:return 'UNKNOWN'
    bull=sum([s['price']>s['ema9'],s['ema9']>s['ema21'],s['macd']>0,s['macd_delta']>0,s['rsi']>=52,s['rsi_delta']>0])
    bear=sum([s['price']<s['ema9'],s['ema9']<s['ema21'],s['macd']<0,s['macd_delta']<0,s['rsi']<=48,s['rsi_delta']<0])
    return 'UP' if bull>=5 else 'DOWN' if bear>=5 else 'MIXED'

def classify(one,five):
    t1,t5=trend(one),trend(five); strong=max(f(one.get('rvol')),f(five.get('rvol')))>=1.15
    fading=f(one.get('rvol_delta'))<0 and f(five.get('rvol_delta'))<0
    over=max(f(one.get('rsi'),50),f(five.get('rsi'),50))>=72
    under=min(f(one.get('rsi'),50),f(five.get('rsi'),50))<=28
    if t1=='UP' and t5=='UP' and strong:return 'LONG ENTRY','CONFIRMED','1m and 5m trend plus participation agree upward'
    if t1=='DOWN' and t5=='DOWN' and strong:return 'SHORT ENTRY','CONFIRMED','1m and 5m trend plus participation agree downward'
    # Crucial semantic separation: local exhaustion is management advice, not an automatic opposite trade.
    if t5=='UP' and over and t1!='UP' and fading:return 'LONG EXIT / PROFIT PROTECT','EXHAUSTION','1m rolled over while 5m remains broadly up; possible local peak'
    if t5=='DOWN' and under and t1!='DOWN' and fading:return 'SHORT EXIT / PROFIT PROTECT','EXHAUSTION','1m bounced while 5m remains broadly down; possible local trough'
    if t5=='UP' and t1=='DOWN':return 'LONG PULLBACK WATCH','PULLBACK','5m uptrend intact while 1m retraces'
    if t5=='DOWN' and t1=='UP':return 'SHORT PULLBACK WATCH','PULLBACK','5m downtrend intact while 1m rebounds'
    if t1=='UP' and t5=='MIXED' and five.get('breakout') and strong:return 'LONG REVERSAL WATCH','REVERSAL BUILDING','1m upturn plus 5m breakout evidence'
    if t1=='DOWN' and t5=='MIXED' and five.get('breakdown') and strong:return 'SHORT REVERSAL WATCH','REVERSAL BUILDING','1m downturn plus 5m breakdown evidence'
    return 'NO ACTION','NEUTRAL','1m/5m evidence not aligned enough'

def analyse(frame):
    one=snap(frame); five=snap(frame.resample('5min').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna(subset=['Close']))
    if not one or not five:return {}
    role,state,reason=classify(one,five)
    return {'price':one['price'],'role_signal':role,'state':state,'reason':reason,'one_minute':one,'five_minute':five}

def main():
    holdings=read(ROOT/'holdings.json',[]); hist=read(HISTORY,[]); signals=[]; unavailable=[]; providers={}; stamp=now()
    # Network I/O is parallelised so one unsupported/slow ticker cannot make a 5-minute scan take many minutes.
    workers=min(10,max(2,len(holdings)))
    results={}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(fetch,str(h.get('symbol') or '').upper()):h for h in holdings}
        for fut in as_completed(futures):
            h=futures[fut]; symbol=str(h.get('symbol') or '').upper()
            try: provider,frame=fut.result()
            except Exception: provider,frame='',pd.DataFrame()
            results[symbol]=(h,provider,frame)
    # Preserve holdings order in persisted output for stable diffs and easier debugging.
    for h in holdings:
        symbol=str(h.get('symbol') or '').upper(); _,provider,frame=results.get(symbol,(h,'',pd.DataFrame()))
        if frame.empty: unavailable.append(symbol); continue
        a=analyse(frame)
        if not a: unavailable.append(symbol); continue
        providers[provider]=providers.get(provider,0)+1
        rec={'recorded_at':stamp,'symbol':symbol,'name':h.get('name') or symbol,'narrative':h.get('narrative') or '','data_source':provider,**a}
        signals.append(rec); hist.append(rec)
    payload={'generated_at':stamp,'timeframe':'1m/5m','signals':signals,'health':{'assets_requested':len(holdings),'assets_analysed':len(signals),'unavailable_assets':unavailable,'providers':providers,'fetch_mode':'parallel','workers':workers}}
    write(LATEST,payload); write(HISTORY,hist[-120000:]); health=read(HEALTH,{}); health['microstructure_observer']={'updated_at':stamp,**payload['health']}; write(HEALTH,health)
    print(json.dumps(payload['health'],indent=2)); return 0
if __name__=='__main__':raise SystemExit(main())
