from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from experience_store import split_for
assert split_for("TRADE_X")==split_for("TRADE_X")
policy=json.loads((ROOT/"config/learning_policy.json").read_text())
assert policy["rules"]["single_trade_can_change_live_policy"] is False
assert policy["rules"]["holdout_visible_to_discovery"] is False
assert policy["rules"]["live_rule_auto_promotion"] is False
runner=(ROOT/"scripts/hourly_runner.py").read_text()
for s in ["experience_store.py","reward_engine.py","counterfactual_lab.py","adversarial_learning_challenger.py","curriculum_engine.py","learning_governor.py"]:
    assert s in runner
print("V21 static smoke test PASSED")
