from pathlib import Path
import importlib.util,json,random
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('micro',ROOT/'scripts/microstructure_observer.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
# 200 deterministic synthetic state comparisons across trend, pullback and exhaustion families.
random.seed(14); passed=0; total=0
for _ in range(50):
    up={'price':110,'ema9':108,'ema21':105,'rsi':60+random.random()*8,'rsi_delta':2,'macd':1,'macd_delta':.3,'rvol':1.2+random.random(),'rvol_delta':.1,'breakout':False,'breakdown':False}
    total+=1; passed+=m.classify(up,up)[0]=='LONG ENTRY'
    down={'price':90,'ema9':92,'ema21':95,'rsi':32+random.random()*8,'rsi_delta':-2,'macd':-1,'macd_delta':-.3,'rvol':1.2+random.random(),'rvol_delta':.1,'breakout':False,'breakdown':False}
    total+=1; passed+=m.classify(down,down)[0]=='SHORT ENTRY'
    peak1=dict(up); peak1.update({'price':106,'ema9':107,'ema21':105,'rsi':74,'rsi_delta':-4,'macd':.4,'macd_delta':-.5,'rvol':.8,'rvol_delta':-.2}); peak5=dict(up); peak5.update({'rsi':76,'rvol':1.2,'rvol_delta':-.1})
    total+=1; passed+=m.classify(peak1,peak5)[0]=='LONG EXIT / PROFIT PROTECT'
    pull=dict(down); pull.update({'rsi':43,'rvol':.8,'rvol_delta':-.1})
    total+=1; passed+=m.classify(pull,up)[0]=='LONG PULLBACK WATCH'
assert passed==total,(passed,total)
print(json.dumps({'status':'passed','synthetic_cases':total,'correct_semantic_classifications':passed,'note':'This validates signal-role semantics and anti-confusion behavior; it is not evidence of future profitability.'},indent=2))
