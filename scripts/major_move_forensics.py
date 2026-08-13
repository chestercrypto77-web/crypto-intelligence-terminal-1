from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"
def now(): return datetime.now(timezone.utc).isoformat()
def read(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except:return d
def write(p,x):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(x,indent=2),encoding="utf-8"); json.loads(t.read_text()); t.replace(p)
def main():
    obs=read(DATA/"observer_history.json",[])
    if isinstance(obs,dict): obs=obs.get("records") or obs.get("history") or []
    by={}
    for r in obs:
        try:p=float(r.get("price"))
        except:continue
        if r.get("symbol") and r.get("recorded_at"):by.setdefault(r["symbol"],[]).append(r)
    cases=[]
    for s,rows in by.items():
        rows=sorted(rows,key=lambda x:x.get("recorded_at",""))
        for i,r in enumerate(rows):
            try:p0=float(r["price"])
            except:continue
            for j in range(i+1,min(len(rows),i+20)):
                try:p1=float(rows[j]["price"])
                except:continue
                move=(p1/p0-1)*100
                if abs(move)>=10:
                    cases.append({"symbol":s,"start_time":r.get("recorded_at"),"end_time":rows[j].get("recorded_at"),
                      "start_price":p0,"end_price":p1,"move_pct":move,
                      "pre_move_fingerprint":{"signal":r.get("signal"),"rvol":r.get("rvol"),"rvol_delta":r.get("rvol_delta"),
                        "return_1h":r.get("return_1h"),"return_4h":r.get("return_4h"),"return_24h":r.get("return_24h"),
                        "rsi":r.get("rsi"),"bullish_conditions":r.get("bullish_conditions"),"bearish_conditions":r.get("bearish_conditions")},
                      "questions":["Was ignition detected before the move?","Was the engine on the wrong side?",
                        "When did evidence flip?","Did a hard stop protect capital?","Was a reversal/re-entry opportunity present?"]})
                    break
    write(DATA/"major_move_forensics.json",{"updated_at":now(),"summary":{"cases":len(cases)},"cases":cases[-10000:]})
    print(json.dumps({"cases":len(cases)},indent=2))
if __name__=="__main__": main()
