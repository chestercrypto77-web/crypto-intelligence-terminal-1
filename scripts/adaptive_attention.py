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

OUT=DATA/"adaptive_attention.json"
def main():
    obs=read(DATA/"observer_latest.json",{"signals":[]}).get("signals") or []
    micro=read(DATA/"microstructure_latest.json",{"signals":[]}).get("signals") or []
    phases=read(DATA/"move_phase_intelligence.json",{"records":[]}).get("records") or []
    ext=read(DATA/"external_attention.json",{"assets":{}})
    open_positions=[]
    for fn in ("observer_wallet.json","core_wallet.json","swing_wallet.json","scalp_wallet.json"):
        for p in read(DATA/fn,{}).get("open_positions") or []:open_positions.append(str(p.get("symbol") or "").upper())
    om={str(x.get("symbol") or "").upper():x for x in obs}
    mm={str(x.get("symbol") or "").upper():x for x in micro}
    pm={str(x.get("symbol") or "").upper():x for x in phases}
    symbols=set(om)|set(mm)|set(pm)|set(open_positions)|set((ext.get("assets") or {}).keys())
    rows=[]
    for sym in symbols:
        o=om.get(sym,{})
        m=mm.get(sym,{})
        p=pm.get(sym,{})
        e=(ext.get("assets") or {}).get(sym,{})
        score=10;reasons=[]
        rvol=f(o.get("rvol"));rvd=f(o.get("rvol_delta"));r4=abs(f(o.get("return_4h")));r24=abs(f(o.get("return_24h")))
        if sym in open_positions:score+=30;reasons.append("Open position")
        if rvol>=2:score+=20;reasons.append("RVOL ≥2")
        elif rvol>=1.3:score+=10;reasons.append("Above-normal RVOL")
        if rvd>=0.15:score+=10;reasons.append("Volume accelerating")
        if r4>=5:score+=15;reasons.append("Large 4H move")
        elif r4>=2:score+=7
        if r24>=15:score+=10;reasons.append("Large 24H move")
        phase=str(p.get("phase") or "")
        if phase in {"IGNITION","ACCELERATION"}:score+=20;reasons.append(phase.title())
        if phase in {"EXTENSION","EXHAUSTION"}:score+=15;reasons.append(phase.title())
        role=str(m.get("role_signal") or "")
        if role!="NO ACTION" and role:score+=8;reasons.append("Active microstructure signal")
        attention=f(e.get("attention_score"))
        if attention>=60:score+=15;reasons.append("External attention")
        level="CRITICAL" if score>=75 else "HIGH" if score>=55 else "ELEVATED" if score>=35 else "BASELINE"
        depth="1m/5m + phase + external + committee" if level in {"CRITICAL","HIGH"} else "1m/5m + phase" if level=="ELEVATED" else "baseline 1m/5m"
        rows.append({"symbol":sym,"priority_score":min(100,score),"attention_level":level,"analysis_depth":depth,
                     "reasons":reasons[:8],"rvol":rvol,"rvol_delta":rvd,"phase":phase or "OBSERVING",
                     "external_attention":attention,"open_position":sym in open_positions})
    rows.sort(key=lambda x:x["priority_score"],reverse=True)
    payload={"updated_at":now(),"summary":{"assets":len(rows),"critical":sum(x["attention_level"]=="CRITICAL" for x in rows),
              "high":sum(x["attention_level"]=="HIGH" for x in rows),"elevated":sum(x["attention_level"]=="ELEVATED" for x in rows)},
             "assets":rows,"principle":"Baseline 5-minute microstructure coverage remains intact. Priority changes analysis depth and escalation, not whether quiet holdings are ignored."}
    write(OUT,payload);print(json.dumps(payload["summary"],indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
