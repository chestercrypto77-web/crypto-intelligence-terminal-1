from pathlib import Path
from datetime import datetime, timezone
import json
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data'
def now():return datetime.now(timezone.utc).isoformat()
def read(p,d):
    try:return json.loads(p.read_text())
    except:return d
def parse(v):
    try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
    except:return None
def age(v):
    t=parse(v);return (datetime.now(timezone.utc)-t).total_seconds()/60 if t else None
def write(p,x):
    t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(x,indent=2));json.loads(t.read_text());t.replace(p)
def main():
    specs=[('5M','microstructure_latest.json','generated_at',10),('15M','observer_latest.json','generated_at',30),
           ('Portfolio','portfolio_manager.json','updated_at',35),('Trade Desk','active_trade_casefiles.json','updated_at',35)]
    checks=[];critical=[]
    for name,fn,key,limit in specs:
        d=read(DATA/fn,{});stamp=d.get(key) or d.get('updated_at') or d.get('generated_at');a=age(stamp)
        status='PASS' if a is not None and a<=limit else 'STALE'
        checks.append({'component':name,'source':fn,'last_output':stamp,'age_minutes':a,'limit_minutes':limit,'status':status})
        if status!='PASS':critical.append(f'{name} stale')
    # State reconciliation: casefile count must match current Core+Swing+Scalp open positions.
    expected=0
    wallet_times=[]
    for fn in ['core_wallet.json','swing_wallet.json','scalp_wallet.json']:
        d=read(DATA/fn,{});expected+=len(d.get('open_positions') or []);wallet_times.append(d.get('updated_at'))
    cf=read(DATA/'active_trade_casefiles.json',{});actual=len(cf.get('positions') or [])
    recon='PASS' if expected==actual else 'FAIL'
    if recon!='PASS':critical.append(f'Trading Desk mismatch wallets={expected} casefiles={actual}')
    payload={'updated_at':now(),'overall':'PASS' if not critical else 'FAIL','checks':checks,
             'reconciliation':{'wallet_open_positions':expected,'casefile_positions':actual,'status':recon},'alerts':critical,
             'rule':'Observation and stop protection have priority. Learning is quarantined when critical observation continuity is not proven.'}
    write(DATA/'runtime_watchdog.json',payload);print(json.dumps(payload,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
