from __future__ import annotations
from datetime import datetime, timezone, timedelta
from pathlib import Path
import copy,json,math,os
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
def now():return datetime.now(timezone.utc).isoformat()
def read(path,default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception:return copy.deepcopy(default)
def write(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    t=path.with_suffix(path.suffix+".tmp")
    t.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8")
    json.loads(t.read_text(encoding="utf-8"));t.replace(path)
def f(v,d=0.0):
    try:
        x=float(v);return x if math.isfinite(x) else d
    except Exception:return d
def parse(v):
    try:
        x=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        if x.tzinfo is None:x=x.replace(tzinfo=timezone.utc)
        return x.astimezone(timezone.utc)
    except Exception:return None

OUT=DATA/"observer_audit.json"
INTERVALS={"5M":5,"15M":15}
LATEST={"5M":"microstructure_latest.json","15M":"observer_latest.json"}
def main():
    mode=str(os.getenv("OBSERVER_AUDIT_MODE") or "ALL").upper()
    audit=read(OUT,{"runs":[],"gaps":[]})
    runs=audit.get("runs") or []
    modes=["5M","15M"] if mode=="ALL" else [mode]
    stamp=now()
    for m in modes:
        if m not in INTERVALS:continue
        payload=read(DATA/LATEST[m],{})
        health=payload.get("health") or {}
        requested=int(health.get("assets_requested") or health.get("assets_requested_count") or 0)
        analysed=int(health.get("assets_analysed") or 0)
        if requested<=0:
            requested=len(read(ROOT/"holdings.json",[]))
        generated=payload.get("generated_at") or payload.get("updated_at")
        coverage=analysed/requested*100 if requested else 0
        runs.append({"mode":m,"audit_time":stamp,"source_generated_at":generated,
                     "requested":requested,"analysed":analysed,"coverage_pct":coverage,
                     "unavailable":health.get("unavailable_assets") or health.get("unavailable") or [],
                     "providers":health.get("providers") or {}})
    # de-duplicate identical run timestamps/modes.
    ded={}
    for r in runs:
        key=(r.get("mode"),r.get("source_generated_at") or r.get("audit_time"))
        ded[key]=r
    runs=sorted(ded.values(),key=lambda x:str(x.get("source_generated_at") or x.get("audit_time")))[-10000:]

    current=datetime.now(timezone.utc);cut=current-timedelta(hours=24)
    summary={};gaps=[]
    for m,minutes in INTERVALS.items():
        rr=[x for x in runs if x.get("mode")==m and (parse(x.get("source_generated_at") or x.get("audit_time")) or datetime.min.replace(tzinfo=timezone.utc))>=cut]
        expected=int(24*60/minutes)
        completed=len(rr)
        avg_cov=sum(f(x.get("coverage_pct")) for x in rr)/completed if completed else 0
        stamps=sorted([parse(x.get("source_generated_at") or x.get("audit_time")) for x in rr if parse(x.get("source_generated_at") or x.get("audit_time"))])
        largest_gap=0
        for a,b in zip(stamps,stamps[1:]):
            gap=(b-a).total_seconds()/60
            largest_gap=max(largest_gap,gap)
            if gap>minutes*2.2:gaps.append({"mode":m,"from":a.isoformat(),"to":b.isoformat(),"gap_minutes":gap})
        schedule_completion=min(100,completed/expected*100) if expected else 0
        summary[m]={"expected_runs_24h":expected,"recorded_runs_24h":completed,
                    "schedule_completion_pct":schedule_completion,"average_asset_coverage_pct":avg_cov,
                    "largest_recorded_gap_minutes":largest_gap,
                    "status":"PASS" if schedule_completion>=90 and avg_cov>=95 else "CAUTION" if schedule_completion>=70 else "FAIL"}
    payload={"updated_at":stamp,"summary":summary,"runs":runs,"gaps":gaps[-500:],
             "note":"Recorded runs prove completed observer outputs. A missing scheduled GitHub run produces a measurable gap rather than being silently assumed successful."}
    write(OUT,payload);print(json.dumps(summary,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
