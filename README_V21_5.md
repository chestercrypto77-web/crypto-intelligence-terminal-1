# V21.5 — Reliability Repair

This release repairs the reliability faults found during the live audit. It is intentionally not a strategy-feature release.

## What changed

### Protected fast loop (5 minutes)
The 5m workflow now does only the work that must happen quickly:
- bootstrap/persistence safety
- 1m/5m microstructure observation
- hard-stop enforcement
- independent completion heartbeat
- lightweight audit/watchdog

Heavy learning, historical mining and committee work were removed from the 5m loop.

### Protected decision loop (15 minutes)
The 15m workflow now performs:
- fresh microstructure check
- 15m market observation
- Risk Guardian
- Move Phase / Adaptive Attention
- Investment Committee / Intelligence Bus
- Portfolio Manager
- hard-stop enforcement
- Active Trade Casefiles
- receipts / audit / health

Deep learning is not run every 15 minutes.

### Faster data collection
The 5m and 15m market fetches are parallelised. A slow or unsupported symbol can no longer serially consume many ten-second timeouts and hold the whole scan hostage.

### Real run proof
`heartbeat_5m.json` and `heartbeat_15m.json` record completed workflow cycles independently. `observer_audit.json` now distinguishes:
- workflow completion frequency
- actual asset analysis coverage

### Trading Desk truth
`runtime_watchdog.json` reconciles Core + Swing + Scalp open positions against Active Trade Casefiles. The Trading Desk now shows an explicit error when its snapshot is stale or its position count differs from the wallets.

### Hard stops now execute
`stop_execution_guard.py` no longer only writes `FORCE_EXIT_REQUIRED`. On fresh, non-quarantined market evidence, a breached paper stop closes the paper position, updates cash/equity, journals the event and records `FORCE_EXIT_EXECUTED`.

### Missing learning engines restored
- `trade_integrity.py` independently validates completed trade records and writes `trade_integrity.json` / `trade_quarantine.json`.
- `winner_failure_school.py` consumes only validated trades and writes `winner_school.json` and `failure_school.json`.

### Learning now fails closed
A completed trade does not enter V21 trusted Experience Store unless Trade Integrity explicitly validates it and the replay contains sufficient chronological evidence. Decision/move experiences are also gated by observer continuity.

### Orchestration simplified
Hourly and nightly workflows no longer rerun the protected 5m/15m observers. Fast observation, decision-making and deep learning now have separate jobs.

## Important infrastructure reality
GitHub Actions scheduled workflows are still a best-effort scheduler, not a guaranteed real-time trading runtime. V21.5 removes avoidable workload/contention, adds proof and catches failures immediately, but the long-term architecture should still move the continuous brain to an always-running service before any real-money execution is considered.

## Validation performed
- Python compile check across the repository
- workflow YAML parse and schedule audit
- persistent-data bootstrap test
- synthetic Trade Integrity valid/quarantine test
- synthetic Winner School validation-only test
- synthetic hard-stop execution test
- fail-closed Experience Store test
- 5m/15m heartbeat and observer-audit test
- runtime wallet/casefile reconciliation test
- ZIP integrity check
