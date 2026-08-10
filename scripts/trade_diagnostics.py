from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import copy,json,math
from collections import defaultdict

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
OUT=DATA/"trade_diagnostics.json"

def now(): return datetime.now(timezone.utc).isoformat()
def read(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return copy.deepcopy(d)
def write(p,x):
    t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding="utf-8")
    json.loads(t.read_text(encoding="utf-8"))
    t.replace(p)
def f(v,d=0.0):
    try:
        n=float(v); return n if math.isfinite(n) else d
    except Exception:return d

def snapshot(review):
    # Future Core/Swing trades carry entry_snapshot. Observer trades carry observer_evidence.
    raw=review.get("entry_snapshot") or review.get("observer_evidence") or {}
    if not raw:
        raw=(review.get("source_position") or {}).get("entry_snapshot") or (review.get("source_position") or {}).get("observer_evidence") or {}
    return {
        "rvol":f(raw.get("rvol")),
        "rvol_delta":f(raw.get("rvol_delta")),
        "return_1h":f(raw.get("return_1h")),
        "return_4h":f(raw.get("return_4h")),
        "return_12h":f(raw.get("return_12h")),
        "return_24h":f(raw.get("return_24h")),
        "bullish":f(raw.get("bullish"),f(raw.get("bullish_conditions"))),
        "bearish":f(raw.get("bearish"),f(raw.get("bearish_conditions"))),
    }

def diagnose(r):
    ret=f(r.get("realised_return"))
    pnl=f(r.get("realised_pnl"))
    mfe=f(r.get("maximum_favourable_excursion_pct"))
    mae=f(r.get("maximum_adverse_excursion_pct"))
    post=r.get("post_exit") or {}
    best_after=f(post.get("best_directional_move_pct"),f(post.get("directional_move_since_exit_pct")))
    a=r.get("assessment") or {}
    entry=str(a.get("entry_quality") or "UNKNOWN")
    reason=str(r.get("exit_reason") or "Unknown")
    category="VALID OUTCOME"
    severity="LOW"
    action="Keep collecting evidence."

    if ret < 0:
        severity="HIGH" if ret<=-3 else "MEDIUM" if ret<=-1 else "LOW"
        if mfe <= 0.35:
            category="ENTRY NEVER WORKED"
            action="Study entry timing and confirmation. The trade never developed meaningful favourable excursion."
        elif mfe >= 3 and ret < 0:
            category="WINNER GIVEN BACK"
            action="Improve profit protection. The trade was meaningfully profitable before finishing negative."
        elif best_after >= 5:
            category="EXIT / RE-ENTRY FAILURE"
            action="Keep the stop decision separate from the next setup. Re-entry surveillance should react to fresh evidence."
        elif mae <= -2 and mfe < 1:
            category="WEAK ENTRY / FAST ADVERSE MOVE"
            action="Compare the entry with winners for volume, multi-timeframe alignment and market regime."
        elif "STOP" in reason.upper():
            category="CONTROLLED RISK LOSS"
            action="Verify whether the stop protected capital afterwards; do not automatically loosen it."
        else:
            category="SMALL LOSS — REVIEW"
            action="Compare against winning entries before changing any rule."
    elif ret > 0:
        if mfe > max(ret+3, ret*1.7):
            category="PROFIT UNDER-CAPTURED"
            action="Study whether trailing or partial exits could capture more without increasing loss severity."
        else:
            category="WIN — PROCESS REVIEW"
            action="Identify which entry conditions repeat across other winners."

    return {
        "position_id":r.get("position_id"),
        "symbol":r.get("symbol"),
        "wallet":r.get("wallet"),
        "direction":r.get("direction"),
        "return_pct":ret,
        "pnl":pnl,
        "mfe_pct":mfe,
        "mae_pct":mae,
        "post_exit_best_pct":best_after,
        "entry_quality":entry,
        "exit_reason":reason,
        "category":category,
        "severity":severity,
        "next_question":action,
        "entry_features":snapshot(r),
    }

def avg(rows,key):
    vals=[f((x.get("entry_features") or {}).get(key)) for x in rows]
    vals=[v for v in vals if v!=0]
    return sum(vals)/len(vals) if vals else 0.0

def main():
    reviews=read(DATA/"trade_reviews.json",{"reviews":[]}).get("reviews") or []
    rows=[diagnose(r) for r in reviews]
    losses=[x for x in rows if f(x.get("return_pct"))<0]
    wins=[x for x in rows if f(x.get("return_pct"))>0]
    small_losses=[x for x in losses if -3 < f(x.get("return_pct")) < 0]
    categories=defaultdict(int)
    for x in rows: categories[str(x.get("category"))]+=1

    features={}
    for key in ("rvol","rvol_delta","return_1h","return_4h","return_12h","return_24h","bullish","bearish"):
        w=avg(wins,key); l=avg(losses,key)
        features[key]={"winner_avg":w,"loser_avg":l,"difference":w-l}

    payload={
        "updated_at":now(),
        "summary":{
            "trades_reviewed":len(rows),
            "wins":len(wins),
            "losses":len(losses),
            "small_losses":len(small_losses),
            "win_rate_pct":len(wins)/len(rows)*100 if rows else 0.0,
            "small_loss_share_pct":len(small_losses)/len(losses)*100 if losses else 0.0,
            "categories":dict(categories),
        },
        "winner_loser_comparison":{
            "features":features,
            "warning":"Feature comparison is descriptive evidence, not proof of causation. Missing legacy snapshots are excluded.",
        },
        "diagnostics":rows[-20000:],
    }
    write(OUT,payload)
    print(json.dumps(payload["summary"],indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
