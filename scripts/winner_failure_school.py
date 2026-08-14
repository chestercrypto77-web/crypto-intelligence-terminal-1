from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
import json, math
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'
def now():return datetime.now(timezone.utc).isoformat()
def read(p,d):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return d
def write(p,x):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf-8');json.loads(t.read_text());t.replace(p)
def f(x,d=0.0):
    try:
        v=float(x);return v if math.isfinite(v) else d
    except Exception:return d
def key(r):return str(r.get('position_id') or r.get('case_id') or f"{r.get('wallet','')}_{r.get('symbol','')}_{r.get('entry_time','')}")
def fingerprint(r):
    e=r.get('entry_snapshot') or r.get('observer_evidence') or {}
    rv=f(e.get('rvol')); r4=f(e.get('return_4h')); bull=f(e.get('bullish'),f(e.get('bullish_conditions'))); bear=f(e.get('bearish'),f(e.get('bearish_conditions')))
    return '|'.join([
      str(r.get('direction') or 'UNK').upper(),
      'RVOL_HIGH' if rv>=1.5 else 'RVOL_ACTIVE' if rv>=1.0 else 'RVOL_LOW',
      'R4_UP' if r4>1 else 'R4_DOWN' if r4<-1 else 'R4_FLAT',
      'BULL' if bull-bear>=3 else 'BEAR' if bear-bull>=3 else 'MIXED',
      str(r.get('exit_reason') or 'OPEN').upper().replace(' ','_')])
def main():
    integrity=read(DATA/'trade_integrity.json',{'records':[]}).get('records') or []
    valid={str(x.get('trade_key')) for x in integrity if x.get('status')=='VALIDATED'}
    reviews=read(DATA/'trade_reviews.json',{'reviews':[]}).get('reviews') or []
    reviews=[r for r in reviews if key(r) in valid] if valid else []
    wins=[r for r in reviews if f(r.get('realised_pnl'))>0]
    failures=[r for r in reviews if f(r.get('realised_pnl'))<0 or str((r.get('assessment') or {}).get('process_quality') or '').upper()=='POOR']
    wg=defaultdict(list); fg=defaultdict(list)
    for r in wins: wg[fingerprint(r)].append(r)
    for r in failures: fg[fingerprint(r)].append(r)
    wf={k:{'samples':len(v),'avg_return_pct':sum(f(x.get('realised_return')) for x in v)/len(v),
           'symbols':sorted({str(x.get('symbol')) for x in v})[:20]} for k,v in wg.items()}
    ff={k:{'samples':len(v),'avg_return_pct':sum(f(x.get('realised_return')) for x in v)/len(v),
           'symbols':sorted({str(x.get('symbol')) for x in v})[:20]} for k,v in fg.items()}
    write(DATA/'winner_school.json',{'updated_at':now(),'summary':{'validated_winners':len(wins),'fingerprints':len(wf)},
         'fingerprints':wf,'examples':wins[-2000:],'guardrail':'Descriptive evidence only; V21 Learning Governor controls promotion.'})
    write(DATA/'failure_school.json',{'updated_at':now(),'summary':{'validated_failures':len(failures),'failure_modes':len(ff)},
         'failure_modes':ff,'examples':failures[-2000:],'guardrail':'Descriptive evidence only; V21 Learning Governor controls promotion.'})
    print(json.dumps({'winners':len(wins),'failures':len(failures)},indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
