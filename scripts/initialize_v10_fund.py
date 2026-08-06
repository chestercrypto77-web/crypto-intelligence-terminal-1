from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import copy, json, shutil
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; TEMPLATES=DATA/'templates'
ARCHIVE_NAMES=['research_wallet.json','strategy_lab.json','observer_wallet.json','scalp_wallet.json','paper_trades.json','portfolio_manager.json','core_wallet.json','swing_wallet.json','trade_lessons.json','fund_state.json']

def now(): return datetime.now(timezone.utc).isoformat()
def read(path,default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return copy.deepcopy(default)
def write(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(payload,indent=2),encoding='utf-8'); json.loads(tmp.read_text()); tmp.replace(path)
def template(name): return read(TEMPLATES/f'{name}.template.json',{})
def main():
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'); archive=DATA/'archive'/f'pre_v10_{stamp}'; archive.mkdir(parents=True,exist_ok=True)
    archived=[]
    for name in ARCHIVE_NAMES:
        src=DATA/name
        if src.exists(): shutil.copy2(src,archive/name); archived.append(name)
    core=template('core_wallet'); swing=template('swing_wallet'); scalp=template('scalp_wallet'); manager=template('portfolio_manager'); lessons=template('trade_lessons'); fund=template('fund_state')
    # Scalp starts deliberately smaller while the quick-trade engine learns.
    scalp.update({'starting_cash':25000.0,'cash':25000.0,'equity':25000.0,'previous_equity':25000.0,'equity_change_this_run':0.0,'realised_pnl':0.0,'unrealised_pnl':0.0,'open_positions':[],'closed_positions':[],'rejected_opportunities':[],'equity_history':[],'activity_journal':[]})
    scalp.setdefault('session',{}).update({'date':None,'starting_equity':25000.0,'realised_pnl':0.0,'consecutive_losses':0,'new_entries_frozen':False,'freeze_reason':None})
    
    try: archive_ref=str(archive.relative_to(ROOT))
    except ValueError: archive_ref=str(archive)
    fund.update({'initialised_at':now(),'baseline_id':f'V10_{stamp}','status':'ACTIVE','archive':archive_ref,'archived_files':archived})
    for name,payload in [('core_wallet.json',core),('swing_wallet.json',swing),('scalp_wallet.json',scalp),('portfolio_manager.json',manager),('trade_lessons.json',lessons),('fund_state.json',fund),('scalp_checkpoints.json',[])]: write(DATA/name,payload)
    # Active strategy competition resets, historical evidence/ledger/signals are preserved.
    registry=read(DATA/'strategy_registry.json',{'strategies':[]}); lab={'updated_at':now(),'baseline_id':fund['baseline_id'],'assumptions':{},'strategies':{}}
    for s in registry.get('strategies',[]):
        sid=s.get('strategy_id'); start=100000.0
        lab['strategies'][sid]={'strategy_id':sid,'name':s.get('name',sid),'role':s.get('role','CHALLENGER'),'version':s.get('version','1.0.0'),'status':'COLLECTING V10 EVIDENCE','starting_capital':start,'cash':start,'equity':start,'previous_equity':start,'equity_change_this_run':0.0,'realised_pnl':0.0,'unrealised_pnl':0.0,'open_positions':[],'closed_positions':[],'rejected_opportunities':[],'equity_history':[],'activity_journal':[],'heartbeat':{},'activity':{},'metrics':{}}
    write(DATA/'strategy_lab.json',lab)
    print(json.dumps({'status':'V10 INITIALISED','baseline_id':fund['baseline_id'],'archive':str(archive),'archived':archived,'preserved':['evidence_ledger.json','signal_history.json','observer_history.json','external_inbox.json','external_calls.json']},indent=2))
if __name__=='__main__': raise SystemExit(main())
