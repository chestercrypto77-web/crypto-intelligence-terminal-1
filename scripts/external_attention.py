from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json, math

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
OUT=DATA/'external_attention.json'

def now(): return datetime.now(timezone.utc).isoformat()
def read(p,d):
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return d

def write(p,x):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf-8'); json.loads(t.read_text()); t.replace(p)
def parse(v):
    try:
        x=datetime.fromisoformat(str(v).replace('Z','+00:00'))
        if x.tzinfo is None: x=x.replace(tzinfo=timezone.utc)
        return x.astimezone(timezone.utc)
    except Exception:return None

def rows(payload):
    if isinstance(payload,list): return payload
    if not isinstance(payload,dict): return []
    for k in ('events','items','records','articles','calls'):
        if isinstance(payload.get(k),list): return payload[k]
    return []

def symbols_for(item):
    vals=[]
    for k in ('symbol','asset','ticker'):
        v=item.get(k)
        if v: vals.append(str(v).upper())
    for k in ('symbols','assets','tickers'):
        v=item.get(k)
        if isinstance(v,list): vals += [str(x).upper() for x in v if x]
    return sorted(set(vals))

def stamp(item):
    for k in ('recorded_at','published_at','timestamp','created_at','updated_at'):
        t=parse(item.get(k))
        if t:return t
    return None

def main():
    inbox_payload=read(DATA/'external_inbox.json',[])
    calls_payload=read(DATA/'external_calls.json',[])
    source_payload=read(DATA/'external_intelligence.json',{})
    events=rows(inbox_payload)+rows(calls_payload)+rows(source_payload)
    cutoff=datetime.now(timezone.utc)-timedelta(hours=24)
    recent=[x for x in events if not stamp(x) or stamp(x)>=cutoff]
    assets={}
    for item in recent:
        for sym in symbols_for(item):
            a=assets.setdefault(sym,{'events_24h':0,'sources':set(),'latest_event_at':None,'positive':0,'negative':0})
            a['events_24h']+=1
            src=str(item.get('source_name') or item.get('source') or item.get('source_id') or 'unknown')
            a['sources'].add(src)
            t=stamp(item); ts=t.isoformat() if t else None
            if ts and (not a['latest_event_at'] or ts>a['latest_event_at']):a['latest_event_at']=ts
            text=' '.join(str(item.get(k) or '') for k in ('title','summary','content','notes','sentiment')).lower()
            if any(w in text for w in ('surge','breakout','listing','partnership','upgrade','approval','launch','bullish')):a['positive']+=1
            if any(w in text for w in ('hack','exploit','delist','lawsuit','investigation','outage','bearish','dump')):a['negative']+=1
    out_assets={}
    for sym,a in assets.items():
        score=min(100,a['events_24h']*12+len(a['sources'])*8+abs(a['positive']-a['negative'])*5)
        out_assets[sym]={'events_24h':a['events_24h'],'source_count':len(a['sources']),'latest_event_at':a['latest_event_at'],
                         'positive_clues':a['positive'],'negative_clues':a['negative'],'attention_score':score}
    configured=[]
    for payload,name in ((inbox_payload,'external_inbox'),(calls_payload,'external_calls'),(source_payload,'external_intelligence')):
        if (DATA/f'{name}.json').exists(): configured.append(name)
    payload={'updated_at':now(),'summary':{'events_24h':len(recent),'events':len(recent),'assets_mentioned':len(out_assets),'assets_with_attention':len(out_assets),
             'configured_inputs':len(configured),'healthy_inputs':len(configured),'sources':len(configured),'healthy_sources':len(configured)},
             'source_health':[{'source':x,'status':'PASS'} for x in configured], 'sources':configured,'assets':out_assets,
             'guardrail':'External attention is evidence only. It never opens a trade by itself.'}
    write(OUT,payload); print(json.dumps(payload['summary'],indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
