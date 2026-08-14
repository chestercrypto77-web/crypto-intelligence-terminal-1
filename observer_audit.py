from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json, math
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data';OUT=DATA/'observer_audit.json'
def now():return datetime.now(timezone.utc).isoformat()
def read(p,d):
    try:return json.loads(p.read_text())
    except Exception:return d
def write(p,x):
    t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(x,indent=2));json.loads(t.read_text());t.replace(p)
def parse(v):
    try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
    except:return None
def f(v,d=0):
    try:return float(v)
    except:return d
SPECS={'5M':('heartbeat_5m.json',5,'microstructure_latest.json'),'15M':('heartbeat_15m.json',15,'observer_latest.json')}
def main():
    cut=datetime.now(timezone.utc)-timedelta(hours=24);summary={};gaps=[];allruns=[]
    for mode,(hb,interval,latestfn) in SPECS.items():
        data=read(DATA/hb,{'runs':[]});runs=[]
        for r in data.get('runs') or []:
            t=parse(r.get('completed_at'))
            if t and t>=cut and str(r.get('state')).upper() in {'COMPLETE','SUCCESS'}:runs.append(r)
        expected=int(1440/interval);completed=len(runs)
        latest=read(DATA/latestfn,{});health=latest.get('health') or {}
        req=int(health.get('assets_requested') or 0);ana=int(health.get('assets_analysed') or 0);cov=ana/req*100 if req else 0
        stamps=sorted(parse(r.get('completed_at')) for r in runs if parse(r.get('completed_at')));largest=0
        for a,b in zip(stamps,stamps[1:]):
            gap=(b-a).total_seconds()/60;largest=max(largest,gap)
            if gap>interval*2.2:gaps.append({'mode':mode,'from':a.isoformat(),'to':b.isoformat(),'gap_minutes':gap})
        pct=min(100,completed/expected*100) if expected else 0
        summary[mode]={'expected_runs_24h':expected,'recorded_runs_24h':completed,'schedule_completion_pct':pct,
            'latest_asset_coverage_pct':cov,'latest_assets_requested':req,'latest_assets_analysed':ana,'largest_recorded_gap_minutes':largest,
            'status':'PASS' if pct>=90 and cov>=90 else 'CAUTION' if pct>=70 else 'FAIL'}
        allruns += [{'mode':mode,**r} for r in runs]
    write(OUT,{'updated_at':now(),'summary':summary,'runs':allruns[-10000:],'gaps':gaps[-1000:],
      'note':'Run counts come from workflow completion heartbeats. Asset coverage comes from actual observer output; schedule and analysis are verified separately.'})
    print(json.dumps(summary,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
