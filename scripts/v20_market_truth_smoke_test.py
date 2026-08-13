from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from market_truth_guard import validate_record
a=validate_record("COTI",0.012,0.011)
assert a["status"]=="PASS" and a["learning_allowed"]
b=validate_record("BTT",0.002777,0.000000264)
assert b["status"]=="QUARANTINE" and not b["learning_allowed"]
c=validate_record("BEAM",0.0652,0.0089)
assert c["status"]=="QUARANTINE"
print("V20 market-truth smoke test PASSED")
