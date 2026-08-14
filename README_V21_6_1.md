# V21.6.1 — Bootstrap Completeness Hotfix

This hotfix repairs the V21.6 GitHub Actions failure caused by missing runtime templates.

## Root cause
`bootstrap_runtime.py` requires one template for every JSON file declared in
`config/persistent_data.json`. V21.6 did not include the complete template set,
so a clean GitHub Actions runner stopped at `heartbeat_5m.template.json` before
the observer pipeline started.

## Repair
- Includes `scripts/bootstrap_runtime.py` explicitly.
- Includes the complete `data/templates/` contract required by persistent data.
- Preserves existing runtime JSON and never overwrites it.
- Retains all V21.6 runtime/integration repairs.

## Validation performed
- All Python files compile.
- Workflow YAML parses.
- Fresh-runtime bootstrap creates every declared JSON file.
- Every generated JSON parses successfully.
- A second bootstrap preserves existing runtime data.
- ZIP integrity passes.
