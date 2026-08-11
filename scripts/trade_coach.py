from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from collections import defaultdict
import copy,json,math
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; OUT=DATA/'trade_coach.json'
def now():return datetime.now(timezone.utc).isoformat()
def read(p,d):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return copy.deepcopy(d)
def write(p,x):
    t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf-8'); json.loads(t.read_text()); t.replace(p)
def f(v,d=0.0):
    try:n=float(v); return n if math.isfinite(n) else d
    except Exception:return d

def grade(r):
    ret=f(r.get('realised_return')); pnl=f(r.get('realised_pnl')); mfe=f(r.get('maximum_favourable_excursion_pct')); mae=f(r.get('maximum_adverse_excursion_pct'))
    post=r.get('post_exit') or {}; best_after=f(post.get('best_directional_move_pct'),f(post.get('directional_move_since_exit_pct')))
    capture=(ret/mfe*100) if ret>0 and mfe>0 else 0.0
    giveback=max(0,mfe-ret)
    if ret<0 and mfe<=0.35: diagnosis='ENTRY NEVER DEVELOPED'; lesson='Demand stronger timing confirmation before allocating.'
    elif ret<0 and mfe>=3: diagnosis='WINNER GIVEN BACK'; lesson='Profit protection failed after a meaningful favourable move.'
    elif ret<0 and best_after>=5: diagnosis='EXIT THEN MISSED RE-ENTRY'; lesson='Separate a valid exit from the next fresh setup; keep active re-entry surveillance.'
    elif ret>0 and mfe>=2 and capture<35: diagnosis='WIN BUT LOW CAPTURE'; lesson='Study peak/exhaustion evidence and test stronger trailing/partial-profit management.'
    elif ret>0 and best_after>=4: diagnosis='WIN THEN MISSED CONTINUATION'; lesson='Good first trade; post-exit surveillance should look for a reset and second entry.'
    elif ret>0: diagnosis='WIN — REPEATABLE PROCESS REVIEW'; lesson='Identify the conditions that were present before entry and preserve what worked.'
    else: diagnosis='CONTROLLED LOSS / REVIEW'; lesson='Compare this case against similar winners before changing a rule.'
    return {'position_id':r.get('position_id'),'case_id':r.get('case_id'),'symbol':r.get('symbol'),'wallet':r.get('wallet'),'direction':r.get('direction'),'return_pct':ret,'pnl':pnl,'mfe_pct':mfe,'mae_pct':mae,'capture_efficiency_pct':capture,'giveback_pct':giveback,'post_exit_best_pct':best_after,'diagnosis':diagnosis,'lesson':lesson,'entry_snapshot':r.get('entry_snapshot') or {},'committee_snapshot':r.get('committee_snapshot') or {},'shared_intelligence':r.get('shared_intelligence') or {}}

def main():
    reviews=read(DATA/'trade_reviews.json',{'reviews':[]}).get('reviews') or []
    integrity=read(DATA/'trade_integrity.json',{'records':[]})
    valid_keys={str(x.get('trade_key')) for x in integrity.get('records') or [] if x.get('status')=='VALIDATED'}
    if valid_keys:
        reviews=[r for r in reviews if str(r.get('position_id') or r.get('case_id') or f"{r.get('wallet','')}_{r.get('symbol','')}_{r.get('entry_time','')}") in valid_keys]
    cases=[grade(r) for r in reviews]; counts=defaultdict(int); lessons=[]
    for c in cases:
        counts[c['diagnosis']]+=1
        if c['lesson'] not in lessons:lessons.append(c['lesson'])
    wins=[c for c in cases if c['return_pct']>0]; losses=[c for c in cases if c['return_pct']<0]
    payload={'updated_at':now(),'summary':{'cases':len(cases),'wins':len(wins),'losses':len(losses),'avg_win_capture_pct':sum(c['capture_efficiency_pct'] for c in wins)/len(wins) if wins else 0.0,'diagnoses':dict(counts)},'cases':cases[-20000:],'lessons':lessons[:100]}
    write(OUT,payload); print(json.dumps(payload['summary'],indent=2)); return 0
if __name__=='__main__':raise SystemExit(main())
