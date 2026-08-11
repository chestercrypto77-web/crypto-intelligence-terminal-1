from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import copy,json,math
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"; OUT=DATA/"learning_state.json"
def now(): return datetime.now(timezone.utc).isoformat()
def read(path,default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception:return copy.deepcopy(default)
def write(path,payload):
    t=path.with_suffix(path.suffix+".tmp"); t.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8")
    json.loads(t.read_text(encoding="utf-8")); t.replace(path)
def num(v,d=0.0):
    try:
        n=float(v); return n if math.isfinite(n) else d
    except Exception:return d
def summarise(rows):
    if not rows:return {"samples":0,"wins":0,"win_rate":0.0,"net_pnl":0.0,"expectancy_pct":0.0}
    wins=sum(num(r.get("realised_pnl"))>0 for r in rows)
    return {"samples":len(rows),"wins":wins,"win_rate":wins/len(rows)*100,
            "net_pnl":sum(num(r.get("realised_pnl")) for r in rows),
            "expectancy_pct":sum(num(r.get("realised_return")) for r in rows)/len(rows)}
def main():
    reviews=read(DATA/"trade_reviews.json",{"reviews":[]}).get("reviews") or []
    integrity=read(DATA/'trade_integrity.json',{'records':[]})
    valid_keys={str(x.get('trade_key')) for x in integrity.get('records') or [] if x.get('status')=='VALIDATED'}
    if valid_keys:
        reviews=[r for r in reviews if str(r.get('position_id') or r.get('case_id') or f"{r.get('wallet','')}_{r.get('symbol','')}_{r.get('entry_time','')}") in valid_keys]
    committee=read(DATA/"committee_learning.json",{})
    diagnostics=read(DATA/"trade_diagnostics.json",{"summary":{},"diagnostics":[]})
    prior=read(OUT,{"promoted_lessons":[],"guardrails":{"minimum_samples_for_candidate":8,
        "minimum_samples_for_promotion":20,"minimum_expectancy_pct":0.25,"auto_modify_live_rules":False}})
    g=prior.get("guardrails") or {}; min_c=int(g.get("minimum_samples_for_candidate",8))
    min_p=int(g.get("minimum_samples_for_promotion",20)); min_e=num(g.get("minimum_expectancy_pct"),0.25)
    by_book=defaultdict(list); by_exit=defaultdict(list); by_entry=defaultdict(list)
    good=poor=missed=0
    for r in reviews:
        by_book[str(r.get("wallet") or "Unknown")].append(r)
        by_exit[str(r.get("exit_reason") or "Unknown")].append(r)
        a=r.get("assessment") or {}; by_entry[str(a.get("entry_quality") or "UNKNOWN")].append(r)
        q=str(a.get("process_quality") or "").upper(); good+=q=="GOOD"; poor+=q=="POOR"
        missed+="MISSED" in str((r.get("reentry") or {}).get("status") or "").upper()
    book_learning={k:summarise(v) for k,v in by_book.items()}
    conditions={f"exit:{k}":summarise(v) for k,v in by_exit.items()}
    conditions.update({f"entry_quality:{k}":summarise(v) for k,v in by_entry.items()})
    for key,row in (committee.get("conditions") or {}).items():
        conditions[f"committee:{key}"]={"samples":int(row.get("trades") or 0),"wins":int(row.get("wins") or 0),
            "win_rate":num(row.get("win_rate")),"net_pnl":num(row.get("net_pnl")),
            "expectancy_pct":num(row.get("expectancy_pct"))}
    candidates=[]; promoted=list(prior.get("promoted_lessons") or []); existing={str(x.get("key")) for x in promoted}
    for key,row in conditions.items():
        samples=int(row.get("samples") or 0); ex=num(row.get("expectancy_pct"))
        if samples>=min_c and abs(ex)>=min_e:
            direction="FAVOUR" if ex>0 else "AVOID / REDUCE"
            status="PROMOTION ELIGIBLE" if samples>=min_p else "TESTING"
            candidates.append({"key":key,"samples":samples,"expectancy_pct":ex,
                "win_rate":num(row.get("win_rate")),"direction":direction,"status":status})
            if samples>=min_p and key not in existing:
                promoted.append({"key":key,"promoted_at":now(),"samples":samples,
                    "expectancy_pct":ex,"direction":direction,"application":"ADVISORY ONLY"})
    candidates.sort(key=lambda x:(x["status"]=="PROMOTION ELIGIBLE",abs(x["expectancy_pct"]),x["samples"]),reverse=True)
    payload={"updated_at":now(),"summary":{"trades_reviewed":len(reviews),"good_process":good,
        "poor_process":poor,"missed_reentries":missed,"candidate_lessons":len(candidates),
        "promoted_lessons":len(promoted),"small_losses":int((diagnostics.get("summary") or {}).get("small_losses") or 0),"diagnosed_trades":int((diagnostics.get("summary") or {}).get("trades_reviewed") or 0)},"book_learning":book_learning,"condition_learning":conditions,
        "rule_candidates":candidates[:100],"promoted_lessons":promoted[-200:],
        "guardrails":{"minimum_samples_for_candidate":min_c,"minimum_samples_for_promotion":min_p,
        "minimum_expectancy_pct":min_e,"auto_modify_live_rules":False},
        "principles":["Judge process separately from outcome.","Keep losses as evidence.",
        "Track missed re-entry separately.","Never rewrite rules automatically.",
        "Require repeated evidence before promotion."]}
    write(OUT,payload); print(json.dumps(payload["summary"],indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
