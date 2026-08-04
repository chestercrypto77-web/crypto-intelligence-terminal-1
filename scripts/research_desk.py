from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json, copy
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'

def now(): return datetime.now(timezone.utc).isoformat()
def read(path,default):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except Exception: return copy.deepcopy(default)
def write(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8'); tmp.replace(path)
def state(sig,changed,prev):
    s=str(sig or 'HOLD').upper(); p=str(prev or '').upper()
    if s in {'BUY WATCH','SELL WATCH'}: return 'FORMING'
    if s in {'BUY','STRONG BUY','SELL','STRONG SELL'}: return 'CONFIRMED' if changed else 'ACTIVE'
    if s=='HOLD' and p in {'BUY','STRONG BUY','SELL','STRONG SELL'}: return 'WEAKENING'
    return 'NEUTRAL'
def direction(sig):
    s=str(sig or '').upper()
    if s in {'BUY','STRONG BUY'}: return 'LONG'
    if s in {'SELL','STRONG SELL'}: return 'SHORT'
    return None
def dret(d,e,c):
    raw=(c/e-1)*100
    return raw if d=='LONG' else -raw

def main():
    latest=read(DATA/'signals_latest.json',{'signals':[]}); signals=latest.get('signals') or []
    registry=read(DATA/'strategy_registry.json',{'champion_id':'conviction_v1','strategies':[]})
    champion=next((x for x in registry.get('strategies',[]) if x.get('strategy_id')==registry.get('champion_id')),{'strategy_id':'conviction_v1','version':'1.0.0'})
    ledger=read(DATA/'evidence_ledger.json',[]); existing={x.get('ledger_id') for x in ledger}
    lifecycle=read(DATA/'signal_lifecycle.json',{'updated_at':None,'assets':{}}); lifecycle.setdefault('assets',{})
    wallet=read(DATA/'research_wallet.json',{})
    if not wallet:
        wallet={'wallet_id':'RESEARCH_WALLET_V1','name':'AI Research Wallet','currency':'USD','starting_cash':100000.0,'cash':100000.0,'equity':100000.0,'realised_pnl':0.0,'unrealised_pnl':0.0,'max_positions':8,'position_size_pct':10.0,'minimum_cash_reserve_pct':20.0,'rejected_opportunities':[],'open_positions':[],'closed_positions':[],'equity_history':[]}
    for s in signals:
        lid=f"{champion.get('strategy_id')}_{s.get('signal_id')}"
        if lid not in existing:
            ledger.append({'ledger_id':lid,'recorded_at':s.get('recorded_at') or now(),'asset':s.get('symbol'),'asset_name':s.get('name'),'narrative':s.get('narrative'),'strategy_id':champion.get('strategy_id'),'strategy_version':champion.get('version'),'signal':s.get('signal'),'previous_signal':s.get('previous_signal'),'changed':bool(s.get('changed')),'lifecycle_state':state(s.get('signal'),bool(s.get('changed')),s.get('previous_signal')),'entry_price':s.get('entry_price'),'candle_time':s.get('candle_time'),'candle_status':'INTRABAR','data_source':s.get('data_source'),'returns_at_signal':{'4h':s.get('return_4h'),'12h':s.get('return_12h'),'24h':s.get('return_24h')},'indicators':{'rvol':s.get('rvol'),'rvol_delta':s.get('rvol_delta'),'rsi':s.get('rsi'),'bullish_conditions':s.get('bullish'),'bearish_conditions':s.get('bearish'),'total_conditions':s.get('total')},'checks':s.get('checks') or [],'immutable':True}); existing.add(lid)
        sym=str(s.get('symbol') or '').upper(); key=f"{champion.get('strategy_id')}:{sym}"
        a=lifecycle['assets'].setdefault(key,{'strategy_id':champion.get('strategy_id'),'symbol':sym,'current_state':'NEUTRAL','current_signal':'HOLD','transitions':[]})
        st=state(s.get('signal'),bool(s.get('changed')),s.get('previous_signal')); tk=f"{s.get('signal_id')}:{st}"
        if not any(t.get('transition_key')==tk for t in a['transitions']): a['transitions'].append({'transition_key':tk,'recorded_at':s.get('recorded_at') or now(),'from_signal':s.get('previous_signal'),'to_signal':s.get('signal'),'state':st,'entry_price':s.get('entry_price'),'bullish':s.get('bullish'),'bearish':s.get('bearish'),'rvol':s.get('rvol')})
        a['current_state']=st; a['current_signal']=s.get('signal'); a['last_updated']=s.get('recorded_at') or now(); a['transitions']=a['transitions'][-500:]
    prices={str(s.get('symbol') or '').upper():float(s.get('entry_price') or 0) for s in signals if float(s.get('entry_price') or 0)>0}
    latestmap={str(s.get('symbol') or '').upper():s for s in signals}
    activity={'retained':0,'closed':0,'opened':0,'rejected_capacity':0,'rejected_cash_reserve':0,'rejected_existing':0}
    keep=[]
    for p in wallet.get('open_positions',[]):
        cur=prices.get(p.get('symbol'),p.get('current_price') or p['entry_price']); p['current_price']=cur; p['unrealised_return']=dret(p['direction'],p['entry_price'],cur); p['unrealised_pnl']=p['allocated_cash']*p['unrealised_return']/100
        ls=str(latestmap.get(p.get('symbol'),{}).get('signal') or 'HOLD'); reverse=(p['direction']=='LONG' and 'SELL' in ls) or (p['direction']=='SHORT' and 'BUY' in ls)
        if reverse or ls=='HOLD':
            activity['closed']+=1; p['status']='CLOSED'; p['exit_time']=now(); p['exit_price']=cur; p['exit_reason']='Signal reversal' if reverse else 'Signal returned to HOLD'; p['realised_return']=p['unrealised_return']; p['realised_pnl']=p['unrealised_pnl']; wallet['cash']+=p['allocated_cash']+p['realised_pnl']; wallet['realised_pnl']+=p['realised_pnl']; wallet.setdefault('closed_positions',[]).append(p)
        else:
            activity['retained']+=1
            keep.append(p)
    wallet['open_positions']=keep; open_syms={p.get('symbol') for p in keep}
    decisive=[s for s in signals if direction(s.get('signal'))]
    decisive.sort(key=lambda s:(abs(float(s.get('bullish') or 0)-float(s.get('bearish') or 0)),float(s.get('rvol') or 0),abs(float(s.get('return_4h') or 0))),reverse=True)
    reserve=wallet['starting_cash']*float(wallet.get('minimum_cash_reserve_pct',20.0))/100
    rejected=wallet.setdefault('rejected_opportunities',[])
    for s in decisive:
        sym=str(s.get('symbol') or '').upper(); d=direction(s.get('signal'))
        if not sym or not d: continue
        if sym in open_syms:
            activity['rejected_existing']+=1
            continue
        if len(wallet['open_positions'])>=int(wallet.get('max_positions',8)):
            activity['rejected_capacity']+=1
            rejected.append({'recorded_at':now(),'symbol':sym,'signal':s.get('signal'),'reason':'WALLET CAPACITY','entry_price':s.get('entry_price')})
            continue
        entry=float(s.get('entry_price') or 0)
        target=wallet['starting_cash']*float(wallet.get('position_size_pct',10))/100
        available=max(0.0,wallet['cash']-reserve)
        alloc=min(available,target)
        if entry<=0 or alloc<=0:
            activity['rejected_cash_reserve']+=1
            rejected.append({'recorded_at':now(),'symbol':sym,'signal':s.get('signal'),'reason':'CASH RESERVE','entry_price':s.get('entry_price')})
            continue
        pos={'position_id':f"{s.get('signal_id')}_WALLET",'symbol':sym,'name':s.get('name') or sym,'narrative':s.get('narrative') or '','strategy_id':champion.get('strategy_id'),'signal':s.get('signal'),'direction':d,'entry_time':s.get('recorded_at') or now(),'entry_price':entry,'current_price':entry,'allocated_cash':alloc,'units':alloc/entry,'status':'OPEN','unrealised_return':0.0,'unrealised_pnl':0.0}
        wallet['cash']-=alloc; wallet['open_positions'].append(pos); open_syms.add(sym); activity['opened']+=1
    wallet['rejected_opportunities']=rejected[-10000:]
    wallet['closed_positions']=wallet.get('closed_positions',[])[-10000:]; wallet['unrealised_pnl']=sum(float(p.get('unrealised_pnl') or 0) for p in wallet['open_positions']); wallet['equity']=wallet['cash']+sum(float(p.get('allocated_cash') or 0)+float(p.get('unrealised_pnl') or 0) for p in wallet['open_positions']); wallet.setdefault('equity_history',[]).append({'recorded_at':now(),'equity':wallet['equity'],'cash':wallet['cash'],'realised_pnl':wallet['realised_pnl'],'unrealised_pnl':wallet['unrealised_pnl'],'open_positions':len(wallet['open_positions'])}); wallet['equity_history']=wallet['equity_history'][-20000:]; wallet['updated_at']=now(); lifecycle['updated_at']=now()
    health=read(DATA/'engine_health.json',{})
    health['research_wallet']={
        'wallet_equity':wallet['equity'],
        'cash':wallet['cash'],
        'realised_pnl':wallet['realised_pnl'],
        'unrealised_pnl':wallet['unrealised_pnl'],
        'open_positions':len(wallet['open_positions']),
        'closed_positions':len(wallet.get('closed_positions',[])),
        'activity':activity,
        'minimum_cash_reserve_pct':wallet.get('minimum_cash_reserve_pct',20.0),
        'max_positions':wallet.get('max_positions',8),
    }
    if health.get('overall_status')!='FAIL': health['overall_status']='PASS WITH WARNINGS' if health.get('warnings') else 'PASS'
    write(DATA/'evidence_ledger.json',ledger[-50000:]); write(DATA/'signal_lifecycle.json',lifecycle); write(DATA/'research_wallet.json',wallet); write(DATA/'engine_health.json',health)
    print(json.dumps({'ledger_records':len(ledger),'lifecycle_assets':len(lifecycle['assets']),'wallet_equity':wallet['equity'],'cash':wallet['cash'],'open_positions':len(wallet['open_positions']),'closed_positions':len(wallet.get('closed_positions',[])),'activity':activity},indent=2))
if __name__=='__main__': raise SystemExit(main())
