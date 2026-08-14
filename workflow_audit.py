from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1];WF=ROOT/'.github/workflows'
expected={'hourly_signal_recorder.yml':'17 * * * *','observer_15m.yml':'2,17,32,47 * * * *','microstructure_5m.yml':'*/5 * * * *','nightly_deep_learning.yml':'37 2 * * *'}
rows=[];bad=[]
for fn,cron in expected.items():
    p=WF/fn
    if not p.exists():rows.append({'workflow':fn,'status':'MISSING'});bad.append(fn);continue
    txt=p.read_text(encoding='utf-8');schedule_ok=cron in txt
    rows.append({'workflow':fn,'status':'PASS' if schedule_ok else 'BAD SCHEDULE','expected_cron':cron})
    if not schedule_ok:bad.append(fn)
print(json.dumps({'status':'passed' if not bad else 'failed','workflows':rows},indent=2))
if bad:raise SystemExit('Workflow audit failed: '+', '.join(bad))
