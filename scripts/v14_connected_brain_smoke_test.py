from pathlib import Path
import importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/'app.py').read_text(); runner=(ROOT/'scripts/hourly_runner.py').read_text(); pm=(ROOT/'scripts/portfolio_manager.py').read_text(); committee=(ROOT/'scripts/investment_committee.py').read_text()
assert 'APP_VERSION = "14.0.0"' in app
assert 'microstructure_observer.py' in runner and 'trade_coach.py' in runner and 'confidence_ledger.py' in runner and 'brain_health.py' in runner
assert 'def microstructure_analyst' in committee
assert 'MICROSTRUCTURE SAYS WAIT' in pm
assert 'microstructure_at_entry' in pm
for wf in ['hourly_signal_recorder.yml','observer_15m.yml','microstructure_5m.yml','nightly_deep_learning.yml']:
    assert (ROOT/'.github/workflows'/wf).exists() and (ROOT/'WORKFLOW_SETUP'/wf).exists()
spec=importlib.util.spec_from_file_location('micro',ROOT/'scripts/microstructure_observer.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
up={'price':110,'ema9':108,'ema21':105,'rsi':64,'rsi_delta':3,'macd':2,'macd_delta':1,'rvol':1.5,'rvol_delta':.2,'breakout':False,'breakdown':False}
down={'price':90,'ema9':92,'ema21':95,'rsi':36,'rsi_delta':-3,'macd':-2,'macd_delta':-1,'rvol':1.5,'rvol_delta':.2,'breakout':False,'breakdown':False}
assert m.classify(up,up)[0]=='LONG ENTRY'; assert m.classify(down,down)[0]=='SHORT ENTRY'
peak1=dict(up); peak1.update({'price':106,'ema9':107,'ema21':105,'rsi':74,'rsi_delta':-4,'macd':.5,'macd_delta':-.7,'rvol':.9,'rvol_delta':-.3})
peak5=dict(up); peak5.update({'rsi':76,'rvol':1.2,'rvol_delta':-.2})
assert m.classify(peak1,peak5)[0]=='LONG EXIT / PROFIT PROTECT'
pull=dict(down); pull.update({'rsi':43,'rvol':.9,'rvol_delta':-.1})
assert m.classify(pull,up)[0]=='LONG PULLBACK WATCH'
print(json.dumps({'status':'passed','tests':['connected pipeline','workflow presence','long/short entry distinction','peak is profit protection not automatic short','pullback distinction','portfolio timing guard']},indent=2))
