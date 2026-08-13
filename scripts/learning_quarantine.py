from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"
def read(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except:return d
def main():
    truth=read(DATA/"market_truth.json",{"records":[]})
    bad={x.get("symbol") for x in truth.get("records",[]) if not x.get("learning_allowed",False)}
    out={"quarantined_symbols":sorted(x for x in bad if x),
         "rule":"Any quarantined/review market record is excluded from lesson promotion, strategy calibration and performance claims until independently validated."}
    (DATA/"learning_quarantine.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
    print(json.dumps(out,indent=2))
if __name__=="__main__": main()
