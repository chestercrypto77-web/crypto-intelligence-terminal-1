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

OUT=DATA/"brain_receipts.json"
def main():
    producer=os.getenv("BRAIN_PRODUCER","").strip()
    consumer=os.getenv("BRAIN_CONSUMER","").strip()
    source=os.getenv("BRAIN_SOURCE","").strip()
    count=int(float(os.getenv("BRAIN_COUNT","0") or 0))
    if not producer or not consumer:return 0
    data=read(OUT,{"receipts":[]})
    rows=data.get("receipts") or []
    rows.append({"recorded_at":now(),"producer":producer,"consumer":consumer,"source":source,"records_consumed":count})
    write(OUT,{"updated_at":now(),"receipts":rows[-20000:]})
    return 0
if __name__=="__main__":raise SystemExit(main())
