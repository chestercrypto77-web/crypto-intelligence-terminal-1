from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import copy,json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; OUT=DATA/'brain_health.json'
def now():return datetime.now(timezone.utc).isoformat()
def read(p,d):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return copy.deepcopy(d)
def write(p,x):
    t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(x,indent=2),encoding='utf-8'); json.loads(t.read_text()); t.replace(p)
def age(value):
    try:return max(0,(pd.Timestamp(now())-pd.Timestamp(value)).total_seconds()/60)
    except Exception:return 999999

def main():
    specs={
      'microstructure':('microstructure_latest.json','generated_at',15),
      'observer_15m':('observer_latest.json','generated_at',35),
      'hourly_signals':('signals_latest.json','recorded_at',90),
      'committee':('committee_latest.json','updated_at',90),
      'market_school':('market_school.json','updated_at',180),
      'intelligence_bus':('intelligence_bus.json','updated_at',35),
      'trade_coach':('trade_coach.json','updated_at',180),
      'confidence_ledger':('confidence_ledger.json','updated_at',180),
      'learning':('learning_state.json','updated_at',180),
    }
    components={}; warnings=[]
    for name,(fn,key,limit) in specs.items():
        d=read(DATA/fn,{}); timestamp=d.get(key)
        if name=='hourly_signals' and not timestamp:
            sig=(d.get('signals') or []); timestamp=(sig[0] or {}).get('recorded_at') if sig else None
        a=age(timestamp); status='PASS' if a<=limit else 'STALE' if timestamp else 'MISSING'
        components[name]={'status':status,'age_minutes':round(a,1) if a<999999 else None,'timestamp':timestamp,'freshness_limit_minutes':limit}
        if status!='PASS':warnings.append(f'{name}: {status}')
    payload={'updated_at':now(),'overall':'PASS' if not warnings else 'CAUTION','components':components,'warnings':warnings}
    write(OUT,payload); print(json.dumps({'overall':payload['overall'],'warnings':warnings},indent=2)); return 0
if __name__=='__main__':raise SystemExit(main())
