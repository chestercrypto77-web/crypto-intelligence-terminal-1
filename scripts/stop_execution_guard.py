from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, math
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'
def now():return datetime.now(timezone.utc).isoformat()
def read(p,d):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return d
def write(p,x):
    p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf-8');json.loads(t.read_text());t.replace(p)
def f(x,d=0.0):
    try:return float(x)
    except:return d
def parse(v):
    try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
    except:return None
def directional(direction,e,p):
    if e<=0 or p<=0:return 0
    raw=(p/e-1)*100;return raw if str(direction).upper()=='LONG' else -raw
def source_prices():
    bad={x.get('symbol') for x in read(DATA/'market_truth.json',{'records':[]}).get('records',[]) if x.get('status')=='QUARANTINE'}
    candidates={}
    for fn,key in [('microstructure_latest.json','signals'),('observer_latest.json','signals')]:
        d=read(DATA/fn,{})
        stamp=parse(d.get('generated_at') or d.get('updated_at'))
        age=(datetime.now(timezone.utc)-stamp).total_seconds()/60 if stamp else 1e9
        maxage=10 if 'microstructure' in fn else 30
        if age>maxage:continue
        for x in d.get(key) or []:
            sym=str(x.get('symbol') or '').upper();p=f(x.get('price'))
            if sym and p>0 and sym not in bad and sym not in candidates:
                candidates[sym]={'price':p,'source':fn,'source_time':d.get('generated_at') or d.get('updated_at'),'age_minutes':age}
    return candidates
def stop_for(pos,wallet):
    e=f(pos.get('entry_price')); d=str(pos.get('direction') or '').upper(); stop=f(pos.get('stop_price'))
    pct=f(pos.get('stop_loss_pct'),f((wallet.get('rules') or {}).get('stop_loss_pct'),3.0))/100
    if stop<=0:stop=e*(1-pct) if d=='LONG' else e*(1+pct)
    return stop
def main():
    prices=source_prices();events=[];executed=[];stamp=now()
    for fn in ['observer_wallet.json','scalp_wallet.json','swing_wallet.json','core_wallet.json']:
        path=DATA/fn; wallet=read(path,{})
        positions=wallet.get('open_positions') if isinstance(wallet.get('open_positions'),list) else wallet.get('positions') or []
        keep=[]; changed=False
        for p in positions:
            if str(p.get('status','OPEN')).upper()!='OPEN':keep.append(p);continue
            sym=str(p.get('symbol') or '').upper();src=prices.get(sym)
            if not src:keep.append(p);continue
            price=f(src.get('price'));stop=stop_for(p,wallet);direction=str(p.get('direction') or '').upper()
            hit=(direction=='LONG' and price<=stop) or (direction=='SHORT' and price>=stop)
            if not hit:keep.append(p);continue
            entry=f(p.get('entry_price'));ret=directional(direction,entry,price)
            alloc=f(p.get('allocated_cash'));pnl=alloc*ret/100
            p.update({'status':'CLOSED','current_price':price,'exit_time':stamp,'exit_price':price,'exit_reason':'HARD STOP — EXECUTION GUARD',
                      'realised_return':ret,'realised_pnl':pnl,'stop_price':stop})
            wallet.setdefault('closed_positions',[]).append(p)
            wallet['cash']=f(wallet.get('cash'))+alloc+pnl;wallet['realised_pnl']=f(wallet.get('realised_pnl'))+pnl
            wallet.setdefault('activity_journal',[]).append({'recorded_at':stamp,'event':'HARD_STOP_EXECUTED','symbol':sym,'detail':'Execution guard closed position at validated market price','pnl':pnl,'return_pct':ret})
            wallet['activity_journal']=wallet['activity_journal'][-20000:]
            event={'time':stamp,'wallet':fn,'position_id':p.get('position_id'),'symbol':sym,'direction':direction,'entry_price':entry,
                   'validated_price':price,'stop_price':stop,'action':'FORCE_EXIT_EXECUTED','priority':'P0','source':src.get('source'),
                   'source_time':src.get('source_time'),'source_age_minutes':src.get('age_minutes'),'realised_return_pct':ret,'realised_pnl':pnl}
            events.append(event);executed.append(event);changed=True
        if isinstance(wallet.get('open_positions'),list):wallet['open_positions']=keep
        else:wallet['positions']=keep
        if changed:
            wallet['unrealised_pnl']=sum(f(x.get('unrealised_pnl')) for x in keep)
            wallet['equity']=f(wallet.get('cash'))+sum(f(x.get('allocated_cash'))+f(x.get('unrealised_pnl')) for x in keep)
            wallet['updated_at']=stamp
            write(path,wallet)
    write(DATA/'stop_execution_alerts.json',{'updated_at':stamp,'summary':{'force_exit_required':0,'force_exit_executed':len(executed)},'events':events[-5000:]})
    print(json.dumps({'force_exit_executed':len(executed)},indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
