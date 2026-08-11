from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import copy, json, math
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
def now(): return datetime.now(timezone.utc).isoformat()
def read(path, default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return copy.deepcopy(default)
def write(path, payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8")
    json.loads(temp.read_text(encoding="utf-8"))
    temp.replace(path)
def f(v,d=0.0):
    try:
        x=float(v)
        return x if math.isfinite(x) else d
    except Exception: return d
def trade_key(r):
    return str(r.get("position_id") or r.get("case_id") or f"{r.get('wallet','')}_{r.get('symbol','')}_{r.get('entry_time','')}")

OUT=DATA/"profit_capture.json"
def main():
    reviews=read(DATA/"trade_reviews.json",{"reviews":[]}).get("reviews") or []
    integrity=read(DATA/"trade_integrity.json",{"records":[]})
    valid={x.get("trade_key") for x in integrity.get("records") or [] if x.get("status")=="VALIDATED"}
    records=[]
    for r in reviews:
        if trade_key(r) not in valid: continue
        ret=f(r.get("realised_return")); mfe=max(0.0,f(r.get("maximum_favourable_excursion_pct")))
        mae=f(r.get("maximum_adverse_excursion_pct"))
        capture=(max(0,ret)/mfe*100) if mfe>0 else 0.0
        giveback=max(0,mfe-ret)
        post=f((r.get("post_exit") or {}).get("best_directional_move_pct"))
        if ret>0 and mfe>=1:
            grade="EXCELLENT" if capture>=70 else "GOOD" if capture>=50 else "LOW CAPTURE" if capture>=25 else "POOR CAPTURE"
        elif ret<0 and mfe>=2: grade="WINNER GIVEN BACK"
        elif ret<0: grade="LOSS REVIEW"
        else: grade="NEUTRAL"
        records.append({"trade_key":trade_key(r),"symbol":r.get("symbol"),"wallet":r.get("wallet"),"direction":r.get("direction"),
                        "return_pct":ret,"mfe_pct":mfe,"mae_pct":mae,"capture_efficiency_pct":capture,
                        "giveback_pct":giveback,"best_after_exit_pct":post,"grade":grade})
    wins=[x for x in records if x["return_pct"]>0]
    summary={"validated_trades":len(records),
             "avg_winner_capture_pct":sum(x["capture_efficiency_pct"] for x in wins)/len(wins) if wins else 0,
             "excellent_capture":sum(x["grade"]=="EXCELLENT" for x in records),
             "low_or_poor_capture":sum(x["grade"] in {"LOW CAPTURE","POOR CAPTURE"} for x in records),
             "winners_given_back":sum(x["grade"]=="WINNER GIVEN BACK" for x in records)}
    write(OUT,{"updated_at":now(),"summary":summary,"records":records[-30000:]})
    print(json.dumps(summary,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
