from pathlib import Path
from datetime import datetime, timezone
import json, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]; P=ROOT/'data/microstructure_latest.json'
def parse(v):
    try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
    except:return None
def main():
    try:d=json.loads(P.read_text()); t=parse(d.get('generated_at'))
    except Exception:t=None
    age=(datetime.now(timezone.utc)-t).total_seconds()/60 if t else 1e9
    if age<=8:
        print(json.dumps({'status':'FRESH','age_minutes':age},indent=2)); return 0
    print(json.dumps({'status':'REFRESHING','age_minutes':age},indent=2))
    return subprocess.run([sys.executable,str(ROOT/'scripts/microstructure_observer.py')],cwd=ROOT).returncode
if __name__=='__main__': raise SystemExit(main())
