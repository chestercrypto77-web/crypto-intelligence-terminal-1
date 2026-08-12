from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import copy,json,math
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
def now(): return datetime.now(timezone.utc).isoformat()
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
def parse_time(v):
    try:
        s=str(v).replace("Z","+00:00")
        dt=datetime.fromisoformat(s)
        if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:return None
def hours(a,b):
    x=parse_time(a);y=parse_time(b)
    return (y-x).total_seconds()/3600 if x and y else None
def trade_key(r):
    return str(r.get("case_id") or r.get("position_id") or f"{r.get('wallet','')}_{r.get('symbol','')}_{r.get('entry_time','')}")

OUT=DATA/"move_phase_intelligence.json"
def price(row):
    return f(row.get("price"),f(row.get("entry_price"),f(row.get("current_price"))))
def pct(a,b):
    return (b/a-1)*100 if a>0 else 0
def classify(rows):
    rows=sorted(rows,key=lambda x:str(x.get("recorded_at") or x.get("candle_time") or ""))
    last=rows[-1]
    prices=[price(x) for x in rows if price(x)>0]
    if len(prices)<2:return "OBSERVING",["Not enough chronological samples yet."],{}
    p0=prices[max(0,len(prices)-5)];p1=prices[-1]
    move=pct(p0,p1)
    rvol=f(last.get("rvol"));rvd=f(last.get("rvol_delta"))
    r1=f(last.get("return_1h"));r4=f(last.get("return_4h"));r24=f(last.get("return_24h"))
    micro=str(last.get("role_signal") or last.get("microstructure_signal") or "NO ACTION").upper()
    reasons=[]
    # Phase is evidence-based state, not a claim that manipulation is occurring.
    if abs(move)>=5 and rvol>=1.5 and rvd>0.15:
        phase="ACCELERATION";reasons+=["Price is moving rapidly across recent samples.","Relative volume is high and still increasing."]
    elif abs(move)>=8 and (rvd<=0 or "PROFIT PROTECT" in micro):
        phase="EXHAUSTION";reasons+=["The move is already extended.","Participation is no longer accelerating or microstructure is protecting profit."]
    elif abs(r1)>=3 and rvol>=1.2 and ((r1>0 and r4>0) or (r1<0 and r4<0)):
        phase="TRENDING";reasons+=["Short and medium timeframe direction agree.","Participation remains active."]
    elif abs(r1)>=5 and rvol<1.1:
        phase="EXTENSION";reasons+=["Price is extended without equally strong current participation."]
    elif (r1*r4<0) or "REVERS" in micro:
        phase="RESET / REVERSAL";reasons+=["Short timeframe direction conflicts with the prior move or microstructure shows reversal evidence."]
    elif abs(move)>=2 and rvd>0.08:
        phase="IGNITION";reasons+=["Movement and participation are beginning to accelerate."]
    else:
        phase="BASE / OBSERVING";reasons+=["No strong timed move phase is confirmed."]
    return phase,reasons,{"recent_move_pct":move,"rvol":rvol,"rvol_delta":rvd,"return_1h":r1,"return_4h":r4,"return_24h":r24,"microstructure":micro}

def main():
    obs=read(DATA/"observer_history.json",[])
    latest=read(DATA/"observer_latest.json",{"signals":[]}).get("signals") or []
    micro=read(DATA/"microstructure_latest.json",{"signals":[]}).get("signals") or []
    micro_map={str(x.get("symbol") or "").upper():x for x in micro}
    grouped={}
    for row in obs[-20000:]:
        grouped.setdefault(str(row.get("symbol") or "").upper(),[]).append(row)
    for row in latest:
        grouped.setdefault(str(row.get("symbol") or "").upper(),[]).append(row)
    records=[]
    for sym,rows in grouped.items():
        rows=rows[-12:]
        if sym in micro_map:
            merged=dict(rows[-1]) if rows else {}
            merged.update({k:v for k,v in micro_map[sym].items() if v is not None})
            rows=rows[:-1]+[merged] if rows else [merged]
        phase,reasons,metrics=classify(rows)
        records.append({"symbol":sym,"phase":phase,"reasons":reasons,"metrics":metrics,"updated_at":now(),
                        "guardrail":"Momentum phase only. This does not identify or endorse market manipulation."})
    counts={}
    for x in records:counts[x["phase"]]=counts.get(x["phase"],0)+1
    write(OUT,{"updated_at":now(),"summary":{"assets":len(records),"phase_counts":counts},"records":records})
    print(json.dumps({"assets":len(records),"phases":counts},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
