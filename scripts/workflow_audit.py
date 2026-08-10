from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
expected=['hourly_signal_recorder.yml','observer_15m.yml','microstructure_5m.yml','nightly_deep_learning.yml']
missing=[x for x in expected if not (ROOT/'.github/workflows'/x).exists()]
setup_missing=[x for x in expected if not (ROOT/'WORKFLOW_SETUP'/x).exists()]
if missing or setup_missing:raise SystemExit(f'Missing workflows: hidden={missing}, setup={setup_missing}')
print(json.dumps({'status':'passed','workflows':expected},indent=2))
