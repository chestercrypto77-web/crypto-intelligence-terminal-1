# V21.6 Brain Runtime & Integration Repair

This release repairs the runtime proof chain exposed by Brain Audit V21.5. It does not promote live lessons or loosen trading risk controls.

## Repairs
- External Attention now always emits a timestamped, auditable output and summarises available external evidence inputs.
- The 15-minute decision loop refreshes External Attention before Investment Committee.
- Investment Committee records explicit External Attention input receipts.
- Active Trade Casefiles records Move Phase input receipts and is part of the 15-minute decision loop.
- Trade Review -> Trade Integrity -> Winner/Failure School now receives a lightweight 15-minute heartbeat so these learning outputs cannot silently remain unexecuted for days.
- Brain receipts verify the External Attention -> Investment Committee and Move Phase -> Active Trade Casefiles links.
- Brain Audit uses honest states: PASS, STALE, MISSING, or NO VERIFIED HEARTBEAT; missing timestamps are never shown as 100000000 minutes old.

## Guardrails retained
- External/news/social evidence never opens a trade by itself.
- Winner/Failure School remains descriptive evidence only.
- V21 Learning Governor remains responsible for promotion; live auto-promotion stays disabled.
- Existing strategy-integrity quarantine remains intact.

## Expected after a successful 15-minute run
Brain Audit should show fresh outputs for External Attention, Trade Integrity, Winner School and Failure School. The two previously unverified links should acquire receipts. External events can legitimately remain zero when no configured source has produced evidence; zero events is different from a missing/stale engine.
