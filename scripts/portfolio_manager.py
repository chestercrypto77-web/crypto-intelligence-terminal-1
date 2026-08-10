from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import copy,json,math
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'

def now(): return datetime.now(timezone.utc).isoformat()
def read(path,default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return copy.deepcopy(default)
def write(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(payload,indent=2),encoding='utf-8'); json.loads(tmp.read_text()); tmp.replace(path)
def f(v,d=0.0):
    try:x=float(v); return x if math.isfinite(x) else d
    except:return d
def side(sig):
    s=str(sig or '').upper()
    if 'BUY' in s:return 'LONG'
    if 'SELL' in s:return 'SHORT'
    return None
def dret(direction,e,c):
    if e<=0:return 0.0
    raw=(c/e-1)*100; return raw if direction=='LONG' else -raw
def journal(w,event,symbol,detail,**extra): w.setdefault('activity_journal',[]).append({'recorded_at':now(),'event':event,'symbol':symbol,'detail':detail,**extra}); w['activity_journal']=w['activity_journal'][-20000:]
def committee_record(committee_map,symbol):
    return committee_map.get(str(symbol or '').upper(),{})

def candidate_quality(s,book,committee_map):
    call=str(s.get('signal') or 'HOLD').upper(); rvol=f(s.get('rvol')); diff=abs(f(s.get('bullish'))-f(s.get('bearish'))); r4=f(s.get('return_4h')); r24=f(s.get('return_24h'))
    committee=committee_record(committee_map,s.get('symbol'))
    decision=committee.get('decision') or {}
    permissions=decision.get('book_permissions') or {}
    direction=decision.get('direction')
    permitted=bool(permissions.get(book))
    signal_side=side(call)
    aligned=direction==signal_side and direction in {'LONG','SHORT'}
    if book=='CORE':
        eligible=permitted and aligned and direction=='LONG' and call in {'BUY','STRONG BUY'} and r24<20
        score=f((decision.get('agreement') or {}).get('long_votes'))*3+diff+rvol
        reasons=[] if eligible else ['COMMITTEE CORE APPROVAL REQUIRED']
    else:
        eligible=permitted and aligned and call in {'BUY','STRONG BUY','SELL','STRONG SELL'}
        score=max(f((decision.get('agreement') or {}).get('long_votes')),f((decision.get('agreement') or {}).get('short_votes')))*3+diff+rvol*2+abs(r4)
        reasons=[] if eligible else ['COMMITTEE SWING APPROVAL REQUIRED']
    return eligible,score,reasons,committee

def update_wallet(wallet,signals,risk_map,book,committee_map):
    rules=wallet.get('rules') or {}; previous=f(wallet.get('equity'),f(wallet.get('starting_cash'),100000)); current={str(s.get('symbol','')).upper():s for s in signals}; actions=[]; keep=[]
    for p in wallet.get('open_positions',[]):
        sym=p['symbol']; s=current.get(sym,{}); price=f(s.get('entry_price'),f(p.get('current_price'),p['entry_price'])); p['current_price']=price; ret=dret(p['direction'],f(p['entry_price']),price)-0.30; p['unrealised_return']=ret; p['unrealised_pnl']=f(p['allocated_cash'])*ret/100; p['maximum_favourable_excursion_pct']=max(f(p.get('maximum_favourable_excursion_pct')),ret); p['maximum_adverse_excursion_pct']=min(f(p.get('maximum_adverse_excursion_pct')),ret)
        call=str(s.get('signal') or 'HOLD').upper(); opposite=(p['direction']=='LONG' and 'SELL' in call) or (p['direction']=='SHORT' and 'BUY' in call); risk=str((risk_map.get(sym) or {}).get('state','NORMAL'))
        reason=None; action='HOLD'
        if opposite: reason='SIGNAL REVERSAL'
        elif risk in {'INVALIDATION RISK','DATA UNRELIABLE'}: reason='RISK GUARDIAN'
        elif ret<=-f(rules.get('stop_loss_pct'),3): reason='STOP LOSS'
        elif book=='SWING':
            mfe=f(p.get('maximum_favourable_excursion_pct'))
            if ret>=f(rules.get('take_profit_pct'),7): reason='TAKE PROFIT'
            elif mfe>=f(rules.get('profit_protection_trigger_pct'),3) and mfe-ret>=f(rules.get('trailing_drawdown_from_peak_pct'),2): reason='PROFIT PROTECTION'
            else:
                try: hours=(pd.Timestamp(now())-pd.Timestamp(p['entry_time'])).total_seconds()/3600
                except: hours=0
                if hours>=f(rules.get('maximum_hold_hours'),240): reason='TIME EXIT'
        else:
            mfe=f(p.get('maximum_favourable_excursion_pct'))
            weakening=call in {'HOLD','BUY WATCH'} or f(s.get('rvol_delta'))<0
            if ret>=f(rules.get('profit_review_pct'),15) and weakening: reason='CORE PROFIT REVIEW'
            elif mfe>=10 and mfe-ret>=f(rules.get('trailing_drawdown_from_peak_pct'),6): reason='CORE PROFIT PROTECTION'
        if reason:
            p.update({'status':'CLOSED','exit_time':now(),'exit_price':price,'exit_reason':reason,'realised_return':ret,'realised_pnl':p['unrealised_pnl']}); wallet['cash']+=f(p['allocated_cash'])+f(p['realised_pnl']); wallet['realised_pnl']=f(wallet.get('realised_pnl'))+f(p['realised_pnl']); wallet.setdefault('closed_positions',[]).append(p); action='EXIT'; journal(wallet,'CLOSED',sym,reason,pnl=p['realised_pnl'],return_pct=ret)
        else: keep.append(p); action='PROTECT PROFIT' if ret>=3 else 'HOLD'
        actions.append({'book':book,'symbol':sym,'action':action,'pnl_pct':ret,'pnl':p.get('unrealised_pnl') if not reason else p.get('realised_pnl'),'reason':reason or 'POSITION VALID'})
    wallet['open_positions']=keep; open_syms={p['symbol'] for p in keep}
    ranked=[]
    for s in signals:
        ok,score,reasons,committee=candidate_quality(s,book,committee_map)
        if ok: ranked.append((score,s,committee))
        elif str(s.get('signal','')).upper() in {'BUY','STRONG BUY','SELL','STRONG SELL'}: wallet.setdefault('rejected_opportunities',[]).append({'recorded_at':now(),'symbol':s.get('symbol'),'signal':s.get('signal'),'reason':' | '.join(reasons)})
    ranked.sort(reverse=True,key=lambda x:x[0]); reserve=f(wallet.get('starting_cash'))*f(rules.get('minimum_cash_reserve_pct'))/100; target=f(wallet.get('starting_cash'))*f(rules.get('position_size_pct'))/100
    for score,s,committee in ranked:
        sym=str(s.get('symbol','')).upper(); d=side(s.get('signal'))
        if book=='CORE' and d!='LONG': continue
        if sym in open_syms or len(wallet['open_positions'])>=int(rules.get('max_positions',5)): continue
        if str((risk_map.get(sym) or {}).get('state','NORMAL')) not in {'NORMAL','CAUTION'}: continue
        alloc=min(target,max(0.0,f(wallet.get('cash'))-reserve)); entry=f(s.get('entry_price'))
        if alloc<=0 or entry<=0: continue
        p={'position_id':f'{book}_{sym}_{str(s.get("recorded_at") or now()).replace(":","")}','book':book,'symbol':sym,'name':s.get('name') or sym,'narrative':s.get('narrative') or '','direction':d,'signal':s.get('signal'),'entry_time':s.get('recorded_at') or now(),'entry_price':entry,'current_price':entry,'allocated_cash':alloc,'units':alloc/entry,'status':'OPEN','unrealised_return':-0.30,'unrealised_pnl':-alloc*0.003,'maximum_favourable_excursion_pct':0.0,'maximum_adverse_excursion_pct':-0.30,'committee_snapshot':committee,'entry_snapshot':{'rvol':s.get('rvol'),'rvol_delta':s.get('rvol_delta'),'return_4h':s.get('return_4h'),'return_12h':s.get('return_12h'),'return_24h':s.get('return_24h'),'bullish':s.get('bullish'),'bearish':s.get('bearish'),'signal':s.get('signal')}}
        wallet['cash']-=alloc; wallet['open_positions'].append(p); open_syms.add(sym); journal(wallet,'OPENED',sym,s.get('signal'),allocation=alloc); actions.append({'book':book,'symbol':sym,'action':'BUY' if d=='LONG' else 'SHORT','pnl_pct':-0.30,'pnl':-alloc*0.003,'reason':'QUALIFIED ENTRY'})
    wallet['unrealised_pnl']=sum(f(p.get('unrealised_pnl')) for p in wallet['open_positions']); wallet['equity']=f(wallet.get('cash'))+sum(f(p.get('allocated_cash'))+f(p.get('unrealised_pnl')) for p in wallet['open_positions']); wallet['previous_equity']=previous; wallet['equity_change_this_run']=wallet['equity']-previous; wallet['updated_at']=now(); wallet.setdefault('equity_history',[]).append({'recorded_at':now(),'equity':wallet['equity'],'cash':wallet['cash'],'realised_pnl':wallet.get('realised_pnl',0),'unrealised_pnl':wallet['unrealised_pnl'],'open_positions':len(wallet['open_positions'])}); wallet['equity_history']=wallet['equity_history'][-20000:]; wallet['closed_positions']=wallet.get('closed_positions',[])[-20000:]; wallet['rejected_opportunities']=wallet.get('rejected_opportunities',[])[-20000:]
    return wallet,actions

def lessons(core,swing,scalp):
    rows=[]
    for book,w in [('CORE',core),('SWING',swing),('SCALP',scalp)]:
        for p in w.get('closed_positions',[]): rows.append((book,p))
    wins=[x for x in rows if f(x[1].get('realised_pnl'))>0]; losses=[x for x in rows if f(x[1].get('realised_pnl'))<0]; gp=sum(f(p.get('realised_pnl')) for _,p in wins); gl=abs(sum(f(p.get('realised_pnl')) for _,p in losses)); by={}
    for book,p in rows:
        b=by.setdefault(book,{'trades':0,'wins':0,'net_pnl':0.0,'returns':[]}); b['trades']+=1; b['wins']+=1 if f(p.get('realised_pnl'))>0 else 0; b['net_pnl']+=f(p.get('realised_pnl')); b['returns'].append(f(p.get('realised_return')))
    for b in by.values(): b['win_rate']=b['wins']/b['trades']*100 if b['trades'] else 0; b['expectancy_pct']=sum(b.pop('returns'))/b['trades'] if b['trades'] else 0
    recent=[]
    for book,p in sorted(rows,key=lambda x:str(x[1].get('exit_time','')),reverse=True)[:30]: recent.append({'book':book,'symbol':p.get('symbol'),'result':'WIN' if f(p.get('realised_pnl'))>0 else 'LOSS','pnl':p.get('realised_pnl'),'return_pct':p.get('realised_return'),'lesson':f"{p.get('exit_reason','EXIT')} produced {'profit' if f(p.get('realised_pnl'))>0 else 'loss'}"})
    return {'updated_at':now(),'closed_trades':len(rows),'wins':len(wins),'losses':len(losses),'win_rate':len(wins)/len(rows)*100 if rows else 0,'net_pnl':gp-gl,'expectancy_pct':sum(f(p.get('realised_return')) for _,p in rows)/len(rows) if rows else 0,'profit_factor':gp/gl if gl else (999 if gp else 0),'by_book':by,'recent_lessons':recent}
def main():
    fund=read(DATA/'fund_state.json',{}); 
    if fund.get('status')!='ACTIVE': print(json.dumps({'status':'SKIPPED','reason':'V10 FUND NOT INITIALISED'},indent=2)); return 0
    signals=read(DATA/'signals_latest.json',{'signals':[]}).get('signals') or []; risks=read(DATA/'risk_guardian.json',{'asset_checks':[]}); risk_map={str(x.get('symbol','')).upper():x for x in risks.get('asset_checks',[])}
    committee_payload=read(DATA/'committee_latest.json',{'assets':[]}); committee_map={str(x.get('symbol','')).upper():x for x in committee_payload.get('assets',[])}
    core=read(DATA/'core_wallet.json',{}); swing=read(DATA/'swing_wallet.json',{}); scalp=read(DATA/'scalp_wallet.json',{})
    core,ca=update_wallet(core,signals,risk_map,'CORE',committee_map); swing,sa=update_wallet(swing,signals,risk_map,'SWING',committee_map); lesson=lessons(core,swing,scalp)
    mgr={'updated_at':now(),'objective':fund.get('objective'),'wallets':{'CORE':{'equity':core.get('equity'),'open':len(core.get('open_positions',[])),'closed':len(core.get('closed_positions',[]))},'SWING':{'equity':swing.get('equity'),'open':len(swing.get('open_positions',[])),'closed':len(swing.get('closed_positions',[]))},'SCALP':{'equity':scalp.get('equity'),'open':len(scalp.get('open_positions',[])),'closed':len(scalp.get('closed_positions',[]))}},'actions':ca+sa,'health':{'signals_checked':len(signals),'committee_assets':len(committee_map),'actions':len(ca)+len(sa)}}
    for n,p in [('core_wallet.json',core),('swing_wallet.json',swing),('portfolio_manager.json',mgr),('trade_lessons.json',lesson)]: write(DATA/n,p)
    health=read(DATA/'engine_health.json',{}); health['portfolio_manager']={'updated_at':mgr['updated_at'],'wallets':mgr['wallets'],'actions':len(mgr['actions'])}; write(DATA/'engine_health.json',health)
    print(json.dumps(mgr,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
