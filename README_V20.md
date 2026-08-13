# V20 — Market Truth & Decision Validation

This release prioritises trustworthy learning over adding more trading features.

Core rules:
1. A symbol is not an identity. Collision-prone assets require canonical IDs.
2. Unvalidated prices cannot create lessons or performance claims.
3. Hard stops are execution-level P0 events and cannot be overridden by committee/signals.
4. Every directional Committee decision is replayed forward at 15m/30m/1h/4h/12h/24h.
5. Large moves automatically become forensic learning cases.
6. Missing observations stay missing. The system must never invent a clean continuous history.
7. Reflection-derived lessons remain sample-gated and require out-of-sample review before promotion.

This is deliberately a brain/safety release, not a front-end expansion.
