from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, math
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'
def now():return datetime.now(timezone.utc).isoformat()
def read(p,d):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return d
def write(p,x):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf-8'); json.loads(t.read_text()); t.replace(p)
def f(x,d=None):
    try:
        v=float(x); return v if math.isfinite(v) else d
    except Exception:return d
def tkey(r):return str(r.get('position_id') or r.get('case_id') or f"{r.get('wallet','')}_{r.get('symbol','')}_{r.get('entry_time','')}")
def expected_return(direction,e,x):
    if not e or not x:return None
    raw=(x/e-1)*100; return raw if str(direction).upper()=='LONG' else -raw
def main():
    reviews=read(DATA/'trade_reviews.json',{'reviews':[]}).get('reviews') or []
    quarantined_symbols=set(read(DATA/'learning_quarantine.json',{}).get('quarantined_symbols') or [])
    records=[]; quarantine=[]
    for r in reviews:
        reasons=[]; k=tkey(r); sym=str(r.get('symbol') or '').upper(); direction=str(r.get('direction') or '').upper()
        e=f(r.get('entry_price')); x=f(r.get('exit_price')); ret=f(r.get('realised_return')); pnl=f(r.get('realised_pnl'))
        if not k or not sym: reasons.append('MISSING_IDENTITY')
        if direction not in {'LONG','SHORT'}: reasons.append('INVALID_DIRECTION')
        if not e or e<=0 or not x or x<=0: reasons.append('INVALID_ENTRY_OR_EXIT_PRICE')
        calc=expected_return(direction,e,x) if e and x and direction in {'LONG','SHORT'} else None
        # Fees/slippage can create small differences; large discrepancies are quarantined.
        if calc is not None and ret is not None and abs(calc-ret)>1.25: reasons.append('RETURN_MISMATCH_GT_1_25PCT')
        alloc=f(r.get('allocated_cash'))
        if alloc is None: alloc=f((r.get('source_position') or {}).get('allocated_cash'))
        if alloc and pnl is not None and ret is not None:
            expected=alloc*ret/100
            tolerance=max(2.0,abs(alloc)*0.015)
            if abs(expected-pnl)>tolerance: reasons.append('PNL_RETURN_MISMATCH')
        replay=((r.get('replay') or {}).get('price_path')) or []
        replay_prices=[f(x.get('price')) for x in replay if f(x.get('price')) and f(x.get('price'))>0]
        for a,b in zip(replay_prices,replay_prices[1:]):
            if a>0 and abs(b/a-1)*100>60:
                reasons.append('REPLAY_PRICE_DISCONTINUITY_GT_60PCT'); break
        if ret is not None and abs(ret)>100: reasons.append('EXTREME_RETURN_GT_100PCT')
        if ret is not None and ret<-10: reasons.append('RISK_CONTROL_BREACH_GT_10PCT_LOSS')
        if sym in quarantined_symbols: reasons.append('SYMBOL_DATA_QUARANTINED')
        status='VALIDATED' if not reasons else 'QUARANTINED'
        row={'trade_key':k,'symbol':sym,'status':status,'reasons':reasons,'entry_price':e,'exit_price':x,
             'reported_return_pct':ret,'recomputed_gross_return_pct':calc,'reported_pnl':pnl}
        records.append(row)
        if reasons: quarantine.append(row)
    reviewed=len(records); valid=sum(x['status']=='VALIDATED' for x in records)
    payload={'updated_at':now(),'summary':{'reviewed':reviewed,'validated':valid,'quarantined':len(quarantine),
              'validation_rate_pct':valid/reviewed*100 if reviewed else 0},'records':records[-50000:],
              'rule':'Only VALIDATED trade records may teach trusted learning engines.'}
    write(DATA/'trade_integrity.json',payload)
    write(DATA/'trade_quarantine.json',{'updated_at':now(),'summary':{'quarantined':len(quarantine)},'records':quarantine[-10000:]})
    print(json.dumps(payload['summary'],indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
