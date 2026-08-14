from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, os, sys
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'
def now(): return datetime.now(timezone.utc).isoformat()
def read(p,d):
    try:return json.loads(p.read_text())
    except Exception:return d
def write(p,x):
    p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(x,indent=2));json.loads(t.read_text());t.replace(p)
def main():
    name=(os.getenv('WORKFLOW_NAME') or (sys.argv[1] if len(sys.argv)>1 else 'unknown')).strip()
    state=(os.getenv('WORKFLOW_STATE') or (sys.argv[2] if len(sys.argv)>2 else 'START')).strip().upper()
    source=(os.getenv('WORKFLOW_SOURCE') or '').strip(); analysed=os.getenv('WORKFLOW_ANALYSED'); requested=os.getenv('WORKFLOW_REQUESTED')
    key=''.join(ch.lower() if ch.isalnum() else '_' for ch in name).strip('_');p=DATA/f'heartbeat_{key}.json';prior=read(p,{'runs':[]})
    stamp=now(); current=prior.get('current') or {}
    if state=='START':
        current={'started_at':stamp,'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_run_attempt':os.getenv('GITHUB_RUN_ATTEMPT')}
    payload={'workflow':name,'state':state,'updated_at':stamp,'source':source,'current':current,'runs':prior.get('runs') or []}
    if state in {'COMPLETE','SUCCESS','FAIL'}:
        row={**current,'completed_at':stamp,'state':state,'source':source}
        if analysed is not None: row['assets_analysed']=int(float(analysed or 0))
        if requested is not None: row['assets_requested']=int(float(requested or 0))
        payload['runs']=(payload['runs']+[row])[-5000:];payload['current']={}
    write(p,payload);print(json.dumps({'workflow':name,'state':state,'runs':len(payload['runs'])},indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
