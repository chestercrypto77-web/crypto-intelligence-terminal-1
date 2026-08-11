from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from collections import defaultdict
import copy,json,math
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; OUT=DATA/'confidence_ledger.json'
def now():return datetime.now(timezone.utc).isoformat()
def read(p,d):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return copy.deepcopy(d)
def write(p,x):
    t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf-8'); json.loads(t.read_text()); t.replace(p)
def f(v,d=0.0):
    try:n=float(v); return n if math.isfinite(n) else d
    except Exception:return d

def main():
    reviews=read(DATA/'trade_reviews.json',{'reviews':[]}).get('reviews') or []
    integrity=read(DATA/'trade_integrity.json',{'records':[]})
    valid_keys={str(x.get('trade_key')) for x in integrity.get('records') or [] if x.get('status')=='VALIDATED'}
    if valid_keys:
        reviews=[r for r in reviews if str(r.get('position_id') or r.get('case_id') or f"{r.get('wallet','')}_{r.get('symbol','')}_{r.get('entry_time','')}") in valid_keys]
    raw=defaultdict(lambda:{'samples':0,'hits':0,'returns':[],'strength':[]})
    for r in reviews:
        e=f(r.get('entry_price')); x=f(r.get('exit_price'))
        if e<=0 or x<=0:continue
        market_ret=(x/e-1)*100
        reports=((r.get('committee_snapshot') or {}).get('reports') or {})
        for name,rep in reports.items():
            d=str((rep or {}).get('direction') or 'NEUTRAL'); strength=f((rep or {}).get('strength'))
            if d not in {'LONG','SHORT'} or strength<=0:continue
            hit=(d=='LONG' and market_ret>0) or (d=='SHORT' and market_ret<0)
            row=raw[name]; row['samples']+=1; row['hits']+=1 if hit else 0; row['returns'].append(market_ret if d=='LONG' else -market_ret); row['strength'].append(strength)
    agents={}
    for name,row in raw.items():
        n=row['samples']; hit=row['hits']/n*100 if n else 0; exp=sum(row['returns'])/n if n else 0
        suggested=1.0
        if n>=30:
            if hit>=60 and exp>0:suggested=1.15
            elif hit<45 or exp<0:suggested=0.85
        agents[name]={'samples':n,'hit_rate_pct':hit,'directional_expectancy_pct':exp,'average_strength':sum(row['strength'])/n if n else 0,'maturity':'MATURE' if n>=50 else 'DEVELOPING' if n>=30 else 'EARLY','suggested_weight':suggested,'applied_weight':1.0}
    payload={'updated_at':now(),'agents':agents,'policy':{'minimum_samples':30,'auto_apply':False,'note':'Calibration is advisory. Weight changes require repeated evidence and explicit strategy validation.'}}
    write(OUT,payload); print(json.dumps({'agents':len(agents)},indent=2)); return 0
if __name__=='__main__':raise SystemExit(main())
