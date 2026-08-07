import re
from pathlib import Path
import importlib.util,json,tempfile,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
def load(name):
 p=ROOT/'scripts'/f'{name}.py'; spec=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def runtime_test():
 init=load('initialize_v10_fund')
 with tempfile.TemporaryDirectory() as td:
  d=Path(td)/'data'; shutil.copytree(ROOT/'data/templates',d/'templates');
  # add old records that must archive/preserve
  (d/'research_wallet.json').write_text(json.dumps({'equity':90000})); (d/'evidence_ledger.json').write_text(json.dumps([{'id':1}]))
  init.DATA=d; init.TEMPLATES=d/'templates'; init.main()
  fund=json.loads((d/'fund_state.json').read_text()); assert fund['status']=='ACTIVE'; assert json.loads((d/'core_wallet.json').read_text())['equity']==100000; assert json.loads((d/'swing_wallet.json').read_text())['equity']==100000; assert json.loads((d/'scalp_wallet.json').read_text())['equity']==25000; assert json.loads((d/'evidence_ledger.json').read_text())==[{'id':1}]; assert list((d/'archive').glob('pre_v10_*'))
def static_test():
 app=(ROOT/'app.py').read_text(); assert 'APP_VERSION = "11.0.0"' in app; assert 'AI Fund:' in app; assert 'PROTECT PROFIT' in app
 runner=(ROOT/'scripts/hourly_runner.py').read_text(); assert 'portfolio_manager.py' in runner
 for n in ['core_wallet','swing_wallet','fund_state','portfolio_manager','trade_lessons']: assert (ROOT/'data/templates'/f'{n}.template.json').exists()
if __name__=='__main__':
 import argparse; p=argparse.ArgumentParser(); p.add_argument('--runtime',action='store_true'); a=p.parse_args(); static_test(); runtime_test(); print(json.dumps({'status':'passed','tests':['archive and reset','knowledge preservation','core/swing/scalp baselines','portfolio manager wiring','simple AI Fund interface']},indent=2))
